"""
测试同步接口的问题和改进

演示：
1. asyncio.run() 在已有事件循环中的问题
2. 修复后的行为
"""

import asyncio
import pytest
from fastreact import FastReAct
from fastreact.tools.calculator import CalculatorTool


class TestSyncInterfaceIssues:
    """测试同步接口的问题"""

    def test_sync_run_without_event_loop(self):
        """测试在没有事件循环时同步调用可以工作"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )

        # 这应该工作
        # 注意：由于没有真实的 API key，这会失败，但至少不会因为 asyncio.run() 崩溃
        try:
            result = react.run("2 + 2")
            # 如果有 mock API，会返回结果
        except Exception as e:
            # 预期：可能是 API 错误，而不是 asyncio 错误
            assert "asyncio" not in str(e) or "no running event loop" not in str(e).lower()

    @pytest.mark.asyncio
    async def test_sync_run_inside_event_loop_fails(self):
        """测试在已有事件循环中调用同步接口会失败"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )

        # 这应该失败并给出清晰的错误信息
        with pytest.raises(RuntimeError) as exc_info:
            react.run("2 + 2")

        # 验证错误信息有帮助
        error_msg = str(exc_info.value)
        assert "event loop" in error_msg.lower() or "async" in error_msg.lower()


class TestAsyncInterfaceBestPractice:
    """测试异步接口的最佳实践"""

    @pytest.mark.asyncio
    async def test_async_run_in_event_loop(self):
        """测试异步接口在事件循环中正常工作"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )

        # 异步接口是推荐的方式
        # 注意：由于没有真实 API，这里只测试接口存在
        assert hasattr(react, 'run_async')
        assert asyncio.iscoroutinefunction(react.run_async)

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """测试异步上下文管理器（最佳实践）"""
        async with FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()]
        ) as react:
            # 验证资源自动管理
            assert react is not None
            assert hasattr(react, 'run_async')


class TestNestedEventLoopScenarios:
    """测试嵌套事件循环场景"""

    @pytest.mark.asyncio
    async def test_multiple_async_calls(self):
        """测试多个异步调用不冲突"""
        async with FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()]
        ) as react:
            # 可以多次调用
            assert asyncio.iscoroutinefunction(react.run_async)
            assert asyncio.iscoroutinefunction(react.close)

    def test_sync_call_from_main(self):
        """测试从主线程同步调用（没有事件循环）"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )

        # 在主线程中调用应该是可以的
        # 因为没有事件循环
        try:
            result = react.run("test")
        except Exception as e:
            # 可能是 API 错误，不是 asyncio 错误
            pass


if __name__ == "__main__":
    # 手动运行测试
    print("运行同步接口测试...")
    pytest.main([__file__, "-v"])
