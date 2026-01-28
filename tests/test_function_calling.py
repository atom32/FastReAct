"""
测试 Function Calling API 改进

验证：
1. _build_tools_schema 正确构建工具 schema
2. _chat 方法返回结构化的响应
3. _parse_tool_calls 优先使用结构化的 tool_calls
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from fastreact.core.engine import FastReAct
from fastreact.tools.calculator import CalculatorTool


class TestFunctionCallingAPI:
    """测试 Function Calling API 集成"""

    def test_build_tools_schema(self):
        """测试工具 schema 构建"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )

        schema = react._build_tools_schema()

        # 验证 schema 结构
        assert isinstance(schema, list)
        assert len(schema) == 1

        tool_schema = schema[0]
        assert tool_schema["type"] == "function"
        assert "function" in tool_schema

        func = tool_schema["function"]
        assert func["name"] == "CalculatorTool"
        assert "description" in func
        assert "parameters" in func
        assert func["parameters"]["type"] == "object"

    def test_build_tools_schema_with_multiple_tools(self):
        """测试多个工具的 schema 构建"""
        from fastreact.tools.search import SearchTool
        from fastreact.tools.weather import WeatherTool

        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool(), SearchTool(), WeatherTool()],
        )

        schema = react._build_tools_schema()

        # 验证所有工具都在 schema 中
        assert len(schema) == 3
        tool_names = {s["function"]["name"] for s in schema}
        assert "CalculatorTool" in tool_names
        assert "SearchTool" in tool_names
        assert "WeatherTool" in tool_names

    @pytest.mark.asyncio
    async def test_parse_tool_calls_from_structured_response(self):
        """测试从结构化响应解析工具调用"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )

        # 模拟 OpenAI 的结构化 tool_calls 响应
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.type = "function"
        mock_tool_call.function.name = "CalculatorTool"
        mock_tool_call.function.arguments = '{"expression": "2 + 2"}'

        llm_response = {
            "content": "I'll calculate that for you.",
            "tool_calls": [mock_tool_call]
        }

        tool_calls = react._parse_tool_calls(llm_response)

        # 验证解析结果
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "CalculatorTool"
        assert tool_calls[0].parameters == {"expression": "2 + 2"}
        assert tool_calls[0].call_id == "call_123"

    @pytest.mark.asyncio
    async def test_parse_tool_calls_fallback_to_regex(self):
        """测试回退到正则解析（向后兼容）"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )

        # 没有结构化 tool_calls，使用正则解析
        llm_response = {
            "content": '[TOOL_CALL] {"name": "CalculatorTool", "parameters": {"expression": "3 + 3"}}'
        }

        tool_calls = react._parse_tool_calls(llm_response)

        # 验证正则解析仍然有效
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "CalculatorTool"
        assert tool_calls[0].parameters == {"expression": "3 + 3"}

    @pytest.mark.asyncio
    async def test_parse_tool_calls_handles_dict_format(self):
        """测试处理字典格式的 tool_calls（流式响应）"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )

        # 流式响应返回的字典格式
        llm_response = {
            "content": "",
            "tool_calls": [
                {
                    "id": "call_456",
                    "type": "function",
                    "function": {
                        "name": "CalculatorTool",
                        "arguments": '{"expression": "5 * 5"}'
                    }
                }
            ]
        }

        tool_calls = react._parse_tool_calls(llm_response)

        # 验证字典格式解析正确
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "CalculatorTool"
        assert tool_calls[0].parameters == {"expression": "5 * 5"}
        assert tool_calls[0].call_id == "call_456"

    @pytest.mark.asyncio
    async def test_chat_returns_structured_response(self):
        """测试 _chat 返回结构化响应"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )

        # Mock OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello"
        mock_response.choices[0].message.tool_calls = None

        react._client = AsyncMock()
        react._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await react._chat([{"role": "user", "content": "Hi"}])

        # 验证返回格式
        assert isinstance(result, dict)
        assert "content" in result
        assert result["content"] == "Hello"

    def test_simplified_system_prompt(self):
        """测试系统提示词已简化"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )

        prompt = react._build_system_prompt()

        # 验证简化的提示词
        assert "可用工具" in prompt
        assert "工作流程" in prompt
        # 不应该再包含详细的工具调用格式说明
        # （因为 Function Calling API 自动处理）

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_in_single_response(self):
        """测试单次响应中的多个工具调用"""
        from fastreact.tools.search import SearchTool

        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool(), SearchTool()],
        )

        # 模拟多个工具调用
        mock_func1 = MagicMock()
        mock_func1.name = "CalculatorTool"
        mock_func1.arguments = '{"expression": "10 + 20"}'

        mock_func2 = MagicMock()
        mock_func2.name = "SearchTool"
        mock_func2.arguments = '{"query": "Python tutorial"}'

        mock_tool_calls = [
            MagicMock(id="call_1", type="function", function=mock_func1),
            MagicMock(id="call_2", type="function", function=mock_func2),
        ]

        llm_response = {
            "content": "I'll calculate and search for you.",
            "tool_calls": mock_tool_calls
        }

        tool_calls = react._parse_tool_calls(llm_response)

        # 验证两个工具调用都被正确解析
        assert len(tool_calls) == 2
        assert tool_calls[0].name == "CalculatorTool"
        assert tool_calls[0].call_id == "call_1"
        assert tool_calls[1].name == "SearchTool"
        assert tool_calls[1].call_id == "call_2"


class TestBackwardCompatibility:
    """测试向后兼容性"""

    @pytest.mark.asyncio
    async def test_old_regex_format_still_works(self):
        """确保旧的 [TOOL_CALL] 格式仍然有效"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )

        # 旧的文本格式
        old_format_response = {
            "content": """
I'll help you calculate.

[TOOL_CALL] {"name": "CalculatorTool", "parameters": {"expression": "100 / 5"}}
"""
        }

        tool_calls = react._parse_tool_calls(old_format_response)

        # 应该能解析
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "CalculatorTool"
        assert tool_calls[0].parameters == {"expression": "100 / 5"}

    @pytest.mark.asyncio
    async def test_tool_xml_format_still_works(self):
        """确保 <tool> 格式仍然有效"""
        react = FastReAct(
            api_key="test-key",
            model="gpt-4",
            tools=[CalculatorTool()],
        )

        # XML 格式
        xml_format_response = {
            "content": '<tool>{"name": "CalculatorTool", "parameters": {"expression": "2 ** 8"}}</tool>'
        }

        tool_calls = react._parse_tool_calls(xml_format_response)

        # 应该能解析
        assert len(tool_calls) == 1
        assert tool_calls[0].name == "CalculatorTool"
        assert tool_calls[0].parameters == {"expression": "2 ** 8"}
