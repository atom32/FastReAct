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
from fastreact.core.config import Config, ExtensionConfig, MCPConfig, MCPServerConfig, PathsConfig, ReactConfig
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


def _agent_with_generic_mcp_tool(
    tmp_path: Path,
    client: MagicMock,
    *,
    budget: int = 200,
    parameters: dict | None = None,
) -> tuple[Agent, str]:
    workspace = tmp_path / "workspace"
    config = Config(
        paths=PathsConfig(
            global_skills_dir=tmp_path / "missing-skills",
            gateway_workspace=workspace,
        ),
        react=ReactConfig(
            mcp_tool_output_budget_chars=budget,
            mcp_tool_output_preview_chars=80,
            mcp_tool_output_retry_attempts=1,
            enable_filesystem_memory=False,
            enable_safety=False,
        ),
    )
    agent = Agent(config=config, multitenant=False)
    wrapper = MCPToolWrapper(
        tool_name="read",
        server_name="generic",
        mcp_client=client,
        mcp_manager=MagicMock(),
        description="Generic MCP read tool",
        parameters=parameters or {
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
        transport="http",
    )
    agent._tools.register(wrapper)
    return agent, wrapper.name


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
async def test_agent_mcp_status_reports_http_pska_config_without_secret(tmp_path):
    config = _config_with_http_mcp(tmp_path)
    agent = Agent(config=config)

    with patch.object(MCPToolManager, "add_server", new=AsyncMock()):
        await agent._load_mcp_servers()

    status = agent.list_mcp_server_status()[0]

    assert status["name"] == "pska"
    assert status["transport"] == "http"
    assert status["isolation"] == "shared"
    assert status["auth_configured"] is True
    assert "mcp_api_keys.pska" not in str(status)
    assert status["last_error"] is None


@pytest.mark.asyncio
async def test_agent_mcp_status_keeps_last_load_error(tmp_path):
    config = _config_with_http_mcp(tmp_path)
    agent = Agent(config=config)

    with patch.object(MCPToolManager, "add_server", new=AsyncMock(side_effect=RuntimeError("boom"))):
        await agent._load_mcp_servers()

    status = agent.list_mcp_server_status()[0]

    assert status["name"] == "pska"
    assert status["alive"] is False
    assert status["loaded"] is False
    assert status["last_error"] == "boom"


@pytest.mark.asyncio
async def test_agent_mcp_reload_preserves_http_pska_config(tmp_path):
    config = _config_with_http_mcp(tmp_path)
    config.extensions = ExtensionConfig(
        runtime_reload_enabled=True,
        mcp_reload_enabled=True,
    )
    agent = Agent(config=config)

    with patch.object(MCPToolManager, "add_server", new=AsyncMock()) as add_server:
        result = await agent.reload_mcp_servers()

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
    assert result["reloaded"] is True


@pytest.mark.asyncio
async def test_agent_mcp_close_unregisters_mcp_wrappers_only(tmp_path):
    config = _config_with_http_mcp(tmp_path)
    agent = Agent(config=config)
    client = MagicMock()
    client.close = AsyncMock()
    wrapper = MCPToolWrapper(
        tool_name="search",
        server_name="pska",
        mcp_client=client,
        mcp_manager=MagicMock(),
        description="PSKA search",
        parameters={},
        transport="http",
    )
    agent._tools.register(wrapper)

    assert "read_file" in agent.list_tools()
    assert "pska_search" in agent.list_tools()

    await agent.close_mcp_servers()

    assert "read_file" in agent.list_tools()
    assert "pska_search" not in agent.list_tools()


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
    user_workspace = workspace / "tenants" / "web" / "users" / "web_alice"
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


@pytest.mark.asyncio
async def test_mcp_tool_passes_tenant_and_user_to_http_client(tmp_path):
    client = MagicMock()
    client.call_tool = AsyncMock(return_value="ok")
    wrapper = MCPToolWrapper(
        tool_name="search",
        server_name="pska",
        mcp_client=client,
        mcp_manager=MagicMock(),
        description="PSKA search",
        parameters={},
        transport="http",
    )
    workspace = tmp_path / "alice"
    user = UserContext(
        user_key="sso:alice",
        tenant_key="acme",
        workspace=workspace,
        config={},
        skills_dir=workspace / "skills",
        memory_file=workspace / "memory.json",
    )

    result = await wrapper.execute(user_context=user, query="Atlas")

    assert result == "ok"
    client.call_tool.assert_awaited_once_with(
        "search",
        {"query": "Atlas"},
        user_key="sso:alice",
        tenant_key="acme",
    )


@pytest.mark.asyncio
async def test_mcp_tool_output_governance_degrades_long_unbroken_text(tmp_path):
    raw_output = "A" * 800
    client = MagicMock()
    client.call_tool = AsyncMock(return_value=raw_output)
    agent, tool_name = _agent_with_generic_mcp_tool(tmp_path, client, budget=120)

    execution, event = await agent.tool_executor.execute(
        tool_name=tool_name,
        tool_params={"query": "large"},
        session_id="mcp-long-unbroken",
    )

    payload = json.loads(event.content)
    assert payload["error_code"] == "tool_output_too_large"
    assert payload["issue_code"] == "tool_result_over_budget"
    assert payload["tool_name"] == tool_name
    assert payload["estimated_size"] == len(raw_output)
    assert payload["configured_budget"] == 120
    assert "A" * 40 not in event.content
    assert execution.context_result == event.content
    assert event.metadata["tool_output_too_large"] is True
    assert event.metadata["tool_result_over_budget"] is True
    assert event.metadata["tool_output_governance"]["full_content_in_context"] is False

    artifacts = agent.store.read("artifacts", limit=0)
    assert artifacts[-1]["artifact_id"] == payload["artifact"]["artifact_id"]
    assert artifacts[-1]["content"] == raw_output
    assert artifacts[-1]["content_length"] == len(raw_output)


@pytest.mark.asyncio
async def test_mcp_tool_output_governance_degrades_long_text_with_separators(tmp_path):
    raw_output = "\n".join(f"section-{idx}" for idx in range(120))
    client = MagicMock()
    client.call_tool = AsyncMock(return_value=raw_output)
    agent, tool_name = _agent_with_generic_mcp_tool(tmp_path, client, budget=160)

    execution, event = await agent.tool_executor.execute(
        tool_name=tool_name,
        tool_params={"query": "large"},
        session_id="mcp-long-separated",
    )

    payload = json.loads(event.content)
    assert payload["error_code"] == "tool_output_too_large"
    assert payload["issue_code"] == "tool_result_over_budget"
    assert payload["preview"]["text_segments_estimate"] > 1
    assert "section-0" not in event.content
    assert execution.context_result == event.content
    assert agent.store.read("artifacts", limit=0)[-1]["content"] == raw_output


@pytest.mark.asyncio
async def test_mcp_tool_output_governance_hides_raw_separator_chunk_error(tmp_path):
    client = MagicMock()
    client.call_tool = AsyncMock(
        side_effect=ValueError("Separator is found, but chunk is longer than limit")
    )
    agent, tool_name = _agent_with_generic_mcp_tool(tmp_path, client, budget=160)

    execution, event = await agent.tool_executor.execute(
        tool_name=tool_name,
        tool_params={"query": "large"},
        session_id="mcp-chunk-error",
    )

    payload = json.loads(event.content)
    assert payload["error_code"] == "tool_output_too_large"
    assert payload["issue_code"] == "upstream_chunk_limit"
    assert payload["estimated_size_available"] is False
    assert payload["artifact"]["available"] is False
    assert "Separator is found" not in event.content
    assert "chunk is longer than limit" not in event.content
    assert execution.error is None
    assert event.metadata["tool_output_too_large"] is True


@pytest.mark.asyncio
async def test_mcp_tool_output_governance_retries_with_smaller_max_params(tmp_path):
    async def call_tool(name, params, **identity):
        if params["max_chars"] > 100:
            return "X" * 800
        return "compact result"

    client = MagicMock()
    client.call_tool = AsyncMock(side_effect=call_tool)
    agent, tool_name = _agent_with_generic_mcp_tool(
        tmp_path,
        client,
        budget=200,
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_chars": {"type": "integer"},
            },
        },
    )

    execution, event = await agent.tool_executor.execute(
        tool_name=tool_name,
        tool_params={"query": "large", "max_chars": 1000},
        session_id="mcp-retry",
    )

    assert execution.result == "compact result"
    assert execution.context_result == "compact result"
    assert event.content == "compact result"
    assert client.call_tool.await_count == 2
    second_call = client.call_tool.await_args_list[1]
    assert second_call.args[1]["max_chars"] == 100
    governance = event.metadata["tool_output_governance"]
    assert governance["retried"] is True
    assert governance["retry_attempts"] == 1
    assert governance["recovered"] is True
    assert governance["previous_issue"]["issue_code"] == "tool_result_over_budget"
    assert agent.store.read("artifacts", limit=0)[-1]["content"] == "X" * 800


