"""
测试FastReAct缓存系统

测试LRU缓存的所有功能
"""

import pytest
from fastreact.core.cache import LRUCache


class TestLRUCache:
    """测试LRU缓存类"""

    def test_init(self):
        """测试缓存初始化"""
        cache = LRUCache(max_size=100)
        assert cache.max_size == 100
        assert len(cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0

    def test_set_and_get(self):
        """测试基本的set和get操作"""
        cache = LRUCache(max_size=10)

        # 设置值
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # 获取值
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") is None

    def test_get_updates_lru_order(self):
        """测试get操作更新LRU顺序"""
        cache = LRUCache(max_size=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        # 访问a，使其成为最近使用
        assert cache.get("a") == 1

        # 添加d，应该淘汰b（最久未使用）
        cache.set("d", 4)

        assert cache.get("a") == 1  # a仍然存在
        assert cache.get("b") is None  # b被淘汰
        assert cache.get("c") == 3  # c仍然存在
        assert cache.get("d") == 4  # d新添加的

    def test_set_updates_existing_key(self):
        """测试更新已存在的键"""
        cache = LRUCache(max_size=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        # 更新a的值
        cache.set("a", 100)

        # 验证值已更新
        assert cache.get("a") == 100

        # 添加d，应该淘汰b（因为a被更新过）
        cache.set("d", 4)

        assert cache.get("a") == 100
        assert cache.get("b") is None
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_eviction_when_full(self):
        """测试缓存满时的淘汰策略"""
        cache = LRUCache(max_size=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # 应该淘汰a

        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_clear(self):
        """测试清空缓存"""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert len(cache) == 2

        cache.clear()
        assert len(cache) == 0
        # Note: get() after clear() will increment misses
        assert cache.get("key1") is None
        assert cache.hits == 0
        assert cache.misses == 1  # One miss from the get() call

    def test_contains(self):
        """测试键存在性检查"""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")

        assert "key1" in cache
        assert "key2" not in cache

    def test_size_method(self):
        """测试size方法"""
        cache = LRUCache(max_size=10)

        assert cache.size() == 0

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.size() == 2

    def test_stats(self):
        """测试统计信息"""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # 命中
        cache.get("key1")
        cache.get("key2")

        # 未命中
        cache.get("key3")

        stats = cache.stats()
        assert stats["size"] == 2
        assert stats["max_size"] == 10
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 2 / 3

    def test_hit_rate_with_no_access(self):
        """测试没有访问时的命中率"""
        cache = LRUCache(max_size=10)

        stats = cache.stats()
        assert stats["hit_rate"] == 0.0

    def test_repr(self):
        """测试字符串表示"""
        cache = LRUCache(max_size=10)

        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key2")

        repr_str = repr(cache)
        assert "LRUCache" in repr_str
        assert "size=1/10" in repr_str  # Format is size/current/max
        assert "hits=1" in repr_str
        assert "misses=1" in repr_str

    def test_different_value_types(self):
        """测试不同类型的值"""
        cache = LRUCache(max_size=10)

        # 字符串
        cache.set("str", "value")
        assert cache.get("str") == "value"

        # 整数
        cache.set("int", 42)
        assert cache.get("int") == 42

        # 浮点数
        cache.set("float", 3.14)
        assert cache.get("float") == 3.14

        # 列表
        cache.set("list", [1, 2, 3])
        assert cache.get("list") == [1, 2, 3]

        # 字典
        cache.set("dict", {"key": "value"})
        assert cache.get("dict") == {"key": "value"}

    def test_max_size_one(self):
        """测试最大容量为1的边界情况"""
        cache = LRUCache(max_size=1)

        cache.set("a", 1)
        assert cache.get("a") == 1

        cache.set("b", 2)
        assert cache.get("a") is None
        assert cache.get("b") == 2

    def test_large_cache(self):
        """测试大容量缓存"""
        cache = LRUCache(max_size=1000)

        # 添加1000个条目
        for i in range(1000):
            cache.set(f"key{i}", i)

        assert len(cache) == 1000

        # 添加第1001个条目
        cache.set("key1000", 1000)

        # 第一个条目应该被淘汰
        assert cache.get("key0") is None
        assert len(cache) == 1000

    def test_overwrite_same_key(self):
        """测试覆盖同一个键多次"""
        cache = LRUCache(max_size=10)

        cache.set("key", 1)
        cache.set("key", 2)
        cache.set("key", 3)

        assert cache.get("key") == 3
        assert len(cache) == 1  # 只有一个条目

    def test_lru_order_after_multiple_updates(self):
        """测试多次更新后的LRU顺序"""
        cache = LRUCache(max_size=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        # 多次访问不同的键
        cache.get("a")
        cache.get("b")
        cache.get("c")

        # 更新a
        cache.set("a", 100)

        # 添加d，应该淘汰b
        cache.set("d", 4)

        assert cache.get("a") == 100
        assert cache.get("b") is None
        assert cache.get("c") == 3
        assert cache.get("d") == 4
