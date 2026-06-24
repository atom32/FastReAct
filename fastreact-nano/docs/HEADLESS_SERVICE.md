# FastReAct Headless Service Manual

FastReAct Nano `2.4.2` runs as a headless HTTP/SSE agentic service. The optional Next.js service console is a client of this service, not a runtime dependency.

## Start

Full local service from the repository root:

```bash
cd /Users/xudawei/FastReAct
./start.sh
```

Daemon-only:

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 -m fastreact.adapters.http --config /Users/xudawei/FastReAct/.fastreact/config.json
```

Default daemon URL:

```text
http://127.0.0.1:8000
```

## Authentication

If `service.service_token` is configured, protected endpoints require one of:

```http
X-FastReAct-Service-Token: replace-with-local-service-token
Authorization: Bearer replace-with-local-service-token
```

`GET /health` is public. Operational endpoints such as `/ready`, `/v1/setup`, `/v1/metrics`, runs, traces, tasks, approvals, policy, and workspace profile require service auth when a token is configured.

## Endpoint Map

Public:

```http
GET /
GET /health
GET /v1/tools
GET /v1/skills
```

Protected when service auth is enabled:

```http
GET /ready
GET /v1/metrics
GET /v1/setup
GET /v1/setup/presets
POST /v1/setup/config-draft
POST /v1/chat/completions
POST /v1/runs
GET /v1/runs
GET /v1/runs/{run_id}
GET /v1/runs/{run_id}/events
POST /v1/runs/{run_id}/cancel
GET /v1/traces
GET /v1/traces/{run_id}
GET /v1/traces/{run_id}/events
GET /v1/tasks
POST /v1/tasks
GET /v1/tasks/{task_id}
PATCH /v1/tasks/{task_id}
GET /v1/skills/diagnostics
GET /v1/workspace/profile
PUT /v1/workspace/profile
GET /v1/policy
POST /v1/policy/check
GET /v1/approvals
GET /v1/approvals/{request_id}
POST /v1/approvals/{request_id}/approve
POST /v1/approvals/{request_id}/deny
```

Legacy compatibility:

```http
POST /run
```

## Chat Completions

Non-streaming:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN" \
  -d '{
    "messages": [
      {"role": "user", "content": "Say hello from FastReAct."}
    ],
    "stream": false
  }'
```

Streaming:

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN" \
  -d '{
    "messages": [
      {"role": "user", "content": "List your available tools."}
    ],
    "stream": true,
    "user_key": "local:user",
    "metadata": {
      "caller": "local",
      "purpose": "smoke"
    }
  }'
```

Streaming payloads use:

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

The stream ends with:

```text
event: done
data: [DONE]
```

## Durable Runs And Traces

Create a background run:

```bash
curl http://127.0.0.1:8000/v1/runs \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN" \
  -d '{
    "messages": [
      {"role": "user", "content": "Summarize the available skills."}
    ],
    "model": "deepseek-v4-flash",
    "temperature": 0.3,
    "top_p": 0.9,
    "max_tokens": 2048,
    "metadata": {"purpose": "background"}
  }'
```

Inspect:

```bash
curl http://127.0.0.1:8000/v1/runs \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN"

curl http://127.0.0.1:8000/v1/traces \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN"
```

Runs expose status and events while the daemon is active. Traces provide summary/replay records through the store when available. For final answers, `session_end.content` and `trace.final_content` are the durable full text; `content_preview` and `final_content_preview` are UI/diagnostic previews and may be truncated.

## Headless Tool Approvals

When a tool requires approval, FastReAct emits an `ask_user` event and stores an approval request. Headless clients should resolve the request through HTTP rather than relying on a terminal prompt.

```bash
curl http://127.0.0.1:8000/v1/approvals \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN"

curl -X POST http://127.0.0.1:8000/v1/approvals/approval-123/approve \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN" \
  -d '{"reason":"operator approved"}'

curl -X POST http://127.0.0.1:8000/v1/approvals/approval-123/deny \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN" \
  -d '{"reason":"unsafe command"}'
```

Default approval timeout is 300 seconds and can be configured with `service.approval_timeout_seconds`.

## Policy

Policy actions:

```text
allow
caution
require_approval
deny
```

Example:

```json
{
  "policy": {
    "default_action": "caution",
    "tool_rules": {
      "exec": "require_approval",
      "write_file": "deny"
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

Inspect:

```bash
curl http://127.0.0.1:8000/v1/policy \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN"
```

Dry-run:

```bash
curl http://127.0.0.1:8000/v1/policy/check \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN" \
  -d '{"tool_name":"exec","tool_args":{"cmd":"pwd"},"user_key":"local:user"}'
```

## MCP And Skills

FastReAct supports stdio and HTTP MCP servers through `mcp.servers`. Skills are loaded from configured skill directories and can recommend tools or MCP servers, but tool execution still flows through policy and approval.

Readiness and diagnostics:

```bash
curl http://127.0.0.1:8000/ready \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN"

curl http://127.0.0.1:8000/v1/skills/diagnostics \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN"
```

See [MCP_CALLING_MECHANISM.md](MCP_CALLING_MECHANISM.md) and [SKILLS_AND_MCP.md](SKILLS_AND_MCP.md).

## PSKA

PSKA integration uses HTTP/SSE plus PSKA MCP tools. FastReAct must not import PSKA internals or access the PSKA database. See [PSKA_FASTREACT_PROTOCOL.md](PSKA_FASTREACT_PROTOCOL.md).
