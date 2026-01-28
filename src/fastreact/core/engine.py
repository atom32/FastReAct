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
        temperature: float = 0.5,
        max_tokens: int = 2048,
        max_tool_retries: int = 3,
        enable_tool_retry: bool = True,
        enable_deduplication: bool = True,
        dedup_window_seconds: float = 10.0,
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
                # 执行工具
                result = await tool.execute_async(**params)
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
        构建系统提示（简化版，因为使用 Function Calling API）

        注意：工具调用由 Function Calling API 自动处理，不需要格式说明
        """
        tools_desc = "\n\n".join([
            f"### {name}\n{tool.description}\n**参数**: {json.dumps(tool.parameters, ensure_ascii=False)}"
            for name, tool in self.tools.items()
        ]) if self.tools else "暂无工具"

        return f"""你是一个智能助手，可以帮助用户完成各种任务。

## 可用工具

{tools_desc}

## 工作流程

1. **Thought**: 思考需要什么信息来回答问题
2. **Action**: 使用工具获取信息（系统会自动处理工具调用）
3. **Observation**: 分析工具返回结果
4. **循环**: 重复步骤1-3，直到收集到足够信息
5. **Final Answer**: 基于工具结果给出最终答案

## 重要提示

- 可以一次调用多个工具来获取信息
- 工具调用结果会给你提供更多信息
- 最终答案必须基于工具返回的结果，不要编造
- 如果信息足够，直接给出答案，不需要调用更多工具

## 示例

**用户**: 北京今天的天气怎么样？

**助手**:
Thought: 需要查询北京今天的天气信息
（系统自动调用 weather 工具）

Observation: 北京今天晴，温度15-25℃

Thought: 已获取天气信息，可以回答了
Final Answer: 北京今天是晴天，温度15-25摄氏度。
"""

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
                    step_callback(step)
                steps.append(step)

                # 更新统计
                elapsed = time.time() - start_time
                self.stats["total_time"] += elapsed

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
                step_callback(step)
            steps.append(step)

            # 并发执行工具
            results = await self._execute_tools_concurrent(tool_calls)

            # 构建观察结果
            observations = []
            for result in results:
                if result.error:
                    obs = f"❌ 错误: {result.error}"
                else:
                    obs = f"✅ {result.result}"
                observations.append(f"**{result.tool_name}**: {obs}")

            observation_text = "\n\n".join(observations)
            step["observation"] = observation_text

            if step_callback:
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

        return {
            "answer": "达到最大迭代次数，未能完成",
            "steps": steps,
            "stats": self.get_stats(),
        }

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
