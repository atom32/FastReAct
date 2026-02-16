"""
去重缓存系统

防止重放攻击和重复请求：
- 基于 idempotency_key 的去重
- TTL 自动过期
- 异步安全
"""

from typing import Dict, Optional, Any
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DedupCache:
    """短期去重缓存（防止重放攻击）

    使用幂等性密钥（idempotency_key）来防止重复请求：
    - 第一次请求：执行并缓存结果
    - 后续相同 key 的请求：直接返回缓存结果

    Usage:
        cache = DedupCache(ttl=300)  # 5分钟 TTL

        # 检查并存储
        is_dup, cached_value = await cache.check_and_store(
            key="unique-key-123",
            value={"result": "data"}
        )
        if is_dup:
            print("Duplicate request, returning cached result")
            return cached_value
        else:
            print("First time, processing...")
            return value

        # 清理过期条目
        await cache.cleanup()
    """

    def __init__(self, ttl: int = 300):
        """初始化去重缓存

        Args:
            ttl: 缓存条目的生存时间（秒），默认 5 分钟
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def check_and_store(
        self,
        key: str,
        value: Any = None
    ) -> tuple[bool, Optional[Any]]:
        """检查并存储键

        Args:
            key: 幂等性密钥
            value: 要缓存的值

        Returns:
            (is_duplicate, cached_value)
            - is_duplicate: 是否是重复请求
            - cached_value: 缓存的值（如果是重复）或传入的值（如果不是）
        """
        async with self._lock:
            now = datetime.utcnow()

            # 清理过期条目
            await self._cleanup_expired(now)

            # 检查是否存在
            if key in self.cache:
                entry = self.cache[key]
                self._hits += 1
                logger.debug(f"Dedup cache hit for key: {key}")
                return True, entry.get("value")

            # 存储新条目
            self.cache[key] = {
                "value": value,
                "created_at": now
            }
            self._misses += 1
            logger.debug(f"Dedup cache miss for key: {key}")
            return False, value

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存的值

        Args:
            key: 幂等性密钥

        Returns:
            缓存的值，不存在返回 None
        """
        async with self._lock:
            now = datetime.utcnow()
            await self._cleanup_expired(now)

            entry = self.cache.get(key)
            if entry:
                # 检查是否过期
                age = (now - entry["created_at"]).total_seconds()
                if age < self.ttl:
                    return entry.get("value")

            return None

    async def set(self, key: str, value: Any):
        """设置缓存值

        Args:
            key: 幂等性密钥
            value: 要缓存的值
        """
        async with self._lock:
            self.cache[key] = {
                "value": value,
                "created_at": datetime.utcnow()
            }

    async def delete(self, key: str) -> bool:
        """删除缓存条目

        Args:
            key: 幂等性密钥

        Returns:
            是否成功删除
        """
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    async def _cleanup_expired(self, now: datetime = None):
        """清理过期条目

        Args:
            now: 当前时间（可选，默认使用当前时间）

        Returns:
            清理的条目数量
        """
        now = now or datetime.utcnow()
        expired_keys = []

        for key, entry in self.cache.items():
            age = (now - entry["created_at"]).total_seconds()
            if age > self.ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired dedup entries")

        return len(expired_keys)

    async def cleanup(self):
        """清理所有过期条目"""
        async with self._lock:
            return await self._cleanup_expired()

    async def clear(self):
        """清空所有缓存"""
        async with self._lock:
            self.cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("Dedup cache cleared")

    def get_stats(self) -> Dict:
        """获取缓存统计信息

        Returns:
            统计信息字典
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0

        return {
            "size": len(self.cache),
            "ttl_seconds": self.ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.2%}"
        }

    async def get_size(self) -> int:
        """获取缓存大小

        Returns:
            当前缓存的条目数量
        """
        async with self._lock:
            return len(self.cache)


class RequestDeduplicator:
    """请求去重器

    更高级的去重功能，支持自定义去重策略。

    Usage:
        dedup = RequestDeduplicator(ttl=300)

        # 处理请求（自动去重）
        async def handle_request(request):
            return await dedup.execute(
                key=request.idempotency_key,
                func=lambda: process_request(request)
            )

        async def process_request(request):
            # 实际处理逻辑
            return {"result": "data"}
    """

    def __init__(self, ttl: int = 300):
        """初始化请求去重器

        Args:
            ttl: 缓存TTL（秒）
        """
        self.cache = DedupCache(ttl=ttl)

    async def execute(
        self,
        key: str,
        func,
        args: tuple = (),
        kwargs: dict = None
    ) -> Any:
        """执行函数（自动去重）

        如果 key 已存在，返回缓存结果
        如果 key 不存在，执行函数并缓存结果

        Args:
            key: 幂等性密钥
            func: 要执行的函数（可以是协程函数）
            args: 函数位置参数
            kwargs: 函数关键字参数

        Returns:
            函数执行结果或缓存结果
        """
        # 检查是否已存在
        cached_value = await self.cache.get(key)
        if cached_value is not None:
            logger.info(f"Returning cached result for key: {key}")
            return cached_value

        # 执行函数
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **(kwargs or {}))
        else:
            result = func(*args, **(kwargs or {}))

        # 缓存结果
        await self.cache.set(key, result)

        return result

    async def invalidate(self, key: str):
        """使缓存失效

        Args:
            key: 幂等性密钥
        """
        await self.cache.delete(key)

    async def clear(self):
        """清空所有缓存"""
        await self.cache.clear()

    def get_stats(self) -> Dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return self.cache.get_stats()
