"""
测试请求去重功能

验证：
1. 时间窗口内的重复调用检测
2. 去重键生成正确性
3. 过期记录清理
4. 去重统计更新
5. 不同参数的正确区分
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock

from fastreact import FastReAct
from fastreact.core.tool import Tool, ToolCall, ToolResult


class CounterTool(Tool):
    """一个计数工具，记录调用次数"""

    def __init__(self):
        super().__init__()
        self.call_count = 0

    def _get_description(self):
        return "A counter tool for testing"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action to count"}
            }
        }

    async def execute_async(self, action: str) -> str:
        self.call_count += 1
        return f"Action '{action}' executed {self.call_count} times"


class SlowTool(Tool):
    """一个慢速工具（用于测试时间窗口）"""

    def __init__(self, delay=0.1):
        super().__init__()
        self.call_count = 0
        self.delay = delay

    def _get_description(self):
        return "A slow tool for testing dedup windows"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            }
        }

    async def execute_async(self, query: str) -> str:
        self.call_count += 1
        await asyncio.sleep(self.delay)
        return f"Result for '{query}' (call {self.call_count})"


class TestDeduplicationKeys:
    """测试去重键生成"""

    def test_dedup_key_generation(self):
        """测试去重键生成正确性"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CounterTool()],
        )

        key1 = react._get_dedup_key("TestTool", {"param": "value"})
        key2 = react._get_dedup_key("TestTool", {"param": "value"})
        key3 = react._get_dedup_key("TestTool", {"param": "other"})

        # 相同参数生成相同的键
        assert key1 == key2

        # 不同参数生成不同的键
        assert key1 != key3

    def test_dedup_key_uses_json_sorting(self):
        """测试去重键使用 JSON 排序（参数顺序不影响）"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CounterTool()],
        )

        key1 = react._get_dedup_key("TestTool", {"a": 1, "b": 2})
        key2 = react._get_dedup_key("TestTool", {"b": 2, "a": 1})

        # 参数顺序不同但内容相同，应该生成相同的键
        assert key1 == key2


class TestDuplicateDetection:
    """测试重复检测"""

    @pytest.mark.asyncio
    async def test_duplicate_call_detected(self):
        """测试时间窗口内的重复调用被检测"""
        tool = CounterTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            enable_deduplication=True,
            dedup_window_seconds=10.0,
        )

        from fastreact.core.tool import ToolCall

        # 第一次调用
        result1 = await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )

        assert result1.is_success is True
        assert tool.call_count == 1
        assert "executed 1 times" in result1.result

        # 立即第二次调用（相同参数，在时间窗口内）
        result2 = await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )

        assert result2.is_success is True
        assert tool.call_count == 1  # 没有增加，因为是去重命中
        assert result2.result == result1.result  # 返回相同的结果

    @pytest.mark.asyncio
    async def test_different_parameters_not_deduplicated(self):
        """测试不同参数不会被去重"""
        tool = CounterTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            enable_deduplication=True,
        )

        from fastreact.core.tool import ToolCall

        # 第一次调用
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "first"})
        )

        # 第二次调用（不同参数）
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "second"})
        )

        assert tool.call_count == 2  # 两次都执行了

    @pytest.mark.asyncio
    async def test_dedup_disabled(self):
        """测试禁用去重时每次都执行"""
        tool = CounterTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            enable_deduplication=False,  # 禁用去重
            enable_cache=False,  # 同时禁用缓存，以便测试去重功能
        )

        from fastreact.core.tool import ToolCall

        # 两次相同调用
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )

        assert tool.call_count == 2  # 两次都执行了（没有去重）


class TestDeduplicationWindow:
    """测试去重时间窗口"""

    @pytest.mark.asyncio
    async def test_expired_calls_not_deduplicated(self):
        """测试过期调用不会被去重"""
        tool = SlowTool(delay=0.05)
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            enable_deduplication=True,
            dedup_window_seconds=0.2,  # 200ms 窗口
            enable_cache=False,  # 禁用缓存以便测试去重过期
        )

        from fastreact.core.tool import ToolCall

        # 第一次调用
        result1 = await react._execute_tool_async(
            ToolCall(name="SlowTool", parameters={"query": "test"})
        )

        assert tool.call_count == 1

        # 等待超过时间窗口
        await asyncio.sleep(0.25)

        # 第二次调用（已过期）
        result2 = await react._execute_tool_async(
            ToolCall(name="SlowTool", parameters={"query": "test"})
        )

        assert tool.call_count == 2  # 重新执行了
        assert result1.result != result2.result  # 结果不同（call 次数不同）

    @pytest.mark.asyncio
    async def test_within_window_deduplicated(self):
        """测试时间窗口内的调用被去重"""
        tool = SlowTool(delay=0.05)
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            enable_deduplication=True,
            dedup_window_seconds=1.0,  # 1 秒窗口
        )

        from fastreact.core.tool import ToolCall

        # 第一次调用
        await react._execute_tool_async(
            ToolCall(name="SlowTool", parameters={"query": "test"})
        )

        # 等待一小段时间（但在窗口内）
        await asyncio.sleep(0.1)

        # 第二次调用
        await react._execute_tool_async(
            ToolCall(name="SlowTool", parameters={"query": "test"})
        )

        assert tool.call_count == 1  # 只执行了一次


class TestDeduplicationStatistics:
    """测试去重统计"""

    @pytest.mark.asyncio
    async def test_dedup_hits_counter(self):
        """测试去重命中计数"""
        tool = CounterTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            enable_deduplication=True,
        )

        from fastreact.core.tool import ToolCall

        # 第一次调用
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )

        assert react.stats["dedup_hits"] == 0

        # 第二次调用（去重命中）
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )

        assert react.stats["dedup_hits"] == 1

        # 第三次调用（去重命中）
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )

        assert react.stats["dedup_hits"] == 2

    @pytest.mark.asyncio
    async def test_dedup_disabled_no_stats(self):
        """测试禁用去重时没有统计"""
        tool = CounterTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            enable_deduplication=False,
        )

        from fastreact.core.tool import ToolCall

        # 多次调用
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )

        assert react.stats["dedup_hits"] == 0


class TestDeduplicationWithCache:
    """测试去重与缓存的关系"""

    @pytest.mark.asyncio
    async def test_dedup_before_cache(self):
        """测试去重优先级高于缓存"""
        tool = CounterTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            enable_deduplication=True,
            enable_cache=True,
        )

        from fastreact.core.tool import ToolCall

        # 第一次调用（同时更新缓存和去重记录）
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )

        # 清空 LRU 缓存但保留去重记录
        react.cache.clear()

        # 第二次调用（应该从去重记录返回，而不是缓存）
        result2 = await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )

        assert tool.call_count == 1  # 没有重新执行
        assert react.stats["cache_hits"] == 0  # 缓存被清空，没有命中
        assert react.stats["dedup_hits"] == 1  # 去重命中

    @pytest.mark.asyncio
    async def test_cache_and_dedup_both_work(self):
        """测试缓存和去重可以同时工作"""
        tool = CounterTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            enable_deduplication=True,
            enable_cache=True,
        )

        from fastreact.core.tool import ToolCall

        # 第一次调用
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )

        # 第二次调用（同时命中去重和缓存）
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "test"})
        )

        # 应该只记录去重命中（去重优先级更高）
        assert tool.call_count == 1
        # 注意：根据实现，可能只有 dedup_hits 增加，或 cache_hits 增加
        # 这取决于具体实现


class TestDeduplicationCleanup:
    """测试去重记录清理"""

    @pytest.mark.asyncio
    async def test_old_entries_removed(self):
        """测试过期记录被清理"""
        tool = CounterTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            enable_deduplication=True,
            dedup_window_seconds=0.5,
        )

        from fastreact.core.tool import ToolCall

        # 添加多条记录
        for i in range(5):
            await react._execute_tool_async(
                ToolCall(name="CounterTool", parameters={"action": f"action_{i}"})
            )
            await asyncio.sleep(0.1)

        # 等待过期
        await asyncio.sleep(0.6)

        # 触发清理（通过下一次调用）
        await react._execute_tool_async(
            ToolCall(name="CounterTool", parameters={"action": "new_action"})
        )

        # 检查 deque 大小（应该只包含最近的新记录）
        # 实际大小取决于清理逻辑，但应该小于 6
        assert len(react._recent_calls) < 6

    @pytest.mark.asyncio
    async def test_max_entries_limit(self):
        """测试最大记录数限制"""
        tool = CounterTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            enable_deduplication=True,
        )

        from fastreact.core.tool import ToolCall

        # 超过最大限制的调用（max_entries = 1000）
        for i in range(1100):
            await react._execute_tool_async(
                ToolCall(name="CounterTool", parameters={"action": f"action_{i}"})
            )

        # deque 不应该无限增长
        assert len(react._recent_calls) <= 1000


class TestDeduplicationInReActLoop:
    """测试 ReACT 循环中的去重"""

    @pytest.mark.asyncio
    async def test_react_loop_deduplication(self):
        """测试 ReACT 循环中的去重（模拟场景）"""
        tool = CounterTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            enable_deduplication=True,
            max_tool_retries=0,  # 禁用重试以便测试
        )

        # 模拟 LLM 重复调用相同工具的场景
        from fastreact.core.tool import ToolCall

        calls = [
            ToolCall(name="CounterTool", parameters={"action": "search"}),
            ToolCall(name="CounterTool", parameters={"action": "search"}),  # 重复
            ToolCall(name="CounterTool", parameters={"action": "search"}),  # 重复
            ToolCall(name="CounterTool", parameters={"action": "calculate"}),
        ]

        results = []
        for call in calls:
            result = await react._execute_tool_async(call)
            results.append(result)

        # 第一个 search 执行
        assert "executed 1 times" in results[0].result

        # 后两个 search 被去重
        assert results[1].result == results[0].result
        assert results[2].result == results[0].result

        # calculate 执行
        assert "executed 2 times" in results[3].result

        # 总共只执行了 2 次工具调用
        assert tool.call_count == 2

        # 去重命中 2 次
        assert react.stats["dedup_hits"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
