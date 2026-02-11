"""
FastReAct Nano v2.1 - Brain-Body Architecture

Agent = The Body (Executor)
Core = The Brain (Intent Generator)

The Agent layer handles:
- Loop control
- Tool execution
- Safety checks
- Context management
- Filesystem memory
"""

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from fastreact.core.config import Config
from fastreact.core.tools import ToolRegistry, ValidationError
from fastreact.core.messages import Message, MessageQueue
from fastreact.core.context import ContextMonitor, FilesystemMemory
from fastreact.core.safety import SafetyPolicy, CLIConfirmationCallback
from fastreact.core.react import ReActCore
from fastreact.core.events import EventType
from fastreact.skills import SkillRegistry
from fastreact.providers.litellm import LiteLLMProvider

from fastreact.tools import ReadFileTool, WriteFileTool, ExecTool, EditFileTool


class Agent:
    """
    The Body - Executor & Loop Controller

    Wraps ReActCore (Brain) and handles all execution logic:
    - Loop control (dual-layer loops for steering/followup)
    - Tool execution
    - Safety checks
    - Context monitoring
    - Filesystem memory

    Architecture:
        User Query → Agent.run_event_stream()
                        ↓
        ┌──────────────────────────────────┐
        │ Loop Control (while True)       │
        │                                  │
        │  1. Brain: run_step_stream()    │
        │     → THINK events              │
        │     → TOOL_CALL events          │
        │     → STEP_END event            │
        │                                  │
        │  2. Body: Execute Tools         │
        │     → Safety check              │
        │     → Tool execution            │
        │     → Context truncate          │
        │     → TOOL_RESULT events        │
        │                                  │
        │  3. Check Steering/Follow-up    │
        └──────────────────────────────────┘
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        skills_dir: Optional[Path] = None,
    ):
        """
        Initialize Agent (The Body)

        Args:
            config: Agent configuration (default: from config file or environment)
            skills_dir: Directory containing skills (default: ./skills/)
        """
        # Load configuration
        self._config = config or Config.load()

        # Initialize LLM provider
        self._llm = LiteLLMProvider(
            model=self._config.llm.model,
            api_base=self._config.llm.api_base,
            api_key=self._config.llm.api_key,
            temperature=self._config.llm.temperature,
            max_tokens=self._config.llm.max_tokens,
        )

        # Initialize tools
        self._tools = ToolRegistry()
        self._setup_tools()

        # Initialize skills
        self._skills = SkillRegistry()
        if skills_dir:
            from fastreact.skills import SkillLoader
            loader = SkillLoader(skills_dir=skills_dir)
            self._skills = SkillRegistry(loader=loader)

        # Initialize context monitor (Body layer)
        self._context_monitor = ContextMonitor(
            max_tokens=self._config.react.max_context_tokens,
            warning_threshold=self._config.react.context_warning_threshold,
            max_tool_output_chars=self._config.react.max_tool_output_chars,
        )

        # Initialize filesystem memory (Body layer)
        self._filesystem_memory = None
        if self._config.react.enable_filesystem_memory:
            self._filesystem_memory = FilesystemMemory(
                max_tree_depth=self._config.react.max_tree_depth,
                max_files_per_dir=self._config.react.max_files_per_dir,
            )

        # Initialize safety policy (Body layer)
        self._safety_policy = None
        self._confirmation_callback = None
        if self._config.react.enable_safety:
            self._safety_policy = SafetyPolicy(
                strict_mode=self._config.react.strict_mode,
            )
            self._confirmation_callback = CLIConfirmationCallback()

        # Initialize Core (Brain) - minimal dependencies
        self._core = ReActCore(
            llm=self._llm,
            tools=self._tools,
            max_iterations=self._config.react.max_iterations,
        )

        # Session queues for steering/followup support
        self._session_queues: dict[str, MessageQueue] = {}

    def _setup_tools(self):
        """Setup core tools with config"""
        tool_config = self._config.tools

        self._tools.register(ReadFileTool(max_size=tool_config.max_file_size))
        self._tools.register(WriteFileTool(
            max_size=tool_config.max_file_size,
            protected_paths=tool_config.protected_paths,
        ))
        self._tools.register(ExecTool(
            timeout=tool_config.exec_timeout,
            working_dir=tool_config.working_dir,
        ))
        self._tools.register(EditFileTool(max_size=tool_config.max_file_size))

    def inject_message(self, session_id: str, message: Message):
        """
        Inject message into active session

        Args:
            session_id: Target session
            message: Message to inject (steering/followup)

        Raises:
            ValueError: If session not active
        """
        if session_id not in self._session_queues:
            raise ValueError(f"Session not active: {session_id}")

        self._session_queues[session_id].push(message)

    async def run_event_stream(
        self,
        query: str,
        skills: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        history: Optional[list[dict]] = None,
    ) -> AsyncIterator["AgentEvent"]:
        """
        Run agent with event stream (Brain-Body Loop)

        This is PREFERRED API. It yields AgentEvent objects,
        providing complete visibility into execution.

        Args:
            query: User query
            skills: List of skills to use (None = auto-select)
            session_id: Session identifier (auto-generated if None)
            history: Optional conversation history (list of message dicts)

        Yields:
            AgentEvent objects (SESSION_START, THINK, TOOL_CALL, TOOL_RESULT, ERROR, SESSION_END)

        Example:
            agent = Agent()

            async for event in agent.run_event_stream("What is 2+2?"):
                if event.type == EventType.THINK:
                    print(f"Thinking: {event.content}")
                elif event.type == EventType.TOOL_CALL:
                    print(f"Calling: {event.tool_name}")

            # With history (multi-turn conversation)
            history = [
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "4"},
            ]
            async for event in agent.run_event_stream("What about 3+3?", history=history):
                ...
        """
        from fastreact.core.events import AgentEvent, EventType

        # Generate session_id if not provided
        session_id = session_id or str(uuid.uuid4())

        # Create session queue for steering/followup
        self._session_queues[session_id] = MessageQueue()

        try:
            # Emit SESSION_START
            yield AgentEvent.session_start(query, session_id)

            # Initialize messages with history
            messages = list(history or [])

            # Add current user message to history
            messages.append(Message.user(query).to_llm_format())

            # === Outer loop: Process follow-up messages ===
            while True:
                has_more_tool_calls = True

                # === Inner loop: Process tools ===
                while has_more_tool_calls:
                    # 1. Brain: Ask LLM for reasoning
                    pending_messages = self._session_queues.get(session_id, MessageQueue())

                    # Process pending messages (steering/followup)
                    if not pending_messages:
                        for msg in pending_messages.drain():
                            messages.append(msg.to_llm_format())
                            # Emit steering event for visibility
                            if msg.role in ("steering", "followup"):
                                yield AgentEvent.think(
                                    f"[{msg.role.upper()}] {msg.content}",
                                    session_id,
                                    metadata={"source": msg.metadata.get("source", "unknown")},
                                )

                    # Call Brain (Core) for reasoning step
                    step_end = None
                    async for event in self._core.run_step_stream(
                        messages=messages,
                        session_id=session_id,
                    ):
                        # Forward THINK events
                        if event.type == EventType.THINK:
                            yield event

                        # Forward TOOL_CALL events (intent only)
                        elif event.type == EventType.TOOL_CALL:
                            yield event

                        # Capture STEP_END to handle tool execution
                        elif event.type == EventType.STEP_END:
                            step_end = event
                            break

                    # 2. Body: Execute tools (if any)
                    if step_end and step_end.metadata.get("has_tool_calls"):
                        # Get tool calls from the last LLM response
                        # We need to extract them from messages
                        last_msg = messages[-1] if messages else {}
                        tool_calls = last_msg.get("tool_calls", [])

                        for tool_call in tool_calls:
                            tool_name = tool_call.get("function", {}).get("name", "")
                            tool_params = tool_call.get("function", {}).get("arguments", {})

                            # Emit TOOL_CALL event (if not already emitted by Core)
                            yield AgentEvent.tool_call(tool_name, tool_params, session_id)

                            # Safety check
                            if self._safety_policy:
                                decision = self._safety_policy.check_tool_call(
                                    tool_name=tool_name,
                                    tool_params=tool_params,
                                )
                                if decision.level == "dangerous" and not decision.allowed:
                                    result = f"[SAFETY_BLOCKED] {decision.reason}"
                                    yield AgentEvent.tool_result(tool_name, result, session_id)
                                    messages.append(Message.tool(
                                        name=tool_name,
                                        result=result,
                                        call_id=tool_call.get("id", ""),
                                    ).to_llm_format())
                                    continue

                            # Execute tool
                            try:
                                result = await self._tools.execute(tool_name, tool_params)

                                # Context truncate if needed
                                if self._context_monitor:
                                    result = self._context_monitor.truncate_tool_output(result)

                            except Exception as e:
                                result = f"[ERROR] {str(e)}"

                            # Emit TOOL_RESULT event
                            yield AgentEvent.tool_result(tool_name, result, session_id)

                            # Add tool result to history
                            messages.append(Message.tool(
                                name=tool_name,
                                result=result,
                                call_id=tool_call.get("id", ""),
                            ).to_llm_format())
                    else:
                        # No tool calls - exit inner loop
                        has_more_tool_calls = False

                # Check for follow-up messages before looping
                if not self._session_queues.get(session_id, MessageQueue()):
                    continue

                # No more tool calls and no pending messages
                break

            # Extract final answer from last assistant message
            final_answer = ""
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if content and not content.startswith("["):
                        final_answer = content
                        break

            # Emit SESSION_END
            yield AgentEvent.session_end(session_id, final_answer)

        except Exception as e:
            yield AgentEvent.error(str(e), session_id)

    async def run(
        self,
        query: str,
        skills: Optional[list[str]] = None,
    ) -> str:
        """
        Run agent (simplified API)

        This is convenience method that aggregates all THINK events
        and returns final answer.

        Args:
            query: User query
            skills: List of skills to use (None = auto-select)

        Returns:
            Agent's final response
        """
        final_content = []

        async for event in self.run_event_stream(query, skills=skills):
            if event.type == EventType.THINK:
                final_content.append(event.content)
            elif event.type == EventType.SESSION_END:
                return event.content or "".join(final_content)

        return "".join(final_content)

    async def chat(
        self,
        message: str,
        history: Optional[list[Message]] = None,
    ) -> str:
        """
        Simple chat interface (legacy compatibility)

        Args:
            message: User message
            history: Conversation history (optional)

        Returns:
            Agent response
        """
        return await self.run(message)

    def list_skills(self) -> list[str]:
        """Return list of available skill names"""
        return self._skills.list_skills()

    @property
    def llm(self):
        """Expose LLM provider for REPL compatibility"""
        return self._llm


# Convenience functions
async def ask(
    query: str,
    skills: Optional[list[str]] = None,
    config: Optional[Config] = None,
) -> str:
    """
    Quick async query

    Args:
        query: User query
        skills: Skills to use (None = auto-select)
        config: Optional config

    Returns:
        Agent response
    """
    agent = Agent(config=config)
    return await agent.run(query, skills=skills)


def ask_sync(
    query: str,
    **kwargs,
) -> str:
    """
    Quick synchronous query

    Args:
        query: User query
        **kwargs: Additional arguments passed to Agent

    Returns:
        Agent response
    """
    return asyncio.run(ask(query, **kwargs))


__all__ = [
    "Agent",
    "ask",
    "ask_sync",
]
