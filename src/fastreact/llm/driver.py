"""
LLM Driver - 统一的 LLM 调用中间层

提供统一的 LLM 调用接口，内部处理：
- 重试逻辑
- 缓存
- 流式响应
- 错误处理
- 日志记录

所有组件（FastReAct, GraphAgent, Replanner 等）都应该通过
这个 driver 调用 LLM，而不是直接调用底层 API。

设计原则：
1. 单一职责：只负责 LLM 调用
2. 统一接口：chat(), stream(), batch()
3. 可配置：重试、超时、缓存等
4. 可扩展：支持不同的 LLM provider
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncIterator, Union
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)


# ============================================================================
# 配置
# ============================================================================

@dataclass
class LLMDriverConfig:
    """LLM Driver 配置"""
    # 模型配置
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4096

    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_on_timeout: bool = True
    retry_on_rate_limit: bool = True

    # 超时配置
    timeout: float = 60.0

    # 缓存配置
    enable_cache: bool = True
    cache_ttl: int = 300  # 秒

    # 日志配置
    log_requests: bool = True
    log_responses: bool = False  # 可能很大

    # 流式配置
    enable_streaming: bool = False


@dataclass
class ChatResponse:
    """聊天响应"""
    content: str = ""
    tool_calls: List[Any] = field(default_factory=list)
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = ""
    raw_response: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in self.tool_calls
            ],
            "model": self.model,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
        }


# ============================================================================
# LLM Driver
# ============================================================================

class LLMDriver:
    """
    统一的 LLM 调用中间层

    作为所有 LLM 调用的单一入口，内部处理：
    - 客户端管理（创建、复用）
    - 请求重试
    - 响应缓存
    - 错误处理
    - 日志记录

    使用方式：
        # 创建 driver
        driver = LLMDriver(
            api_key="sk-...",
            base_url="https://api.openai.com/v1",
            config=LLMDriverConfig(model="gpt-4")
        )

        # 调用 LLM
        response = await driver.chat(messages=[...])

        # 流式调用
        async for chunk in driver.stream(messages=[...]):
            print(chunk.content)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        config: Optional[LLMDriverConfig] = None,
        http_client: Optional[Any] = None,
    ):
        """
        初始化 LLM Driver

        Args:
            api_key: API key
            base_url: Base URL
            config: 配置（可选）
            http_client: HTTP 客户端（可选，用于测试）
        """
        self.api_key = api_key
        self.base_url = base_url
        self.config = config or LLMDriverConfig()
        self.http_client = http_client

        # 延迟初始化的客户端
        self._client = None

        # 缓存
        self._cache = {} if self.config.enable_cache else None

        # Context Monitor: 实时追踪 Token 消耗
        from ..context.monitor import get_context_monitor
        self.context_monitor = get_context_monitor(
            context_window=self.config.max_tokens * 10  # 估算：max_tokens * 10轮对话
        )

    # ========================================================================
    # 客户端管理
    # ========================================================================

    def _get_client(self):
        """获取或创建 LLM 客户端"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                import httpx

                # 创建 HTTP 客户端（如果未提供）
                if self.http_client is None:
                    self.http_client = httpx.AsyncClient(
                        timeout=self.config.timeout,
                        limits=httpx.Limits(max_connections=100),
                    )

                # 创建 OpenAI 客户端
                self._client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    http_client=self.http_client,
                )

                logger.debug("LLM client created")

            except ImportError:
                raise ImportError(
                    "请安装 openai>=1.0.0 和 httpx>=0.25.0: "
                    "pip install openai httpx"
                )

        return self._client

    # ========================================================================
    # 核心 API
    # ========================================================================

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Any]] = None,
        **kwargs
    ) -> ChatResponse:
        """
        发送聊天请求（非流式）

        这是所有 LLM 调用的主要入口点。

        Args:
            messages: 消息列表
            tools: 工具定义（可选）
            **kwargs: 额外参数（覆盖 config）

        Returns:
            ChatResponse 对象
        """
        # 合并配置
        config = self._merge_config(kwargs)

        # 检查缓存
        cache_key = None
        if config.enable_cache and not tools:
            cache_key = self._get_cache_key(messages, config)
            cached = self._get_cached_response(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key[:16]}...")
                return cached

        # 记录请求
        if config.log_requests:
            logger.info(f"[LLM Request] model={config.model}, messages={len(messages)}")

        # 执行请求（带重试）
        response = await self._chat_with_retry(
            messages=messages,
            tools=tools,
            config=config
        )

        # 解析响应
        result = self._parse_response(response, config)

        # 缓存响应
        if cache_key and config.enable_cache:
            self._cache_response(cache_key, result)

        # 记录响应
        if config.log_responses and config.log_requests:
            logger.info(f"[LLM Response] content_len={len(result.content)}, "
                       f"tool_calls={len(result.tool_calls)}")

        return result

    async def stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        发送流式聊天请求

        Args:
            messages: 消息列表
            **kwargs: 额外参数（覆盖 config）

        Yields:
            内容片段（字符串）
        """
        # 合并配置
        config = self._merge_config(kwargs)
        config.enable_streaming = True

        # 记录请求
        if config.log_requests:
            logger.info(f"[LLM Stream] model={config.model}, messages={len(messages)}")

        # 获取客户端
        client = self._get_client()

        # 构建请求参数
        request_params = self._build_request_params(messages, None, config)

        # 修复：计算实际发送的token数并更新ContextMonitor
        if self.context_monitor:
            from ..context import TokenCounter
            counter = TokenCounter(model=config.model)
            current_tokens = counter.count_messages_tokens(messages)
            self.context_monitor.metrics.set_current(current_tokens)

        # 流式调用
        stream = await client.chat.completions.create(**request_params)

        # 解析流式响应
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    # ========================================================================
    # 内部方法
    # ========================================================================

    async def _chat_with_retry(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Any]],
        config: LLMDriverConfig
    ) -> Any:
        """
        带重试的聊天请求

        内部处理：
        - 超时重试
        - 速率限制重试
        - 服务器错误重试
        """
        client = self._get_client()

        # 构建请求参数
        request_params = self._build_request_params(messages, tools, config)

        # 修复：计算实际发送的token数并更新ContextMonitor
        # 显示当前请求的真实context大小，而不是累加值
        if self.context_monitor:
            from ..context import TokenCounter
            counter = TokenCounter(model=config.model)
            current_tokens = counter.count_messages_tokens(messages)
            self.context_monitor.metrics.set_current(current_tokens)

        # 重试循环
        last_error = None
        for attempt in range(config.max_retries):
            try:
                response = await client.chat.completions.create(**request_params)
                return response

            except Exception as e:
                last_error = e

                # 判断是否应该重试
                should_retry = self._should_retry(e, attempt, config)

                if not should_retry:
                    logger.error(f"[LLM Error] {type(e).__name__}: {e}")
                    raise

                # 计算重试延迟
                delay = config.retry_delay * (2 ** attempt)  # 指数退避

                logger.warning(
                    f"[LLM Retry] attempt={attempt + 1}/{config.max_retries}, "
                    f"error={type(e).__name__}, delay={delay}s"
                )

                await asyncio.sleep(delay)

        # 所有重试都失败
        logger.error(f"[LLM Failed] all {config.max_retries} attempts failed")

        # 确保 last_error 是有效的异常对象
        if last_error is None:
            # 创建有意义的错误消息
            raise RuntimeError(f"LLM request failed with no specific error (max_retries={config.max_retries})")
        else:
            raise last_error

    def _build_request_params(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Any]],
        config: LLMDriverConfig
    ) -> Dict[str, Any]:
        """构建请求参数"""
        params = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        # 添加工具（如果有）
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        # 流式模式
        if config.enable_streaming:
            params["stream"] = True
            params["stream_options"] = {"include_usage": True}

        return params

    def _parse_response(self, response: Any, config: LLMDriverConfig) -> ChatResponse:
        """解析 LLM 响应"""
        message = response.choices[0].message

        result = ChatResponse(
            content=message.content or "",
            model=response.model,
            usage=response.usage.dict() if hasattr(response, 'usage') else {},
            finish_reason=response.choices[0].finish_reason,
            raw_response=response,
        )

        # 提取工具调用
        if hasattr(message, 'tool_calls') and message.tool_calls:
            result.tool_calls = message.tool_calls

        # 更新 Context Monitor: 追踪 Token 消耗
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            prompt_tokens = getattr(usage, 'prompt_tokens', 0)
            completion_tokens = getattr(usage, 'completion_tokens', 0)

            # 更新监控状态
            status = self.context_monitor.track_request(
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens
            )

            # 显示警告（如果需要）
            if status.get("warning"):
                warning_level = status["warning"]
                if config.log_requests:
                    # 显示进度条和警告
                    progress_bar = self.context_monitor.get_progress_bar()
                    status_text = self.context_monitor.get_status_text()

                    if warning_level == "WARNING":
                        logger.warning(f"[ContextMonitor] {progress_bar}")
                        logger.warning(f"[ContextMonitor] {status_text}")
                        logger.warning("[ContextMonitor] Consider enabling Memory Flush or pruning history")
                    elif warning_level == "ALERT":
                        logger.error(f"[ContextMonitor] {progress_bar}")
                        logger.error(f"[ContextMonitor] {status_text}")
                        logger.error("[ContextMonitor] Strongly recommend enabling Memory Flush immediately!")
                    elif warning_level == "CRITICAL":
                        logger.critical(f"[ContextMonitor] {progress_bar}")
                        logger.critical(f"[ContextMonitor] {status_text}")
                        logger.critical("[ContextMonitor] Context limit approaching! System will trigger Memory Flush!")

        return result

    def _should_retry(self, error: Exception, attempt: int, config: LLMDriverConfig) -> bool:
        """判断是否应该重试"""
        # 已经达到最大重试次数
        if attempt >= config.max_retries - 1:
            return False

        # 超时错误
        if config.retry_on_timeout and isinstance(error, asyncio.TimeoutError):
            return True

        # 速率限制
        if config.retry_on_rate_limit:
            # OpenAI 速率限制错误
            if "rate limit" in str(error).lower():
                return True

        # 服务器错误（5xx）
        if hasattr(error, 'status'):
            status = getattr(error, 'status', None)
            if status and 500 <= status < 600:
                return True

        return False

    def _merge_config(self, overrides: Dict[str, Any]) -> LLMDriverConfig:
        """合并配置"""
        import copy

        config = copy.copy(self.config)

        # 应用覆盖
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return config

    # ========================================================================
    # 缓存
    # ========================================================================

    def _get_cache_key(
        self,
        messages: List[Dict[str, str]],
        config: LLMDriverConfig
    ) -> str:
        """生成缓存键"""
        # 序列化消息
        cache_data = {
            "messages": messages,
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        # 计算 hash
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[ChatResponse]:
        """获取缓存的响应"""
        if self._cache is None:
            return None

        cached = self._cache.get(cache_key)
        if cached is None:
            return None

        # 检查是否过期
        now = datetime.now().timestamp()
        if now - cached["timestamp"] > self.config.cache_ttl:
            del self._cache[cache_key]
            return None

        return cached["response"]

    def _cache_response(self, cache_key: str, response: ChatResponse):
        """缓存响应"""
        if self._cache is None:
            return

        self._cache[cache_key] = {
            "timestamp": datetime.now().timestamp(),
            "response": response,
        }

    # ========================================================================
    # 清理
    # ========================================================================

    async def close(self):
        """关闭客户端"""
        if self._client is not None:
            if self.http_client:
                await self.http_client.aclose()
            self._client = None
            logger.debug("LLM client closed")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# ============================================================================
# 工厂函数
# ============================================================================

def create_llm_driver(
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    config: Optional[LLMDriverConfig] = None,
) -> LLMDriver:
    """
    创建 LLM Driver

    Args:
        api_key: API key
        base_url: Base URL
        config: 配置（可选）

    Returns:
        LLMDriver 实例
    """
    return LLMDriver(
        api_key=api_key,
        base_url=base_url,
        config=config,
    )


def create_llm_driver_from_config(config: Dict[str, Any]) -> LLMDriver:
    """
    从配置字典创建 LLM Driver

    Args:
        config: 配置字典（从 load_config() 加载）

    Returns:
        LLMDriver 实例
    """
    from fastreact.bootstrap.config_loader import get_api_key, get_base_url

    api_key = get_api_key(config)
    base_url = get_base_url(config)

    # 从配置中提取 LLM 参数
    llm_config = config.get("llm", {})
    model = llm_config.get("default_provider", "siliconflow")
    provider_config = llm_config.get("providers", {}).get(model, {})

    # 创建 driver 配置
    driver_config = LLMDriverConfig(
        model=provider_config.get("model", "gpt-4"),
        temperature=provider_config.get("temperature", 0.7),
        max_tokens=provider_config.get("max_tokens", 4096),
    )

    return create_llm_driver(
        api_key=api_key,
        base_url=base_url,
        config=driver_config,
    )
