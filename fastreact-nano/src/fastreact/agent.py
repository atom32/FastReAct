"""
FastReAct Nano v2.0 - Event-Driven Agent

Agent facade over ReActCore event generator.
All communication through AgentEvent stream.
"""

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from fastreact.core.config import Config
from fastreact.core.tools import ToolRegistry
from fastreact.core.messages import Message
from fastreact.core.context import ContextMonitor, FilesystemMemory
from fastreact.core.safety import SafetyPolicy, CLIConfirmationCallback
from fastreact.core.react import ReActCore
from fastreact.core.events import EventType
from fastreact.skills import SkillRegistry
from fastreact.providers.litellm import LiteLLMProvider

from fastreact.tools import ReadFileTool, WriteFileTool, ExecTool, EditFileTool


class Agent:
    """
    Event-driven Agent facade

    Provides a simple interface over ReActCore event generator.
    All execution happens through AgentEvent stream.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        skills_dir: Optional[Path] = None,
    ):
        """
        Initialize agent

        Args:
            config: Agent configuration (default: from environment)
            skills_dir: Directory containing skills (default: ./skills/)
        """
        # Load configuration
        self._config = config or Config.from_env()

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

        # Initialize context monitor
        self._context_monitor = ContextMonitor(
            max_tokens=self._config.react.max_context_tokens,
            warning_threshold=self._config.react.context_warning_threshold,
            max_tool_output_chars=self._config.react.max_tool_output_chars,
        )

        # Initialize filesystem memory (Ghost Map)
        self._filesystem_memory = None
        if self._config.react.enable_filesystem_memory:
            self._filesystem_memory = FilesystemMemory(
                max_tree_depth=self._config.react.max_tree_depth,
                max_files_per_dir=self._config.react.max_files_per_dir,
            )

        # Initialize safety policy (Guardrails)
        self._safety_policy = None
        self._confirmation_callback = None
        if self._config.react.enable_safety:
            self._safety_policy = SafetyPolicy(
                strict_mode=self._config.react.strict_mode,
            )
            # Use CLI confirmation by default
            self._confirmation_callback = CLIConfirmationCallback()

        # Initialize ReAct core (no callbacks)
        self._core = ReActCore(
            llm=self._llm,
            tools=self._tools,
            context_monitor=self._context_monitor,
            filesystem_memory=self._filesystem_memory,
            safety_policy=self._safety_policy,
            confirmation_callback=self._confirmation_callback,
            max_iterations=self._config.react.max_iterations,
        )

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

    async def run_event_stream(
        self,
        query: str,
        skills: Optional[list[str]] = None,
        session_id: Optional[str] = None,
    ):
        """
        Run the agent with event stream

        This is the PREFERRED API. It yields AgentEvent objects,
        providing complete visibility into execution.

        Args:
            query: User query
            skills: List of skills to use (None = auto-select)
            session_id: Session identifier (auto-generated if None)

        Yields:
            AgentEvent objects (SESSION_START, THINK, TOOL_CALL, TOOL_RESULT, ERROR, SESSION_END)

        Example:
            agent = Agent()

            async for event in agent.run_event_stream("What is 2+2?"):
                if event.type == EventType.THINK:
                    print(f"Thinking: {event.content}")
                elif event.type == EventType.TOOL_CALL:
                    print(f"Calling: {event.tool_name}")
        """
        # Generate session_id if not provided
        session_id = session_id or str(uuid.uuid4())

        # Inject skills into query if specified
        enhanced_query = query
        if skills:
            skill_prompts = []
            for skill_name in skills:
                skill_prompt = self._skills.get_prompt(skill_name)
                if skill_prompt:
                    skill_prompts.append(f"[SKILL: {skill_name}]\n{skill_prompt}")

            if skill_prompts:
                enhanced_query = "\n\n".join([query] + skill_prompts)

        # Delegate to core
        async for event in self._core.run_event_stream(enhanced_query, session_id):
            yield event

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
