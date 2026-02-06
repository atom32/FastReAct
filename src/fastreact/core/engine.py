"""
FastReAct核心引擎

高性能ReACT循环实现
- 异步并发工具调用
- 智能LRU缓存
- 流式响应支持
- 连接池复用
"""

import asyncio
import json
import re
import time
import anyio
from collections import deque
from typing import Any, Callable, Dict, List, Optional, AsyncIterator

from ..core.tool import Tool, ToolCall, ToolResult
from ..core.cache import LRUCache
from ..core.exceptions import (
    ToolNotFoundError,
    NonRetryableError,
    RetryableError,
    is_retryable_error,
    get_suggested_retry_delay,
)
from ..utils.logger import get_logger
from ..observability.events import (
    LifecycleEvent,
    AssistantEvent,
    ToolEvent,
    AgentEvent,
    EventManager,
)
from ..utils.resilience import RetryExecutor, RetryPolicy
from ..context import ContextConfig, LLMProviderConfig, ContextBuilder, get_default_context_window

# 获取logger
logger = get_logger("fastreact.engine")


# ============================================================================
# Tool Result Pruning - Smart Truncation for Context Management
# ============================================================================

def prune_tool_output(result: str, max_lines: int = 100) -> str:
    """
    Smart truncation for tool outputs to prevent context explosion.

    Uses Head/Tail mode: keeps first 50 and last 50 lines when truncated.

    Args:
        result: The tool output string to potentially truncate
        max_lines: Maximum number of lines to keep (default: 100)

    Returns:
        Original result if under limit, or truncated result with guidance message
    """
    if not result:
        return result

    lines = result.splitlines()

    # If under limit, return as-is
    if len(lines) <= max_lines:
        return result

    # Split into head and tail
    head_size = max_lines // 2
    tail_size = max_lines - head_size

    head_lines = lines[:head_size]
    tail_lines = lines[-tail_size:]
    hidden_count = len(lines) - max_lines

    # Build truncated output with guidance for LLM
    nl = '\n'
    truncated = (
        f"Output (truncated, {len(lines)} total lines):\n"
        f"{''.join(f'{line}{nl}' for line in head_lines)}"
        f"... {hidden_count} lines hidden ...\n"
        f"{''.join(f'{line}{nl}' for line in tail_lines)}"
        f"[INFO] Output was truncated. Use grep or read specific line ranges to see missing parts."
    )

    return truncated


