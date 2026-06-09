"""
Integration tests for MCP tool structure

Tests that MCP tools are properly structured without requiring server execution.
"""

import pytest
from pathlib import Path

from fastreact import Agent, Config, MCPToolManager
from fastreact.core.tools import ToolRegistry
from fastreact.mcp.manager import MCPToolWrapper


class TestMCPStructure:
    """Test MCP tool structure and integration"""

    def test_mcp_config_exists(self):
        """MCPConfig should be available"""
        from fastreact import MCPConfig

        config = MCPConfig()

        assert config.servers == []

        # Can create from dict - returns MCPServerConfig objects
        config2 = MCPConfig.from_dict({
            "servers": [
                {"name": "test", "command": "echo", "args": []}
            ]
        })

        assert len(config2.servers) == 1
        # MCPServerConfig is a dataclass, access attributes instead of dict keys
        assert config2.servers[0].name == "test"
        assert config2.servers[0].command == "echo"

    def test_mcp_wrapper_tool_structure(self):
        """MCPToolWrapper should have correct tool structure"""
        # Create mock client
        from fastreact.mcp.client import SimpleMCPClient
        client = SimpleMCPClient("echo", ["test"])

        # Create wrapper
        wrapper = MCPToolWrapper(
            tool_name="test_tool",
            server_name="test_server",
            mcp_client=client,
            description="Test tool",
            parameters={"type": "object"},
        )

        # Check properties
        assert wrapper.name == "test_server_test_tool"
        assert wrapper.description == "Test tool"
        assert wrapper.parameters == {"type": "object"}

    def test_mcp_manager_initialization(self):
        """MCPToolManager should initialize correctly"""
        registry = ToolRegistry()
        manager = MCPToolManager(registry)

        assert manager.list_servers() == []
        assert manager.list_mcp_tools() == []

    def test_agent_with_mcp_config(self):
        """Agent should accept MCP config"""
        config = Config()
        config.mcp.servers = [
            {
                "name": "test_server",
                "command": "python3",
                "args": ["-c", "print('test')"],
            }
        ]

        # Agent should create without error
        # (MCP servers are loaded lazily)
        agent = Agent(config=config)

        assert agent._config.mcp.servers == config.mcp.servers

    def test_feishu_config_exists(self):
        """FeishuConfig should be available"""
        from fastreact import FeishuConfig

        config = FeishuConfig()

        assert config.app_id == ""
        assert config.app_secret == ""
        assert config.enable_multitenant == True
        assert config.port == 8001

    def test_multitenant_config(self):
        """Agent should accept multi-tenant config"""
        from fastreact import Agent, MultiTenantManager
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as tmpdir:
            agent = Agent(
                multitenant=True,
                base_workspace=Path(tmpdir),
            )

            assert agent._multitenant_enabled == True
            assert agent._multitenant is not None
            assert isinstance(agent._multitenant, MultiTenantManager)

    def test_user_key_format_in_agent(self):
        """Agent should handle user_key parameter"""
        from fastreact import Agent
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as tmpdir:
            agent = Agent(multitenant=True, base_workspace=Path(tmpdir))

            # Get user context (this should work synchronously)
            user_key = "feishu:ou_test123"
            context = agent._multitenant.get_user_context(user_key)

            assert context.user_key == user_key
            assert context.workspace.exists()

    def test_graphrag_skill_exists(self):
        """GraphRAG skill file should exist"""
        skill_path = Path(__file__).parent.parent.parent / "skills" / "graphrag_workflow" / "SKILL.md"

        assert skill_path.exists()

        # Check content
        content = skill_path.read_text(encoding="utf-8")

        assert "graphrag" in content.lower()
        assert "search_graph" in content

    def test_graphrag_server_exists(self):
        """GraphRAG server file should exist"""
        server_path = Path(__file__).parent.parent.parent / "examples" / "graph_rag_server.py"

        assert server_path.exists()

        # Check it's valid Python
        content = server_path.read_text(encoding="utf-8")

        assert "GraphRAGMCPServer" in content
        assert "search_graph" in content

    def test_feishu_adapter_exists(self):
        """Feishu adapter should exist"""
        from fastreact.adapters.feishu import FeishuChannel

        assert FeishuChannel is not None

    def test_feishu_bot_example_exists(self):
        """Feishu GraphRAG bot example should exist"""
        bot_path = Path(__file__).parent.parent.parent / "examples" / "feishu_graphrag_bot.py"

        assert bot_path.exists()

        content = bot_path.read_text(encoding="utf-8")

        assert "FeishuChannel" in content
        assert "GraphRAG" in content

    def test_config_extensions(self):
        """Config should have MCP and Feishu extensions"""
        from fastreact import Config, MCPConfig, FeishuConfig

        # Default config should have MCP config
        config = Config()
        assert hasattr(config, "mcp")
        assert isinstance(config.mcp, MCPConfig)

        # Can create Feishu config
        feishu_config = FeishuConfig.from_env()
        assert feishu_config is not None

    def test_all_exports_available(self):
        """All new exports should be available from fastreact"""
        from fastreact import (
            MCPConfig,
            FeishuConfig,
            MultiTenantManager,
            UserContext,
            MCPToolManager,
            MCPToolWrapper,
        )

        assert MCPConfig is not None
        assert FeishuConfig is not None
        assert MultiTenantManager is not None
        assert UserContext is not None
        assert MCPToolManager is not None
        assert MCPToolWrapper is not None
