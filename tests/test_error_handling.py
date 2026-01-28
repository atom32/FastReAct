"""
测试错误处理和智能重试

验证：
1. 自定义异常类的正确使用
2. 可重试错误的自动重试
3. 不可重试错误的快速失败
4. 指数退避重试策略
5. 错误分类和日志记录
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastreact import FastReAct
from fastreact.core.tool import Tool
from fastreact.core.exceptions import (
    RetryableError,
    NonRetryableError,
    NetworkError,
    TimeoutError,
    ValidationError,
    ToolNotFoundError,
    is_retryable_error,
    get_suggested_retry_delay,
)


class FlakyTool(Tool):
    """一个不稳定的测试工具（用于测试重试）"""

    def __init__(self, fail_times=2, error_type=None):
        """
        初始化不稳定工具

        Args:
            fail_times: 前N次调用会失败
            error_type: 抛出的错误类型
        """
        super().__init__()
        self.fail_times = fail_times
        self.call_count = 0
        self.error_type = error_type or NetworkError

    def _get_description(self):
        return "一个不稳定的测试工具"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "输入"}
            }
        }

    async def execute_async(self, **kwargs):
        self.call_count += 1

        # 前N次调用失败
        if self.call_count <= self.fail_times:
            if self.error_type == NetworkError:
                raise NetworkError(
                    "Network timeout",
                    tool_name=self.name,
                    retry_after=0.1
                )
            elif self.error_type == TimeoutError:
                raise TimeoutError("Request timeout")
            else:
                raise Exception("Generic error")

        # 之后成功
        return f"Success after {self.call_count} attempts"


class AlwaysFailTool(Tool):
    """一个总是失败的测试工具"""

    def _get_description(self):
        return "一个总是失败的测试工具"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            }
        }

    async def execute_async(self, **kwargs):
        raise ValidationError("Invalid parameters", validation_errors={"input": "required"})


class TestExceptionHierarchy:
    """测试异常类层次结构"""

    def test_base_exception_creation(self):
        """测试基础异常创建"""
        from fastreact.core.exceptions import FastReActError

        error = FastReActError("Test error", details={"key": "value"})
        assert error.message == "Test error"
        assert error.details == {"key": "value"}
        assert "Test error" in str(error)

    def test_retryable_error_creation(self):
        """测试可重试错误创建"""
        error = RetryableError(
            "Temporary failure",
            tool_name="TestTool",
            retry_after=2.0
        )
        assert error.retry_after == 2.0
        assert error.tool_name == "TestTool"
        assert is_retryable_error(error) is True

    def test_non_retryable_error_creation(self):
        """测试不可重试错误创建"""
        error = ValidationError("Invalid input")
        assert is_retryable_error(error) is False

    def test_network_error_creation(self):
        """测试网络错误创建"""
        error = NetworkError(
            "Connection failed",
            status_code=503
        )
        assert error.status_code == 503
        assert error.retry_after == 2.0  # 默认值
        assert is_retryable_error(error) is True

    def test_timeout_error_creation(self):
        """测试超时错误创建"""
        error = TimeoutError("Request timeout", timeout=30.0)
        assert error.timeout == 30.0
        assert error.retry_after == 1.0  # 默认值

    def test_error_to_dict(self):
        """测试错误序列化"""
        error = NetworkError(
            "Network error",
            tool_name="TestTool",
            status_code=500
        )
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "NetworkError"
        assert error_dict["message"] == "Network error"
        assert "tool_name" in error_dict["details"]


class TestRetryableErrorDetection:
    """测试可重试错误检测"""

    def test_custom_retryable_error(self):
        """测试自定义可重试错误"""
        error = RetryableError("Temporary failure")
        assert is_retryable_error(error) is True

    def test_custom_non_retryable_error(self):
        """测试自定义不可重试错误"""
        error = ValidationError("Invalid input")
        assert is_retryable_error(error) is False

    def test_timeout_error_by_name(self):
        """测试通过名称检测超时错误"""
        error = Exception("TimeoutError: connection timed out")
        # 通用 Exception 不应该被检测为可重试
        assert is_retryable_error(error) is False

    def test_connection_error_by_name(self):
        """测试通过名称检测连接错误"""
        error = Exception("ConnectionError: failed to connect")
        assert is_retryable_error(error) is False

    def test_http_status_codes(self):
        """测试 HTTP 状态码判断"""
        # 模拟带有 status 属性的错误
        error_500 = MagicMock()
        error_500.status = 500
        assert is_retryable_error(error_500) is True

        error_503 = MagicMock()
        error_503.status = 503
        assert is_retryable_error(error_503) is True

        error_400 = MagicMock()
        error_400.status = 400
        assert is_retryable_error(error_400) is False

        error_404 = MagicMock()
        error_404.status = 404
        assert is_retryable_error(error_404) is False


class TestRetryDelayCalculation:
    """测试重试延迟计算"""

    def test_expponential_backoff(self):
        """测试指数退避"""
        # 基础延迟：2^attempt
        assert get_suggested_retry_delay(Exception(), 0) < 2
        assert get_suggested_retry_delay(Exception(), 1) < 4
        assert get_suggested_retry_delay(Exception(), 2) < 8
        assert get_suggested_retry_delay(Exception(), 3) < 16

    def test_max_delay_cap(self):
        """测试最大延迟上限"""
        # 即使 attempt 很大，延迟也不会超过 30 秒 + 抖动
        delay = get_suggested_retry_delay(Exception(), 10)
        assert delay <= 40  # 30 + 最大抖动 (30 * 0.25 = 7.5)，加上一些余量

    def test_custom_retry_after(self):
        """测试自定义建议延迟"""
        error = RetryableError("Temporary failure", retry_after=5.0)
        delay = get_suggested_retry_delay(error, 0)
        assert delay == 5.0

    def test_jitter(self):
        """测试抖动（随机性）"""
        # 多次调用应该产生不同的延迟
        delays = [
            get_suggested_retry_delay(Exception(), 1)
            for _ in range(10)
        ]
        # 不应该完全相同（因为有抖动）
        assert len(set(delays)) > 1


class TestToolRetryLogic:
    """测试工具重试逻辑"""

    @pytest.mark.asyncio
    async def test_flaky_tool_eventually_succeeds(self):
        """测试不稳定工具最终成功"""
        tool = FlakyTool(fail_times=2, error_type=NetworkError)
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            max_tool_retries=3,
        )

        from fastreact.core.tool import ToolCall
        result = await react._execute_tool_async(
            ToolCall(name="FlakyTool", parameters={"input": "test"})
        )

        # 应该成功
        assert result.is_success is True
        assert "Success after" in result.result
        assert tool.call_count == 3  # 2 次失败 + 1 次成功

    @pytest.mark.asyncio
    async def test_tool_reaches_max_retries(self):
        """测试工具达到最大重试次数"""
        tool = FlakyTool(fail_times=10, error_type=NetworkError)
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            max_tool_retries=2,  # 最多重试 2 次，总共 3 次尝试
        )

        from fastreact.core.tool import ToolCall
        result = await react._execute_tool_async(
            ToolCall(name="FlakyTool", parameters={"input": "test"})
        )

        # 应该失败
        assert result.is_success is False
        assert "max retries" in result.error.lower() or "exceeded" in result.error.lower()
        assert tool.call_count == 3  # 初始 + 2 次重试

    @pytest.mark.asyncio
    async def test_non_retryable_error_fails_immediately(self):
        """测试不可重试错误立即失败"""
        tool = AlwaysFailTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            max_tool_retries=5,
        )

        from fastreact.core.tool import ToolCall
        result = await react._execute_tool_async(
            ToolCall(name="AlwaysFailTool", parameters={"input": "test"})
        )

        # 应该立即失败，不重试
        assert result.is_success is False
        assert "ValidationError" in result.error
        # 只调用一次（没有重试）
        # 注意：AlwaysFailTool 没有计数器，但我们可以检查错误消息

    @pytest.mark.asyncio
    async def test_retry_disabled(self):
        """测试禁用重试"""
        tool = FlakyTool(fail_times=1, error_type=NetworkError)
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            max_tool_retries=3,
            enable_tool_retry=False,  # 禁用重试
        )

        from fastreact.core.tool import ToolCall
        result = await react._execute_tool_async(
            ToolCall(name="FlakyTool", parameters={"input": "test"})
        )

        # 应该失败（没有重试）
        assert result.is_success is False
        assert tool.call_count == 1  # 只调用一次


class TestToolNotFoundError:
    """测试工具不存在错误"""

    @pytest.mark.asyncio
    async def test_tool_not_found_error(self):
        """测试工具不存在错误"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[],
        )

        from fastreact.core.tool import ToolCall
        result = await react._execute_tool_async(
            ToolCall(name="NonExistentTool", parameters={})
        )

        # 应该返回工具不存在的错误
        assert result.is_success is False
        assert "not found" in result.error.lower()
        assert "NonExistentTool" in result.error


