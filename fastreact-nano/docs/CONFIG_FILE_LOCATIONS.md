# FastReAct Configuration File Locations

Version: `2.4.2`

FastReAct uses one JSON config for the daemon, MCP servers, service auth, paths, policy, and optional PSKA integration.

## Recommended Local Config

```text
/Users/xudawei/FastReAct/.fastreact/config.json
```

Create it from the PSKA-ready example:

```bash
cd /Users/xudawei/FastReAct
mkdir -p .fastreact
cp fastreact-nano/config.pska.example.json .fastreact/config.json
```

## `./start.sh` Resolution Order

The repository root `./start.sh` resolves config in this order:

1. Explicit path: `./start.sh /path/to/config.json`
2. `/Users/xudawei/FastReAct/.fastreact/config.json`
3. `~/.fastreact/config.json`
4. `/Users/xudawei/FastReAct/fastreact-nano/.fastreact/config.json`
5. `/Users/xudawei/FastReAct/fastreact-nano/config.json`

`./start.sh` also reads:

- `service.*` for daemon host, port, log level, auth, CORS, run and approval settings.
- `web.*` for the optional service console.
- `logs.*` for daemon and web log paths.
- `pska.*` for optional PSKA config generation.

## Backend `Config.load()` Resolution Order

When running the backend directly:

```bash
python3 -m fastreact.adapters.http --config /path/to/config.json
```

If `--config` is omitted, backend config lookup is relative to the backend process working directory:

1. `~/.fastreact/config.json`
2. `./.fastreact/config.json`
3. `./config.json`

For predictable deployments, pass `--config` explicitly or run through the repository root `./start.sh`.

## Minimal Config

```json
{
  "llm": {
    "model": "deepseek-v4-flash",
    "api_base": "https://api.deepseek.com",
    "api_key": "replace-with-real-key"
  },
  "service": {
    "host": "127.0.0.1",
    "port": 8000,
    "log_level": "info",
    "service_token": "replace-with-local-service-token",
    "cors_origins": [
      "http://127.0.0.1:3000",
      "http://localhost:3000"
    ]
  },
  "paths": {
    "workspaces_root": "~/FastReAct_workspaces",
    "gateway_workspace": "~/FastReAct_workspaces/single/default"
  },
  "mcp": {
    "servers": []
  }
}
```

## Secrets

Do not commit real tokens or API keys.

Supported patterns:

- Put `llm.api_key` in a local untracked config.
- Use `llm.api_key_file` to point at a local file.
- Use `~/.fastreact/credentials.json` for MCP auth references such as `mcp_api_keys.pska`.
- Keep repository examples as placeholders only.

`~/api_key.txt` is still supported for smoke tests and credential bootstrap. It may be JSON or legacy line-based text, but production-like runs should use explicit JSON config.

## PSKA Config

Use `fastreact-nano/config.pska.example.json` when PSKA integration is needed.

Important fields:

- `pska.enabled`: whether this config is for PSKA integration.
- `pska.refresh_config`: whether `./start.sh` should call the PSKA config generator.
- `pska.archive`: local PSKA archive path when config generation is enabled.
- `pska.config_file`: generated config output path.
- `mcp.servers`: PSKA MCP HTTP endpoint or other MCP servers.
- `policy.tenant_rules.pska.tools`: explicit PSKA tenant tool policy.

When `pska.refresh_config=false`, FastReAct uses the local config directly.

## MCP Server Config

Stdio MCP:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "timeserver",
        "transport": "stdio",
        "command": "uvx",
        "args": ["--from", "mcp_servers/builtin/timeserver", "mcp-timeserver"],
        "isolation": "shared"
      }
    ]
  }
}
```

HTTP MCP:

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

## Runtime Text Files

Workspace memory/history files are runtime state, not maintained documentation. Do not include `MagicMock`, `.pytest_cache`, generated logs, or `workspaces/*/{HISTORY,MEMORY,SOUL,AGENTS}.md` in documentation inventories.
