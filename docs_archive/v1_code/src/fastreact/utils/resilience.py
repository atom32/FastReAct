"""
弹性机制 - 错误重试和容错

提供智能重试策略，处理临时性错误。
"""

import asyncio
import inspect
import random
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from time import time

logger = logging.getLogger(__name__)


class RetryExhaustedError(Exception):
    """重试耗尽错误"""

    def __init__(self, message: str, last_error: Exception = None):
        super().__init__(message)
        self.last_error = last_error


@dataclass
class RetryPolicy:
    """
    重试策略

    定义如何重试失败的请求。
    """
    max_attempts: int = 3                  # 最大重试次数
    base_delay: float = 1.0               # 基础延迟（秒）
    max_delay: float = 60.0               # 最大延迟（秒）
    exponential_base: float = 2.0         # 指数退避基数
    jitter: bool = True                   # 添加随机抖动（避免雷群效应）

    # 可重试的错误类型
    retriable_errors: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )

    def should_retry(self, error: Exception) -> bool:
        """
        判断错误是否应该重试

        Args:
            error: 异常对象

        Returns:
            是否应该重试
        """
        return isinstance(error, self.retriable_errors)

    def calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟

        Args:
            attempt: 当前尝试次数（从0开始）

        Returns:
            延迟时间（秒）
        """
        # 指数退避
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        # 添加抖动（±25%）
        if self.jitter:
            delay = delay * (0.75 + random.random() * 0.5)

        return delay


@dataclass
class RetryStats:
    """重试统计"""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_delay: float = 0.0
    last_error: Optional[Exception] = None


class RetryExecutor:
    """
    重试执行器

    执行函数并在失败时重试。
    """

    def __init__(self, policy: RetryPolicy = None):
        """
        初始化重试执行器

        Args:
            policy: 重试策略，默认使用默认策略
        """
        self.policy = policy or RetryPolicy()
        self.stats = RetryStats()

    async def execute(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        执行函数，支持重试

        Args:
            func: 要执行的函数（可以是协程函数）
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果

        Raises:
            RetryExhaustedError: 所有重试都失败
        """
        last_error = None

        for attempt in range(self.policy.max_attempts):
            self.stats.total_attempts += 1

            try:
                # 执行函数
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    # 同步函数，在线程池中执行
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, func, *args, **kwargs)

                self.stats.successful_attempts += 1
                return result

            except Exception as e:
                last_error = e
                self.stats.failed_attempts += 1
                self.stats.last_error = e

                # 检查是否应该重试
                if not self.policy.should_retry(e):
                    logger.error(f"Non-retriable error: {type(e).__name__}: {e}")
                    # 不可重试的错误，包装后立即抛出
                    raise RetryExhaustedError(
                        message=f"Non-retriable error: {type(e).__name__}: {e}",
                        last_error=e
                    )

                # 最后一次尝试失败，不再重试
                if attempt == self.policy.max_attempts - 1:
                    break

                # 计算延迟
                delay = self.policy.calculate_delay(attempt)
                self.stats.total_delay += delay

                logger.warning(
                    f"Attempt {attempt + 1}/{self.policy.max_attempts} failed: "
                    f"{type(e).__name__}: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                await asyncio.sleep(delay)

        # 所有重试都失败
        raise RetryExhaustedError(
            f"All {self.policy.max_attempts} attempts failed. "
            f"Last error: {type(last_error).__name__}: {last_error}",
            last_error=last_error
        )

    def get_stats(self) -> RetryStats:
        """获取重试统计"""
        return self.stats

    def reset_stats(self):
        """重置统计"""
        self.stats = RetryStats()


# 便捷函数
async def retry_with_backoff(
    func: Callable,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retriable_errors: Tuple[Type[Exception], ...] = (ConnectionError, TimeoutError),
    *args: Any,
    **kwargs: Any
) -> Any:
    """
    带退避的重试执行（便捷函数）

    Args:
        func: 要执行的函数
        max_attempts: 最大尝试次数
        base_delay: 基础延迟
        retriable_errors: 可重试的错误类型
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        函数执行结果

    Example:
        result = await retry_with_backoff(
            api_call,
            max_attempts=3,
            retriable_errors=(ConnectionError, TimeoutError)
        )
    """
    policy = RetryPolicy(
        max_attempts=max_attempts,
        base_delay=base_delay,
        retriable_errors=retriable_errors
    )
    executor = RetryExecutor(policy)
    return await executor.execute(func, *args, **kwargs)
