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
import logging
import re
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
from fastreact.runtime import (
    AgentRuntime,
    SessionService,
    ToolExecutionService,
    SkillResolver,
    MCPBootstrapper,
    StoreService,
    RunService,
    TaskService,
    TaskCreateTool,
    TaskUpdateTool,
    TaskListTool,
    TaskGetTool,
)

logger = logging.getLogger(__name__)


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
        self._mcp_loaded_server_keys: set[str] = set()
        self._mcp_user_scoped_server_names: set[str] = set()

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
                policy_config=self._config.policy.to_safety_policy(),
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

        # Runtime service boundaries. These keep adapters and public methods
        # away from Agent private state.
        self.store = StoreService.from_agent(self)
        self.runs = RunService(
            self.store,
            lease_seconds=self._config.service.run_lease_seconds,
            max_attempts=self._config.service.run_max_attempts,
        )
        self.tasks = TaskService(self.store)
        self._register_task_tools()
        self.sessions = SessionService(self)
        self.runtime = AgentRuntime(self)
        self.tool_executor = ToolExecutionService(self)
        self.skill_resolver = SkillResolver(self)
        self.mcp_bootstrapper = MCPBootstrapper(self)

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

        workspace_profile = self._load_workspace_profile_context()
        if workspace_profile:
            variable_content += workspace_profile

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

    def _load_workspace_profile_context(self, max_chars_per_file: int = 4000) -> str:
        """Load optional workspace profile files such as AGENTS.md or SOUL.md."""
        roots = []
        paths = getattr(self._config, "paths", None)
        workspace = getattr(paths, "gateway_workspace", None)
        if workspace:
            roots.append(Path(workspace))
        tool_working_dir = getattr(getattr(self._config, "tools", None), "working_dir", None)
        if tool_working_dir:
            roots.append(Path(tool_working_dir))
        roots.append(Path.cwd())

        seen_roots = []
        for root in roots:
            root = root.expanduser()
            if root not in seen_roots:
                seen_roots.append(root)

        candidates = []
        for root in seen_roots:
            candidates.extend([
                root / "AGENTS.md",
                root / "SOUL.md",
                root / ".fastreact" / "AGENT.md",
                root / ".fastreact" / "SOUL.md",
            ])

        sections = []
        seen_files = set()
        for path in candidates:
            if path in seen_files or not path.exists() or not path.is_file():
                continue
            seen_files.add(path)
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue
            if not content.strip():
                continue
            if len(content) > max_chars_per_file:
                content = content[:max_chars_per_file] + "\n[... workspace profile truncated ...]"
            sections.append(f"## {path.name} ({path})\n{content.strip()}")

        if not sections:
            return ""
        return "\n\n# Workspace Profile\nUse these local workspace instructions when they apply.\n\n" + "\n\n".join(sections)

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

    def _register_task_tools(self):
        """Register durable task board tools after StoreService is ready."""
        for tool in (
            TaskCreateTool(self.tasks),
            TaskUpdateTool(self.tasks),
            TaskListTool(self.tasks),
            TaskGetTool(self.tasks),
        ):
            if not self._tools.get(tool.name):
                self._tools.register(tool)

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
        self._last_compression_metadata = {
            "compressed": False,
            "reason": "under_limit",
            "original_message_count": len(messages),
            "compressed_message_count": len(messages),
            "dropped_count": 0,
            "tool_output_truncation_count": 0,
            "preserved_message_indices": list(range(len(messages))),
        }
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
        preserved_indices: list[int] = []

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
            preserved_indices.append(messages.index(system_msg))

        if initial_query:
            compressed.append(initial_query)
            preserved_indices.append(initial_query_index)

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
        for msg in recent_messages:
            try:
                preserved_indices.append(messages.index(msg))
            except ValueError:
                pass

        # Level 3: Character-level truncation (if still over limit)
        # Estimate compressed tokens
        compressed_tokens = 0
        for msg in compressed:
            content = msg.get("content", "")
            compressed_tokens += len(content) // 4

        if compressed_tokens > max_tokens:
            # Truncate tool outputs to fit
            tool_output_truncation_count = 0
            for msg in compressed:
                if msg.get("role") == "tool":
                    content = msg.get("content", "")
                    # Truncate to 80% of original
                    if len(content) > 2000:
                        head = content[:1600]
                        tail = content[-400:] if len(content) > 2000 else ""
                        msg["content"] = f"{head}\n... [Context truncated] ...\n{tail}"
                        tool_output_truncation_count += 1
        else:
            tool_output_truncation_count = 0

        self._last_compression_metadata = {
            "compressed": True,
            "reason": "sliding_window" if tool_output_truncation_count == 0 else "sliding_window_and_tool_truncation",
            "original_message_count": len(messages),
            "compressed_message_count": len(compressed),
            "dropped_count": max(0, len(messages) - len(compressed)),
            "tool_output_truncation_count": tool_output_truncation_count,
            "preserved_message_indices": sorted(set(preserved_indices)),
            "estimated_tokens_before": total_tokens,
            "estimated_tokens_after": compressed_tokens,
        }

        return compressed

    def _user_scoped_mcp_server_name(self, user_key: str, server_name: str) -> str:
        safe_user = re.sub(r"[^a-zA-Z0-9_]+", "_", user_key).strip("_") or "user"
        safe_server = re.sub(r"[^a-zA-Z0-9_]+", "_", server_name).strip("_") or "server"
        return f"user_{safe_user}_{safe_server}"

    def _configured_mcp_servers(self, user_key: Optional[str] = None) -> list:
        from fastreact.core.config import MCPServerConfig

        servers = list(self._config.mcp.servers or [])
        if not (self._multitenant_enabled and user_key and self._multitenant):
            return servers

        user_context = self._multitenant.get_user_context(user_key)
        user_mcp = (user_context.config or {}).get("mcp", {})
        user_servers = user_mcp.get("servers", []) if isinstance(user_mcp, dict) else []
        for raw_server in user_servers:
            try:
                server_config = raw_server if isinstance(raw_server, MCPServerConfig) else MCPServerConfig.from_dict(raw_server)
                original_name = server_config.name
                server_config.name = self._user_scoped_mcp_server_name(user_key, original_name)
                server_config.allowed_user_key = user_key
                self._mcp_user_scoped_server_names.add(server_config.name)
                if not server_config.description:
                    server_config.description = f"User-scoped MCP server '{original_name}' for {user_key}."
                servers.append(server_config)
            except Exception as exc:  # noqa: BLE001 - user config should not break global MCP.
                logger.warning("Ignoring invalid user MCP config for '%s': %s", user_key, exc)
        return servers

    async def _load_mcp_servers(
        self,
        required_skills: Optional[list[str]] = None,
        user_key: Optional[str] = None,
    ) -> None:
        """
        Load MCP servers from configuration

        This is called during first agent run to avoid blocking __init__.

        Args:
            required_skills: Optional list of skill names. If provided, only loads
                           MCP servers that are associated with these skills or
                           have no skill association.
            user_key: Optional user identifier for loading workspace-scoped MCP configs.
        """
        if self._mcp_manager is None:
            # Create MCP manager based on multi-tenant mode
            if self._multitenant_enabled:
                self._mcp_manager = MultiTenantMCPManager(self._tools, self._multitenant)
            else:
                self._mcp_manager = MCPToolManager(self._tools)

        # Load servers from config
        mcp_servers = self._configured_mcp_servers(user_key=user_key)

        # Build set of required MCP servers from skills
        required_mcp_servers = set()
        if required_skills:
            for skill_name in required_skills:
                skill = self._skills.get(skill_name)
                if skill and skill.metadata.mcp_servers:
                    required_mcp_servers.update(skill.metadata.mcp_servers)

        for server_config in mcp_servers:
            server_name = server_config.name if hasattr(server_config, 'name') else server_config.get("name", "unknown")
            is_user_scoped_server = server_name in self._mcp_user_scoped_server_names
            server_key = f"{user_key}:{server_name}" if is_user_scoped_server else f"global:{server_name}"
            if server_key in self._mcp_loaded_server_keys:
                continue

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
                    env = server_config.env
                    transport = server_config.transport
                    url = server_config.url
                    auth_token_ref = server_config.auth_token_ref
                    description = server_config.description
                    associated_skill = server_config.associated_skill
                    isolation = server_config.isolation
                else:
                    # Dict format (backward compatibility)
                    command = server_config.get("command", "")
                    args = server_config.get("args", [])
                    env = server_config.get("env")
                    transport = server_config.get("transport", "stdio")
                    url = server_config.get("url")
                    auth_token_ref = server_config.get("auth_token_ref")
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
                        self._mcp_loaded_server_keys.add(server_key)

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
                        transport=transport,
                        server_command=command,
                        server_args=args,
                        env=env,
                        url=url,
                        auth_token_ref=auth_token_ref,
                        allowed_user_key=user_key if is_user_scoped_server else None,
                    )
                    self._mcp_loaded_server_keys.add(server_key)

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
                logger.warning("Failed to load MCP server '%s': %s", server_name, e)

    async def close_mcp_servers(self) -> None:
        """Close all MCP server connections"""
        if self._mcp_manager:
            await self._mcp_manager.close_all()
            self._mcp_manager = None

    # === Session Management (NEW) ===

    def _create_session_impl(
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
            user_key: User identifier for multi-tenant mode (format: "channel:user_id")
            max_history: Maximum conversation turns to keep in memory
            followup_window_seconds: Time window for follow-up detection (default: 30s)
            max_queue_size: Maximum messages in queue (for flow control)

        Returns:
            AgentSession instance

        Multi-tenant Support:
        - If multitenant=True and user_key provided, auto-creates user workspace
        - Workspace isolation: /var/fastreact/tenants/gateway/{user_key}/
        - Each user gets their own config, skills, and memory

        Example:
            agent = Agent(multitenant=True)
            session = agent.create_session("session-123", user_key="web:user@example.com")
            # Use session for business logic
            await session.process_message({"type": "query", "content": "Hello"}, on_event=...)
        """
        from fastreact.core.session import AgentSession

        # Return existing session if already exists
        if session_id in self._sessions:
            return self._sessions[session_id]

        # NEW: Auto-create workspace for multi-tenant mode
        user_context = None
        if self._multitenant_enabled and user_key:
            # This will auto-create user workspace with proper directory structure
            # Exceptions will propagate to caller for validation
            user_context = self._multitenant.get_user_context(user_key)
            logger.debug("Created/loaded workspace for user %s at %s", user_key, user_context.workspace)

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

        # NEW: Store user_context in session for workspace access
        if user_context:
            session._user_context = user_context

        self._sessions[session_id] = session

        # Also create MessageQueue for legacy compatibility
        if session_id not in self._session_queues:
            from fastreact.core.messages import MessageQueue
            self._session_queues[session_id] = MessageQueue()

        return session

    def _get_session_impl(self, session_id: str) -> Optional["AgentSession"]:
        """
        Get existing session

        Args:
            session_id: Session identifier

        Returns:
            AgentSession instance if exists, None otherwise
        """
        return self._sessions.get(session_id)

    def _close_session_impl(self, session_id: str):
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

    def _find_active_session_impl(self, user_key: str) -> Optional["AgentSession"]:
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

    def _list_sessions_impl(self, user_key: Optional[str] = None) -> list[dict]:
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

    def _get_session_status_impl(self, session_id: str) -> Optional[str]:
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

    def _inject_message_impl(self, session_id: str, message: Message):
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

    # === Public service-backed session facade ===

    def create_session(
        self,
        session_id: str,
        user_key: Optional[str] = None,
        max_history: int = 50,
        followup_window_seconds: int = 30,
        max_queue_size: int = 5,
    ) -> "AgentSession":
        return self.sessions.create(
            session_id=session_id,
            user_key=user_key,
            max_history=max_history,
            followup_window_seconds=followup_window_seconds,
            max_queue_size=max_queue_size,
        )

    def get_session(self, session_id: str) -> Optional["AgentSession"]:
        return self.sessions.get(session_id)

    def close_session(self, session_id: str):
        self.sessions.close(session_id)

    def find_active_session(self, user_key: str) -> Optional["AgentSession"]:
        return self.sessions.find_active(user_key)

    def list_sessions(self, user_key: Optional[str] = None) -> list[dict]:
        return self.sessions.list(user_key=user_key)

    def get_session_status(self, session_id: str) -> Optional[str]:
        return self.sessions.status(session_id)

    def inject_message(self, session_id: str, message: Message):
        self.sessions.inject(session_id, message)

    async def run_event_stream(
        self,
        query: str,
        skills: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        history: Optional[list[dict]] = None,
        user_key: Optional[str] = None,
    ) -> AsyncIterator["AgentEvent"]:
        """
        Public execution stream entrypoint.

        Delegates to AgentRuntime so adapters and tests use a single runtime
        boundary with timing metadata.
        """
        async for event in self.runtime.run_event_stream(
            query=query,
            skills=skills,
            session_id=session_id,
            history=history,
            user_key=user_key,
        ):
            yield event

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
            if active_session.get_status() == "idle":
                # Session is idle - execute query on existing session
                logger.info(
                    "Reusing idle session %s for user %s",
                    active_session.session_id,
                    user_key,
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
                logger.info(
                    "Injecting into running session %s for user %s",
                    active_session.session_id,
                    user_key,
                )

                # Inject into Agent's session queue (not AgentSession's queue)
                # This will be checked in run_event_stream's inner loop
                from fastreact.core.messages import Message

                intervention_msg = Message.steering(
                    query,
                    source="feishu",  # Pass as keyword argument, not nested dict
                    user_intervention=True
                )

                logger.debug("Pushing intervention message to queue %s", active_session.session_id)
                self._session_queues[active_session.session_id].push(intervention_msg)

                # Verify message was added
                queue_after = self._session_queues.get(active_session.session_id, MessageQueue())
                logger.debug("After push, queue has %s messages", len(queue_after._messages))

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

    async def _run_event_stream_impl(
        self,
        query: str,
        skills: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        history: Optional[list[dict]] = None,
        user_key: Optional[str] = None,
    ) -> AsyncIterator["AgentEvent"]:
        """Compatibility shim; AgentRuntime owns the execution loop."""
        async for event in self.runtime._run_event_stream_impl(
            query=query,
            skills=skills,
            session_id=session_id,
            history=history,
            user_key=user_key,
        ):
            yield event

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
        return self.skill_resolver.list_available()

    def get_skill(self, skill_name: str):
        """Return a skill by name for admin/read-only views."""
        return self._skills.get(skill_name)

    def list_tools(self) -> list[str]:
        """Return registered tool names."""
        return self._tools.list_all()

    def list_tool_schema_summary(self) -> list[dict]:
        """Return public tool schema summaries for admin/read-only views."""
        summaries = []
        for schema in self._tools.schemas():
            function = schema.get("function", {})
            parameters = function.get("parameters") or {}
            summaries.append({
                "name": function.get("name", ""),
                "description": function.get("description", ""),
                "parameters": sorted((parameters.get("properties") or {}).keys()),
            })
        return summaries

    def list_mcp_tools(self) -> list[str]:
        """Return registered MCP tool names."""
        if self._mcp_manager:
            return self._mcp_manager.list_mcp_tools()
        return []

    async def ensure_mcp_loaded(
        self,
        required_skills: Optional[list[str]] = None,
        user_key: Optional[str] = None,
    ) -> dict:
        """Public MCP bootstrap hook for admin/read-only endpoints."""
        return await self.mcp_bootstrapper.ensure_loaded(required_skills=required_skills, user_key=user_key)

    def list_mcp_server_status(self) -> list[dict]:
        """Return MCP server health without exposing manager internals."""
        if not self._mcp_manager or not hasattr(self._mcp_manager, "_servers"):
            return []
        statuses = []
        for server_name in self._mcp_manager._servers.keys():
            statuses.append({
                "name": server_name,
                "alive": self._mcp_manager.is_server_alive(server_name),
            })
        return statuses

    def get_temp_user_stats(self) -> dict:
        """Return temporary multi-tenant user stats when available."""
        if self._multitenant:
            return self._multitenant.get_temp_user_stats()
        return {}

    def register_temp_user_if_needed(self, user_key: str) -> bool:
        """Register a temporary user in multi-tenant mode if applicable."""
        if self._multitenant and self._multitenant.is_temp_user(user_key):
            self._multitenant.register_temp_user(user_key)
            return True
        return False

    @property
    def config(self) -> Config:
        """Expose loaded configuration for admin/read-only views."""
        return self._config

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
