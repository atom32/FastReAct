"""
Contract tests for HTTP MCP transport wiring.

These tests lock the PSKA-facing contract: when a server is configured with
transport="http" and url=..., the agent and multi-tenant loaders must pass
those fields through to MCPToolManager instead of falling back to stdio.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import json

import pytest

from fastreact.agent import Agent
from fastreact.core.multitenant import UserContext
from fastreact.core.config import Config, MCPConfig, MCPServerConfig, PathsConfig
from fastreact.core.tools import ToolRegistry
from fastreact.mcp.http_client import StreamableHTTPMCPClient
from fastreact.mcp.manager import MCPToolManager, MCPToolWrapper
from fastreact.mcp.multitenant_manager import MultiTenantMCPManager


def _config_with_http_mcp(tmp_path: Path) -> Config:
    return Config(
        mcp=MCPConfig(
            servers=[
                MCPServerConfig(
                    name="pska",
                    transport="http",
                    url="http://127.0.0.1:8765/mcp",
                    auth_token_ref="mcp_api_keys.pska",
                    description="PSKA HTTP MCP endpoint.",
                )
            ]
        ),
        paths=PathsConfig(
            global_skills_dir=tmp_path / "missing-skills",
            gateway_workspace=tmp_path / "workspace",
        ),
    )


@pytest.mark.asyncio
async def test_agent_loader_passes_http_mcp_config(tmp_path):
    config = _config_with_http_mcp(tmp_path)
    agent = Agent(config=config)

    with patch.object(MCPToolManager, "add_server", new=AsyncMock()) as add_server:
        await agent._load_mcp_servers()

    add_server.assert_awaited_once_with(
        name="pska",
        transport="http",
        server_command="",
        server_args=[],
        env=None,
        url="http://127.0.0.1:8765/mcp",
        auth_token_ref="mcp_api_keys.pska",
        allowed_user_key=None,
    )


@pytest.mark.asyncio
async def test_multitenant_shared_loader_passes_http_mcp_config():
    registry = ToolRegistry()
    manager = MultiTenantMCPManager(registry)
    server_config = MCPServerConfig(
        name="pska",
        transport="http",
        url="http://127.0.0.1:8765/mcp",
        auth_token_ref="mcp_api_keys.pska",
        isolation="shared",
    )

    with patch.object(MCPToolManager, "add_server", new=AsyncMock()) as add_server:
        await manager.preload_shared_servers([server_config])

    add_server.assert_awaited_once_with(
        name="pska",
        transport="http",
        server_command="",
        server_args=[],
        env=None,
        url="http://127.0.0.1:8765/mcp",
        auth_token_ref="mcp_api_keys.pska",
        allowed_user_key=None,
    )


@pytest.mark.asyncio
async def test_multitenant_agent_loads_user_workspace_http_mcp_config(tmp_path):
    workspace = tmp_path / "tenants"
    user_workspace = workspace / "web_alice"
    user_workspace.mkdir(parents=True)
    (user_workspace / "config.json").write_text(
        json.dumps(
            {
                "user_key": "web:alice",
                "channel": "web",
                "user_id": "alice",
                "mcp": {
                    "servers": [
                        {
                            "name": "pska",
                            "transport": "http",
                            "url": "http://127.0.0.1:8765/mcp",
                            "auth_token_ref": "mcp_api_keys.pska",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    config = Config(
        paths=PathsConfig(
            global_skills_dir=tmp_path / "missing-skills",
            gateway_workspace=workspace,
        )
    )
    agent = Agent(config=config, multitenant=True, base_workspace=workspace)

    with patch.object(MCPToolManager, "add_server", new=AsyncMock()) as add_server:
        await agent.mcp_bootstrapper.ensure_loaded(user_key="web:alice")

    add_server.assert_awaited_once_with(
        name="user_web_alice_pska",
        transport="http",
        server_command="",
        server_args=[],
        env=None,
        url="http://127.0.0.1:8765/mcp",
        auth_token_ref="mcp_api_keys.pska",
        allowed_user_key="web:alice",
    )


@pytest.mark.asyncio
async def test_user_scoped_mcp_tool_rejects_other_users(tmp_path):
    client = MagicMock()
    client.call_tool = AsyncMock(return_value="secret result")
    wrapper = MCPToolWrapper(
        tool_name="search",
        server_name="user_web_alice_pska",
        mcp_client=client,
        mcp_manager=MagicMock(),
        description="User scoped PSKA search",
        parameters={},
        transport="http",
        allowed_user_key="web:alice",
    )

    other_user = UserContext(
        user_key="web:bob",
        workspace=tmp_path / "bob",
        config={},
        skills_dir=tmp_path / "bob" / "skills",
        memory_file=tmp_path / "bob" / "memory.json",
    )

    result = await wrapper.execute(user_context=other_user, query="private")

    assert "scoped to user 'web:alice'" in result
    client.call_tool.assert_not_awaited()


def test_http_client_uses_path_url_as_mcp_endpoint():
    client = StreamableHTTPMCPClient("http://127.0.0.1:8765/mcp")

    assert client._message_url() == "http://127.0.0.1:8765/mcp"


def test_http_client_keeps_legacy_message_endpoint_for_root_url():
    client = StreamableHTTPMCPClient("http://127.0.0.1:8765")

    assert client._message_url() == "http://127.0.0.1:8765/message"
