"""
FastReAct Nano v2.0 - Complete Agent Implementation

Integrates all components into a fully autonomous agent:
- ReActCore: Dual-layer loop engine
- Skills: Progressive disclosure capabilities
- Tools: 4 core tools (Pi's philosophy)
- Config: Centralized configuration
"""

import asyncio
from pathlib import Path
from typing import Optional

from fastreact.core.config import Config
from fastreact.core.tools import ToolRegistry
from fastreact.core.callbacks import CallbackManager
from fastreact.core.messages import Message
from fastreact.core.context import ContextMonitor, FilesystemMemory
from fastreact.core.safety import SafetyPolicy, CLIConfirmationCallback
from fastreact.core.react import ReActCore
from fastreact.skills import SkillRegistry
from fastreact.providers.litellm import LiteLLMProvider

from fastreact.tools import ReadFileTool, WriteFileTool, ExecTool, EditFileTool


class Agent:
    """
    Complete autonomous agent

    Integrates ReActCore with skills, tools, and configuration.
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

        # Initialize callbacks
        self._callbacks = CallbackManager()
        if self._config.react.enable_steering:
            from fastreact.core.callbacks import FileSteeringCallback
            self._callbacks = CallbackManager(
                steering_callback=FileSteeringCallback(
                    self._config.react.steering_file
                ),
            )
        if self._config.react.enable_followup:
            from fastreact.core.callbacks import QueueFollowUpCallback
            self._callbacks = CallbackManager(
                followup_callback=QueueFollowUpCallback(),
            )

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

        # Initialize ReAct core
        self._core = ReActCore(
            llm=self._llm,
            tools=self._tools,
            callbacks=self._callbacks,
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

    async def run(
        self,
        query: str,
        skills: Optional[list[str]] = None,
        stream_callback: Optional[callable] = None,
    ) -> str:
        """
        Run the agent

        Args:
            query: User query
            skills: List of skills to use (None = auto-select)
            stream_callback: Optional callback for streaming

        Returns:
            Agent response
        """
        # Build messages
        messages = [Message.user(query)]

        # Inject skill prompts if specified
        if skills:
            for skill_name in skills:
                skill_prompt = self._skills.get_prompt(skill_name)
                if skill_prompt:
                    messages.append(Message.user(
                        f"[SKILL: {skill_name}]\n{skill_prompt}"
                    ))

        # Run ReAct loop
        response = await self._core.run(
            messages=messages,
            stream_callback=stream_callback,
        )

        return response

    async def chat(
        self,
        message: str,
        history: Optional[list[Message]] = None,
    ) -> str:
        """
        Simple chat interface

        Args:
            message: User message
            history: Conversation history (optional)

        Returns:
            Agent response
        """
        messages = history or []
        messages.append(Message.user(message))

        return await self._core.run(messages)

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


async def main():
    """Example usage"""
    # Create agent
    agent = Agent()

    # Run query
    response = await agent.run("Read the file README.md")

    print(response)


# Convenience function
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
