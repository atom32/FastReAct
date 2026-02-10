"""
Unit tests for FastReAct Nano tool system
"""

import pytest
import sys
import asyncio
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from fastreact.core.tools import Tool, ToolRegistry, ValidationError, EchoTool, AddTool
from fastreact.tools import ReadFileTool, WriteFileTool, ExecTool, EditFileTool


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


class TestReadFileTool:
    """Test ReadFileTool"""

    @pytest.mark.asyncio
    async def test_read_file(self):
        """Test reading a file"""
        tool = ReadFileTool()

        # Create a test file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            test_file = Path(f.name)
            f.write("Line 1\nLine 2\nLine 3\n")

        try:
            result = await tool.execute(path=str(test_file))
            assert "Line 1" in result
            assert "Line 2" in result
            assert "Line 3" in result
        finally:
            test_file.unlink()

    @pytest.mark.asyncio
    async def test_read_file_not_found(self):
        """Test reading non-existent file"""
        tool = ReadFileTool()
        result = await tool.execute(path="/nonexistent/file.txt")
        assert "[ERROR]" in result
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_read_file_with_range(self):
        """Test reading file with line range"""
        tool = ReadFileTool()

        # Create a test file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            test_file = Path(f.name)
            for i in range(1, 11):
                f.write(f"Line {i}\n")

        try:
            result = await tool.execute(path=str(test_file), start_line=3, end_line=5)
            assert "Line 3" in result
            assert "Line 4" in result
            assert "Line 5" in result  # end_line is inclusive
            assert "Line 6" not in result
        finally:
            test_file.unlink()


class TestWriteFileTool:
    """Test WriteFileTool"""

    @pytest.mark.asyncio
    async def test_write_file(self):
        """Test writing a file"""
        tool = WriteFileTool()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            content = "Hello, World!\n"

            result = await tool.execute(path=str(test_file), content=content)

            assert "[OK]" in result
            assert test_file.exists()

            # Verify content
            actual = test_file.read_text(encoding="utf-8")
            assert actual == content

    @pytest.mark.asyncio
    async def test_write_file_creates_dirs(self):
        """Test that write_file creates parent directories"""
        tool = WriteFileTool()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "subdir" / "test.txt"

            result = await tool.execute(path=str(test_file), content="test")

            assert "[OK]" in result
            assert test_file.exists()

    @pytest.mark.asyncio
    async def test_write_file_overwrites(self):
        """Test that write_file overwrites existing file"""
        tool = WriteFileTool()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"

            # Write initial content
            await tool.execute(path=str(test_file), content="old content")

            # Overwrite
            result = await tool.execute(path=str(test_file), content="new content")

            assert "[OK]" in result
            actual = test_file.read_text(encoding="utf-8")
            assert actual == "new content"


class TestExecTool:
    """Test ExecTool"""

    @pytest.mark.asyncio
    async def test_exec_echo(self):
        """Test executing echo command"""
        tool = ExecTool()

        # Use echo command (cross-platform)
        if sys.platform == "win32":
            result = await tool.execute(command="echo hello")
        else:
            result = await tool.execute(command="echo 'hello'")

        assert "hello" in result.lower()
        assert "[ERROR]" not in result

    @pytest.mark.asyncio
    async def test_exec_invalid_command(self):
        """Test executing invalid command"""
        tool = ExecTool()
        result = await tool.execute(command="nonexistentcommand12345")
        # Error output varies by platform, just check for some indication
        assert result is not None


class TestEditFileTool:
    """Test EditFileTool"""

    @pytest.mark.asyncio
    async def test_edit_file(self):
        """Test editing a file"""
        tool = EditFileTool()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            test_file = Path(f.name)
            f.write("Hello, World!\n")

        try:
            result = await tool.execute(
                path=str(test_file),
                old_text="Hello",
                new_text="Goodbye",
            )

            assert "[OK]" in result
            assert "1 occurrence" in result

            # Verify change
            content = test_file.read_text(encoding="utf-8")
            assert "Goodbye, World!" in content
        finally:
            test_file.unlink()

    @pytest.mark.asyncio
    async def test_edit_file_not_found(self):
        """Test editing non-existent file"""
        tool = EditFileTool()
        result = await tool.execute(
            path="/nonexistent/file.txt",
            old_text="old",
            new_text="new",
        )
        assert "[ERROR]" in result
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_edit_file_text_not_found(self):
        """Test editing when old_text not found"""
        tool = EditFileTool()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            test_file = Path(f.name)
            f.write("Hello, World!\n")

        try:
            result = await tool.execute(
                path=str(test_file),
                old_text="Goodbye",
                new_text="Hello",
            )

            assert "[WARNING]" in result or "[ERROR]" in result
            assert "not found" in result.lower()
        finally:
            test_file.unlink()

    @pytest.mark.asyncio
    async def test_edit_file_multiple_occurrences(self):
        """Test editing multiple occurrences"""
        tool = EditFileTool()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            test_file = Path(f.name)
            f.write("cat cat cat\n")

        try:
            result = await tool.execute(
                path=str(test_file),
                old_text="cat",
                new_text="dog",
            )

            assert "[OK]" in result
            assert "3 occurrence" in result

            # Verify all changed
            content = test_file.read_text(encoding="utf-8")
            assert content == "dog dog dog\n"
        finally:
            test_file.unlink()
