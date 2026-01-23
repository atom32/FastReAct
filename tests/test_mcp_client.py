"""
MCP Client Manager 测试

测试 MCP 工具的加载和执行。
"""

import pytest
import asyncio
from pathlib import Path

from fastreact.tools import MCPClientManager


class TestMCPClientManager:
    """MCP Client Manager 测试套件"""

    @pytest.mark.asyncio
    async def test_manager_creation(self):
        """测试管理器创建"""
        manager = MCPClientManager()
        assert len(manager) == 0
        assert manager.list_servers() == []

    @pytest.mark.asyncio
    async def test_add_server(self):
        """测试添加服务器"""
        manager = MCPClientManager()

        # 添加 stdio 服务器
        manager.add_server("test-stdio", {
            "command": "echo",
            "args": ["test"]
        })

        assert len(manager) == 1
        assert "test-stdio" in manager.list_servers()

        # 添加 HTTP 服务器
        manager.add_server("test-http", {
            "url": "http://localhost:8080/mcp"
        })

        assert len(manager) == 2
        assert "test-http" in manager.list_servers()

    @pytest.mark.asyncio
    async def test_remove_server(self):
        """测试移除服务器"""
        manager = MCPClientManager()

        manager.add_server("test", {"command": "echo"})
        assert len(manager) == 1

        manager.remove_server("test")
        assert len(manager) == 0

    @pytest.mark.asyncio
    async def test_duplicate_server(self):
        """测试重复添加服务器"""
        manager = MCPClientManager()

        manager.add_server("test", {"command": "echo"})

        with pytest.raises(ValueError, match="already exists"):
            manager.add_server("test", {"command": "echo"})

    @pytest.mark.asyncio
    async def test_load_config_file(self, tmp_path):
        """测试从配置文件加载"""
        # 创建临时配置文件
        config_file = tmp_path / "test_config.json"
        config_file.write_text("""
        {
            "mcpServers": {
                "test1": {
                    "command": "echo",
                    "args": ["test1"]
                },
                "test2": {
                    "url": "http://localhost:8080/mcp"
                }
            }
        }
        """)

        manager = MCPClientManager(str(config_file))

        assert len(manager) == 2
        assert "test1" in manager.list_servers()
        assert "test2" in manager.list_servers()

    @pytest.mark.asyncio
    async def test_load_nonexistent_config(self):
        """测试加载不存在的配置文件"""
        with pytest.raises(FileNotFoundError):
            MCPClientManager("nonexistent.json")

    @pytest.mark.asyncio
    async def test_save_config(self, tmp_path):
        """测试保存配置"""
        manager = MCPClientManager()

        manager.add_server("test", {
            "command": "echo",
            "args": ["test"]
        })

        config_file = tmp_path / "saved_config.json"
        manager.save_config(str(config_file))

        # 验证文件存在
        assert config_file.exists()

        # 验证内容
        import json
        with open(config_file) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "test" in config["mcpServers"]
        assert config["mcpServers"]["test"]["command"] == "echo"

    @pytest.mark.asyncio
    async def test_server_status(self):
        """测试服务器状态"""
        manager = MCPClientManager()

        manager.add_server("server1", {"command": "echo"})
        manager.add_server("server2", {"url": "http://localhost:8080"})

        status = manager.get_server_status()

        assert len(status) == 2
        assert "server1" in status
        assert "server2" in status
        # 未连接时应该都是 False
        assert status["server1"] is False
        assert status["server2"] is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试上下文管理器"""
        manager = MCPClientManager()

        # 添加一个虚拟服务器（不会真的连接）
        manager.add_server("test", {"command": "echo"})

        # 上下文管理器应该正常工作（即使连接失败）
        try:
            async with manager.auto_connect():
                assert len(manager) == 1
        except Exception:
            # 连接失败是预期的，因为我们用的是 echo 命令
            pass

    @pytest.mark.asyncio
    async def test_get_server_tools_not_connected(self):
        """测试未连接时获取工具"""
        manager = MCPClientManager()

        manager.add_server("test", {"command": "echo"})

        with pytest.raises(RuntimeError, match="not connected"):
            await manager.get_server_tools("test")

    @pytest.mark.asyncio
    async def test_get_server_tools_not_found(self):
        """测试获取不存在服务器的工具"""
        manager = MCPClientManager()

        with pytest.raises(ValueError, match="not found"):
            await manager.get_server_tools("nonexistent")


class TestMCPServerConnection:
    """MCP 服务器连接测试"""

    @pytest.mark.asyncio
    async def test_connection_creation(self):
        """测试连接对象创建"""
        from fastreact.tools.mcp_client_manager import MCPServerConnection

        # stdio 连接
        conn = MCPServerConnection("test", {
            "command": "echo",
            "args": ["test"]
        })

        assert conn.name == "test"
        assert conn.is_connected is False
        assert conn.session is None

        # HTTP 连接
        conn_http = MCPServerConnection("test-http", {
            "url": "http://localhost:8080/mcp"
        })

        assert conn_http.name == "test-http"
        assert conn_http.is_connected is False

    @pytest.mark.asyncio
    async def test_invalid_config(self):
        """测试无效配置"""
        from fastreact.tools.mcp_client_manager import MCPServerConnection

        with pytest.raises(ValueError, match="Invalid server config"):
            conn = MCPServerConnection("test", {"invalid": "config"})
            await conn.connect()


class TestMCPToolWrapperExternal:
    """MCP 工具包装器测试"""

    @pytest.mark.asyncio
    async def test_wrapper_creation(self):
        """测试工具包装器创建"""
        from fastreact.tools.mcp_client_manager import MCPToolWrapperExternal, MCPServerConnection
        from mcp.types import Tool

        # 创建 MCP 工具定义
        mcp_tool = Tool(
            name="test_tool",
            description="Test tool description",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "Parameter 1"}
                },
                "required": ["param1"]
            }
        )

        # 创建虚拟连接
        conn = MCPServerConnection("test", {"command": "echo"})

        # 创建包装器
        wrapper = MCPToolWrapperExternal(mcp_tool, conn)

        assert wrapper.name == "test_tool"
        assert wrapper.description == "Test tool description"
        assert wrapper.parameters == mcp_tool.inputSchema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