class FastReAct:
    """
    轻量级ReACT引擎

    核心特性：
    1. 异步HTTP请求（并发工具调用）
    2. 流式响应（实时输出）
    3. 连接池复用（httpx.AsyncClient）
    4. LRU缓存（减少重复计算）
    5. 简洁清晰的实现
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4",
        tools: Optional[List[Tool]] = None,
        max_iterations: int = 5,
        max_concurrent_tools: int = 3,
        enable_streaming: bool = False,
        enable_cache: bool = True,
        cache_size: int = 1000,
        temperature: float = 0.3,  # 降低温度，增加思考确定性
        max_tokens: int = 8192,
        max_tool_retries: int = 3,
        enable_tool_retry: bool = True,
        enable_deduplication: bool = True,
        dedup_window_seconds: float = 10.0,
        enable_bootstrap: bool = True,
        workspace: Optional[str] = None,
        enable_event_stream: bool = True,
        event_callback: Optional[Callable] = None,
        context_config: Optional[ContextConfig] = None,
        # V2: 工具分组支持
        enable_groups: Optional[List[str]] = None,
        respect_group_policies: bool = True,
        # V2: 策略与审批系统
        policy_engine=None,
        approval_manager=None,
        # 配置系统：用于传递给工具创建函数
        config: Optional[Dict[str, Any]] = None,
        # Phase 3: LLMDriver 支持
        llm_driver=None,  # 新增：外部传入的 LLMDriver
    ):
        """
        初始化FastReAct引擎

        Args:
            api_key: [DEPRECATED] OpenAI API密钥，建议通过 config 传入
            base_url: [DEPRECATED] API基础URL，建议通过 config 传入
            model: [DEPRECATED] 模型名称，建议通过 config 传入
            tools: 工具列表（如果不指定，使用默认工具）
            max_iterations: 最大迭代次数
            max_concurrent_tools: 最大并发工具数
            enable_streaming: 是否启用流式响应
            enable_cache: 是否启用缓存
            cache_size: 缓存大小
            temperature: 温度参数
            max_tokens: 最大token数
            max_tool_retries: 工具调用最大重试次数（默认3）
            enable_tool_retry: 是否启用智能重试（默认True）
            enable_deduplication: 是否启用请求去重（默认True）
            dedup_window_seconds: 去重时间窗口（秒，默认10）
            enable_bootstrap: 是否启用Bootstrap配置系统（默认True）
            workspace: Bootstrap工作区路径（默认~/.fastreact）
            enable_event_stream: 是否启用事件流（默认True）
            event_callback: 事件回调函数（异步）
            context_config: 上下文管理配置（可选，使用默认值）
            enable_groups: 启用的工具分组列表（V2，如 ['file_ops', 'web']）
            respect_group_policies: 是否遵守分组策略（V2，默认True）
            policy_engine: 工具策略引擎实例（V2，可选）
            approval_manager: 审批管理器实例（V2，可选）
            llm_driver: LLMDriver 实例（推荐，优先级最高）

        Note:
            - 优先使用 llm_driver 参数传入 LLMDriver 实例
            - 如果未传入 llm_driver 但 enable_bootstrap=True，将自动从 config 创建 LLMDriver
            - 直接传入 api_key/base_url/model 的方式已废弃，建议使用配置系统
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_iterations = max_iterations
        self.max_concurrent_tools = max_concurrent_tools
        self.enable_streaming = enable_streaming
        self.enable_cache = enable_cache
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_tool_retries = max_tool_retries
        self.enable_tool_retry = enable_tool_retry
        self.enable_deduplication = enable_deduplication
        self.dedup_window_seconds = dedup_window_seconds
        self.enable_bootstrap = enable_bootstrap
        self.workspace = workspace
        self.enable_event_stream = enable_event_stream
        self.event_callback = event_callback
        self.config = config or {}

        # V2: 工具分组系统
        self.enable_groups = enable_groups
        self.respect_group_policies = respect_group_policies
        self._tool_manager = None
        if enable_groups is not None:
            try:
                from ..core.tool_manager import get_global_manager
                self._tool_manager = get_global_manager()
                logger.info(f"Tool groups enabled: {enable_groups}")
            except Exception as e:
                logger.warning(f"Failed to initialize tool manager: {e}")

        # V2: 策略与审批系统
        self._policy_engine = policy_engine
        self._approval_manager = approval_manager
        if policy_engine:
            logger.info("Policy engine enabled")
        if approval_manager:
            logger.info("Approval manager enabled")
            # 设置用户输入回调（用于审批请求）
            if hasattr(approval_manager, 'set_user_input_callback'):
                approval_manager.set_user_input_callback(self._handle_approval_request)

        # 将策略和审批系统附加到工具管理器
        if self._tool_manager:
            if policy_engine:
                self._tool_manager.set_policy_engine(policy_engine)
            if approval_manager:
                self._tool_manager.set_approval_manager(approval_manager)

        # 事件管理器
        self._event_manager = EventManager()
        if event_callback:
            self._event_manager.on_event(event_callback)

        # 重试执行器
        self._retry_executor = RetryExecutor(RetryPolicy(
            max_attempts=max_tool_retries
        ))

        # Bootstrap 配置系统
        self._bootstrap_loader = None
        if enable_bootstrap:
            try:
                from ..bootstrap.loader import BootstrapLoader
                self._bootstrap_loader = BootstrapLoader(workspace=workspace)
                logger.info(f"Bootstrap enabled: {self._bootstrap_loader.workspace}")
            except Exception as e:
                logger.warning(f"Failed to initialize Bootstrap: {e}")

        # 上下文管理配置
        from ..context import ContextConfig
        if context_config is None and config is not None:
            # Create ContextConfig from config dict
            self._context_config = ContextConfig.from_dict(config)
        else:
            self._context_config = context_config or ContextConfig()
        self._llm_config = LLMProviderConfig(
            name=model,
            model=model,
            max_tokens=max_tokens,
            context_window=get_default_context_window(model),
            temperature=temperature,
            base_url=base_url,
            api_key=api_key,
        )
        self._context_builder: Optional[ContextBuilder] = None

        # Memory Flush (if enabled)
        self._memory_flush = None
        if context_config and context_config.memory_flush_enabled:
            try:
                from ..context import Summarizer, MemoryFlush

                # Create summarizer
                summarizer = Summarizer(
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    prompt=context_config.memory_flush_prompt,
                    temperature=context_config.memory_flush_temperature,
                )

                # Create memory flush
                self._memory_flush = MemoryFlush(
                    summarizer=summarizer,
                    context_config=context_config,
                )
                logger.info("Memory Flush enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Memory Flush: {e}")

        # Progressive Compaction (if enabled)
        self._compaction = None
        if context_config and context_config.compaction and context_config.compaction.enabled:
            try:
                from ..context import Summarizer, ProgressiveCompaction

                # Create summarizer for compaction (reuse if exists)
                if context_config.memory_flush_enabled:
                    # Reuse the summarizer created for Memory Flush
                    compaction_summarizer = summarizer
                else:
                    # Create new summarizer for compaction
                    compaction_summarizer = Summarizer(
                        api_key=api_key,
                        base_url=base_url,
                        model=model,
                        temperature=0.3,  # Lower temperature for consistent summaries
                    )

                # Create progressive compaction
                self._compaction = ProgressiveCompaction(
                    summarizer=compaction_summarizer,
                    base_chunk_ratio=context_config.compaction.base_chunk_ratio,
                    min_chunk_ratio=context_config.compaction.min_chunk_ratio,
                    safety_margin=context_config.compaction.safety_margin,
                    summary_levels=context_config.compaction.summary_levels,
                )
                logger.info(
                    f"Progressive Compaction enabled: "
                    f"trigger_threshold={context_config.compaction.trigger_threshold_tokens} tokens, "
                    f"auto_compact={context_config.compaction.auto_compact}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Progressive Compaction: {e}")

        # Memory Retriever (if enabled)
        self._retriever = None
        self._retrieval_config = self._context_config.retrieval if self._context_config else None
        self._embedding_generator = None
        self._model_change_callback = None
        if self._retrieval_config and self._retrieval_config.enabled:
            try:
                self._setup_retriever()
            except Exception as e:
                logger.warning(f"Failed to initialize Memory Retriever: {e}")
                self._retriever = None
                self._retrieval_config = None
                self._embedding_generator = None
                self._model_change_callback = None

        # 工具注册表
        self.tools: Dict[str, Tool] = {}

        # V2: 使用工具分组系统
        if self._tool_manager and self.enable_groups:
            # 从工具管理器获取指定分组的工具
            from ..tools import create_builtin_tools
            all_tools = create_builtin_tools(config=self.config, model=self.model)

            # 注册所有工具到工具管理器
            for tool in all_tools:
                if tool.group:
                    self._tool_manager.register_tool(tool, tool.group, overwrite=True)

            # 获取启用的分组工具
            group_tools = self._tool_manager.get_tools_by_groups(
                self.enable_groups,
                respect_policies=self.respect_group_policies
            )

            for tool in group_tools:
                self.register_tool(tool)

            logger.info(f"Loaded {len(self.tools)} tools from groups: {self.enable_groups}")
        elif tools:
            # 传统方式：直接使用传入的工具列表
            for tool in tools:
                self.register_tool(tool)

        # MCP (Model Context Protocol) 集成
        # 标记为需要异步加载（延迟到第一次 run_async 时）
        self._mcp_manager = None
        self._mcp_loaded = False
        self._mcp_enabled = self.config.get("mcp", {}).get("enabled", False)
        if self._mcp_enabled:
            logger.info("MCP enabled - will load tools on first use")

        # Sprint 4: Reactive Loop - Message Pumps
        # 初始化转向泵（需要中断队列）
        self._steering_pump = None
        self._interrupt_queue = None
        self._enable_reactive_loop = self.config.get("reactive_loop", {}).get("enabled", False)
        if self._enable_reactive_loop or policy_engine:
            try:
                from .pumps import SteeringPump
                from ..graph.interrupt import PriorityInterruptQueue

                # 创建或复用中断队列
                self._interrupt_queue = PriorityInterruptQueue()
                self._steering_pump = SteeringPump(
                    interrupt_queue=self._interrupt_queue,
                    policy_engine=policy_engine,
                )
                logger.info("[SPRINT-4] Reactive Loop enabled with SteeringPump")
            except Exception as e:
                logger.warning(f"[SPRINT-4] Failed to initialize SteeringPump: {e}")

        # Sprint 4: FollowUp Pump - Task chaining
        self._followup_pump = None
        self._task_scheduler = None
        if self._enable_reactive_loop:
            try:
                from .pumps import FollowUpPump
                from .scheduler import SimpleTaskScheduler

                # 创建任务调度器
                self._task_scheduler = SimpleTaskScheduler()

                # 创建跟进泵
                self._followup_pump = FollowUpPump(
                    task_scheduler=self._task_scheduler,
                )
                logger.info("[SPRINT-4] FollowUpPump enabled with SimpleTaskScheduler")
            except Exception as e:
                logger.warning(f"[SPRINT-4] Failed to initialize FollowUpPump: {e}")

        # LRU缓存
        self.cache = LRUCache(max_size=cache_size) if enable_cache else None

        # 异步客户端（延迟初始化）
        self._client = None
        self._http_client = None

        # Phase 3-4: LLMDriver 支持
        if llm_driver is not None:
            # 外部传入的 LLMDriver（优先级最高）
            self._llm_driver = llm_driver
            self._use_driver = True
            logger.info("Using external LLMDriver")
        elif enable_bootstrap and config:
            # Bootstrap 模式：自动创建 LLMDriver
            try:
                from ..llm import create_llm_driver_from_config
                self._llm_driver = create_llm_driver_from_config(config)
                self._use_driver = True
                logger.info("Auto-created LLMDriver from Bootstrap config")
            except Exception as e:
                logger.warning(f"Failed to create LLMDriver from config: {e}")
                self._llm_driver = None
                self._use_driver = False
        else:
            # 兼容旧方式：延迟初始化（保留向后兼容）
            self._llm_driver = None
            self._use_driver = False
            logger.debug("LLMDriver not provided, will use legacy _get_client() path")

        # 请求去重（时间窗口内的最近调用）
        self._recent_calls: deque = deque()
        self._recent_results: Dict[str, Any] = {}

        # 进度回调（用于显示长时间运行的工具的进度）
        self._progress_callback: Optional[Callable[[str], None]] = None

        # 性能统计
        self.stats = {
            "total_calls": 0,
            "total_time": 0.0,
            "tool_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "tool_retries": 0,  # 新增：重试次数统计
            "tool_errors": 0,    # 新增：错误次数统计
            "dedup_hits": 0,    # 新增：去重命中次数
        }

        # 延迟初始化：标记是否已注入 LLM client 到工具
        self._llm_client_injected = False

    def register_tool(self, tool: Tool) -> None:
        """注册工具"""
        self.tools[tool.name] = tool

    def _ensure_llm_client_injected(self):
        """确保需要 LLM client 的工具已经注入 client"""
        if self._llm_client_injected:
            return

        # 获取 client（这会触发初始化）
        client = self._get_client()

        # 注入到需要 client 的工具
        if "deep_research" in self.tools:
            tool = self.tools["deep_research"]
            # 检查工具是否需要注入 client
            import inspect
            closure_vars = inspect.getclosurevars(tool.execute)

            # 如果 llm_client 是 None，则注入
            if "llm_client" in closure_vars.nonlocals and closure_vars.nonlocals["llm_client"] is None:
                # 重新创建工具并注入 client
                from ..tools import create_deep_research_tool
                tavily_api_key = self.config.get("tools", {}).get("tavily", {}).get("api_key")

                new_tool = create_deep_research_tool(
                    llm_client=client,
                    tavily_api_key=tavily_api_key,
                    model=self.model,  # 传入模型名
                )
                self.tools["deep_research"] = new_tool
                logger.info("LLM client injected to deep_research tool")

        self._llm_client_injected = True

    def set_progress_callback(self, callback: Optional[Callable[[str], None]]):
        """设置进度回调函数

        Args:
            callback: 接收进度消息的回调函数，参数为字符串
        """
        self._progress_callback = callback

    def set_workspace(self, workspace: str, db_path: Optional[str] = None) -> None:
        """动态切换工作区（多租户支持）

        允许在运行时切换 RAG 检索的工作区，支持多租户场景。
        切换后，所有后续检索操作将使用新的工作区。

        Args:
            workspace: 新的工作区路径（支持绝对或相对路径）
            db_path: 可选的向量数据库路径。如果不提供，将在 workspace 目录下创建 memory.db

        Examples:
            >>> agent.set_workspace("./tenant_a/docs")
            >>> agent.set_workspace("/data/tenant_b/knowledge")
            >>> agent.set_workspace("./tenant_c", db_path="./tenant_c/memory.db")

        Multi-Tenant Usage:
            >>> # Tenant A
            >>> agent.set_workspace("./tenants/a/docs")
            >>> result_a = await agent.run_async("查询 A 的文档")
            >>>
            >>> # Tenant B
            >>> agent.set_workspace("./tenants/b/docs")
            >>> result_b = await agent.run_async("查询 B 的文档")
        """
        import os

        # Convert to absolute path for consistency
        workspace_abs = os.path.abspath(workspace)

        # Generate db_path if not provided
        if db_path is None:
            db_path = os.path.join(workspace_abs, "memory.db")

        # Update workspace attribute
        self.workspace = workspace_abs

        # Update retrieval config if retriever is enabled
        if self._retrieval_config:
            # Update workspace_paths
            self._retrieval_config.workspace_paths = [workspace_abs]

            # Update db_path
            self._retrieval_config.db_path = os.path.abspath(db_path)

            logger.info(
                f"Workspace switched: path={workspace_abs}, "
                f"db={self._retrieval_config.db_path}"
            )

            # Re-initialize retriever with new config
            if self._retriever is not None:
                try:
                    # Close old retriever resources
                    if hasattr(self._retriever, 'close'):
                        self._retriever.close()

                    # Re-setup retriever with new config
                    self._setup_retriever()

                    logger.info("Memory Retriever re-initialized with new workspace")
                except Exception as e:
                    logger.error(f"Failed to re-initialize retriever: {e}")
                    # Keep old retriever if re-init fails
        else:
            logger.info(
                f"Workspace updated (RAG disabled): {workspace_abs}. "
                f"Enable retrieval config to use RAG."
            )

    def get_workspace(self) -> Optional[str]:
        """获取当前工作区路径

        Returns:
            当前工作区的绝对路径，如果未设置则返回 None
        """
        return self.workspace

    def _get_context_builder(self) -> ContextBuilder:
        """获取或创建 ContextBuilder 实例

        Returns:
            ContextBuilder 实例
        """
        if self._context_builder is None:
            self._context_builder = ContextBuilder(
                context_config=self._context_config,
                llm_config=self._llm_config,
            )
            logger.debug("ContextBuilder initialized")
        return self._context_builder

    def _setup_retriever(self) -> None:
        """Setup memory retriever for semantic search

        Initializes:
        - Embedding generator (ModelScope/Qwen3)
        - Vector store (SQLite-vec)
        - Memory retriever
        - BM25 retriever (if hybrid search enabled)

        Raises:
            ImportError: If required dependencies are missing
            Exception: If initialization fails
        """
        from ..memory import (
            MemoryRetriever,
            EmbeddingGenerator,
            VectorStoreBuilder,
            create_model_change_callback,
        )

        # Create embedding provider
        provider = EmbeddingGenerator.create_provider(
            provider_name=self._retrieval_config.provider,
            model_id=self._retrieval_config.embedding_model,
            device=self._retrieval_config.device,
        )

        # Create embedding generator with cache
        generator = EmbeddingGenerator(
            provider=provider,
            enable_cache=True,
            cache_size=10000,
            db_path=self._retrieval_config.db_path.replace(".db", "_embedding_cache.db"),
        )

        # Create model change callback (interactive for CLI)
        model_change_callback = create_model_change_callback(interactive=True)

        # NOTE: We'll initialize the generator later (async)
        # Store for later initialization
        self._embedding_generator = generator
        self._model_change_callback = model_change_callback

        # Get embedding dimension from provider (try sync method first)
        embedding_dim = provider.get_embedding_dim_sync()
        if embedding_dim is None:
            # Fallback to config value for backward compatibility
            embedding_dim = self._retrieval_config.embedding_dim if hasattr(self._retrieval_config, 'embedding_dim') else 1536
            logger.info(f"Using embedding_dim from config: {embedding_dim}")

        # Create vector store
        vector_store = VectorStoreBuilder.create(
            backend=self._retrieval_config.vector_store,
            db_path=self._retrieval_config.db_path,
            embedding_dim=embedding_dim,
        )

        # Get hybrid search config (if enabled)
        hybrid_config = self._retrieval_config.hybrid_search

        # Create retriever
        self._retriever = MemoryRetriever(
            vector_store=vector_store,
            embedding_generator=generator,
            chunk_size=self._retrieval_config.chunk_size,
            chunk_overlap=self._retrieval_config.chunk_overlap,
            top_k=self._retrieval_config.top_k,
            min_similarity=self._retrieval_config.min_similarity,
            hybrid_config=hybrid_config,  # NEW: Pass hybrid search config
        )

        # Log initialization info
        hybrid_info = ""
        if hybrid_config and hybrid_config.enabled:
            hybrid_info = f", hybrid={hybrid_config.fusion_method}, alpha={hybrid_config.alpha}"

        logger.info(
            f"Memory Retriever initialized: "
            f"model={self._retrieval_config.embedding_model}, "
            f"device={self._retrieval_config.device}, "
            f"top_k={self._retrieval_config.top_k}"
            f"{hybrid_info}"
        )

    async def _load_mcp_tools(self) -> None:
        """Load tools from MCP (Model Context Protocol) servers

        This method:
        1. Reads MCP server config from self.config
        2. Initializes MCPClientManager
        3. Connects to all configured servers
        4. Fetches tools from each server
        5. Wraps and registers MCP tools

        Raises:
            ImportError: If MCP dependencies are missing
            Exception: If connection or tool loading fails
        """
        try:
            from ..tools.mcp_client_manager import MCPClientManager
        except ImportError as e:
            logger.error(f"MCP dependencies not available: {e}")
            logger.error("Install with: pip install mcp")
            return

        # Get MCP config
        mcp_config = self.config.get("mcp", {})
        servers_config = mcp_config.get("servers", {})

        if not servers_config:
            logger.warning("MCP enabled but no servers configured")
            return

        logger.info(f"Loading MCP tools from {len(servers_config)} server(s)...")

        # Create MCP manager
        self._mcp_manager = MCPClientManager()

        # Add servers
        for server_name, server_config in servers_config.items():
            try:
                # Build server config dict
                # Check if it's stdio or http
                if "command" in server_config:
                    # stdio transport
                    config = {
                        "command": server_config["command"],
                        "args": server_config.get("args", []),
                        "env": server_config.get("env", {}),
                    }
                elif "url" in server_config:
                    # http transport
                    config = {
                        "url": server_config["url"],
                        "headers": server_config.get("headers", {}),
                    }
                else:
                    logger.error(f"Invalid server config for '{server_name}': missing 'command' or 'url'")
                    continue

                self._mcp_manager.add_server(server_name, config)
                logger.info(f"  Registered MCP server: {server_name}")
            except Exception as e:
                logger.error(f"Failed to register server '{server_name}': {e}")

        # Connect to all servers and fetch tools
        # Note: We DON'T use auto_connect() as a context manager here
        # because we need to keep connections alive for the agent's lifetime
        try:
            # Connect to all servers
            await self._mcp_manager.connect_all()

            # Get server status
            status = self._mcp_manager.get_server_status()
            connected_count = sum(1 for connected in status.values() if connected)
            logger.info(f"MCP: Connected to {connected_count}/{len(servers_config)} server(s)")

            # Show connection details
            for server_name, connected in status.items():
                status_str = "[OK]" if connected else "[FAILED]"
                logger.info(f"  {status_str} {server_name}")

            # Fetch and register tools
            mcp_tools = await self._mcp_manager.get_all_tools()
            logger.info(f"MCP: Fetched {len(mcp_tools)} tool(s)")

            # Register each MCP tool
            for tool in mcp_tools:
                self.register_tool(tool)
                logger.info(f"  [+] {tool.name} ({tool.group})")

            logger.info(f"MCP: Registered {len(mcp_tools)} tool(s) successfully")
            self._mcp_loaded = True

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to connect/fetch MCP tools: {error_msg}")

            # Provide helpful guidance for common errors
            if "ERR_UNSUPPORTED_DIR_IMPORT" in error_msg:
                logger.warning("")
                logger.warning("=" * 70)
                logger.warning("[MCP Environment Issue Detected]")
                logger.warning("=" * 70)
                logger.warning("This error is caused by an upstream Node.js v24 compatibility")
                logger.warning("issue with certain npm packages (not FastReAct code).")
                logger.warning("")
                logger.warning("Solutions:")
                logger.warning("  1. Use Python-based MCP servers")
                logger.warning("  2. Use HTTP-transport MCP servers")
                logger.warning("  3. Downgrade Node.js to v20 LTS for npx-based servers")
                logger.warning("")
                logger.warning("FastReAct will continue to function with built-in tools.")
                logger.warning("=" * 70)
                logger.warning("")
            else:
                import traceback
                logger.error(traceback.format_exc())

            # Mark as loaded but with errors (don't retry)
            self._mcp_loaded = True
            return

    async def _build_messages_context(
        self,
        query: str,
        session_context: Optional[Dict[str, Any]] = None,
        iteration: int = 0,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """构建带上下文的消息列表（替代硬编码的 [-10:]）

        Args:
            query: 用户查询
            session_context: 可选的会话上下文，包含 history
            iteration: 当前迭代次数（用于 Memory Flush）

        Returns:
            Tuple of (messages, metadata)
            - messages: 消息列表
            - metadata: 包含 token 使用情况的元数据
        """
        system_prompt = self._build_system_prompt()
        history = list(session_context.get("history", [])) if session_context else None

        # 检查是否需要 Memory Flush
        if history and self._memory_flush:
            # 计算当前 token 数
            from ..context import TokenCounter
            counter = TokenCounter(model=self.model)

            history_tokens = counter.count_messages_tokens(history)
            system_tokens = counter.count_system_prompt_tokens(system_prompt)
            query_tokens = counter.count_tokens(query)
            total_tokens = system_tokens + history_tokens + query_tokens

            # 检查触发条件
            if self._memory_flush.should_trigger(
                current_tokens=total_tokens,
                context_window=self._llm_config.context_window,
                iteration=iteration,
            ):
                logger.info(f"Memory Flush triggered at iteration {iteration}")

                # 执行 flush（这将更新 history）
                try:
                    session_id = session_context.get("session_id", "unknown") if session_context else "unknown"
                    flush_metadata, updated_history = await self._memory_flush.flush_and_update_context(
                        history=history,
                        session_id=session_id,
                        iteration=iteration,
                    )

                    # 更新 session_context 中的 history
                    if session_context:
                        session_context["history"] = updated_history

                        # 存储总结到 metadata
                        if "flush_metadata" not in session_context:
                            session_context["flush_metadata"] = []
                        session_context["flush_metadata"].append(flush_metadata)

                    # 使用更新后的 history
                    history = updated_history

                    logger.info(
                        f"Memory Flush complete: {flush_metadata['message_count']} -> "
                        f"{len(updated_history)} messages"
                    )

                except Exception as e:
                    logger.error(f"Memory Flush failed, continuing with original history: {e}")

        # ========== Progressive Compaction ==========
        if history and self._compaction and context_config.compaction.auto_compact:
            # 计算当前 token 数
            from ..context import TokenCounter
            counter = TokenCounter(model=self.model)

            history_tokens = counter.count_messages_tokens(history)
            system_tokens = counter.count_system_prompt_tokens(system_prompt)
            query_tokens = counter.count_tokens(query)
            total_tokens = system_tokens + history_tokens + query_tokens

            # 检查是否需要渐进式压缩（阈值通常比 Memory Flush 高）
            trigger_threshold = context_config.compaction.trigger_threshold_tokens
            if total_tokens >= trigger_threshold:
                logger.info(
                    f"Progressive Compaction triggered at iteration {iteration}: "
                    f"{total_tokens} tokens >= {trigger_threshold} threshold"
                )

                try:
                    # 计算目标压缩级别（基于超出的 token 数量）
                    excess_tokens = total_tokens - trigger_threshold
                    if excess_tokens > 20000:
                        target_level = 3  # Ultra-compressed
                    elif excess_tokens > 10000:
                        target_level = 2  # Compressed
                    else:
                        target_level = 1  # Single summary

                    logger.info(f"Compaction target level: {target_level}")

                    # 执行压缩
                    compaction_result = await self._compaction.compact(
                        messages=history,
                        target_level=target_level,
                        current_tokens=total_tokens,
                        context_window=self._llm_config.context_window,
                    )

                    # 将压缩结果转换为消息格式
                    if compaction_result.compressed_text:
                        # 创建压缩历史消息
                        compacted_message = {
                            "role": "system",
                            "content": (
                                f"[Compacted Conversation History - Level {target_level}]\n"
                                f"Original: {compaction_result.original_tokens} tokens, "
                                f"Compressed: {compaction_result.compressed_tokens} tokens "
                                f"({compaction_result.compression_ratio:.1%})\n\n"
                                f"{compaction_result.compressed_text}"
                            ),
                        }

                        # 替换历史为压缩版本
                        history = [compacted_message]

                        # 存储压缩元数据
                        if session_context:
                            if "compaction_metadata" not in session_context:
                                session_context["compaction_metadata"] = []
                            session_context["compaction_metadata"].append({
                                "level": target_level,
                                "original_tokens": compaction_result.original_tokens,
                                "compressed_tokens": compaction_result.compressed_tokens,
                                "compression_ratio": compaction_result.compression_ratio,
                                "preserved_nodes": compaction_result.preserved_nodes,
                            })

                        logger.info(
                            f"Progressive Compaction complete: "
                            f"{compaction_result.original_tokens} -> "
                            f"{compaction_result.compressed_tokens} tokens "
                            f"({compaction_result.compression_ratio:.1%} ratio)"
                        )

                except Exception as e:
                    logger.error(f"Progressive Compaction failed, continuing with original history: {e}")

        # ========== 记忆检索 ==========
        retrieved_context = ""
        if self._retriever and self._retrieval_config.enabled:
            try:
                # Lazy initialization of vector store
                await self._retriever.initialize()

                # Initialize embedding generator if not yet initialized
                if self._embedding_generator and not self._embedding_generator._initialized:
                    await self._embedding_generator.initialize(
                        on_model_change=self._model_change_callback,
                    )

                # 检索相关历史对话
                # Note: top_k and min_similarity are already set in retriever initialization
                results = await self._retriever.retrieve(
                    query=query,
                    session_id=session_context.get("session_id") if session_context else None,
                )

                if results:
                    # 格式化检索结果
                    context_chunks = []
                    for i, result in enumerate(results[:self._retrieval_config.max_context_chunks]):
                        chunk_text = result.get("content", "")[:500]  # 限制chunk长度
                        similarity = result.get("similarity", 0)
                        context_chunks.append(f"[{i+1}] {chunk_text}... (相似度: {similarity:.2f})")

                    retrieved_context = self._retrieval_config.template.format(
                        context="\n".join(context_chunks)
                    )

                    logger.debug(f"Retrieved {len(results)} chunks for query")

            except Exception as e:
                logger.error(f"Memory retrieval failed: {e}")

        # 注入检索结果到系统提示
        if retrieved_context and self._retrieval_config.inject_position == "system":
            system_prompt = f"{retrieved_context}{system_prompt}"
        # ========== 检索结束 ==========

        # 使用 ContextBuilder 构建上下文
        context_builder = self._get_context_builder()
        messages, metadata = context_builder.build_context(
            system_prompt=system_prompt,
            user_query=query,
            history=history,
        )

        logger.debug(
            f"Context built: {metadata['history_messages_used']}/{metadata['history_messages_total']} messages, "
            f"{metadata['total_tokens']} tokens total"
        )

        # 注入检索结果到 user position（如果配置）
        if retrieved_context and self._retrieval_config.inject_position == "user":
            # 在用户查询之前插入检索上下文
            messages.insert(-1, {
                "role": "system",
                "content": retrieved_context
            })

        return messages, metadata

    async def _emit_event(self, event: AgentEvent) -> None:
        """
        发送事件到回调

        Args:
            event: 事件对象
        """
        if self.enable_event_stream and self._event_manager:
            await self._event_manager.emit(event)

    async def _emit_lifecycle(self, phase: str, error: str = None) -> None:
        """发送生命周期事件"""
        import uuid
        run_id = getattr(self, '_run_id', f"run_{uuid.uuid4().hex[:12]}")

        await self._emit_event(LifecycleEvent(
            type="lifecycle",
            phase=phase,
            run_id=run_id,
            error=error
        ))

    async def _emit_assistant_delta(self, delta: str) -> None:
        """发送助手输出事件"""
        import uuid
        run_id = getattr(self, '_run_id', f"run_{uuid.uuid4().hex[:12]}")

        await self._emit_event(AssistantEvent(
            type="assistant",
            run_id=run_id,
            delta=delta
        ))

    async def _emit_tool_start(self, tool_name: str, tool_call_id: str, args: dict) -> None:
        """发送工具开始事件"""
        import uuid
        run_id = getattr(self, '_run_id', f"run_{uuid.uuid4().hex[:12]}")

        await self._emit_event(ToolEvent(
            type="tool",
            phase="start",
            run_id=run_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            args=args
        ))

    async def _emit_tool_result(self, tool_name: str, tool_call_id: str, result: Any, duration_ms: float) -> None:
        """发送工具结果事件"""
        import uuid
        run_id = getattr(self, '_run_id', f"run_{uuid.uuid4().hex[:12]}")

        await self._emit_event(ToolEvent(
            type="tool",
            phase="result",
            run_id=run_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            result=str(result)[:500] if result else None,
            duration_ms=duration_ms
        ))

    async def _emit_tool_error(self, tool_name: str, tool_call_id: str, error: str) -> None:
        """发送工具错误事件"""
        import uuid
        run_id = getattr(self, '_run_id', f"run_{uuid.uuid4().hex[:12]}")

        await self._emit_event(ToolEvent(
            type="tool",
            phase="error",
            run_id=run_id,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            error=error
        ))

    def _get_client(self):
        """
        获取或创建异步客户端

        [DEPRECATED] 此方法已废弃，请使用 LLMDriver 代替

        警告：直接使用 OpenAI 客户端绕过了 LLMDriver 的重试、缓存和日志功能。
        建议通过 FastReAct 构造函数传入 llm_driver 参数。

        计划移除版本：v2.0.0
        """
        import warnings
        warnings.warn(
            "_get_client() is deprecated and will be removed in v2.0.0. "
            "Use LLMDriver instead by passing llm_driver parameter to FastReAct.__init__(). "
            "Direct client usage bypasses retry, caching, and logging features.",
            DeprecationWarning,
            stacklevel=2
        )

        if self._client is None:
            try:
                from openai import AsyncOpenAI
                import httpx

                # 创建带连接池的HTTP客户端
                self._http_client = httpx.AsyncClient(
                    limits=httpx.Limits(
                        max_connections=100,
                        max_keepalive_connections=20,
                    ),
                    timeout=60.0,
                )

                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    http_client=self._http_client,
                    max_retries=2,
                )
            except ImportError:
                raise ImportError("请安装 openai>=1.0.0 和 httpx>=0.25.0")

        return self._client

    def _get_cache_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """生成缓存键"""
        return f"{tool_name}:{json.dumps(params, sort_keys=True)}"

    def _get_dedup_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """生成去重键"""
        return self._get_cache_key(tool_name, params)

    def _clean_expired_dedup_entries(self):
        """清理过期的去重记录"""
        current_time = time.time()
        cutoff_time = current_time - self.dedup_window_seconds

        # 移除时间窗口外的记录
        while self._recent_calls and self._recent_calls[0][0] < cutoff_time:
            timestamp, dedup_key = self._recent_calls.popleft()
            # 只从结果字典中移除（如果该键没有更新的话）
            if dedup_key in self._recent_results:
                # 检查是否有更新的记录
                has_newer = False
                for ts, key in self._recent_calls:
                    if key == dedup_key:
                        has_newer = True
                        break
                if not has_newer:
                    del self._recent_results[dedup_key]

    def _check_duplicate(self, tool_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        检查是否为重复调用

        Args:
            tool_name: 工具名称
            params: 工具参数

        Returns:
            如果是重复调用，返回缓存结果；否则返回 None
        """
        if not self.enable_deduplication:
            return None

        # 清理过期记录
        self._clean_expired_dedup_entries()

        # 生成去重键
        dedup_key = self._get_dedup_key(tool_name, params)

        # 检查是否在时间窗口内已调用过
        if dedup_key in self._recent_results:
            self.stats["dedup_hits"] += 1
            logger.debug(
                f"Duplicate tool call detected: {tool_name}",
                extra={
                    "tool": tool_name,
                    "dedup_key": dedup_key[:50],
                }
            )
            return self._recent_results[dedup_key]

        return None

    def _record_call(self, tool_name: str, params: Dict[str, Any], result: Any):
        """
        记录工具调用

        Args:
            tool_name: 工具名称
            params: 工具参数
            result: 执行结果
        """
        if not self.enable_deduplication:
            return

        dedup_key = self._get_dedup_key(tool_name, params)
        current_time = time.time()

        # 记录调用
        self._recent_calls.append((current_time, dedup_key))
        self._recent_results[dedup_key] = result

        # 限制 deque 大小（防止无限增长）
        max_entries = 1000
        if len(self._recent_calls) > max_entries:
            # 移除最老的记录
            old_timestamp, old_key = self._recent_calls.popleft()
            # 只在结果字典中没有更新的情况下移除
            has_newer = False
            for ts, key in self._recent_calls:
                if key == old_key:
                    has_newer = True
                    break
            if not has_newer and old_key in self._recent_results:
                del self._recent_results[old_key]

    async def _execute_tool_async(self, tool_call: ToolCall) -> ToolResult:
        """
        异步执行工具（带缓存、去重和智能重试）

        Args:
            tool_call: 工具调用对象

        Returns:
            工具执行结果
        """
        start_time = time.time()
        tool_name = tool_call.name
        params = tool_call.parameters

        # 检查工具是否存在
        tool = self.tools.get(tool_name)
        if not tool:
            logger.error(f"Tool not found: {tool_name}")
            self.stats["tool_errors"] += 1
            return ToolResult(
                tool_name=tool_name,
                result=None,
                error=f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}",
                execution_time=time.time() - start_time,
            )

        # V2: 检查工具访问权限（分组策略 + 工具策略 + 审批）
        if self._tool_manager is not None and self.respect_group_policies:
            allowed, reason, approval_id = self._tool_manager.check_tool_access_with_policy(
                tool_name,
                policy_engine=getattr(self, '_policy_engine', None),
                approval_manager=getattr(self, '_approval_manager', None),
                context={"parameters": params}
            )

            if not allowed:
                logger.warning(f"Tool '{tool_name}' access denied: {reason}")
                self.stats["tool_errors"] += 1
                return ToolResult(
                    tool_name=tool_name,
                    result=None,
                    error=f"Access denied for tool '{tool_name}': {reason}",
                    execution_time=time.time() - start_time,
                )

        # 检查去重（优先级最高，在缓存之前）
        duplicate_result = self._check_duplicate(tool_name, params)
        if duplicate_result is not None:
            # 发现重复调用，返回缓存结果
            return ToolResult(
                tool_name=tool_name,
                result=duplicate_result,
                execution_time=0.001,  # 去重命中，执行时间极短
            )

        # 检查 LRU 缓存
        if self.cache is not None:
            cache_key = self._get_cache_key(tool_name, params)
            cached_result = self.cache.get(cache_key)

            if cached_result is not None:
                self.stats["cache_hits"] += 1
                return ToolResult(
                    tool_name=tool_name,
                    result=cached_result,
                    execution_time=time.time() - start_time,
                )

        # 执行工具（带重试）
        last_error = None

        for attempt in range(self.max_tool_retries + 1):
            try:
                # 注入 progress_callback（如果工具支持）
                import inspect
                execute_params = params.copy()

                # 检查工具的 execute 函数是否接受 progress_callback 参数
                if self._progress_callback is not None:
                    sig = inspect.signature(tool.execute)
                    if 'progress_callback' in sig.parameters:
                        execute_params['progress_callback'] = self._progress_callback

                # 执行工具 - 兼容旧方式和新方式
                if hasattr(tool, 'execute_async'):
                    # 旧的 Tool 类（面向对象）
                    result = await tool.execute_async(**execute_params)
                elif hasattr(tool, 'execute') and asyncio.iscoroutinefunction(tool.execute):
                    # 新的函数式 Tool
                    result = await tool.execute(**execute_params)
                else:
                    # 同步函数式 Tool
                    result = tool.execute(**execute_params)

                execution_time = time.time() - start_time

                # 记录调用（用于去重）
                self._record_call(tool_name, params, result)

                # 更新 LRU 缓存（无论是否重试，只要成功就缓存）
                if self.cache is not None:
                    cache_key = self._get_cache_key(tool_name, params)
                    self.cache.set(cache_key, result)

                self.stats["tool_calls"] += 1
                if self.cache is not None:
                    self.stats["cache_misses"] += 1

                # 如果有重试，记录日志
                if attempt > 0:
                    logger.info(
                        f"Tool {tool_name} succeeded after {attempt} retries",
                        extra={
                            "tool": tool_name,
                            "attempt": attempt,
                            "execution_time": execution_time,
                        }
                    )

                return ToolResult(
                    tool_name=tool_name,
                    result=result,
                    execution_time=execution_time,
                )

            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                error_msg = str(e)

                # 判断是否应该重试
                should_retry = (
                    self.enable_tool_retry and
                    attempt < self.max_tool_retries and
                    is_retryable_error(e)
                )

                if should_retry:
                    self.stats["tool_retries"] += 1

                    # 计算重试延迟
                    delay = get_suggested_retry_delay(e, attempt)

                    logger.warning(
                        f"Tool {tool_name} failed (attempt {attempt + 1}/{self.max_tool_retries + 1}), "
                        f"retrying in {delay:.2f}s: {error_type}: {error_msg}",
                        extra={
                            "tool": tool_name,
                            "attempt": attempt + 1,
                            "max_retries": self.max_tool_retries + 1,
                            "error_type": error_type,
                            "error": error_msg,
                            "retry_delay": delay,
                        }
                    )

                    # 等待后重试
                    await asyncio.sleep(delay)
                else:
                    # 不可重试或达到最大重试次数
                    self.stats["tool_errors"] += 1

                    # 构建详细的错误信息
                    if isinstance(e, NonRetryableError):
                        # 自定义不可重试错误
                        error_str = f"{e.__class__.__name__}: {e.message}"
                        log_details = {
                            "error_type": e.__class__.__name__,
                            "error_details": e.details,
                            "attempt": attempt + 1,
                        }
                    elif isinstance(e, RetryableError):
                        # 可重试错误但达到最大重试次数
                        error_str = f"{e.__class__.__name__}: {e.message} (exceeded max retries)"
                        log_details = {
                            "error_type": e.__class__.__name__,
                            "error_details": e.details,
                            "attempts": attempt + 1,
                            "max_retries": self.max_tool_retries + 1,
                        }
                    else:
                        # 通用错误
                        error_str = f"{error_type}: {error_msg}"
                        log_details = {
                            "error_type": error_type,
                            "attempt": attempt + 1,
                        }

                    logger.error(
                        f"Tool {tool_name} failed permanently: {error_str}",
                        extra={
                            "tool": tool_name,
                            **log_details,
                            "execution_time": time.time() - start_time,
                        }
                    )

                    return ToolResult(
                        tool_name=tool_name,
                        result=None,
                        error=error_str,
                        execution_time=time.time() - start_time,
                    )

        # 理论上不会到达这里，但为了类型检查
        return ToolResult(
            tool_name=tool_name,
            result=None,
            error=f"Unknown error: {last_error}",
            execution_time=time.time() - start_time,
        )

    async def _execute_tools_concurrent(
        self, tool_calls: List[ToolCall]
    ) -> List[ToolResult]:
        """
        并发执行多个工具

        Args:
            tool_calls: 工具调用列表

        Returns:
            工具执行结果列表
        """
        # 限制并发数量
        calls_to_execute = tool_calls[: self.max_concurrent_tools]

        # 创建任务
        tasks = [self._execute_tool_async(call) for call in calls_to_execute]

        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        final_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final_results.append(
                    ToolResult(
                        tool_name=tool_calls[i].name, result=None, error=str(r)
                    )
                )
            else:
                final_results.append(r)

        return final_results

    async def _execute_tools_concurrent_with_events(
        self, tool_calls: List[ToolCall]
    ) -> List[ToolResult]:
        """
        并发执行多个工具（带事件流和重试）

        Args:
            tool_calls: 工具调用列表

        Returns:
            工具执行结果列表
        """
        # 限制并发数量
        calls_to_execute = tool_calls[:self.max_concurrent_tools]

        # 为每个工具调用创建异步任务
        async def execute_with_events(call: ToolCall) -> ToolResult:
            tool_call_id = getattr(call, 'call_id', f"tool_{id(call)}")

            try:
                # 发送工具开始事件
                await self._emit_tool_start(
                    tool_name=call.name,
                    tool_call_id=tool_call_id,
                    args=call.parameters
                )

                # 执行工具（带重试）
                start_time = time.time()

                # 获取工具实例
                tool = self.tools.get(call.name)
                if not tool:
                    raise ValueError(f"Tool not found: {call.name}")

                # 兼容旧方式和新方式
                if hasattr(tool, 'execute_async'):
                    # 旧的 Tool 类（面向对象）
                    execute_fn = tool.execute_async
                elif hasattr(tool, 'execute') and asyncio.iscoroutinefunction(tool.execute):
                    # 新的函数式 Tool
                    execute_fn = tool.execute
                else:
                    # 同步函数式 Tool
                    execute_fn = tool.execute

                # 使用重试执行器
                result = await self._retry_executor.execute(
                    execute_fn,
                    **call.parameters
                )

                execution_time = time.time() - start_time
                duration_ms = execution_time * 1000

                # 发送工具结果事件
                await self._emit_tool_result(
                    tool_name=call.name,
                    tool_call_id=tool_call_id,
                    result=result,
                    duration_ms=duration_ms
                )

                return ToolResult(
                    tool_name=call.name,
                    result=result,
                    execution_time=execution_time,
                )

            except Exception as e:
                # 发送工具错误事件
                await self._emit_tool_error(
                    tool_name=call.name,
                    tool_call_id=tool_call_id,
                    error=str(e)
                )

                # 返回错误结果
                return ToolResult(
                    tool_name=call.name,
                    result=None,
                    error=str(e),
                    execution_time=0
                )

        # 并发执行所有工具
        tasks = [execute_with_events(call) for call in calls_to_execute]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        final_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final_results.append(
                    ToolResult(
                        tool_name=tool_calls[i].name, result=None, error=str(r)
                    )
                )
            else:
                final_results.append(r)

        return final_results

    def _parse_tool_calls(self, llm_response: Dict[str, Any], fallback_text: str = "") -> List[ToolCall]:
        """
        从 LLM 响应中解析工具调用

        优先级：
        1. 结构化的 tool_calls（来自 Function Calling API）
        2. 正则解析（向后兼容）

        Args:
            llm_response: LLM 响应对象 {"content": "...", "tool_calls": [...]}
            fallback_text: 回退文本（用于正则解析）

        Returns:
            工具调用列表
        """
        tool_calls = []

        # 方法1：优先使用结构化的 tool_calls（最可靠）
        if "tool_calls" in llm_response and llm_response["tool_calls"]:
            logger.debug(f"Using structured tool_calls from LLM: {len(llm_response['tool_calls'])} calls")

            for tc in llm_response["tool_calls"]:
                try:
                    # OpenAI 格式：tc.function.name 和 tc.function.arguments (JSON string)
                    if hasattr(tc, 'function'):
                        name = tc.function.name
                        arguments = json.loads(tc.function.arguments) if tc.function.arguments else {}
                        call_id = tc.id
                    # 字典格式（流式响应）
                    elif isinstance(tc, dict):
                        name = tc["function"]["name"]
                        arguments = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                        call_id = tc["id"]
                    else:
                        continue

                    tool_calls.append(
                        ToolCall(
                            name=name,
                            parameters=arguments,
                            call_id=call_id,
                        )
                    )
                except (json.JSONDecodeError, KeyError, AttributeError) as e:
                    logger.warning(f"Failed to parse tool call: {e}")
                    continue

            return tool_calls

        # 方法2：回退到正则解析（兼容性）
        logger.debug("No structured tool_calls, falling back to regex parsing")
        response_cleaned = fallback_text or llm_response.get("content", "")

        # 移除 markdown 代码块标记
        response_cleaned = re.sub(r'```[\w]*\n?', '', response_cleaned)

        # 格式1: [TOOL_CALL]{"name": "...", "parameters": {...}}
        pattern1 = r"\[TOOL_CALL\]\s*(\{(?:[^{}]|(?:\{[^{}]*\}))*\})"
        for match in re.finditer(pattern1, response_cleaned, re.DOTALL):
            try:
                data = json.loads(match.group(1))
                tool_calls.append(
                    ToolCall(
                        name=data.get("name", ""),
                        parameters=data.get("parameters", {}),
                        call_id=f"call_{len(tool_calls)}",
                    )
                )
            except json.JSONDecodeError:
                continue

        # 格式2: <tool>...</tool>
        pattern2 = r"<tool>\s*(\{(?:[^{}]|(?:\{[^{}]*\}))*\})\s*</tool>"
        for match in re.finditer(pattern2, response_cleaned, re.DOTALL):
            try:
                data = json.loads(match.group(1))
                tool_calls.append(
                    ToolCall(
                        name=data.get("name", ""),
                        parameters=data.get("parameters", {}),
                        call_id=f"call_{len(tool_calls)}",
                    )
                )
            except json.JSONDecodeError:
                continue

        logger.debug(f"Parsed {len(tool_calls)} tool calls from text (regex)")
        return tool_calls

    def _build_system_prompt(self) -> str:
        """
        构建系统提示（使用模块化 PromptBuilder）

        优先级：
        1. Bootstrap 文件内容（AGENTS.md, SOUL.md, TOOLS.md）
        2. PromptBuilder 构建的模块化提示
        3. 工具描述

        注意：工具调用由 Function Calling API 自动处理，不需要格式说明
        """
        # 使用模块化 Prompt 构建器（类似 moltbot）
        from ..tools.fn_registry import Tool as FnTool
        from ..core.prompt_builder import build_system_prompt, PromptConfig

        # 将 FastReAct 的 Tool 对象转换为函数式 Tool
        tools_dict = {}
        for name, tool in self.tools.items():
            # 创建函数式 Tool 包装
            tools_dict[name] = FnTool(
                name=name,
                description=tool.description,
                parameters=tool.parameters,
                execute=tool.execute,
                label=getattr(tool, 'label', name),
                category=getattr(tool, 'category', None)
            )

        # 构建 PromptConfig（可通过外部配置扩展）
        config = PromptConfig(
            temperature=self.temperature,
            max_iterations=self.max_iterations,
            prompt_mode="full",  # full/minimal/none
            reasoning_level="off",  # 默认 off，让 LLM 自主决定
            thinking_level="concise",  # silent/concise/verbose
            workspace_dir=self.workspace if self.workspace else None,
            enable_workspace_files=bool(self.workspace),
        )

        # 使用模块化构建器生成基础 prompt
        base_prompt = build_system_prompt(tools_dict, config)

        # 如果启用 Bootstrap，注入配置文件
        if self._bootstrap_loader:
            try:
                enhanced_prompt = self._bootstrap_loader.build_system_prompt(
                    base_prompt=base_prompt,
                    inject_position="after"  # Bootstrap 内容追加到基础提示后
                )
                logger.debug("Bootstrap configuration injected into system prompt")
                return enhanced_prompt
            except Exception as e:
                logger.warning(f"Failed to inject Bootstrap: {e}")

        return base_prompt

    def _build_tools_schema(self) -> List[Dict[str, Any]]:
        """
        构建工具 schema（用于 OpenAI Function Calling API）

        Returns:
            工具 schema 列表
        """
        tools_schema = []
        for tool in self.tools.values():
            tools_schema.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        return tools_schema

    async def _chat(
        self, messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        发送聊天请求（支持 Function Calling）

        Returns:
            {
                "content": "响应内容",
                "tool_calls": [工具调用列表]  # 如果有工具调用
            }
        """
        # Phase 3: 优先使用 LLMDriver（如果可用）
        if self._use_driver and self._llm_driver is not None:
            return await self._chat_with_driver(messages)
        else:
            # 旧方式：直接调用 OpenAI 客户端（向后兼容）
            return await self._chat_with_client(messages)

    async def _chat_with_driver(
        self, messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        使用 LLMDriver 发送聊天请求

        Returns:
            {
                "content": "响应内容",
                "tool_calls": [工具调用列表]  # 如果有工具调用
            }
        """
        from ..llm import LLMDriverConfig

        # 构建 tools schema
        tools_schema = None
        if self.tools:
            tools_schema = self._build_tools_schema()

        # 调用 LLMDriver
        response = await self._llm_driver.chat(
            messages=messages,
            tools=tools_schema,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # 转换 ChatResponse 为 FastReAct 期望的格式
        result = {
            "content": response.content or "",
        }

        # LLMDriver 已经透传了原始的 tool_calls 对象
        if response.tool_calls:
            result["tool_calls"] = response.tool_calls

        return result

    async def _chat_with_client(
        self, messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        使用原始 OpenAI 客户端发送聊天请求（向后兼容）

        [DEPRECATED] 此方法为向后兼容保留，新代码应使用 _chat_with_driver()

        注意：此路径不包含 LLMDriver 的自动重试、缓存和日志功能。

        Returns:
            {
                "content": "响应内容",
                "tool_calls": [工具调用列表]  # 如果有工具调用
            }
        """
        client = self._get_client()

        # 构建请求参数
        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # 如果有工具，添加 tools 参数
        if self.tools:
            request_params["tools"] = self._build_tools_schema()
            # 让 LLM 可以在需要时调用工具
            request_params["tool_choice"] = "auto"

        response = await client.chat.completions.create(**request_params)

        message = response.choices[0].message

        # 返回内容和工具调用
        result = {
            "content": message.content or "",
        }

        # 如果有工具调用，提取出来
        if hasattr(message, 'tool_calls') and message.tool_calls:
            result["tool_calls"] = message.tool_calls

        return result

    async def _chat_with_streaming(
        self, messages: List[Dict[str, str]], callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        发送流式聊天请求（支持 Function Calling）

        Returns:
            {
                "content": "完整响应内容",
                "tool_calls": [工具调用列表]  # 如果有工具调用
            }
        """
        client = self._get_client()

        full_response = ""
        accumulated_tool_calls = {}

        # 构建请求参数
        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True,
        }

        # 如果有工具，添加 tools 参数
        if self.tools:
            request_params["tools"] = self._build_tools_schema()
            request_params["tool_choice"] = "auto"

        stream = await client.chat.completions.create(**request_params)

        async for chunk in stream:
            # 处理内容流
            delta = chunk.choices[0].delta
            if delta.content:
                full_response += delta.content
                if callback:
                    callback(delta.content)

            # 处理工具调用流
            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                for tool_call in delta.tool_calls:
                    index = tool_call.index

                    # 初始化工具调用
                    if index not in accumulated_tool_calls:
                        accumulated_tool_calls[index] = {
                            "id": tool_call.id or f"call_{index}",
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name if tool_call.function else "",
                                "arguments": ""
                            }
                        }

                    # 累积参数
                    if tool_call.function:
                        if tool_call.function.name:
                            accumulated_tool_calls[index]["function"]["name"] = tool_call.function.name
                        if tool_call.function.arguments:
                            accumulated_tool_calls[index]["function"]["arguments"] += tool_call.function.arguments

        # 构建返回结果
        result = {"content": full_response}

        # 如果有工具调用，转换为对象列表
        if accumulated_tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": tc["type"],
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"]
                    }
                }
                for tc in accumulated_tool_calls.values()
            ]

        return result

    def _extract_final_answer(self, response: str) -> str:
        """提取最终答案"""
        # 如果包含Final Answer标记
        if "Final Answer:" in response:
            return response.split("Final Answer:")[-1].strip()

        # 如果包含最终答案标记
        if "最终答案:" in response:
            return response.split("最终答案:")[-1].strip()

        # 否则返回整个响应
        return response.strip()

    def _extract_thought(self, response: str) -> str:
        """提取思考内容"""
        # 如果包含Thought:标记，提取后面的内容
        if "Thought:" in response:
            thought = response.split("Thought:")[-1].strip()
            # 去掉可能的Action:或Final Answer:部分
            if "Action:" in thought:
                thought = thought.split("Action:")[0].strip()
            if "Final Answer:" in thought:
                thought = thought.split("Final Answer:")[0].strip()
            return thought

        # 如果包含思考：标记
        if "思考：" in response:
            thought = response.split("思考：")[-1].strip()
            if "Action:" in thought:
                thought = thought.split("Action:")[0].strip()
            if "Final Answer:" in thought:
                thought = thought.split("Final Answer:")[0].strip()
            return thought

        # 否则返回整个响应（可能不包含Thought标记）
        return response.strip()

    async def run_async(
        self,
        query: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        step_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        session_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        异步运行ReACT循环

        Args:
            query: 用户查询
            stream_callback: 流式回调（实时输出）
            step_callback: 步骤回调（记录每一步）
            session_context: 会话上下文（用于多轮对话）

        Returns:
            {
                "answer": "最终答案",
                "steps": [步骤列表],
                "stats": {"tool_calls": 5, "cache_hits": 2, ...}
            }
        """
        start_time = time.time()
        self.stats["total_calls"] += 1

        # 生成 run_id
        import uuid
        self._run_id = f"run_{uuid.uuid4().hex[:12]}"

        # 发送生命周期开始事件
        await self._emit_lifecycle("start")

        # 加载 MCP 工具（如果启用且尚未加载）
        if self._mcp_enabled and not self._mcp_loaded:
            try:
                await self._load_mcp_tools()
            except Exception as e:
                logger.warning(f"MCP tool loading failed: {e}")

        # 确保需要 LLM client 的工具已经注入 client
        self._ensure_llm_client_injected()

        try:
            # 使用 ContextBuilder 构建消息上下文
            # Memory Flush 检查在 iteration 0 执行
            messages, context_metadata = await self._build_messages_context(
                query,
                session_context,
                iteration=0,  # Initial context build
            )

            steps = []

            # Sprint 4: Reactive Loop - 转向消息列表
            pending_steering_messages = []

            for iteration in range(self.max_iterations):
                # ============================================================
                # Phase 1: Ingestion - 检查转向消息（Steering Check #1）
                # ============================================================
                # 在 LLM 思考前检查用户干预/策略引擎
                if self._steering_pump:
                    try:
                        # 创建临时上下文用于泵检查
                        temp_context = type('obj', (object,), {
                            'messages': messages,
                            'iteration': iteration,
                            'metadata': {}
                        })()

                        steering_msgs = await self._steering_pump.pump(temp_context)

                        if steering_msgs:
                            # 检查是否有终止信号
                            for msg in steering_msgs:
                                if msg.metadata.get("critical"):
                                    logger.warning("[REACTIVE] Critical interrupt - terminating")
                                    elapsed = time.time() - start_time
                                    self.stats["total_time"] += elapsed
                                    await self._emit_lifecycle("end")
                                    return {
                                        "answer": f"[TERMINATED] {msg.content}",
                                        "steps": steps,
                                        "stats": self.get_stats(),
                                    }

                            # 添加转向消息到上下文
                            for msg in steering_msgs:
                                # 转换为 OpenAI 格式
                                messages.append(msg.to_dict())
                                logger.info(f"[REACTIVE] Steering message injected: {msg.source.value}")

                    except Exception as e:
                        logger.error(f"[REACTIVE] Steering pump failed: {e}")

                # ============================================================
                # Phase 2: Reasoning - 调用LLM
                # ============================================================
                if self.enable_streaming:
                    llm_response = await self._chat_with_streaming(messages, stream_callback)
                else:
                    llm_response = await self._chat(messages)

                # 提取响应内容和工具调用
                response_content = llm_response.get("content", "")

                # 发送助手输出事件
                if response_content:
                    await self._emit_assistant_delta(f"Thought: {response_content[:100]}...")

                # 记录步骤
                step = {
                    "iteration": iteration,
                    "thought": response_content,
                }

                # 解析工具调用（优先使用结构化的 tool_calls）
                tool_calls = self._parse_tool_calls(llm_response, fallback_text=response_content)

                if not tool_calls:
                    # 没有工具调用，说明是最终答案
                    step["is_final"] = True
                    step["answer"] = self._extract_final_answer(response_content)

                    if step_callback:
                        if asyncio.iscoroutinefunction(step_callback):
                            await step_callback(step)
                        else:
                            step_callback(step)
                    steps.append(step)

                    # 更新统计
                    elapsed = time.time() - start_time
                    self.stats["total_time"] += elapsed

                    # 发送生命周期结束事件
                    await self._emit_lifecycle("end")

                    return {
                        "answer": step["answer"],
                        "steps": steps,
                        "stats": self.get_stats(),
                    }

                # 执行工具调用
                # NOTE: Format is {"name": str, "parameters": dict}
                # Test suite validates parameter extraction: test_integration_4_tool_graph.py
                # Key name is 'parameters', NOT 'args' or 'params'
                step["tool_calls"] = [
                    {"name": tc.name, "parameters": tc.parameters} for tc in tool_calls
                ]

                if step_callback:
                    if asyncio.iscoroutinefunction(step_callback):
                        await step_callback(step)
                    else:
                        step_callback(step)
                steps.append(step)

                # 并发执行工具（带事件和重试）
                results = await self._execute_tools_concurrent_with_events(tool_calls)

                # 构建观察结果（应用智能截断）
                observations = []
                for result in results:
                    if result.error:
                        obs = f"[ERROR] {result.error}"
                    else:
                        # 应用智能截断 - 防止 Context 爆炸
                        pruned_result = prune_tool_output(result.result)
                        obs = f"[OK] {pruned_result}"
                    observations.append(f"**{result.tool_name}**: {obs}")

                observation_text = "\n\n".join(observations)
                step["observation"] = observation_text

                if step_callback:
                    if asyncio.iscoroutinefunction(step_callback):
                        await step_callback(step)
                    else:
                        step_callback(step)

                # 添加到消息历史
                messages.append({"role": "assistant", "content": response_content})
                messages.append(
                    {
                        "role": "user",
                        "content": f"工具返回结果:\n\n{observation_text}\n\n请基于这些信息继续思考或给出最终答案。",
                    }
                )

                # ============================================================
                # Phase 3: Post-Tool Steering Check (Double Check Mechanism)
                # ============================================================
                # 工具执行后再次检查转向消息
                # 关键创新：防止长任务执行后的"惯性错误"
                if self._steering_pump:
                    try:
                        temp_context = type('obj', (object,), {
                            'messages': messages,
                            'iteration': iteration,
                            'metadata': {}
                        })()

                        post_tool_steering = await self._steering_pump.pump(temp_context)

                        if post_tool_steering:
                            # 检查终止信号
                            for msg in post_tool_steering:
                                if msg.metadata.get("critical"):
                                    logger.warning("[REACTIVE] Critical interrupt after tools - terminating")
                                    elapsed = time.time() - start_time
                                    self.stats["total_time"] += elapsed
                                    await self._emit_lifecycle("end")
                                    return {
                                        "answer": f"[TERMINATED] {msg.content}",
                                        "steps": steps,
                                        "stats": self.get_stats(),
                                    }

                            # 添加转向消息
                            for msg in post_tool_steering:
                                messages.append(msg.to_dict())
                                logger.info(f"[REACTIVE] Post-tool steering: {msg.source.value}")

                    except Exception as e:
                        logger.error(f"[REACTIVE] Post-tool steering check failed: {e}")


            # 达到最大迭代次数
            elapsed = time.time() - start_time
            self.stats["total_time"] += elapsed

            # 发送生命周期结束事件（达到最大迭代次数）
            await self._emit_lifecycle("end")

            return {
                "answer": "达到最大迭代次数，未能完成",
                "steps": steps,
                "stats": self.get_stats(),
            }

        except Exception as e:
            # 发送错误事件
            await self._emit_lifecycle("error", error=str(e))
            raise

        finally:
            # ========== 自动索引对话到向量存储 ==========
            # 在每次查询完成后索引对话（用于未来的检索）
            if (
                self._retriever
                and self._retrieval_config.enabled
                and self._retrieval_config.auto_index
                and session_context
                and len(steps) > self._retrieval_config.index_delay
            ):
                try:
                    session_id = session_context.get("session_id", "unknown")
                    history = list(session_context.get("history", []))

                    if len(history) > 0:
                        # 异步索引（不阻塞响应）
                        await self._retriever.index_session(
                            session_id=session_id,
                            messages=history,
                        )

                        logger.debug(f"Indexed {len(history)} messages for session {session_id}")

                except Exception as e:
                    logger.error(f"Session indexing failed: {e}")
            # ========== 索引结束 ==========

    def run(
        self,
        query: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        step_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        同步运行 ReACT 循环（兼容性接口）

        [WARNING] 警告：此方法仅用于简单的同步场景。

        强烈推荐使用异步接口：
        - 在异步代码中：使用 `await run_async(...)`
        - 在同步代码中：使用 `asyncio.run(run_async(...))`

        Args:
            query: 用户查询
            stream_callback: 流式回调
            step_callback: 步骤回调

        Returns:
            执行结果

        Raises:
            RuntimeError: 如果在已有事件循环中调用（请使用 run_async 代替）
        """
        try:
            # 尝试获取当前运行的事件循环
            loop = asyncio.get_running_loop()
            # 如果成功获取，说明已在事件循环中
            raise RuntimeError(
                "Detected running event loop. The sync `run()` method cannot be called "
                "from within an async context. Please use `await run_async(...)` instead.\n"
                "\n"
                "Example:\n"
                "  # [ERROR] Wrong (will cause this error):\n"
                "  async def my_function():\n"
                "      result = react.run('query')  # Error!\n"
                "\n"
                "  # [OK] Correct:\n"
                "  async def my_function():\n"
                "      result = await react.run_async('query')\n"
                "\n"
                "  # [OK] Or use in sync context (no event loop):\n"
                "  result = asyncio.run(react.run_async('query'))"
            )
        except RuntimeError:
            # 没有运行的事件循环，可以安全使用 asyncio.run
            pass

        # 检查是否启用了 MCP
        # 如果启用了 MCP，使用 anyio.run() 以修复 Windows 兼容性问题
        # MCP SDK 的 HTTP 客户端在 Windows 上需要 anyio 事件循环
        use_anyio = self._mcp_enabled and self.config.get("mcp", {}).get("enabled", False)

        if use_anyio:
            # 使用 anyio 运行（MCP 兼容模式）
            async def run_with_anyio():
                return await self.run_async(query, stream_callback, step_callback)
            return anyio.run(run_with_anyio)
        else:
            # 没有事件循环，使用 asyncio.run（默认模式）
            return asyncio.run(self.run_async(query, stream_callback, step_callback))

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = self.stats.copy()

        # 计算缓存命中率
        if stats["cache_hits"] + stats["cache_misses"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / (
                stats["cache_hits"] + stats["cache_misses"]
            )
        else:
            stats["cache_hit_rate"] = 0.0

        # 计算平均时间
        if stats["total_calls"] > 0:
            stats["avg_time_per_call"] = stats["total_time"] / stats["total_calls"]
        else:
            stats["avg_time_per_call"] = 0.0

        return stats

    # ========================================================================
    # Sprint 4: Reactive Loop - Public API
    # ========================================================================

    def get_interrupt_queue(self):
        """
        Get the interrupt queue for reactive loop

        Allows external code (like REPL) to inject user input for cognitive steering.

        Returns:
            PriorityInterruptQueue instance, or None if reactive loop is disabled

        Example:
            ```python
            agent = FastReAct(...)
            queue = agent.get_interrupt_queue()
            if queue:
                await queue.put_user_input("Wait, check tests too")
            ```
        """
        return self._interrupt_queue

    def get_steering_pump(self):
        """
        Get the steering pump for reactive loop

        Returns:
            SteeringPump instance, or None if reactive loop is disabled

        Example:
            ```python
            pump = agent.get_steering_pump()
            if pump:
                stats = pump.get_stats()
                print(f"Interrupts handled: {stats['total_interrupts_handled']}")
            ```
        """
        return self._steering_pump

    async def inject_steering_message(self, content: str, source: str = "user") -> None:
        """
        Inject a steering message directly into the interrupt queue

        Convenience method for cognitive steering without accessing the queue directly.

        Args:
            content: The steering message content
            source: Message source identifier (default: "user")

        Example:
            ```python
            # In a background task
            await agent.inject_steering_message("Check the tests first")
            ```
        """
        if self._interrupt_queue:
            await self._interrupt_queue.put_user_input(content, source=source)
            logger.info(f"[REACTIVE] Steering message injected: {content[:50]}...")
        else:
            logger.warning("[REACTIVE] Cannot inject message - reactive loop is disabled")

    def get_task_scheduler(self):
        """
        Get the task scheduler for reactive loop

        Allows external code to schedule follow-up tasks.

        Returns:
            TaskScheduler instance, or None if reactive loop is disabled

        Example:
            ```python
            scheduler = agent.get_task_scheduler()
            if scheduler:
                from fastreact.core import ScheduledTask
                scheduler.add_task(ScheduledTask(
                    task_id="test",
                    instruction="Run the test suite"
                ))
            ```
        """
        return self._task_scheduler

    def get_followup_pump(self):
        """
        Get the follow-up pump for reactive loop

        Returns:
            FollowUpPump instance, or None if reactive loop is disabled

        Example:
            ```python
            pump = agent.get_followup_pump()
            if pump:
                stats = pump.get_stats()
                print(f"Follow-ups triggered: {stats['total_followups']}")
            ```
        """
        return self._followup_pump

    async def schedule_task(self, instruction: str, task_type: str = "general", priority: int = 0) -> str:
        """
        Schedule a follow-up task

        Convenience method for task scheduling.

        Args:
            instruction: Task instruction for the agent
            task_type: Type of task (default: "general")
            priority: Task priority (higher = earlier execution)

        Returns:
            Task ID of the scheduled task

        Example:
            ```python
            task_id = await agent.schedule_task(
                "Run the test suite",
                task_type="test",
                priority=10
            )
            ```
        """
        if not self._task_scheduler:
            logger.warning("[REACTIVE] Cannot schedule task - reactive loop is disabled")
            return None

        import uuid
        from .scheduler import ScheduledTask

        task = ScheduledTask(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            instruction=instruction,
            task_type=task_type,
            priority=priority,
        )

        self._task_scheduler.add_task(task)
        logger.info(f"[REACTIVE] Task scheduled: {task.task_id} - {instruction[:50]}...")

        return task.task_id

    def is_reactive_loop_enabled(self) -> bool:
        """Check if reactive loop (steering pump) is enabled"""
        return self._steering_pump is not None

    # ========================================================================
    # End Sprint 4
    # ========================================================================

    async def run_streaming(
        self,
        query: str,
        enable_thinking: bool = True,
    ) -> AsyncIterator:
        """
        流式执行（V2 新功能）

        实时输出 <thinking> 推理过程和工具调用结果。

        Args:
            query: 用户查询
            enable_thinking: 是否输出思考过程（默认 True）

        Yields:
            StreamChunk: 流式数据块

        使用示例:
            ```python
            agent = FastReAct(api_key="...", streaming_mode="sse")
            async for chunk in agent.run_streaming("帮我写个排序算法"):
                if chunk.type == StreamChunkType.THINKING:
                    print(f"<thinking>{chunk.content}</thinking>")
                elif chunk.type == StreamChunkType.TOOL_CALL:
                    print(f"<tool>{chunk.tool_name}({chunk.tool_params})</tool>")
                elif chunk.type == StreamChunkType.ANSWER:
                    print(f"<answer>{chunk.content}</answer>")
            ```
        """
        from .streaming import StreamingContext, StreamChunkType

        # 创建流式上下文
        stream_ctx = StreamingContext(self, enable_thinking=enable_thinking)

        # 流式执行
        async for chunk in stream_ctx.stream_with_sse(query):
            yield chunk

    def clear_cache(self) -> None:
        """清空缓存"""
        if self.cache is not None:
            self.cache.clear()

    async def close(self) -> None:
        """
        关闭连接池和清理资源

        注意：建议使用 async with FastReAct(...) 自动管理资源
        """
        # 关闭 MCP 连接
        if self._mcp_manager:
            try:
                await self._mcp_manager.close_all()
                logger.info("MCP: Disconnected all servers")
            except Exception as e:
                logger.warning(f"MCP cleanup failed: {e}")

        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            self._client = None

    async def __aenter__(self):
        """
        异步上下文管理器入口

        示例:
            async with FastReAct(...) as agent:
                result = await agent.run_async(...)
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        异步上下文管理器退出，自动清理资源
        """
        await self.close()

    # ==================== 实时控制功能 ====================

    async def run_async_streaming(
        self,
        query: str,
        callbacks: Optional['StreamingCallbacks'] = None,
        session_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        运行 Agent（带实时控制）

        这是 run_async 的增强版本，提供细粒度的事件回调，
        支持实时监控和控制 Agent 执行过程。

        Args:
            query: 用户查询
            callbacks: 回调管理器（StreamingCallbacks）
            session_context: 会话上下文

        Returns:
            {
                "answer": "最终答案",
                "stats": {"iterations": 5, "total_time": 2.5},
                "events": [事件列表]  # 如果 callbacks 是 CallbackRecorder
            }

        使用示例:
            from fastreact.core.callbacks import ConsoleCallbacks

            agent = FastReAct(api_key="xxx")

            # 使用默认控制台回调
            callbacks = ConsoleCallbacks(
                show_thoughts=True,
                show_actions=True,
                show_observations=True
            )

            result = await agent.run_async_streaming(
                "帮我查询天气并计算",
                callbacks=callbacks
            )
        """
        from .callbacks import StreamingCallbacks, StepEvent, Phase
        import time

        # 如果没有提供回调，使用默认的控制台输出
        if callbacks is None:
            from .callbacks import ConsoleCallbacks
            callbacks = ConsoleCallbacks()

        start_time = time.time()
        self.stats["total_calls"] += 1

        # 生成 run_id
        import uuid
        self._run_id = f"run_{uuid.uuid4().hex[:12]}"

        try:
            # 发送开始事件
            await callbacks.emit_start(query, {"run_id": self._run_id})

            # 发送生命周期开始事件
            await self._emit_lifecycle("start")

            # 使用 ContextBuilder 构建消息上下文
            # Memory Flush 检查在 iteration 0 执行
            messages, context_metadata = await self._build_messages_context(
                query,
                session_context,
                iteration=0,  # Initial context build
            )

            steps = []
            answer_parts = []  # 收集回答片段

            for iteration in range(self.max_iterations):
                # === 思考阶段 ===
                if self.enable_streaming:
                    # 使用流式 API
                    response_content = ""
                    async for chunk in await self._chat_with_streaming_direct(
                        messages,
                        lambda chunk: callbacks.emit(StepEvent(
                            phase=Phase.ANSWER,
                            content=chunk,
                            metadata={"iteration": iteration + 1}
                        ))
                    ):
                        # 收集流式输出
                        response_content += chunk
                else:
                    # 非流式
                    llm_response = await self._chat(messages)
                    response_content = llm_response.get("content", "")

                # 提取思考内容（去掉 Thought: 前缀）
                thought = self._extract_thought(response_content)

                # 发送思考事件
                await callbacks.emit(StepEvent(
                    phase=Phase.THINK,
                    content=thought,
                    metadata={"iteration": iteration + 1}
                ))

                # 解析工具调用
                tool_calls = self._parse_tool_calls(
                    llm_response,
                    fallback_text=response_content
                )

                if not tool_calls:
                    # 没有工具调用，说明是最终答案
                    final_answer = self._extract_final_answer(response_content)

                    await callbacks.emit(StepEvent(
                        phase=Phase.ANSWER,
                        content=final_answer,
                        metadata={"is_final": True, "iteration": iteration + 1}
                    ))

                    steps.append({
                        "iteration": iteration + 1,
                        "thought": thought,
                        "is_final": True,
                        "answer": final_answer
                    })

                    # 计算统计
                    elapsed = time.time() - start_time
                    self.stats["total_time"] += elapsed
                    self.stats["iterations"] = iteration + 1

                    # 发送结束事件
                    result = {
                        "answer": final_answer,
                        "steps": steps,
                        "stats": self.get_stats(),
                    }

                    await callbacks.emit_end(result)
                    await self._emit_lifecycle("end")

                    return result

                # === 行动阶段 ===
                # 发送行动事件
                await callbacks.emit(StepEvent(
                    phase=Phase.ACTION,
                    content=json.dumps({
                        "tool_calls": [
                            {"name": tc.name, "parameters": tc.parameters}
                            for tc in tool_calls
                        ]
                    }),
                    metadata={"iteration": iteration + 1}
                ))

                # === 工具执行阶段 ===
                results = []

                for tool_call in tool_calls:
                    tool_name = tool_call.name
                    params = tool_call.parameters

                    # 发送工具开始事件
                    await callbacks.emit(StepEvent(
                        phase=Phase.TOOL_START,
                        content=f"Executing {tool_name}",
                        metadata={
                            "tool_name": tool_name,
                            "parameters": params
                        }
                    ))

                    # 执行工具
                    tool_start = time.time()

                    try:
                        # 执行工具
                        tool_result = await self._execute_tool_async(tool_call)

                        duration = time.time() - tool_start

                        # 构建观察结果
                        if tool_result.error:
                            observation = f"[ERROR] {tool_result.error}"
                        else:
                            observation = f"[OK] {tool_result.result}"

                        results.append(observation)

                        # 发送工具结束事件
                        await callbacks.emit(StepEvent(
                            phase=Phase.TOOL_END,
                            content=observation,
                            metadata={
                                "tool_name": tool_name,
                                "duration": duration,
                                "success": tool_result.is_success
                            }
                        ))

                    except Exception as e:
                        # 工具执行错误
                        duration = time.time() - tool_start

                        error_msg = f"工具执行失败: {e}"

                        await callbacks.emit(StepEvent(
                            phase=Phase.ERROR,
                            content=error_msg,
                            metadata={
                                "tool_name": tool_name,
                                "duration": duration,
                                "error": str(e)
                            }
                        ))

                        results.append(error_msg)

                # 构建观察结果
                observation_text = "\n\n".join([
                    f"**{tool_call.name}**: {obs}"
                    for tool_call, obs in zip(tool_calls, results)
                ])

                # 发送观察事件
                await callbacks.emit(StepEvent(
                    phase=Phase.OBSERVATION,
                    content=observation_text,
                    metadata={"iteration": iteration + 1}
                ))

                # 添加到消息历史
                messages.append({"role": "assistant", "content": response_content})
                messages.append({
                    "role": "user",
                    "content": f"工具返回结果:\n\n{observation_text}\n\n请基于这些信息继续思考或给出最终答案。",
                })

                steps.append({
                    "iteration": iteration + 1,
                    "thought": thought,
                    "tool_calls": [
                        {"name": tc.name, "parameters": tc.parameters}
                        for tc in tool_calls
                    ],
                    "observation": observation_text
                })

            # 达到最大迭代次数
            elapsed = time.time() - start_time
            self.stats["total_time"] += elapsed
            self.stats["iterations"] = self.max_iterations

            result = {
                "answer": "达到最大迭代次数，未能完成",
                "steps": steps,
                "stats": self.get_stats(),
            }

            await callbacks.emit_end(result)
            await self._emit_lifecycle("end")

            return result

        except Exception as e:
            # 发送错误事件
            await callbacks.emit(StepEvent(
                phase=Phase.ERROR,
                content=str(e),
                metadata={"error_type": type(e).__name__}
            ))
            await self._emit_lifecycle("error", error=str(e))
            raise

    # ============================================================================
    # V2: 审批请求处理
    # ============================================================================

    async def _handle_approval_request(self, request):
        """
        处理审批请求

        这是 ApprovalManager 调用的回调函数。在同步上下文中，
        返回默认拒绝，避免阻塞执行。

        Args:
            request: ApprovalRequest 对象

        Returns:
            ApprovalResponse
        """
        logger.warning(
            f"Approval request for '{request.tool_name}' "
            f"(no interactive handler, auto-denying)"
        )

        # 在非交互式环境中，自动拒绝高风险操作
        from .approval import ApprovalResponse
        return ApprovalResponse.DENY

    def set_approval_handler(self, handler: Callable):
        """
        设置自定义审批处理函数

        Args:
            handler: 处理审批请求的函数，接收 ApprovalRequest，返回 ApprovalResponse
        """
        if self._approval_manager and hasattr(self._approval_manager, 'set_user_input_callback'):
            self._approval_manager.set_user_input_callback(handler)
            logger.info("Custom approval handler set")
        else:
            logger.warning("Cannot set approval handler: no approval manager")