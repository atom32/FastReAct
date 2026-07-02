# Skills And MCP Tools

Version: `2.4.2`

Skills and MCP tools solve different problems:

- Skills describe how the agent should approach a class of work.
- MCP tools expose typed capabilities the agent can call.

FastReAct combines both inside a single headless service loop, with policy and approvals between planning and execution.

## Skills

A skill is a structured prompt, workflow pattern, and tool-use guide. It can include:

- task framing
- decision rules
- recommended tools
- recommended MCP servers
- extra files used as context

Built-in skills live in:

```text
fastreact-nano/skills/builtin/
```

Custom/user skills live under configured workspace skill paths. FastReAct resolves skills through multiple search roots in this precedence order:

```text
explicit Agent(skills_dir=...)
configured paths.user_skills_dir
configured paths.global_skills_dir
legacy ./skills fallback, only when no configured roots exist
```

In multi-tenant runs, the current user's workspace `skills/` directory is temporarily placed ahead of global skills for that request. This lets a user override a global skill without changing the global registry.

List skills:

```bash
curl http://127.0.0.1:18741/v1/skills
```

Diagnostics:

```bash
curl http://127.0.0.1:18741/v1/skills/diagnostics \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN"
```

Diagnostics include each skill's active `source_path`, duplicate/overridden sources, recommended tools, and missing MCP server/tool dependencies.

Runtime reload is available through an authenticated admin endpoint only when explicitly enabled:

```json
{
  "extensions": {
    "runtime_reload_enabled": true,
    "mcp_reload_enabled": false
  }
}
```

```bash
curl -X POST http://127.0.0.1:18741/v1/extensions/reload \
  -H "Content-Type: application/json" \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN" \
  -d '{"skills": true, "mcp": false}'
```

Skill reload rescans configured skill roots without touching MCP or active sessions. MCP reload is separately gated by `mcp_reload_enabled` because it can reconnect stateful integrations such as PSKA.

## MCP Tools

MCP tools are deterministic external capabilities exposed by MCP servers. FastReAct supports both:

- `stdio`: local child process MCP servers
- `http`: remote or separately managed MCP endpoints

MCP config lives in the main JSON config:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "pska",
        "transport": "http",
        "url": "http://127.0.0.1:8765/mcp",
        "auth_token_ref": "mcp_api_keys.pska",
        "isolation": "shared"
      }
    ]
  }
}
```

List available tools:

```bash
curl http://127.0.0.1:18741/v1/tools
```

The tools response includes compact tool summaries and MCP server status so operators can inspect loaded tools, transport mode, isolation mode, and recent load errors without exposing secrets.

## Execution Flow

```text
Request
  -> FastReAct service
  -> agent context and optional skill selection
  -> available native and MCP tools
  -> policy check
  -> optional approval
  -> tool execution
  -> event stream, trace, and audit records
```

Skills do not bypass policy. MCP tools do not make FastReAct planning decisions. PSKA knowledge ACL remains in PSKA and its MCP tools.

## Directory Structure

```text
fastreact-nano/
├── skills/
│   ├── builtin/
│   └── custom/
├── mcp_servers/
│   └── builtin/
├── docs/
└── workspaces/
```

Workspace memory/history files are runtime state and should not be treated as maintained documentation.

## Choosing The Right Extension Point

Use a skill when the agent needs a repeatable reasoning/workflow pattern.

Use an MCP tool when the agent needs a typed external capability, especially one that reads or changes external state.

Use a native tool when the capability belongs to the FastReAct runtime itself and should be available without an external MCP server.

## Maintenance Rules

- Keep skill instructions concise and task-specific.
- Keep MCP schemas explicit and typed.
- Put dangerous side effects behind `require_approval` or `deny`.
- Prefer HTTP MCP for PSKA and other separately deployed systems.
- Prefer stdio MCP for bundled local tools.
- Update [DOCS_INDEX.md](DOCS_INDEX.md) when adding a user-facing skill or MCP guide.
