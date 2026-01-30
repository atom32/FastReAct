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
from typing import Any, Callable, Dict, List, Optional

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

# 获取logger
logger = get_logger("fastreact.engine")


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
    ):
        """
        初始化FastReAct引擎

        Args:
            api_key: OpenAI API密钥
            base_url: API基础URL（支持兼容API）
            model: 模型名称
            tools: 工具列表
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

        # 工具注册表
        self.tools: Dict[str, Tool] = {}
        if tools:
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

    def register_tool(self, tool: Tool) -> None:
        """注册工具"""
        self.tools[tool.name] = tool

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
                # 执行工具 - 兼容旧方式和新方式
                if hasattr(tool, 'execute_async'):
                    # 旧的 Tool 类（面向对象）
                    result = await tool.execute_async(**params)
                elif hasattr(tool, 'execute') and asyncio.iscoroutinefunction(tool.execute):
                    # 新的函数式 Tool
                    result = await tool.execute(**params)
                else:
                    # 同步函数式 Tool
                    result = tool.execute(**params)

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

        try:
            messages = [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": query},
            ]

            # 如果有会话上下文，添加历史消息
            if session_context and "history" in session_context:
                # 只添加最近的历史消息（避免 token 过多）
                history = session_context["history"][-10:]  # 最近 10 条
                for msg in history:
                    messages.insert(-1, {
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

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

                # 构建观察结果
                observations = []
                for result in results:
                    if result.error:
                        obs = f"[ERROR] {result.error}"
                    else:
                        obs = f"[OK] {result.result}"
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
                "  # ❌ Wrong (will cause this error):\n"
                "  async def my_function():\n"
                "      result = react.run('query')  # Error!\n"
                "\n"
                "  # ✅ Correct:\n"
                "  async def my_function():\n"
                "      result = await react.run_async('query')\n"
                "\n"
                "  # ✅ Or use in sync context (no event loop):\n"
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
        return False
