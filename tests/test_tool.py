"""
测试FastReAct工具系统

测试Tool基类和相关数据类
"""

import pytest
import asyncio
from fastreact.core.tool import Tool, ToolCall, ToolResult


class MockTool(Tool):
    """用于测试的模拟工具"""

    def _get_description(self) -> str:
        return "这是一个测试工具"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "输入参数"
                }
            },
            "required": ["input"]
        }

    async def execute_async(self, input: str) -> str:
        return f"处理结果: {input}"


class AsyncTool(Tool):
    """真正的异步工具"""

    def _get_description(self) -> str:
        return "异步测试工具"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "delay": {
                    "type": "number",
                    "description": "延迟时间（秒）"
                }
            },
            "required": ["delay"]
        }

    async def execute_async(self, delay: float) -> str:
        await asyncio.sleep(delay)
        return f"等待了 {delay} 秒"


class FailingTool(Tool):
    """会抛出异常的工具"""

    def _get_description(self) -> str:
        return "会失败的工具"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "should_fail": {
                    "type": "boolean",
                    "description": "是否失败"
                }
            },
            "required": ["should_fail"]
        }

    async def execute_async(self, should_fail: bool) -> str:
        if should_fail:
            raise ValueError("工具执行失败")
        return "成功"


class TestToolCall:
    """测试ToolCall数据类"""

    def test_create_tool_call(self):
        """测试创建ToolCall"""
        call = ToolCall(
            name="test_tool",
            parameters={"param1": "value1"},
            call_id="test_id_123"
        )

        assert call.name == "test_tool"
        assert call.parameters == {"param1": "value1"}
        assert call.call_id == "test_id_123"

    def test_tool_call_default_call_id(self):
        """测试默认call_id"""
        call = ToolCall(
            name="test_tool",
            parameters={"param1": "value1"}
        )

        assert call.call_id == ""

    def test_tool_call_to_dict(self):
        """测试转换为字典"""
        call = ToolCall(
            name="test_tool",
            parameters={"param1": "value1"},
            call_id="test_id"
        )

        result = call.to_dict()
        assert result == {
            "name": "test_tool",
            "parameters": {"param1": "value1"},
            "call_id": "test_id"
        }


class TestToolResult:
    """测试ToolResult数据类"""

    def test_create_success_result(self):
        """测试创建成功结果"""
        result = ToolResult(
            tool_name="test_tool",
            result="执行成功",
            execution_time=0.5
        )

        assert result.tool_name == "test_tool"
        assert result.result == "执行成功"
        assert result.error is None
        assert result.execution_time == 0.5
        assert result.is_success is True

    def test_create_error_result(self):
        """测试创建错误结果"""
        result = ToolResult(
            tool_name="test_tool",
            result=None,
            error="执行失败",
            execution_time=0.3
        )

        assert result.tool_name == "test_tool"
        assert result.result is None
        assert result.error == "执行失败"
        assert result.execution_time == 0.3
        assert result.is_success is False

    def test_tool_result_to_dict(self):
        """测试转换为字典"""
        result = ToolResult(
            tool_name="test_tool",
            result="成功",
            error=None,
            execution_time=1.0
        )

        result_dict = result.to_dict()
        assert result_dict == {
            "tool_name": "test_tool",
            "result": "成功",
            "error": None,
            "execution_time": 1.0
        }

    def test_is_success_property(self):
        """测试is_success属性"""
        success_result = ToolResult(
            tool_name="tool",
            result="ok",
            error=None
        )
        assert success_result.is_success is True

        error_result = ToolResult(
            tool_name="tool",
            result=None,
            error="error"
        )
        assert error_result.is_success is False


class TestTool:
    """测试Tool基类"""

    def test_tool_initialization(self):
        """测试工具初始化"""
        tool = MockTool()

        assert tool.name == "MockTool"
        assert tool.description == "这是一个测试工具"
        assert "input" in tool.parameters["properties"]

    def test_tool_to_dict(self):
        """测试转换为字典"""
        tool = MockTool()
        tool_dict = tool.to_dict()

        assert tool_dict["name"] == "MockTool"
        assert tool_dict["description"] == "这是一个测试工具"
        assert "properties" in tool_dict["parameters"]

    def test_tool_repr(self):
        """测试字符串表示"""
        tool = MockTool()
        assert repr(tool) == "Tool(name=MockTool)"

    @pytest.mark.asyncio
    async def test_execute_async(self):
        """测试异步执行"""
        tool = MockTool()
        result = await tool.execute_async(input="测试输入")

        assert result == "处理结果: 测试输入"

    @pytest.mark.asyncio
    async def test_execute_async_with_delay(self):
        """测试真正的异步执行"""
        tool = AsyncTool()
        import time
        start = time.time()
        result = await tool.execute_async(delay=0.1)
        elapsed = time.time() - start

        assert result == "等待了 0.1 秒"
        assert elapsed >= 0.1  # 至少等待了0.1秒

    def test_execute_sync(self):
        """测试同步执行"""
        tool = MockTool()
        result = tool.execute(input="同步测试")

        assert result == "处理结果: 同步测试"

    @pytest.mark.asyncio
    async def test_execute_with_exception(self):
        """测试工具执行异常"""
        tool = FailingTool()

        with pytest.raises(ValueError, match="工具执行失败"):
            await tool.execute_async(should_fail=True)

    @pytest.mark.asyncio
    async def test_execute_without_exception(self):
        """测试工具正常执行"""
        tool = FailingTool()
        result = await tool.execute_async(should_fail=False)

        assert result == "成功"


class TestToolIntegration:
    """工具集成测试"""

    @pytest.mark.asyncio
    async def test_multiple_tools_execution(self):
        """测试多个工具并发执行"""
        tool1 = MockTool()
        tool2 = AsyncTool()

        results = await asyncio.gather(
            tool1.execute_async(input="任务1"),
            tool2.execute_async(delay=0.05)
        )

        assert results[0] == "处理结果: 任务1"
        assert results[1] == "等待了 0.05 秒"

    @pytest.mark.asyncio
    async def test_tool_with_complex_parameters(self):
        """测试复杂参数"""
        tool = MockTool()
        result = await tool.execute_async(input="复杂参数测试")

        assert "复杂参数测试" in result

    def test_tool_parameters_schema(self):
        """测试参数schema格式"""
        tool = MockTool()
        schema = tool.parameters

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "input" in schema["properties"]
        assert schema["properties"]["input"]["type"] == "string"
        assert "input" in schema["required"]

    @pytest.mark.asyncio
    async def test_tool_execution_tracking(self):
        """测试工具执行追踪"""
        tool = MockTool()

        import time
        start = time.time()
        await tool.execute_async(input="测试")
        execution_time = time.time() - start

        # 工具应该快速执行
        assert execution_time < 1.0
