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
import json
import uuid
from pathlib import Path
from typing import Optional, AsyncIterator

from fastreact.core.config import Config
from fastreact.core.tools import ToolRegistry, ValidationError
from fastreact.core.messages import Message, MessageQueue
from fastreact.core.context import ContextMonitor, FilesystemMemory
from fastreact.core.safety import SafetyPolicy, SafetyLevel, CLIConfirmationCallback
from fastreact.core.react import ReActCore
from fastreact.core.events import EventType
from fastreact.core.multitenant import MultiTenantManager, UserContext
from fastreact.skills import SkillRegistry
from fastreact.providers.litellm import LiteLLMProvider
from fastreact.mcp.manager import MCPToolManager
from fastreact.mcp.multitenant_manager import MultiTenantMCPManager
from fastreact.mcp.discovery import MCPToolDiscovery

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
        multitenant: bool = False,
        base_workspace: Optional[Path] = None,
    ):
        """
        Initialize Agent (The Body)

        Args:
            config: Agent configuration (default: from config file or environment)
            skills_dir: Directory containing skills (default: ./skills/)
            multitenant: Enable multi-tenant mode (default: False)
            base_workspace: Base directory for user workspaces (default: ./workspace)
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

        # Initialize MCP tool manager
        self._mcp_manager = None  # Single-tenant mode
        self._multitenant_mcp_manager = None  # Multi-tenant mode

        # Initialize MCP tool discovery service
        self._mcp_discovery = MCPToolDiscovery()

        # Setup tools (core + MCP)
        self._setup_tools()

        # Initialize multi-tenant manager
        self._multitenant_enabled = multitenant
        self._multitenant = None
        if multitenant:
            workspace_path = base_workspace or Path.cwd() / "workspace"
            self._multitenant = MultiTenantManager(workspace_path)

        # Initialize skills (global skills, not user-specific)
        from fastreact.skills import SkillLoader, SkillRegistry
        self._skills = SkillRegistry()
        # Always try to load skills from configured locations
        try:
            # Use global skills directory from config
            global_skills_dir = self._config.paths.global_skills_dir
            if global_skills_dir.exists():
                loader = SkillLoader(skills_dir=global_skills_dir)
                self._skills = SkillRegistry(loader=loader)
                # Load all global skills
                for skill_name in loader.list_skills():
                    skill = loader.load_skill(skill_name)
                    if skill:
                        self._skills.add_skill(skill_name, skill)

            # Load user skills (if configured)
            user_skills_dir = self._config.paths.user_skills_dir
            if user_skills_dir and user_skills_dir.exists():
                user_loader = SkillLoader(skills_dir=user_skills_dir)

                # Add user skills to existing registry
                for skill_name in user_loader.list_skills():
                    skill = user_loader.load_skill(skill_name)
                    if skill:
                        self._skills.add_skill(skill_name, skill)

            # Fallback to custom skills directory parameter
            elif skills_dir:
                loader = SkillLoader(skills_dir=skills_dir)
                self._skills = SkillRegistry(loader=loader)
                for skill_name in loader.list_skills():
                    skill = loader.load_skill(skill_name)
                    if skill:
                        self._skills.add_skill(skill_name, skill)

            # Final fallback to legacy location
            else:
                legacy_skills_dir = Path.cwd() / "skills"
                if legacy_skills_dir.exists():
                    loader = SkillLoader(skills_dir=legacy_skills_dir)
                    self._skills = SkillRegistry(loader=loader)
                    for skill_name in loader.list_skills():
                        skill = loader.load_skill(skill_name)
                        if skill:
                            self._skills.add_skill(skill_name, skill)
        except Exception as e:
            # Skills not available
            pass

        # Skills selection configuration
        self._auto_select_skills = True  # Auto-select skills when not specified
        self._max_auto_skills = 3  # Max skills to auto-select

        # Initialize context monitor (Body layer)
        self._context_monitor = ContextMonitor(
            max_tokens=self._config.react.max_context_tokens,
            warning_threshold=self._config.react.context_warning_threshold,
            max_tool_output_chars=self._config.react.max_tool_output_chars,
            model=self._config.react.tiktoken_model,
            use_tiktoken=self._config.react.use_tiktoken,
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

        # Session management (NEW: AgentSession lifecycle)
        self._sessions: dict[str, "AgentSession"] = {}

    def _select_skills_auto(
        self,
        query: str,
        max_skills: int = 3,
        user_context: Optional[UserContext] = None,
    ) -> list[str]:
        """
        Automatically select relevant skills based on query

        Args:
            query: User's query
            max_skills: Maximum number of skills to select
            user_context: Optional user context for user-specific skills

        Returns:
            List of selected skill names
        """
        import re
        from fastreact.skills import Skill, SkillLoader, SkillRegistry

        # Get all available skills (global + user-specific)
        all_skills = []

        # Global skills
        try:
            for skill_name in self._skills.list_available():
                skill = self._skills.get(skill_name)
                if skill:
                    all_skills.append(skill)
        except Exception:
            pass

        # User-specific skills (higher priority)
        if user_context and user_context.skills_dir.exists():
            try:
                user_loader = SkillLoader(skills_dir=user_context.skills_dir)
                user_skills = SkillRegistry(loader=user_loader)
                for skill_name in user_skills.list_available():
                    skill = user_skills.get(skill_name)
                    if skill:
                        all_skills.append(skill)
            except Exception:
                pass

        if not all_skills:
            return []

        # Extract keywords from query (simple tokenization)
        # For Chinese, use character-level matching as fallback
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))

        # Enhanced Chinese tokenization: extract bigrams for better matching
        # For "机器学习", generate: ["机器", "学习", "机器学习"]
        chinese_bigrams = set()
        for char in query_lower:
            if '\u4e00' <= char <= '\u9fff':  # Chinese character range
                # Extract consecutive Chinese characters as n-grams
                chinese_chars = [c for c in query_lower if '\u4e00' <= c <= '\u9fff']
                for i in range(len(chinese_chars)):
                    # Unigrams
                    chinese_bigrams.add(chinese_chars[i])
                    # Bigrams
                    if i < len(chinese_chars) - 1:
                        chinese_bigrams.add(chinese_chars[i] + chinese_chars[i+1])
                    # Trigrams
                    if i < len(chinese_chars) - 2:
                        chinese_bigrams.add(chinese_chars[i] + chinese_chars[i+1] + chinese_chars[i+2])
                break

        # Combine English words and Chinese n-grams
        query_words = query_words | chinese_bigrams

        # Score each skill
        skill_scores = []

        for skill in all_skills:
            score = 0

            # Match in name (high weight)
            if skill.name.lower() in query_lower:
                score += 10

            # Match in description
            desc_lower = skill.description.lower()
            desc_words = set(re.findall(r'\w+', desc_lower))

            # Chinese n-grams for description (better matching)
            desc_chinese = set()
            for char in desc_lower:
                if '\u4e00' <= char <= '\u9fff':
                    chinese_chars = [c for c in desc_lower if '\u4e00' <= c <= '\u9fff']
                    for i in range(len(chinese_chars)):
                        desc_chinese.add(chinese_chars[i])
                        if i < len(chinese_chars) - 1:
                            desc_chinese.add(chinese_chars[i] + chinese_chars[i+1])
                        if i < len(chinese_chars) - 2:
                            desc_chinese.add(chinese_chars[i] + chinese_chars[i+1] + chinese_chars[i+2])
                    break

            desc_words_enhanced = desc_words | desc_chinese

            # Keyword overlap (enhanced with Chinese n-grams)
            overlap = query_words & desc_words_enhanced
            score += len(overlap) * 2

            # Tag matching (lower weight to reduce over-matching)
            for tag in skill.metadata.tags:
                if tag.lower() in query_lower:
                    score += 2  # Reduced from 5 to 2

            skill_scores.append((skill.name, score))

        # Sort by score and return top-k
        skill_scores.sort(key=lambda x: x[1], reverse=True)
        selected = [name for name, score in skill_scores[:max_skills] if score > 0]

        return selected

    def _build_system_prompt_with_skills(self, skills: Optional[list[str]]) -> tuple[str, str]:
        """
        Build system prompt with skills and tools injected

        Args:
            skills: List of skill names to inject

        Returns:
            Tuple of (base_prompt, skills_content) where:
            - base_prompt: Constant base system prompt (cacheable)
            - skills_content: Variable skills and tools content (injected as message)
        """
        from fastreact.core.prompts import get_system_prompt

        # Get base system prompt (constant, cacheable)
        base_prompt = get_system_prompt("core")

        # === Build Variable Content Section (skills + tools) ===
        # This will be injected as a separate system message to preserve cache
        variable_content = ""

        # === Add Available Tools Section ===
        tools_section = "\n\n# Available Tools\nYou have access to the following tools:\n\n"

        # Get all tool names and separate by type (builtin vs MCP)
        builtin_tools = []
        mcp_tools = []

        for tool_name in self._tools.list_all():
            tool = self._tools.get(tool_name)
            if tool:
                # Check if this is an MCP tool by instance type
                from fastreact.mcp.manager import MCPToolWrapper
                if isinstance(tool, MCPToolWrapper):
                    mcp_tools.append(tool_name)
                else:
                    builtin_tools.append(tool_name)

        # Add built-in tools
        if builtin_tools:
            tools_section += "## Built-in Tools\n"
            for tool_name in builtin_tools:
                # Get description from schema
                for schema in self._tools.schemas():
                    if schema["function"]["name"] == tool_name:
                        desc = schema["function"].get("description", "No description")
                        tools_section += f"- `{tool_name}`: {desc}\n"
                        break
                else:
                    # Schema not found, add without description
                    tools_section += f"- `{tool_name}`: Tool\n"

        # Add MCP tools
        if mcp_tools:
            tools_section += "\n## MCP Tools (Model Context Protocol)\n"
            for tool_name in mcp_tools:
                # Get description from schema
                for schema in self._tools.schemas():
                    if schema["function"]["name"] == tool_name:
                        desc = schema["function"].get("description", "No description")
                        tools_section += f"- `{tool_name}`: {desc}\n"
                        break

        tools_section += "\nUse these tools to complete the user's request."
        variable_content += tools_section

        # === Add Available Skills Section (always show available skills) ===
        skills_list_section = "\n\n# Available Skills\nThese skills are available:\n\n"

        # Get all available skills
        all_skill_names = self._skills.list_available()
        if all_skill_names:
            for skill_name in all_skill_names:
                skill = self._skills.get(skill_name)
                if skill:
                    skills_list_section += f"## {skill.name}\n"
                    skills_list_section += f"{skill.description}\n"
                    if skill.metadata.tags:
                        skills_list_section += f"Tags: {', '.join(skill.metadata.tags)}\n"
                    skills_list_section += "\n"
        else:
            skills_list_section += "No skills currently available.\n\n"

        variable_content += skills_list_section

        # === Add Skills Section (if specific skills selected) ===
        skills_section = ""
        if skills:
            # Load skill descriptions
            skill_descriptions = []
            mcp_servers_for_skills = set()

            for skill_name in skills:
                skill = self._skills.get(skill_name)
                if skill:
                    # Format skill info
                    skill_info = f"## {skill.name}\n{skill.description}"
                    if skill.metadata.tags:
                        skill_info += f"\nTags: {', '.join(skill.metadata.tags)}"

                    # Add recommended tools if any
                    if skill.metadata.recommended_tools:
                        skill_info += f"\nRecommended Tools: {', '.join(['`' + t + '`' for t in skill.metadata.recommended_tools])}"

                    skill_descriptions.append(skill_info)

                    # Collect MCP servers required by this skill
                    if skill.metadata.mcp_servers:
                        mcp_servers_for_skills.update(skill.metadata.mcp_servers)

            # Inject skills into variable content
            if skill_descriptions:
                skills_section = "\n\n# Active Skills\nThese skills are available for this task:\n\n"
                skills_section += "\n\n".join(skill_descriptions)
                skills_section += "\n\nUse these skills when appropriate to complete the user's request."

                # Add MCP tools section if skills reference MCP servers
                if mcp_servers_for_skills and self._mcp_discovery:
                    mcp_section_parts = []
                    for skill_name in skills:
                        # Get MCP servers for this skill
                        skill = self._skills.get(skill_name)
                        if skill and skill.metadata.mcp_servers:
                            tools_section = self._mcp_discovery.generate_skill_tools_section(
                                skill_name=skill_name,
                                mcp_servers=skill.metadata.mcp_servers,
                            )
                            if tools_section:
                                mcp_section_parts.append(tools_section)

                    if mcp_section_parts:
                        skills_section += "\n\n" + "\n\n".join(mcp_section_parts)

        variable_content += skills_section

        return base_prompt, variable_content

    def enable_auto_skill_selection(self, max_skills: int = 3):
        """
        Enable automatic skill selection

        Args:
            max_skills: Maximum number of skills to auto-select
        """
        self._auto_select_skills = True
        self._max_auto_skills = max_skills

    def disable_auto_skill_selection(self):
        """Disable automatic skill selection"""
        self._auto_select_skills = False

    def _validate_history(self, history: Optional[list[dict]]) -> list[dict]:
        """
        Validate and clean conversation history

        Args:
            history: Raw history from user

        Returns:
            Validated and cleaned history
        """
        if not history:
            return []

        # Validate each message
        clean_history = []
        for msg in history:
            if not isinstance(msg, dict):
                continue

            role = msg.get("role")
            content = msg.get("content", "")

            # Skip invalid messages
            if role not in ("user", "assistant"):
                continue

            # Ensure content exists and is string
            if not content or not isinstance(content, str):
                continue

            # Clean content
            content = content.strip()

            # Skip empty messages
            if not content:
                continue

            clean_history.append({"role": role, "content": content})

        return clean_history

    def _setup_tools(self):
        """Setup core tools with config"""
        tool_config = self._config.tools

        # Register core tools
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

        # Note: MCP servers are loaded lazily in _load_mcp_servers()
        # to avoid async operations in __init__

    def _compress_context(
        self,
        messages: list[dict],
        max_tokens: int = 12000,
        preserve_system: bool = True,
        preserve_initial_query: bool = True,
        recent_count: Optional[int] = None,
    ) -> list[dict]:
        """
        Multi-level context compression strategy

        Level 1: Estimate tokens and check if compression needed
        Level 2: Sliding window (preserve System + initial query + recent N messages)
        Level 3: Character-level truncation (last resort)

        Args:
            messages: Message list to compress
            max_tokens: Maximum token limit (default 12000 for GPT-4o with 4K buffer)
            preserve_system: Whether to preserve system prompt
            preserve_initial_query: Whether to preserve the initial user query
            recent_count: Number of recent messages to preserve (default: from config)

        Returns:
            Compressed message list
        """
        # Use config value if not specified
        if recent_count is None:
            recent_count = self._config.react.sliding_window_size
        if not messages:
            return messages

        # Level 1: Estimate tokens
        total_tokens = 0
        for msg in messages:
            content = msg.get("content", "")
            # Simple estimation: 1 token ~ 4 characters
            total_tokens += len(content) // 4

        # If under limit, no compression needed
        if total_tokens <= max_tokens:
            return messages

        # Level 2: Sliding window compression
        compressed = []

        # Preserve system prompt if requested
        system_msg = None
        if preserve_system:
            for msg in messages:
                if msg.get("role") == "system":
                    system_msg = msg
                    break

        # Find and preserve initial user query
        initial_query = None
        initial_query_index = -1
        if preserve_initial_query:
            for i, msg in enumerate(messages):
                if msg.get("role") == "user":
                    initial_query = msg
                    initial_query_index = i
                    break

        # Build sliding window
        if system_msg:
            compressed.append(system_msg)

        if initial_query:
            compressed.append(initial_query)

        # Add recent messages (excluding system and initial query)
        recent_messages = []
        for msg in messages:
            # Skip system and initial query (already added)
            if msg.get("role") == "system":
                continue
            if preserve_initial_query and msg == initial_query:
                continue

            recent_messages.append(msg)

        # Keep only the most recent messages
        if len(recent_messages) > recent_count:
            recent_messages = recent_messages[-recent_count:]

        compressed.extend(recent_messages)

        # Level 3: Character-level truncation (if still over limit)
        # Estimate compressed tokens
        compressed_tokens = 0
        for msg in compressed:
            content = msg.get("content", "")
            compressed_tokens += len(content) // 4

        if compressed_tokens > max_tokens:
            # Truncate tool outputs to fit
            for msg in compressed:
                if msg.get("role") == "tool":
                    content = msg.get("content", "")
                    # Truncate to 80% of original
                    if len(content) > 2000:
                        head = content[:1600]
                        tail = content[-400:] if len(content) > 2000 else ""
                        msg["content"] = f"{head}\n... [Context truncated] ...\n{tail}"

        return compressed

    async def _load_mcp_servers(self, required_skills: Optional[list[str]] = None) -> None:
        """
        Load MCP servers from configuration

        This is called during first agent run to avoid blocking __init__.

        Args:
            required_skills: Optional list of skill names. If provided, only loads
                           MCP servers that are associated with these skills or
                           have no skill association.
        """
        if self._mcp_manager is not None:
            # Already loaded
            return

        # Create MCP manager based on multi-tenant mode
        if self._multitenant_enabled:
            self._mcp_manager = MultiTenantMCPManager(self._tools, self._multitenant)
        else:
            self._mcp_manager = MCPToolManager(self._tools)

        # Load servers from config
        mcp_servers = self._config.mcp.servers or []

        # Build set of required MCP servers from skills
        required_mcp_servers = set()
        if required_skills:
            for skill_name in required_skills:
                skill = self._skills.get(skill_name)
                if skill and skill.metadata.mcp_servers:
                    required_mcp_servers.update(skill.metadata.mcp_servers)

        for server_config in mcp_servers:
            server_name = server_config.name if hasattr(server_config, 'name') else server_config.get("name", "unknown")

            # Skip if skills specified and this server is not required
            # unless it has no skill association (global servers)
            if required_skills is not None:
                associated_skill = server_config.associated_skill if hasattr(server_config, 'associated_skill') else server_config.get("associated_skill")
                if associated_skill and associated_skill not in required_skills:
                    # Server is associated with a skill that's not in our list
                    if server_name not in required_mcp_servers:
                        continue

            try:
                # Extract config based on type (dict or MCPServerConfig)
                if hasattr(server_config, 'command'):
                    # MCPServerConfig object
                    command = server_config.command
                    args = server_config.args
                    description = server_config.description
                    associated_skill = server_config.associated_skill
                    isolation = server_config.isolation
                else:
                    # Dict format (backward compatibility)
                    command = server_config.get("command", "")
                    args = server_config.get("args", [])
                    description = server_config.get("description")
                    associated_skill = server_config.get("associated_skill")
                    isolation = server_config.get("isolation", "shared")

                # Index server description for discovery
                if description:
                    self._mcp_discovery.index_server(server_name, description)

                # Add server and register tools based on manager type
                if isinstance(self._mcp_manager, MultiTenantMCPManager):
                    # Multi-tenant mode: Only preload shared servers
                    if isolation == "shared":
                        # Convert to MCPServerConfig if needed
                        if not hasattr(server_config, 'isolation'):
                            from fastreact.core.config import MCPServerConfig
                            server_config = MCPServerConfig.from_dict(server_config)

                        # Preload shared server for tool discovery
                        await self._mcp_manager.preload_shared_servers([server_config])

                        # Index tools for discovery
                        mcp_tools = self._mcp_manager.list_mcp_tools()
                        for tool_name in mcp_tools:
                            if tool_name not in self._mcp_discovery.list_all_tools():
                                # Get tool wrapper to extract info
                                tool_wrapper = self._mcp_manager._tool_wrappers.get(tool_name)
                                if tool_wrapper:
                                    self._mcp_discovery.index_tool(
                                        tool_name=tool_name,
                                        server_name=server_name,
                                        description=tool_wrapper.description,
                                        parameters=tool_wrapper.parameters,
                                        associated_skill=associated_skill,
                                    )
                    # per_user and lazy_per_user servers are not preloaded
                    # They will be created on-demand during tool execution
                else:
                    # Single-tenant mode: Load all servers immediately
                    await self._mcp_manager.add_server(
                        name=server_name,
                        server_command=command,
                        server_args=args,
                    )

                    # Index tools for discovery
                    mcp_tools = self._mcp_manager.list_mcp_tools()
                    for tool_name in mcp_tools:
                        if tool_name not in self._mcp_discovery.list_all_tools():
                            # Get tool wrapper to extract info
                            tool_wrapper = self._mcp_manager._tool_wrappers.get(tool_name)
                            if tool_wrapper:
                                self._mcp_discovery.index_tool(
                                    tool_name=tool_name,
                                    server_name=server_name,
                                    description=tool_wrapper.description,
                                    parameters=tool_wrapper.parameters,
                                    associated_skill=associated_skill,
                                )

            except Exception as e:
                # Log error but continue with other servers
                import sys
                print(f"[ERROR] Failed to load MCP server '{server_name}': {e}", file=sys.stderr)

    async def close_mcp_servers(self) -> None:
        """Close all MCP server connections"""
        if self._mcp_manager:
            await self._mcp_manager.close_all()
            self._mcp_manager = None

    # === Session Management (NEW) ===

    def create_session(
        self,
        session_id: str,
        user_key: Optional[str] = None,
        max_history: int = 50,
        followup_window_seconds: int = 30,
        max_queue_size: int = 5,
    ) -> "AgentSession":
        """
        Create or get existing session

        Args:
            session_id: Unique session identifier
            max_history: Maximum conversation turns to keep in memory
            followup_window_seconds: Time window for follow-up detection (default: 30s)
            max_queue_size: Maximum messages in queue (for flow control)

        Returns:
            AgentSession instance

        Example:
            agent = Agent()
            session = agent.create_session("user-123")
            # Use session for business logic
            await session.process_message({"type": "query", "content": "Hello"}, on_event=...)
        """
        from fastreact.core.session import AgentSession

        # Return existing session if already exists
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Create new session
        session = AgentSession(
            session_id=session_id,
            agent=self,
            max_history=max_history,
            followup_window_seconds=followup_window_seconds,
            max_queue_size=max_queue_size,
        )

        # Set user_key for multi-tenant session tracking
        session.user_key = user_key

        self._sessions[session_id] = session

        # Also create MessageQueue for legacy compatibility
        if session_id not in self._session_queues:
            from fastreact.core.messages import MessageQueue
            self._session_queues[session_id] = MessageQueue()

        return session

    def get_session(self, session_id: str) -> Optional["AgentSession"]:
        """
        Get existing session

        Args:
            session_id: Session identifier

        Returns:
            AgentSession instance if exists, None otherwise
        """
        return self._sessions.get(session_id)

    def close_session(self, session_id: str):
        """
        Close and cleanup session

        Args:
            session_id: Session identifier to close
        """
        # Remove AgentSession
        if session_id in self._sessions:
            del self._sessions[session_id]

        # Remove MessageQueue (legacy compatibility)
        if session_id in self._session_queues:
            del self._session_queues[session_id]

    def find_active_session(self, user_key: str) -> Optional["AgentSession"]:
        """
        Find active session for user (non-closed status)

        Args:
            user_key: User identifier (e.g., "feishu:ou_xxx")

        Returns:
            AgentSession if found, None otherwise

        Example:
            >>> session = agent.find_active_session("feishu:ou_123")
            >>> if session:
            ...     # Inject message into existing session
            ...     await session.enqueue_message({"type": "query", "content": "停下"})
        """
        for session in self._sessions.values():
            if session.user_key == user_key and session.status != "closed":
                return session
        return None

    def list_sessions(self, user_key: Optional[str] = None) -> list[dict]:
        """
        List all sessions (optionally filtered by user)

        Args:
            user_key: Optional user filter

        Returns:
            List of session metadata dictionaries

        Example:
            >>> # All sessions
            >>> all_sessions = agent.list_sessions()
            >>> # Specific user's sessions
            >>> user_sessions = agent.list_sessions("feishu:ou_123")
        """
        sessions = []
        for session in self._sessions.values():
            if user_key is None or session.user_key == user_key:
                sessions.append(session.get_metadata())
        return sessions

    def get_session_status(self, session_id: str) -> Optional[str]:
        """
        Get session status

        Args:
            session_id: Session identifier

        Returns:
            Status string or None if session not found
        """
        session = self.get_session(session_id)
        return session.get_status() if session else None

    # === End Session Management ===

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

    async def run_or_inject(
        self,
        query: str,
        user_key: str,
        skills: Optional[list[str]] = None,
        force_new: bool = False,
    ) -> AsyncIterator["AgentEvent"]:
        """
        Unified execution entry: auto-create session OR inject into active session

        This is the RECOMMENDED API for adapters to use. It automatically handles
        session lifecycle based on user activity.

        Args:
            query: User message
            user_key: User identifier (e.g., "feishu:ou_xxx")
            skills: Optional skill list (only for new sessions)
            force_new: Force creating new session (even if active session exists)

        Yields:
            AgentEvent objects stream

        Behavior:
            - If user has active session AND not force_new: inject message
            - Otherwise: create new session and execute

        Example:
            >>> # Feishu adapter usage
            >>> async for event in agent.run_or_inject(
            ...     query="停下",
            ...     user_key="feishu:ou_123"
            ... ):
            ...     await send_to_feishu(event)
        """
        from fastreact.core.events import AgentEvent

        # Check for active session
        active_session = None
        if not force_new:
            active_session = self.find_active_session(user_key)

        if active_session:
            # Active session exists - check if it's idle or running
            import sys

            if active_session.get_status() == "idle":
                # Session is idle - execute query on existing session
                print(
                    f"[INFO] Reusing idle session {active_session.session_id} "
                    f"for user {user_key}",
                    file=sys.stderr
                )

                # Run on existing session (will use history)
                async for event in self.run_event_stream(
                    query=query,
                    session_id=active_session.session_id,
                    user_key=user_key,
                ):
                    yield event
                return
            else:
                # Session is running - inject as user intervention
                print(
                    f"[INFO] Injecting into running session {active_session.session_id} "
                    f"for user {user_key}",
                    file=sys.stderr
                )

                # Inject into Agent's session queue (not AgentSession's queue)
                # This will be checked in run_event_stream's inner loop
                from fastreact.core.messages import Message

                intervention_msg = Message.steering(
                    query,
                    source="feishu",  # Pass as keyword argument, not nested dict
                    user_intervention=True
                )

                import sys
                print(
                    f"[DEBUG] Pushing intervention message to queue {active_session.session_id}",
                    file=sys.stderr
                )
                self._session_queues[active_session.session_id].push(intervention_msg)

                # Verify message was added
                queue_after = self._session_queues.get(active_session.session_id, MessageQueue())
                print(
                    f"[DEBUG] After push, queue has {len(queue_after._messages)} messages",
                    file=sys.stderr
                )

                # Yield injection events
                yield AgentEvent.session_start(
                    query,
                    active_session.session_id,
                    skills=None,
                    metadata={
                        "injected": True,
                        "user_key": user_key,
                        "session_status": active_session.get_status(),
                    }
                )
                yield AgentEvent.session_end(
                    active_session.session_id,
                    f"[INJECTED] Message added to active session",
                )
                return

        # Create new session
        session_id = f"{user_key}:session-{uuid.uuid4()}"
        session = self.create_session(
            session_id=session_id,
            user_key=user_key,
            max_history=50,
            followup_window_seconds=30,
        )

        # Run execution stream
        async for event in self.run_event_stream(
            query=query,
            skills=skills,
            session_id=session_id,
            user_key=user_key,
        ):
            yield event

    async def run_event_stream(
        self,
        query: str,
        skills: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        history: Optional[list[dict]] = None,
        user_key: Optional[str] = None,
    ) -> AsyncIterator["AgentEvent"]:
        """
        Run agent with event stream (Brain-Body Loop)

        This is PREFERRED API. It yields AgentEvent objects,
        providing complete visibility into execution.

        Args:
            query: User query
            skills: List of skill names to inject into system prompt
                   Skills provide specialized knowledge and capabilities
                   Example: ["git_workflow", "code_review"]
                   Set to None for no specific skills
            session_id: Session identifier (auto-generated if None)
                       Use same session_id across multiple calls for multi-turn conversation
            history: Optional conversation history in OpenAI format
                    [
                        {"role": "user", "content": "..."},
                        {"role": "assistant", "content": "..."},
                    ]
                    Note: Tool messages are managed internally, don't include them
            user_key: User identifier for multi-tenant mode (format: "channel:user_id")
                     Example: "feishu:ou_1234567890"
                     If None and multi-tenant enabled, will extract from session_id

        Yields:
            AgentEvent objects (DOES NOT consume LLM context)

            Events are yielded in real-time for UI visualization only.
            They do NOT affect the LLM's context window.

            Event types:
                - SESSION_START: Conversation started
                - THINK: LLM reasoning (may be empty if only tool call)
                - TOOL_CALL: Tool being called (intent, not execution yet)
                - TOOL_RESULT: Tool execution result
                - SESSION_END: Conversation ended with final answer
                - ERROR: Error occurred

        Example:
            # Simple query
            agent = Agent()
            async for event in agent.run_event_stream("What is 2+2?"):
                if event.type == EventType.THINK:
                    print(f"Thinking: {event.content}")
                elif event.type == EventType.SESSION_END:
                    print(f"Answer: {event.content}")

            # With skills
            async for event in agent.run_event_stream(
                "Review this code",
                skills=["code_review", "python_best_practices"]
            ):
                ...

            # Multi-turn conversation with history
            history = [
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "4"},
            ]
            async for event in agent.run_event_stream(
                "What about 3+3?",
                session_id="same-session",  # Maintain context
                history=history
            ):
                ...

            # Multi-tenant mode
            agent = Agent(multitenant=True)
            async for event in agent.run_event_stream(
                "Create file test.txt",
                user_key="feishu:ou_xxx"  # User-specific workspace
            ):
                ...
        """
        from fastreact.core.events import AgentEvent, EventType

        # Extract user_key from session_id if not provided
        if user_key is None and self._multitenant_enabled and session_id:
            # Try to extract from session_id (e.g., "feishu:ou_xxx:session-uuid")
            if ":" in session_id:
                parts = session_id.split(":")
                if len(parts) >= 2:
                    user_key = f"{parts[0]}:{parts[1]}"

        # Get user context if multi-tenant (must be before skill selection)
        user_context: Optional[UserContext] = None
        if self._multitenant_enabled and user_key:
            user_context = self._multitenant.get_user_context(user_key)

        # Auto-select skills if not specified and enabled
        if skills is None and self._auto_select_skills:
            skills = self._select_skills_auto(
                query,
                self._max_auto_skills,
                user_context=user_context,
            )

        # Load MCP servers on first run (lazy initialization)
        # Pass selected skills to load only required MCP servers
        await self._load_mcp_servers(required_skills=skills)

        # Update Core's tool registry to include newly loaded MCP tools
        # This ensures Core has access to all tools (builtin + MCP) when generating tool calls
        self._core._tools = self._tools

        # Generate session_id if not provided
        session_id = session_id or str(uuid.uuid4())

        # Prepend user_key to session_id for multi-tenant
        if user_context and ":" not in session_id:
            session_id = f"{user_key}:{session_id}"

        # Get or create session and set user_key
        session = self.get_session(session_id)
        if not session:
            session = self.create_session(session_id, user_key=user_key)
        else:
            session.user_key = user_key

        # Set running status
        session.set_status("running")

        # Create session queue for steering/followup (only if not exists)
        # This prevents overwriting queue that may have injected messages
        if session_id not in self._session_queues:
            self._session_queues[session_id] = MessageQueue()

        try:
            # Emit SESSION_START with skills information
            yield AgentEvent.session_start(query, session_id, skills=skills)

            # Validate and clean history
            messages = self._validate_history(history)

            # Add current user message
            messages.append(Message.user(query).to_llm_format())

            # Build system prompt with skills (skills already selected above)
            # Returns (base_prompt, skills_content) for cache-friendly injection
            base_prompt, skills_content = self._build_system_prompt_with_skills(skills)

            # Inject skills content as a separate system message at the START of messages
            # This keeps base_prompt constant (cacheable) while providing skills context
            messages.insert(0, {"role": "system", "content": skills_content})

            # Use base_prompt for Core (constant, cacheable)
            system_prompt = base_prompt

            # Interrupt flag
            interrupted = False

            # Iteration counter with hard limit to prevent infinite loops
            iteration_count = 0
            max_iterations = self._config.react.max_iterations if self._config else 25

            # === Outer loop: Process follow-up messages ===
            while True:
                # HARD LIMIT: Prevent infinite loops
                iteration_count += 1
                if iteration_count > max_iterations:
                    # Circuit breaker: immediately terminate with clear error message
                    yield AgentEvent.session_end(
                        session_id,
                        f"[STOPPED] Task stopped due to maximum iteration limit ({max_iterations}). "
                        f"This usually means the agent is stuck in a loop or the task is too complex. "
                        f"Please try breaking down the task into smaller steps."
                    )
                    return
                has_more_tool_calls = True
                executed_tools_this_iteration = False  # Track tools in this iteration only

                # === Inner loop: Process tools ===
                while has_more_tool_calls:
                    # 1. Brain: Ask LLM for reasoning
                    pending_messages = self._session_queues.get(session_id, MessageQueue())

                    # Debug: Always log queue status
                    import sys
                    msg_count = len(pending_messages._messages) if pending_messages else 0
                    print(
                        f"[DEBUG] Inner loop start: queue has {msg_count} messages",
                        file=sys.stderr
                    )

                    # Process pending messages (steering/interrupt/followup)
                    if pending_messages:
                        for msg in pending_messages.drain():
                            import sys
                            print(
                                f"[DEBUG] Processing message: role={msg.role}, content={msg.content[:30]}",
                                file=sys.stderr
                            )

                            # Check for steering messages (user intervention from any adapter)
                            # Use role="steering" instead of hardcoded adapter types
                            if msg.role == "steering":
                                msg_source = msg.metadata.get("source", "unknown")
                                # User intervention: append as new user message
                                # This preserves all previous tool results so LLM can understand "what you just did"
                                messages.append({
                                    "role": "user",
                                    "content": f"[USER INTERVENTION]: {msg.content}"
                                })

                                # Send notification
                                yield AgentEvent.think(
                                    f"[USER INTERVENTION] {msg.content}",
                                    session_id,
                                    source=msg_source,
                                    user_intervention=True
                                )
                                # Continue execution, don't set interrupted flag
                                break

                            # Legacy interrupt signal handling (for backward compatibility)
                            if msg.content.startswith("[INTERRUPT]"):
                                # Extract new query from metadata
                                new_query = msg.metadata.get("new_query", "")
                                if new_query:
                                    # Replace the original user query with the new one
                                    # Find and replace the first user message
                                    for i, m in enumerate(messages):
                                        if m.get("role") == "user":
                                            messages[i] = {
                                                "role": "user",
                                                "content": new_query
                                            }
                                            break

                                    # Notify user about the query switch
                                    yield AgentEvent.think(
                                        f"[查询切换] {new_query}",
                                        session_id,
                                        metadata={"source": "user", "query_switch": True}
                                    )

                                    # Continue processing with new query (don't set interrupted flag)
                                    # This preserves context from previous tool calls
                                    break

                            # Regular steering/followup messages
                            messages.append(msg.to_llm_format())
                            # Emit steering event for visibility
                            if msg.role in ("steering", "followup"):
                                yield AgentEvent.think(
                                    f"[{msg.role.upper()}] {msg.content}",
                                    session_id,
                                    metadata={"source": msg.metadata.get("source", "unknown")},
                                )

                    # Compress context before LLM call (each iteration)
                    compressed_messages = self._compress_context(
                        messages,
                        max_tokens=12000,  # Leave 4K buffer for GPT-4o (16K total)
                        preserve_system=True,
                        preserve_initial_query=True,
                        # recent_count defaults to config value
                    )

                    # Call Brain (Core) for reasoning step
                    step_end = None
                    tool_calls = []  # Collect tool calls from Core

                    async for event in self._core.run_step_stream(
                        messages=compressed_messages,  # Use compressed messages
                        session_id=session_id,
                        system_prompt=system_prompt,  # Pass skills-enhanced prompt
                    ):
                        # Forward all events directly
                        yield event

                        # Collect TOOL_CALL events for execution
                        if event.type == EventType.TOOL_CALL:
                            tool_calls.append({
                                "id": event.metadata.get("call_id", ""),
                                "name": event.tool_name,
                                "arguments": event.tool_args,
                            })

                        # Capture STEP_END to handle tool execution
                        elif event.type == EventType.STEP_END:
                            step_end = event
                            # CRITICAL: Add LLM response to message history
                            # Must include tool_calls if present (OpenAI format requirement)
                            if step_end.content and step_end.content.strip() or tool_calls:
                                assistant_msg = {
                                    "role": "assistant",
                                }
                                # Add content if present
                                if step_end.content and step_end.content.strip():
                                    assistant_msg["content"] = step_end.content
                                else:
                                    assistant_msg["content"] = ""  # Required by OpenAI

                                # Add tool_calls if present (CRITICAL for function calling)
                                if tool_calls:
                                    assistant_msg["tool_calls"] = [
                                        {
                                            "id": tc.get("id", ""),
                                            "type": "function",
                                            "function": {
                                                "name": tc.get("name", ""),
                                                "arguments": json.dumps(tc.get("arguments", {})),
                                            },
                                        }
                                        for tc in tool_calls
                                    ]

                                messages.append(assistant_msg)
                            break

                    # 2. Body: Execute tools (if any)
                    if step_end and step_end.metadata.get("has_tool_calls") and tool_calls:
                        for tool_call in tool_calls:
                            tool_name = tool_call.get("name", "")
                            tool_params = tool_call.get("arguments", {})
                            call_id = tool_call.get("id", "")

                            # TOOL_CALL already emitted by Core, no need to re-emit

                            # Safety check
                            if self._safety_policy:
                                decision = self._safety_policy.check(
                                    tool_name=tool_name,
                                    args=tool_params,
                                )
                                # Block forbidden operations
                                if decision.level == SafetyLevel.FORBIDDEN:
                                    result = f"[SAFETY_BLOCKED] {decision.reason}"
                                    yield AgentEvent.tool_result(tool_name, result, session_id)
                                    messages.append(Message.tool(
                                        name=tool_name,
                                        result=result,
                                        call_id=call_id,
                                    ).to_llm_format())
                                    continue

                            # User input checkpoint: check for pending messages before tool execution
                            pending = self._session_queues.get(session_id, MessageQueue())
                            if pending:
                                import sys
                                print(
                                    f"[DEBUG] Tool execution checkpoint: found {len(pending._messages)} messages",
                                    file=sys.stderr
                                )
                                for msg in pending.drain():
                                    import sys
                                    print(
                                        f"[DEBUG] Tool checkpoint processing: role={msg.role}, content={msg.content[:30]}",
                                        file=sys.stderr
                                    )

                                    # Check for steering messages (user intervention from any adapter)
                                    # Use role="steering" instead of hardcoded adapter types
                                    if msg.role == "steering":
                                        msg_source = msg.metadata.get("source", "unknown")
                                        # User intervention during tool execution
                                        # Pass metadata as keyword arguments, not nested dict
                                        yield AgentEvent.think(
                                            f"[USER INTERVENTION] {msg.content}",
                                            session_id,
                                            source=msg_source,
                                            user_intervention=True,
                                            tool_interrupted=True
                                        )

                                        # Add as steering message
                                        messages.append({
                                            "role": "user",
                                            "content": f"[USER INTERVENTION]: {msg.content}"
                                        })

                                        # Exit tool execution loop
                                        has_more_tool_calls = False
                                        break

                                # If user interrupted, skip remaining tools
                                if not has_more_tool_calls:
                                    break

                            # Execute tool
                            try:
                                result = await self._tools.execute(
                                    tool_name,
                                    tool_params,
                                    user_context=user_context
                                )

                                # Context truncate if needed
                                if self._context_monitor:
                                    result = self._context_monitor.truncate_tool_output(result)

                            except Exception as e:
                                result = f"[ERROR] {str(e)}"

                            # Emit TOOL_RESULT event
                            yield AgentEvent.tool_result(tool_name, result, session_id)

                            # Add tool result to history
                            import sys
                            print(f"[DEBUG] Tool result: tool_name={tool_name}, call_id='{call_id}', result_length={len(result)}", file=sys.stderr)
                            messages.append(Message.tool(
                                name=tool_name,
                                result=result,
                                call_id=call_id,
                            ).to_llm_format())
                        # Tools executed, prepare for next LLM call
                        executed_tools_this_iteration = True
                        has_more_tool_calls = False
                        import sys
                        print(f"[DEBUG] Tools executed in this iteration, will continue to next iteration", file=sys.stderr)
                    else:
                        # No tool calls - exit inner loop
                        has_more_tool_calls = False

                # After inner loop, check if we should continue
                # Continue if:
                # 1. We just executed tools in this iteration (need LLM to process results)
                # 2. There are follow-up messages
                # 3. LLM hasn't generated a final answer yet

                # Check for follow-up messages (user intervention, etc.)
                followup_queue = self._session_queues.get(session_id, MessageQueue())
                has_followup = bool(followup_queue)

                import sys
                queue_in_dict = self._session_queues.get(session_id)
                print(
                    f"[DEBUG] After inner loop: queue_in_dict={queue_in_dict is not None}, has_followup={has_followup}, len={len(followup_queue._messages) if followup_queue else 'N/A'}, executed_tools={executed_tools_this_iteration}",
                    file=sys.stderr
                )
                if has_followup:
                    print(
                        f"[DEBUG] Found {len(followup_queue._messages)} follow-up messages, continuing loop",
                        file=sys.stderr
                    )

                # If we executed tools in this iteration, continue to next iteration
                # (LLM needs to process tool results and generate next action)
                if executed_tools_this_iteration and not has_followup:
                    continue

                # If there are follow-up messages, continue to process them
                if has_followup:
                    continue

                # CRITICAL FIX: Check if LLM has generated a final answer
                # If the last assistant message is a text response (not tool calls),
                # we can consider the task complete
                has_final_answer = False
                for msg in reversed(messages):
                    if msg.get("role") == "assistant":
                        content = msg.get("content", "")
                        # Check if this is a meaningful text response (not just thinking)
                        if content and not content.startswith("[") and len(content.strip()) > 0:
                            has_final_answer = True
                            break

                # Only break if we have a final answer OR we've hit max iterations
                if has_final_answer:
                    import sys
                    print(f"[DEBUG] Agent loop completed: has_final_answer=True, executed_tools={executed_tools_this_iteration}, has_followup={has_followup}", file=sys.stderr)
                    break
                elif not executed_tools_this_iteration and not has_followup:
                    # LLM didn't call tools AND didn't generate text response
                    # This might be an error or empty response - log warning
                    import sys
                    print(f"[WARNING] Agent loop ended without final answer or tool calls (executed_tools={executed_tools_this_iteration}, has_followup={has_followup})", file=sys.stderr)
                    break
                # Otherwise, continue the loop
                import sys
                print(f"[DEBUG] Agent loop continuing (executed_tools={executed_tools_this_iteration}, has_followup={has_followup}, has_final_answer={has_final_answer})", file=sys.stderr)

            # Check if we were interrupted
            if interrupted:
                # Extract last assistant message if available
                last_response = ""
                for msg in reversed(messages):
                    if msg.get("role") == "assistant":
                        content = msg.get("content", "")
                        if content and not content.startswith("["):
                            last_response = content
                            break

                # Emit interrupted session end
                interrupt_msg = "[INTERRUPTED] User stopped the execution"
                if last_response:
                    interrupt_msg = f"{last_response}\n\n[INTERRUPTED] User stopped the execution"

                yield AgentEvent.session_end(session_id, interrupt_msg)
                return

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

        finally:
            # Update session state to idle and update activity
            session = self.get_session(session_id)
            if session:
                session.set_status("idle")
                session.update_activity()

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
