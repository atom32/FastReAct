"""
Unit tests for MCP tool user isolation

Tests the multi-tenant isolation features for MCP tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from fastreact.core.tools import ToolRegistry, Tool
from fastreact.core.multitenant import UserContext, MultiTenantManager
from fastreact.mcp.client import SimpleMCPClient
from fastreact.mcp.manager import MCPToolWrapper, MCPToolManager
from fastreact.mcp.multitenant_manager import MultiTenantMCPManager, LazyMCPInstance
from fastreact.core.config import MCPServerConfig


# ===== Tool.execute() Tests =====

@pytest.mark.asyncio
async def test_tool_execute_receives_user_context():
    """Verify Tool.execute() accepts user_context parameter"""

    class TestTool(Tool):
        @property
        def name(self) -> str:
            return "test_tool"

        @property
        def description(self) -> str:
            return "Test tool"

        async def execute(self, user_context=None, **kwargs):
            if user_context:
                return f"User: {user_context.user_key}"
            return "No user"

    tool = TestTool()
    result = await tool.execute(user_context=UserContext(
        user_key="feishu:ou_123",
        workspace=Path("/tmp/test"),
        config={},
        skills_dir=Path("/tmp/skills"),
        memory_file=Path("/tmp/memory.json"),
    ))

    assert result == "User: feishu:ou_123"


@pytest.mark.asyncio
async def test_tool_backward_compatibility_no_user_context():
    """Verify Tool.execute() works without user_context (backward compatibility)"""

    class TestTool(Tool):
        @property
        def name(self) -> str:
            return "test_tool"

        @property
        def description(self) -> str:
            return "Test tool"

        async def execute(self, user_context=None, **kwargs):
            return "OK"

    tool = TestTool()
    result = await tool.execute(param1="value1")

    assert result == "OK"


# ===== ToolRegistry Tests =====

@pytest.mark.asyncio
async def test_tool_registry_passes_user_context():
    """Verify ToolRegistry.execute() passes user_context to tool"""

    received_context = []

    class TestTool(Tool):
        @property
        def name(self) -> str:
            return "test_tool"

        @property
        def description(self) -> str:
            return "Test tool"

        async def execute(self, user_context=None, **kwargs):
            received_context.append(user_context)
            return "OK"

    registry = ToolRegistry()
    registry.register(TestTool())

    user_context = UserContext(
        user_key="feishu:ou_456",
        workspace=Path("/tmp/test"),
        config={},
        skills_dir=Path("/tmp/skills"),
        memory_file=Path("/tmp/memory.json"),
    )

    result = await registry.execute("test_tool", {}, user_context=user_context)

    assert result == "OK"
    assert len(received_context) == 1
    assert received_context[0].user_key == "feishu:ou_456"


# ===== MCPToolWrapper Tests =====

@pytest.mark.asyncio
async def test_mcp_wrapper_receives_user_context():
    """Verify MCPToolWrapper.execute() extracts and passes user_key"""

    mock_client = MagicMock()
    mock_client.call_tool = AsyncMock(return_value="result")
    mock_manager = MagicMock()

    wrapper = MCPToolWrapper(
        tool_name="test_tool",
        server_name="test_server",
        mcp_client=mock_client,
        mcp_manager=mock_manager,
        description="Test tool",
        parameters={},
        isolation_mode="per_user",
        transport="stdio",
    )

    user_context = UserContext(
        user_key="feishu:ou_789",
        workspace=Path("/tmp/test"),
        config={},
        skills_dir=Path("/tmp/skills"),
        memory_file=Path("/tmp/memory.json"),
    )

    result = await wrapper.execute(user_context=user_context, param1="value1")

    assert result == "result"
    mock_client.call_tool.assert_called_once_with(
        "test_tool",
        {"param1": "value1"},
        user_key="feishu:ou_789"
    )


@pytest.mark.asyncio
async def test_mcp_wrapper_no_user_context():
    """Verify MCPToolWrapper works without user_context (backward compatibility)"""

    mock_client = MagicMock()
    mock_client.call_tool = AsyncMock(return_value="result")
    mock_manager = MagicMock()

    wrapper = MCPToolWrapper(
        tool_name="test_tool",
        server_name="test_server",
        mcp_client=mock_client,
        mcp_manager=mock_manager,
        description="Test tool",
        parameters={},
        isolation_mode="shared",
        transport="stdio",
    )

    result = await wrapper.execute(param1="value1")

    assert result == "result"
    mock_client.call_tool.assert_called_once_with(
        "test_tool",
        {"param1": "value1"},
        user_key=None
    )


# ===== SimpleMCPClient Tests =====

@pytest.mark.asyncio
async def test_mcp_client_passes_user_key():
    """Verify SimpleMCPClient.call_tool() includes user_key in request"""

    with patch('fastreact.mcp.client.asyncio.create_subprocess_exec') as mock_subprocess:
        # Mock subprocess
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline = AsyncMock(return_value=b'{"result": {"content": [{"text": "test result"}]}}\n')
        mock_subprocess.return_value = mock_process

        client = SimpleMCPClient(
            server_command="python3",
            server_args=["test_server.py"]
        )

        await client.connect()

        # Call tool with user_key
        result = await client.call_tool(
            "test_tool",
            {"param1": "value1"},
            user_key="feishu:ou_abc"
        )

        assert "test result" in result

        # Verify request included user_key
        written_data = mock_process.stdin.write.call_args[0][0]
        import json
        request = json.loads(written_data.decode())

        assert request["params"]["user_key"] == "feishu:ou_abc"

        await client.close()


@pytest.mark.asyncio
async def test_mcp_client_no_user_key():
    """Verify SimpleMCPClient.call_tool() works without user_key"""

    with patch('fastreact.mcp.client.asyncio.create_subprocess_exec') as mock_subprocess:
        # Mock subprocess
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline = AsyncMock(return_value=b'{"result": {"content": [{"text": "test result"}]}}\n')
        mock_subprocess.return_value = mock_process

        client = SimpleMCPClient(
            server_command="python3",
            server_args=["test_server.py"]
        )

        await client.connect()

        # Call tool without user_key
        result = await client.call_tool(
            "test_tool",
            {"param1": "value1"}
        )

        assert "test result" in result

        # Verify request does NOT include user_key
        written_data = mock_process.stdin.write.call_args[0][0]
        import json
        request = json.loads(written_data.decode())

        assert "user_key" not in request["params"]

        await client.close()


# ===== MultiTenantMCPManager Tests =====

@pytest.mark.asyncio
async def test_multitenant_mcp_shared_mode():
    """Verify shared mode creates only one manager"""

    tool_registry = ToolRegistry()
    multitenant_mgr = MultiTenantManager(base_workspace=Path("/tmp/test_workspace"))
    manager = MultiTenantMCPManager(tool_registry, multitenant_mgr)

    server_config = MCPServerConfig(
        name="test_server",
        command="python3",
        args=["test.py"],
        isolation="shared"
    )

    # Mock the add_server method to avoid actual subprocess creation
    with patch.object(MCPToolManager, 'add_server', new=AsyncMock()):
        # User A request
        mgr1, _ = await manager.get_manager("test_server", server_config, "feishu:ou_aaa")

        # User B request
        mgr2, _ = await manager.get_manager("test_server", server_config, "feishu:ou_bbb")

        # Should be same manager instance
        assert mgr1 is mgr2

    await manager.close_all()


@pytest.mark.asyncio
async def test_multitenant_mcp_per_user_mode():
    """Verify per_user mode creates separate managers"""

    tool_registry = ToolRegistry()
    multitenant_mgr = MultiTenantManager(base_workspace=Path("/tmp/test_workspace"))
    manager = MultiTenantMCPManager(tool_registry, multitenant_mgr)

    server_config = MCPServerConfig(
        name="test_server",
        command="python3",
        args=["test.py"],
        isolation="per_user",
        per_user_args_template=["--user-dir", "{user_workspace}"]
    )

    # Mock the add_server method to avoid actual subprocess creation
    with patch.object(MCPToolManager, 'add_server', new=AsyncMock()):
        # User A request
        mgr1, _ = await manager.get_manager("test_server", server_config, "feishu:ou_aaa")

        # User B request
        mgr2, _ = await manager.get_manager("test_server", server_config, "feishu:ou_bbb")

        # Should be different manager instances
        assert mgr1 is not mgr2

    await manager.close_all()


@pytest.mark.asyncio
async def test_multitenant_mcp_per_user_requires_user_key():
    """Verify per_user mode raises error without user_key"""

    tool_registry = ToolRegistry()
    multitenant_mgr = MultiTenantManager(base_workspace=Path("/tmp/test_workspace"))
    manager = MultiTenantMCPManager(tool_registry, multitenant_mgr)

    server_config = MCPServerConfig(
        name="test_server",
        command="python3",
        args=["test.py"],
        isolation="per_user"
    )

    with pytest.raises(ValueError, match="user_key required"):
        await manager.get_manager("test_server", server_config, None)

    await manager.close_all()


@pytest.mark.asyncio
async def test_user_args_substitution():
    """Verify user argument template substitution"""

    tool_registry = ToolRegistry()
    multitenant_mgr = MultiTenantManager(base_workspace=Path("/tmp/test_workspace"))
    manager = MultiTenantMCPManager(tool_registry, multitenant_mgr)

    template = ["--user-dir", "{user_workspace}", "--user-key", "{user_key}"]
    args = manager._substitute_user_args(template, "feishu:ou_123")

    assert args[0] == "--user-dir"
    # args[1] should contain the user workspace path
    assert "feishu" in args[1]
    assert "ou_123" in args[1]
    assert args[2] == "--user-key"
    assert args[3] == "feishu:ou_123"

    await manager.close_all()


# ===== LazyMCPInstance Tests =====

def test_lazy_mcp_instance_idle_detection():
    """Verify LazyMCPInstance correctly detects idle state"""

    mock_manager = MagicMock()
    instance = LazyMCPInstance(mock_manager, idle_timeout=1)

    # Should not be idle immediately
    assert not instance.is_idle()

    # Should be idle after timeout
    import time
    time.sleep(1.1)
    assert instance.is_idle()


@pytest.mark.asyncio
async def test_lazy_mcp_instance_ref_count():
    """Verify LazyMCPInstance ref counting prevents idle detection"""

    mock_manager = MagicMock()
    instance = LazyMCPInstance(mock_manager, idle_timeout=1)

    # Acquire reference
    _ = instance.manager
    assert instance._ref_count == 1

    # Should not be idle while referenced
    import time
    time.sleep(1.1)
    assert not instance.is_idle()

    # Release reference
    await instance.release()
    assert instance._ref_count == 0

    # Now should be idle
    assert instance.is_idle()


# ===== MCPServerConfig Tests =====

def test_mcp_server_config_defaults():
    """Verify MCPServerConfig has correct defaults"""

    config = MCPServerConfig(
        name="test",
        command="python3",
        args=["test.py"]
    )

    assert config.isolation == "shared"
    assert config.per_user_args_template is None
    assert config.idle_timeout == 300
    assert config.max_instances == 10


def test_mcp_server_config_from_dict():
    """Verify MCPServerConfig.from_dict parses isolation settings"""

    data = {
        "name": "test_server",
        "command": "python3",
        "args": ["test.py"],
        "isolation": "lazy_per_user",
        "per_user_args_template": ["--user-dir", "{user_workspace}"],
        "idle_timeout": 600,
        "max_instances": 20
    }

    config = MCPServerConfig.from_dict(data)

    assert config.name == "test_server"
    assert config.isolation == "lazy_per_user"
    assert config.per_user_args_template == ["--user-dir", "{user_workspace}"]
    assert config.idle_timeout == 600
    assert config.max_instances == 20


# ===== UserContext Tests =====

def test_user_context_mcp_manager_field():
    """Verify UserContext has optional mcp_manager field"""

    context = UserContext(
        user_key="feishu:ou_123",
        workspace=Path("/tmp/test"),
        config={},
        skills_dir=Path("/tmp/skills"),
        memory_file=Path("/tmp/memory.json"),
    )

    # Default should be None
    assert context.mcp_manager is None

    # Can set mcp_manager
    mock_manager = MagicMock()
    context.mcp_manager = mock_manager
    assert context.mcp_manager is mock_manager
