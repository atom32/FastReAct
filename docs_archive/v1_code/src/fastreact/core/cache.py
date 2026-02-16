"""
FastReAct缓存系统

实现高效的LRU缓存
"""

from collections import OrderedDict
from typing import Any, Optional, Dict


class LRUCache:
    """
    LRU（最近最少使用）缓存

    特性：
    - O(1)时间复杂度的get和set
    - 自动淘汰最久未使用的条目
    - 线程不安全（ReACT是单线程的）
    """

    def __init__(self, max_size: int = 1000):
        """
        初始化LRU缓存

        Args:
            max_size: 最大缓存条目数
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在返回None
        """
        if key in self.cache:
            # 移动到末尾（标记为最近使用）
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]

        self.misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
        """
        if key in self.cache:
            # 更新现有值，移动到末尾
            self.cache.move_to_end(key)
        else:
            # 检查是否需要淘汰
            if len(self.cache) >= self.max_size:
                # 删除最久未使用的条目（第一个）
                self.cache.popitem(last=False)

        self.cache[key] = value

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def __len__(self) -> int:
        """返回当前缓存条目数"""
        return len(self.cache)

    def __contains__(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self.cache

    def size(self) -> int:
        """返回当前缓存大小"""
        return len(self.cache)

    def stats(self) -> Dict[str, Any]:
        """返回缓存统计信息"""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }

    def __repr__(self) -> str:
        return f"LRUCache(size={len(self.cache)}/{self.max_size}, hits={self.hits}, misses={self.misses})"
