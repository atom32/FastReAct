"""
Contract tests for HTTP MCP transport wiring.

These tests lock the PSKA-facing contract: when a server is configured with
transport="http" and url=..., the agent and multi-tenant loaders must pass
those fields through to MCPToolManager instead of falling back to stdio.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from fastreact.agent import Agent
from fastreact.core.config import Config, MCPConfig, MCPServerConfig, PathsConfig
from fastreact.core.tools import ToolRegistry
from fastreact.mcp.http_client import StreamableHTTPMCPClient
from fastreact.mcp.manager import MCPToolManager
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
    )


def test_http_client_uses_path_url_as_mcp_endpoint():
    client = StreamableHTTPMCPClient("http://127.0.0.1:8765/mcp")

    assert client._message_url() == "http://127.0.0.1:8765/mcp"


def test_http_client_keeps_legacy_message_endpoint_for_root_url():
    client = StreamableHTTPMCPClient("http://127.0.0.1:8765")

    assert client._message_url() == "http://127.0.0.1:8765/message"
