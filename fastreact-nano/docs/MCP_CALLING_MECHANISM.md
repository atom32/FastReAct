# FastReAct Nano MCP Calling Mechanism

Version: `2.4.2`

FastReAct supports MCP servers through both `stdio` and `http` transports. MCP tools are execution capabilities; FastReAct remains responsible for planning, policy, approval, audit, and event streaming.

## Transport Modes

### Stdio MCP

FastReAct starts the MCP server as a child process and communicates over JSON-RPC through stdin/stdout.

```json
{
  "mcp": {
    "servers": [
      {
        "name": "timeserver",
        "transport": "stdio",
        "command": "uvx",
        "args": ["--from", "mcp_servers/builtin/timeserver", "mcp-timeserver"],
        "isolation": "shared",
        "description": "Current time and date information"
      }
    ]
  }
}
```

Use stdio for local tools, bundled servers, and process-level isolation.

### HTTP MCP

FastReAct connects to a remote or separately managed MCP endpoint.

```json
{
  "mcp": {
    "servers": [
      {
        "name": "pska",
        "transport": "http",
        "url": "http://127.0.0.1:8765/mcp",
        "auth_token_ref": "mcp_api_keys.pska",
        "isolation": "shared",
        "description": "PSKA HTTP MCP endpoint"
      }
    ]
  }
}
```

Use HTTP for PSKA integration or separately deployed MCP services. `auth_token_ref` points to a value in local credentials, not to a token committed in the repository.

## Runtime Flow

```text
User request
  -> FastReAct HTTP service
  -> Agent planning loop
  -> Skill context and available tool list
  -> Tool policy check
  -> Approval request if required
  -> MCP manager/client
  -> MCP server tool call
  -> Tool result
  -> Agent event stream and trace/audit records
```

MCP servers do not make ACL decisions for FastReAct. For PSKA knowledge, ACL decisions remain in PSKA and its MCP tools.

## Tool Naming

MCP tools are surfaced in FastReAct's tool list alongside native tools. Use:

```bash
curl http://127.0.0.1:18741/v1/tools
```

The tools response includes `mcp_servers` and `tool_summaries` for diagnostics. MCP server status reports transport, isolation, loaded tool count, liveness, and recent load errors; auth token references are reported only as configured/not configured, never as secret values.

Readiness includes configured server status and loaded tool status:

```bash
curl http://127.0.0.1:18741/ready \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN"
```

Runtime MCP reload is deliberately disabled by default. To allow an authenticated reload, both flags must be set:

```json
{
  "extensions": {
    "runtime_reload_enabled": true,
    "mcp_reload_enabled": true
  }
}
```

This keeps PSKA and other stateful MCP integrations on the existing startup-time loading path unless an operator explicitly opts into reconnecting them.

## Isolation Modes

Supported config values:

- `shared`: one server instance or endpoint for all callers.
- `per_user`: per-user server instance when supported.
- `lazy_per_user`: per-user server instance with idle cleanup when supported.

The exact behavior depends on the MCP manager and server transport. Do not treat `shared` as safe for user-private state.

## Tool Output Governance

MCP tool results pass through a generic output governance boundary before they
are appended to the agent's next LLM context. This is not a domain-specific
adapter and does not increase model token limits.

- Oversized MCP results are converted to a structured `tool_output_too_large`
  issue with `issue_code=tool_result_over_budget`.
- Upstream parser failures such as separator/chunk limit errors are converted
  to `tool_output_too_large` with `issue_code=upstream_chunk_limit`; raw parser
  messages are not exposed to the LLM context.
- The structured issue includes `tool_name`, estimated size when available,
  configured budget, artifact handle, and retry hints. It does not include raw
  tool content.
- Full oversized content is stored in the runtime `artifacts` stream; the LLM
  context receives only the compact issue envelope.
- The runtime may retry once by shrinking numeric `max_*` arguments when the
  tool schema or original call makes that possible.
- A single MCP read issue remains a tool issue in events/traces, not an
  automatic run failure.

Relevant configuration:

```json
{
  "react": {
    "mcp_tool_output_budget_chars": 20000,
    "mcp_tool_output_preview_chars": 1200,
    "mcp_tool_output_retry_attempts": 1
  }
}
```

## Policy And Approval

Every MCP tool should be governed by the same policy model as native tools:

```json
{
  "policy": {
    "tool_rules": {
      "exec": "require_approval",
      "filesystem_write": "require_approval"
    },
    "tenant_rules": {
      "pska": {
        "tools": {
          "pska_*": "allow",
          "exec": "deny"
        }
      }
    }
  }
}
```

Use `/v1/policy/check` to inspect a tool decision before calling it through an agent run.

## Built-In MCP Servers

Bundled examples live under `mcp_servers/builtin/`:

- `timeserver`
- `filesystem`
- `fetch`
- `graphrag`
- `http_test_server`

See [../mcp_servers/README.md](../mcp_servers/README.md) for server development notes.

## Troubleshooting

- Check `/ready` for MCP server and tool status.
- Check `/v1/skills/diagnostics` for skill-recommended tools or servers that are missing.
- For stdio servers, verify `command`, `args`, working directory, and environment.
- For HTTP servers, verify URL, auth token reference, network reachability, and server protocol compatibility.
- Keep tool stderr/log output out of stdout for stdio servers; stdout is reserved for JSON-RPC.