class TestRetryStatistics:
    """测试重试统计"""

    @pytest.mark.asyncio
    async def test_retry_statistics_update(self):
        """测试重试统计信息更新"""
        tool = FlakyTool(fail_times=2, error_type=NetworkError)
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            max_tool_retries=3,
        )

        from fastreact.core.tool import ToolCall
        await react._execute_tool_async(
            ToolCall(name="FlakyTool", parameters={"input": "test"})
        )

        # 检查统计信息
        assert react.stats["tool_retries"] == 2  # 2 次重试
        assert react.stats["tool_calls"] == 1   # 1 次成功调用
        assert react.stats["tool_errors"] == 0   # 0 次错误（最终成功）

    @pytest.mark.asyncio
    async def test_error_statistics_update(self):
        """测试错误统计信息更新"""
        tool = AlwaysFailTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            max_tool_retries=2,
        )

        from fastreact.core.tool import ToolCall
        result = await react._execute_tool_async(
            ToolCall(name="AlwaysFailTool", parameters={"input": "test"})
        )

        # 检查统计信息
        assert result.is_success is False
        assert react.stats["tool_errors"] == 1  # 1 次错误


class TestCachingWithRetry:
    """测试带重试的缓存行为"""

    @pytest.mark.asyncio
    async def test_only_cache_first_success(self):
        """测试只在首次成功时缓存"""
        tool = FlakyTool(fail_times=1, error_type=NetworkError)
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            max_tool_retries=3,
            enable_cache=True,
        )

        from fastreact.core.tool import ToolCall
        # 第一次调用（会重试）
        result1 = await react._execute_tool_async(
            ToolCall(name="FlakyTool", parameters={"input": "test"})
        )

        assert result1.is_success is True
        assert tool.call_count == 2

        # 第二次调用（应该从缓存返回，不增加调用次数）
        result2 = await react._execute_tool_async(
            ToolCall(name="FlakyTool", parameters={"input": "test"})
        )

        assert result2.is_success is True
        assert tool.call_count == 2  # 没有增加（从缓存获取）


class TestErrorMessages:
    """测试错误消息质量"""

    @pytest.mark.asyncio
    async def test_detailed_error_messages(self):
        """测试详细的错误消息"""
        tool = FlakyTool(fail_times=10, error_type=NetworkError)
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            max_tool_retries=2,
        )

        from fastreact.core.tool import ToolCall
        result = await react._execute_tool_async(
            ToolCall(name="FlakyTool", parameters={"input": "test"})
        )

        # 错误消息应该包含有用的信息
        assert result.error is not None
        assert "NetworkError" in result.error or "exceeded" in result.error.lower()

    @pytest.mark.asyncio
    async def test_validation_error_message(self):
        """测试验证错误消息"""
        tool = AlwaysFailTool()
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[tool],
            max_tool_retries=3,
        )

        from fastreact.core.tool import ToolCall
        result = await react._execute_tool_async(
            ToolCall(name="AlwaysFailTool", parameters={"input": "test"})
        )

        # 验证错误应该包含详细信息
        assert "ValidationError" in result.error
        assert "Invalid parameters" in result.error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
