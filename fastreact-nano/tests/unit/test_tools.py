"""
Unit tests for FastReAct Nano tool system
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastreact.core.tools import Tool, ToolRegistry, ValidationError, EchoTool, AddTool


class TestTool:
    """Test Tool base class"""

    def test_echo_tool(self):
        """Test EchoTool"""
        tool = EchoTool()
        assert tool.name == "echo"
        assert "echo" in tool.description.lower()
        assert isinstance(tool.parameters, dict)

    def test_add_tool(self):
        """Test AddTool"""
        tool = AddTool()
        assert tool.name == "add"
        assert tool.parameters["properties"]["a"]["type"] == "number"
        assert tool.parameters["properties"]["b"]["type"] == "number"

    def test_tool_validation(self):
        """Test parameter validation"""
        tool = AddTool()

        # Valid params
        errors = tool.validate_params({"a": 1, "b": 2})
        assert len(errors) == 0

        # Missing required param
        errors = tool.validate_params({"a": 1})
        assert len(errors) > 0
        assert "b" in errors[0]

        # Wrong type
        errors = tool.validate_params({"a": "not_a_number", "b": 2})
        assert len(errors) > 0


class TestToolRegistry:
    """Test ToolRegistry"""

    @pytest.fixture
    def registry(self):
        """Create registry for testing"""
        reg = ToolRegistry()
        reg.register(EchoTool())
        reg.register(AddTool())
        return reg

    def test_list_all(self, registry):
        """Test listing tools"""
        tools = registry.list_all()
        assert len(tools) == 2
        assert "echo" in tools
        assert "add" in tools

    def test_get_tool(self, registry):
        """Test getting tool"""
        tool = registry.get("echo")
        assert tool is not None
        assert tool.name == "echo"

    def test_get_nonexistent(self, registry):
        """Test getting non-existent tool"""
        tool = registry.get("nonexistent")
        assert tool is None

    def test_schemas(self, registry):
        """Test getting schemas"""
        schemas = registry.schemas()
        assert len(schemas) == 2

    def test_duplicate_registration(self, registry):
        """Test that duplicate registration raises error"""
        with pytest.raises(ValueError):
            registry.register(EchoTool())

    @pytest.mark.asyncio
    async def test_execute_echo(self, registry):
        """Test executing echo tool"""
        result = await registry.execute("echo", {"text": "hello"})
        assert "[ECHO]" in result
        assert "hello" in result

    @pytest.mark.asyncio
    async def test_execute_add(self, registry):
        """Test executing add tool"""
        result = await registry.execute("add", {"a": 5, "b": 3})
        assert "8" in result

    @pytest.mark.asyncio
    async def test_execute_invalid_tool(self, registry):
        """Test executing invalid tool"""
        result = await registry.execute("invalid", {})
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_execute_invalid_params(self, registry):
        """Test executing with invalid params"""
        with pytest.raises(ValidationError):
            await registry.execute("add", {"a": "invalid"})
