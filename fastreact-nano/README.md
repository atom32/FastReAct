# FastReAct Nano

FastReAct Nano is the current FastReAct implementation. Version `2.4.2` runs primarily as a headless HTTP/SSE agentic service: one agent daemon, explicit tool policy, MCP integration, approval round trips, durable runs, trace replay, task metadata, and an optional local service console.

## Quick Start

From the repository root:

```bash
cd /Users/xudawei/FastReAct
mkdir -p .fastreact
cp fastreact-nano/config.pska.example.json .fastreact/config.json
# Edit .fastreact/config.json and set llm.api_key or llm.api_key_file.
./start.sh
```

Default URLs:

```text
Service console: http://127.0.0.1:3000/service
HTTP daemon:     http://127.0.0.1:18741
```

Daemon-only:

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 -m pip install -e ".[all]"
python3 -m fastreact.adapters.http --config /Users/xudawei/FastReAct/.fastreact/config.json
```

## Primary API

```http
POST /v1/chat/completions
```

Minimal request:

```bash
curl http://127.0.0.1:18741/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $AUTHNODE_FASTREACT_JWT" \
  -d '{
    "messages": [
      {"role": "user", "content": "Say hello from FastReAct."}
    ],
    "stream": false
  }'
```

Streaming uses Server-Sent Events and the schema:

```text
fastreact.agent_event.v1
```

Common event types:

```text
session_start
think
tool_call
tool_result
session_end
error
ask_user
```

## Endpoint Map

- `GET /health`: public process health.
- `GET /ready`: authenticated readiness including agent, MCP server, and MCP tool status.
- `GET /v1/setup`, `GET /v1/setup/presets`, `POST /v1/setup/config-draft`: setup status and config draft helpers.
- `GET /v1/metrics`: runtime metrics.
- `POST /v1/chat/completions`: OpenAI-style agent invocation, streaming or non-streaming.
- `POST /v1/runs`, `GET /v1/runs`, `GET /v1/runs/{run_id}`, `GET /v1/runs/{run_id}/events`, `POST /v1/runs/{run_id}/cancel`: durable background runs.
- `GET /v1/traces`, `GET /v1/traces/{run_id}`, `GET /v1/traces/{run_id}/events`: trace summary and replay.
- `GET /v1/tasks`, `POST /v1/tasks`, `GET /v1/tasks/{task_id}`, `PATCH /v1/tasks/{task_id}`: durable task metadata.
- `GET /v1/approvals`, `GET /v1/approvals/{request_id}`, `POST /v1/approvals/{request_id}/approve`, `POST /v1/approvals/{request_id}/deny`: headless tool approvals.
- `GET /v1/policy`, `POST /v1/policy/check`: policy inspection and dry-run checks.
- `GET /v1/tools`: native and MCP tool list.
- `GET /v1/skills`, `GET /v1/skills/diagnostics`: skill list and diagnostics.
- `GET /v1/workspace/profile`, `PUT /v1/workspace/profile`: workspace profile files.

Details: [docs/HEADLESS_SERVICE.md](docs/HEADLESS_SERVICE.md).

## Configuration

Recommended local config:

```text
/Users/xudawei/FastReAct/.fastreact/config.json
```

Long-running daemon config:

```text
~/.fastreact/config.json
```

Minimal config:

```json
{
  "llm": {
    "model": "deepseek-v4-flash",
    "api_base": "https://api.deepseek.com",
    "api_key": "replace-with-real-key"
  },
  "service": {
    "host": "127.0.0.1",
    "port": 18741,
    "log_level": "info"
  },
  "auth": {
    "mode": "jwt",
    "jwt_secret_env": "AUTHNODE_JWT_SECRET",
    "jwt_issuer": "authnode.local",
    "jwt_audience": "fastreact"
  },
  "mcp": {
    "servers": []
  }
}
```

`~/api_key.txt` remains supported for local smoke tests and bootstrap. Production-like service runs should use JSON config and keep secrets outside the repository.

## PSKA Integration

FastReAct is PSKA's agentic service layer, not a PSKA internal module.

PSKA owns knowledge storage, ACL, review/jobs, citations, and PSKA MCP tools. FastReAct owns agent planning, model calls, tool orchestration, session/runtime control, event streaming, approvals, runs, traces, and the PSKA digest worker.

See [docs/PSKA_FASTREACT_PROTOCOL.md](docs/PSKA_FASTREACT_PROTOCOL.md).

## Current Boundaries

FastReAct Nano is intentionally a single-agent daemon. It is not yet a multi-agent collaboration platform. Request/session-scoped MCP binding, multi-worker leasing semantics, trace redaction policy, policy hot reload, and full cross-repo PSKA CI are still productization areas.

The optional web console is a product shell over the service. The backend service contract remains the source of truth.

## Documentation

Start at [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md). Current docs live in `docs/`; historical implementation reports live in `docs_archive/`.
