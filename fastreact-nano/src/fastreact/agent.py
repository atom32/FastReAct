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
        llm_config = self._config.llm
        self._llm = LiteLLMProvider(
            model=llm_config.model,
            api_base=llm_config.api_base,
            api_key=llm_config.api_key,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
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
        Run the agent with event stream (Brain-Body Loop)

        This is the PREFERRED API. It yields AgentEvent objects,
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
        pending_messages = self._session_queues[session_id]

        try:
            # Emit SESSION_START
            yield AgentEvent.session_start(query, session_id)

            # Initialize messages with history
            messages = list(history or [])

            # Inject skills into query if specified
            enhanced_query = query
            if skills:
                skill_prompts = []
                for skill_name in skills:
                    skill_prompt = self._skills.get_prompt(skill_name)
                    if skill_prompt:
                        skill_prompts.append(f"[SKILL: {skill_name}]\\n{skill_prompt}")

                if skill_prompts:
                    enhanced_query = "\\n\\n".join([query] + skill_prompts)

            # Add current query to messages
            messages.append(Message.user(enhanced_query).to_llm_format())

            # Build system prompt with Ghost Map
            system_prompt = None
            if self._filesystem_memory:
                memory_injection = self._filesystem_memory.get_prompt_injection()
                if memory_injection:
                    from fastreact.core.prompts import SYSTEM_PROMPT_CORE
                    system_prompt = f"{SYSTEM_PROMPT_CORE}\\n\\n{memory_injection}"

            final_answer = ""

            # === Outer loop: Process follow-up messages ===
            iteration = 0
            while iteration < self._core._max_iterations:
                iteration += 1
                has_more_tool_calls = True

                # === Inner loop: Process tools ===
                while has_more_tool_calls or pending_messages:
                    # 1. Process pending messages (steering/followup)
                    if pending_messages:
                        for msg in pending_messages.drain():
                            messages.append(msg.to_llm_format())
                            # Emit steering event for visibility
                            if msg.role in ("steering", "followup"):
                                yield AgentEvent.think(
                                    f"[{msg.role.upper()}] {msg.content}",
                                    session_id,
                                    metadata={"source": msg.metadata.get("source", "unknown")},
                                )

                    # 2. Brain: Think & Intent
                    step_response = None
                    tool_calls = []

                    async for event in self._core.run_step_stream(messages, session_id, system_prompt):
                        # Forward THINK events
                        if event.type == EventType.THINK:
                            yield event

                        # Collect TOOL_CALL intents
                        elif event.type == EventType.TOOL_CALL:
                            tool_calls.append(event)
                            yield event  # Forward for visibility

                        # Track step completion
                        elif event.type == EventType.STEP_END:
                            step_response = event.content

                        # Forward ERROR events
                        elif event.type == EventType.ERROR:
                            yield event
                            return

                    has_more_tool_calls = len(tool_calls) > 0

                    # 3. Body: Execute tools
                    if has_more_tool_calls:
                        # Add assistant message with tool_calls to history
                        assistant_msg = {
                            "role": "assistant",
                            "content": step_response or "",
                            "tool_calls": [
                                {
                                    "id": f"call_{i}",
                                    "type": "function",
                                    "function": {
                                        "name": call.tool_name,
                                        "arguments": str(call.tool_args),
                                    },
                                }
                                for i, call in enumerate(tool_calls)
                            ],
                        }
                        messages.append(assistant_msg)

                        for call_event in tool_calls:
                            tool_name = call_event.tool_name
                            tool_args = call_event.tool_args

                            try:
                                # A. Safety check
                                if self._safety_policy:
                                    decision = self._safety_policy.check(
                                        tool_name,
                                        tool_args,
                                    )

                                    # Log decision
                                    self._safety_policy.log(
                                        tool_name,
                                        tool_args,
                                        decision,
                                    )

                                    # Check if forbidden
                                    if not decision.should_allow:
                                        error_result = (
                                            f"[FORBIDDEN] {decision.reason}\\n"
                                            f"Pattern: {decision.pattern_matched}"
                                        )
                                        tool_msg = Message.tool(
                                            name=tool_name,
                                            result=error_result,
                                            call_id=f"call_{len(tool_calls)}",
                                        )
                                        messages.append(tool_msg.to_llm_format())

                                        yield AgentEvent.tool_result(
                                            tool_name,
                                            error_result,
                                            session_id,
                                        )
                                        continue

                                    # Check if needs confirmation
                                    if decision.should_ask and self._confirmation_callback:
                                        yield AgentEvent.ask_user(
                                            decision.reason,
                                            tool_name,
                                            tool_args,
                                            session_id,
                                        )

                                        user_approved = await self._confirmation_callback.request_confirmation(
                                            tool_name,
                                            tool_args,
                                            decision.reason,
                                        )

                                        self._safety_policy.log(
                                            tool_name,
                                            tool_args,
                                            decision,
                                            user_approved=user_approved,
                                        )

                                        if not user_approved:
                                            deny_result = f"[DENIED] {decision.reason}"
                                            tool_msg = Message.tool(
                                                name=tool_name,
                                                result=deny_result,
                                                call_id=f"call_{len(tool_calls)}",
                                            )
                                            messages.append(tool_msg.to_llm_format())

                                            yield AgentEvent.tool_result(
                                                tool_name,
                                                deny_result,
                                                session_id,
                                            )
                                            continue

                                # B. Execute tool
                                result = await self._tools.execute(
                                    tool_name,
                                    tool_args,
                                )

                                # C. Update Ghost Map
                                if self._filesystem_memory:
                                    self._filesystem_memory.update_from_tool_call(
                                        tool_name,
                                        tool_args,
                                        result,
                                    )

                                # D. Apply context truncation
                                safe_result = self._context_monitor.truncate_tool_output(
                                    result,
                                    tool_name=tool_name,
                                )

                                # Add tool result message
                                tool_msg = Message.tool(
                                    name=tool_name,
                                    result=safe_result,
                                    call_id=f"call_{len(tool_calls)}",
                                )
                                messages.append(tool_msg.to_llm_format())

                                # Emit TOOL_RESULT event
                                yield AgentEvent.tool_result(
                                    tool_name,
                                    safe_result,
                                    session_id,
                                )

                            except ValidationError as e:
                                error_msg = f"Validation error: {e}"
                                safe_error = self._context_monitor.truncate_tool_output(
                                    error_msg,
                                    tool_name=tool_name,
                                )
                                tool_msg = Message.tool(
                                    name=tool_name,
                                    result=safe_error,
                                    call_id=f"call_{len(tool_calls)}",
                                )
                                messages.append(tool_msg.to_llm_format())

                                yield AgentEvent.tool_result(
                                    tool_name,
                                    safe_error,
                                    session_id,
                                )

                            except Exception as e:
                                error_msg = f"Tool execution error: {str(e)}"
                                safe_error = self._context_monitor.truncate_tool_output(
                                    error_msg,
                                    tool_name=tool_name,
                                )
                                tool_msg = Message.tool(
                                    name=tool_name,
                                    result=safe_error,
                                    call_id=f"call_{len(tool_calls)}",
                                )
                                messages.append(tool_msg.to_llm_format())

                                yield AgentEvent.tool_result(
                                    tool_name,
                                    safe_error,
                                    session_id,
                                )
                    else:
                        # No tool calls - add assistant response to history
                        assistant_msg = {
                            "role": "assistant",
                            "content": step_response or "",
                        }
                        messages.append(assistant_msg)
                        final_answer = step_response or ""

                # Check one more time for follow-up before exiting
                if pending_messages:
                    continue

                # No more tool calls and no pending messages
                break

            # Emit SESSION_END
            yield AgentEvent.session_end(session_id, final_answer)

        except Exception as e:
            yield AgentEvent.error(str(e), session_id)

        finally:
            # Cleanup session queue
            if session_id in self._session_queues:
                del self._session_queues[session_id]

    async def run(
        self,
        query: str,
        skills: Optional[list[str]] = None,
    ) -> str:
        """
        Run the agent (simplified API)

        This is a convenience method that aggregates all THINK events
        and returns the final answer. Use run_event_stream() for
        complete visibility.

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
                # Return final answer from SESSION_END
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
        """List available skills"""
        return self._skills.list_available()

    def list_tools(self) -> list[str]:
        """List available tools"""
        return self._tools.list_all()

    @property
    def config(self) -> Config:
        """Get agent configuration"""
        return self._config

    @property
    def skills(self) -> SkillRegistry:
        """Get skill registry"""
        return self._skills

    @property
    def tools(self) -> ToolRegistry:
        """Get tool registry"""
        return self._tools


async def ask(
    query: str,
    skills: Optional[list[str]] = None,
    config: Optional[Config] = None,
) -> str:
    """
    Quick async query

    Args:
        query: User query
        skills: Skills to use
        config: Optional config

    Returns:
        Agent response
    """
    agent = Agent(config=config)
    return await agent.run(query, skills=skills)


def ask_sync(query: str, **kwargs) -> str:
    """
    Quick synchronous query

    Args:
        query: User query
        **kwargs: Passed to ask()

    Returns:
        Agent response
    """
    return asyncio.run(ask(query, **kwargs))


__all__ = [
    "Agent",
    "ask",
    "ask_sync",
]