@pytest.mark.asyncio
async def test_mcp_tool_issue_persists_artifact_preview_context_and_trace_semantics(tmp_path):
    raw_output = "B" * 700
    client = MagicMock()
    client.call_tool = AsyncMock(return_value=raw_output)
    agent, tool_name = _agent_with_generic_mcp_tool(tmp_path, client, budget=100)

    execution, event = await agent.tool_executor.execute(
        tool_name=tool_name,
        tool_params={"query": "large"},
        session_id="mcp-run-event",
    )
    agent.runs.create(
        run_id="run-mcp-governance",
        session_id="mcp-run-event",
        query="read generically",
    )
    saved_event = agent.runs.append_event("run-mcp-governance", event.to_dict())
    trace = agent.runs.persist_trace("run-mcp-governance")

    payload = json.loads(saved_event["content"])
    artifact_id = payload["artifact"]["artifact_id"]
    assert saved_event["content"] == execution.context_result
    assert saved_event["metadata"]["tool_output_governance"]["artifact_id"] == artifact_id
    assert saved_event["metadata"]["tool_output_governance"]["context_compressed"] is True
    assert saved_event["metadata"]["tool_output_governance"]["full_content_in_context"] is False
    assert "B" * 40 not in saved_event["content"]
    assert agent.store.read("artifacts", limit=0)[-1]["content"] == raw_output
    assert trace["status"] == "queued"
    assert trace["tool_issue_count"] == 1
    assert trace["tool_issues"][0]["artifact_id"] == artifact_id
    assert trace["error"] is None


def test_http_client_uses_path_url_as_mcp_endpoint():
    client = StreamableHTTPMCPClient("http://127.0.0.1:8765/mcp")

    assert client._message_url() == "http://127.0.0.1:8765/mcp"


def test_http_client_keeps_legacy_message_endpoint_for_root_url():
    client = StreamableHTTPMCPClient("http://127.0.0.1:8765")

    assert client._message_url() == "http://127.0.0.1:8765/message"


@pytest.mark.asyncio
async def test_http_client_includes_tenant_and_user_in_tool_call_params():
    client = StreamableHTTPMCPClient("http://127.0.0.1:8765/mcp")
    client._send_request = AsyncMock(return_value={"result": {"content": [{"type": "text", "text": "ok"}]}})

    result = await client.call_tool("search", {"query": "Atlas"}, user_key="sso:alice", tenant_key="acme")

    assert result == "ok"
    request = client._send_request.await_args.args[0]
    assert request["params"]["user_key"] == "sso:alice"
    assert request["params"]["tenant_key"] == "acme"
