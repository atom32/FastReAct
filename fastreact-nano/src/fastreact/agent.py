"""
FastReAct Nano v2.1.0 - The Body - Executor & Loop Controller
"""

import sys
sys.path.insert(0, 'src')

from pathlib import Path as LibPath

from fastreact.core.config import Config, LLMConfig, ReactConfig, ToolConfig
from fastreact.core.tools import ToolRegistry
from fastreact.core.context import ContextMonitor, FilesystemMemory, FilesystemNode
from fastreact.core.safety import SafetyPolicy, CLIConfirmationCallback
from fastreact.core.messages import Message, MessageQueue
from fastreact.core.react import ReActCore
from fastreact.core.events import EventType
from fastreact.skills import SkillRegistry
from fastreact.skills.loader import SkillLoader
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
    """

    def __init__(
        self,
        config,
        skills_dir: LibPath = None,
    ):
        """
        Initialize agent

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
            # Use CLI confirmation by default
            self._confirmation_callback = CLIConfirmationCallback()

        # Initialize Core (Brain) - minimal dependencies only
        self._core = ReActCore(
            llm=self._llm,
            tools=self._tools,
            max_iterations=self._config.react.max_iterations,
        )

        # Session queues for steering/followup support
        self._session_queues: dict[str, MessageQueue] = {}

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
        Run the agent with event stream

        This is the PREFERRED API. It yields AgentEvent objects,
        providing complete visibility into execution.

        Args:
            query: User query
            skills: List of skills to use (None = auto-select)
            session_id: Session identifier (auto-generated if None)
            history: Optional conversation history (list of message dicts with role/content)

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

                    # 2. Build messages for LLM
                    messages_for_llm = []

                    # Inject system prompt
                    messages_for_llm.append({
                        "role": "system",
                        "content": "You are a helpful assistant with access to tools: read_file, write_file, exec, edit_file.",
                    })

                    # Add conversation history
                    messages_for_llm.extend(messages)

                    # Call LLM
                    try:
                        response = await self._llm.chat(
                            messages_for_llm,
                            tools=self._tools.schemas(),
                        )
                    except Exception as e:
                        yield AgentEvent.error(str(e), session_id)
                        return

                    # Stream thinking content
                    if response.content:
                        yield AgentEvent.think(response.content, session_id)

                    # Check for tool calls
                    has_more_tool_calls = len(response.tool_calls) > 0

                    # Execute tools
                    if has_more_tool_calls:
                        for tool_call in response.tool_calls:
                            # Emit TOOL_CALL event
                            yield AgentEvent.tool_call(
                                tool_call.name,
                                tool_call.params,
                                session_id,
                            )

                            # Execute tool (without safety checks in Core)
                            try:
                                result = await self._tools.execute(
                                    tool_call.name,
                                    tool_call.params,
                                )
                            except Exception as e:
                                result = f"Error: {str(e)}"
                                yield AgentEvent.tool_result(tool_call.name, result, session_id)

                            # Add tool result to history
                            messages.append(Message.tool(
                                name=tool_call.name,
                                result=result,
                                call_id=tool_call.id,
                            ).to_llm_format())

                    else:
                        # No tool calls - add assistant response to history
                        assistant_msg = {
                            "role": "assistant",
                            "content": response.content or "",
                        }
                        messages.append(assistant_msg)

                # Check for follow-up messages before looping
                if not pending_messages.empty():
                    continue

                # No more tool calls and no pending messages
                break

            # Extract final answer
            final_answer = ""
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    final_answer = msg.get("content", "")
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
        Run the agent (simplified API)

        This is a convenience method that aggregates all THINK events
        and returns the final answer.

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
        return await self.run(message, history=history)


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
    import asyncio
    return asyncio.run(ask(query, **kwargs))


__all__ = [
    "Agent",
    "ask",
    "ask_sync",
]
