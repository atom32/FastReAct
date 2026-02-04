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
    truncated = (
        f"Output (truncated, {len(lines)} total lines):\n"
        f"{''.join(f'{line}\n' for line in head_lines)}"
        f"... {hidden_count} lines hidden ...\n"
        f"{''.join(f'{line}\n' for line in tail_lines)}\n"
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
    ):
        """
        初始化FastReAct引擎

        Args:
            api_key: OpenAI API密钥
            base_url: API基础URL（支持兼容API）
            model: 模型名称
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
        if context_config is None and config is not None:
            # Create ContextConfig from config dict
            from ..context import ContextConfig
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

        # LRU缓存
        self.cache = LRUCache(max_size=cache_size) if enable_cache else None

        # 异步客户端（延迟初始化）
        self._client = None
        self._http_client = None

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
        """获取或创建异步客户端"""
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

            for iteration in range(self.max_iterations):
                # 调用LLM
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

        ⚠️ 警告：此方法仅用于简单的同步场景。

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

        # 没有事件循环，使用 asyncio.run
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