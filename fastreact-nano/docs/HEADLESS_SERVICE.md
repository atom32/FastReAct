# FastReAct Headless Service Manual

FastReAct Nano can run as a headless agentic service for PSKA and other systems.
The service contract is HTTP plus SSE. Web UI is optional and is not required for
normal PSKA integration.

## Start

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 -m fastreact.adapters.http
```

Default URL:

```text
http://127.0.0.1:8000
```

Primary endpoint:

```http
POST /v1/chat/completions
```

Health endpoint:

```http
GET /health
```

Tool list:

```http
GET /v1/tools
```

Skill list:

```http
GET /v1/skills
```

Approval list:

```http
GET /v1/approvals
```

Background runs:

```http
POST /v1/runs
GET /v1/runs
GET /v1/runs/{run_id}
GET /v1/runs/{run_id}/events
POST /v1/runs/{run_id}/cancel
GET /v1/traces
GET /v1/traces/{run_id}
GET /v1/traces/{run_id}/events
```

## Service Authentication

If `FASTREACT_SERVICE_TOKEN` or `service.service_token` is configured, clients
must include a service token header. Without the header, FastReAct returns:

```json
{"detail":"FastReAct service token required"}
```

Clients can authenticate with either header:

```http
X-FastReAct-Service-Token: replace-with-local-service-token
```

or:

```http
Authorization: Bearer replace-with-local-service-token
```

Shell helper:

```bash
export FASTREACT_SERVICE_TOKEN='replace-with-local-service-token'
```

## Minimal Requests

Non-streaming without service auth:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "messages": [
      {"role": "user", "content": "Say hello from FastReAct."}
    ],
    "stream": false
  }'
```

Non-streaming with service auth:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN" \
  -d '{
    "messages": [
      {"role": "user", "content": "Say hello from FastReAct."}
    ],
    "stream": false
  }'
```

Streaming with service auth:

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN" \
  -d '{
    "messages": [
      {"role": "system", "content": "Use PSKA MCP tools and cite evidence."},
      {"role": "user", "content": "What does PSKA know about Project Atlas?"}
    ],
    "stream": true,
    "user_key": "pska:user_primary",
    "metadata": {
      "caller": "pska",
      "purpose": "qa",
      "pska_user_id": "user_primary"
    }
  }'
```

## Event Contract

Streaming responses use Server-Sent Events. Event payloads use:

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

Each event includes stable protocol fields such as `run_id`, `session_id`,
`event_id`, `parent_event_id`, `tool_call_id`, `tool_name`, `tool_args`,
`approval_request_id`, `cited_source_ids`, and `metadata`.

The stream ends with:

```text
event: done
data: [DONE]
```

See [PSKA_FASTREACT_PROTOCOL.md](PSKA_FASTREACT_PROTOCOL.md) for the full
interop protocol.

## Headless Tool Approvals

When a tool is dangerous, FastReAct emits an `ask_user` event and stores a
pending approval request. Headless clients can resolve it through HTTP.

List pending and historical approval requests:

```bash
curl http://127.0.0.1:8000/v1/approvals \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN"
```

Inspect one approval request:

```bash
curl http://127.0.0.1:8000/v1/approvals/approval-123 \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN"
```

Approve:

```bash
curl -X POST http://127.0.0.1:8000/v1/approvals/approval-123/approve \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN" \
  -d '{"reason":"operator approved"}'
```

Deny:

```bash
curl -X POST http://127.0.0.1:8000/v1/approvals/approval-123/deny \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN" \
  -d '{"reason":"unsafe command"}'
```

If a headless client cannot safely decide, it should deny the request or let it
expire. Production deployments should avoid exposing broad shell/file tools to
untrusted callers.

## Service Policy Configuration

Use `policy` in `~/.fastreact/config.json` to define explicit tool execution
policy. Rules are checked before the default safety heuristics.

```json
{
  "policy": {
    "tool_rules": {
      "exec": "require_approval",
      "write_file": "deny"
    },
    "tenant_rules": {
      "pska": {
        "tools": {
          "pska_search": "allow",
          "exec": "deny"
        }
      }
    },
    "user_rules": {
      "pska:operator": {
        "tools": {
          "exec": "require_approval"
        }
      }
    }
  }
}
```

Supported actions:

```text
allow
caution
require_approval
deny
```

Rule priority is `user_rules`, then `tenant_rules`, then `tool_rules`, then
`default_action`. Tenant defaults to the prefix before `:` in `user_key`, such
as `pska` in `pska:user_primary`. Formal config files validate policy actions
and accept only `allow`, `caution`, `require_approval`, and `deny`.

Inspect active policy:

```bash
curl http://127.0.0.1:8000/v1/policy \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN"
```

Dry-run a tool decision without executing the tool:

```bash
curl http://127.0.0.1:8000/v1/policy/check \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN" \
  -d '{
    "tool_name": "exec",
    "tool_args": {"command": "ls"},
    "user_key": "pska:user_primary"
  }'
```

The dry-run response includes `policy_matched`, `policy_scope`, and
`policy_action` when a configured policy rule made the decision. The same fields
are written to approval records and audit JSONL entries.

## Background Runs

Use background runs for long-lived daemon-style work where the caller should not
hold one request open.

Create a run:

```bash
curl http://127.0.0.1:8000/v1/runs \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN" \
  -d '{
    "messages": [
      {"role": "user", "content": "Generate the PSKA report."}
    ],
    "metadata": {
      "run_id": "optional-run-id",
      "caller": "pska",
      "purpose": "report"
    }
  }'
```

Inspect status:

```bash
curl http://127.0.0.1:8000/v1/runs/optional-run-id \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN"
```

Fetch collected events:

```bash
curl 'http://127.0.0.1:8000/v1/runs/optional-run-id/events?limit=200&after_sequence=0' \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN"
```

Run and trace event APIs return events ordered by ascending `sequence`. Use
`limit` and `after_sequence` for replay pagination. Responses include `count`,
`total_event_count`, `next_after_sequence`, and `has_more`.

Fetch trace summary:

```bash
curl http://127.0.0.1:8000/v1/traces/optional-run-id \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN"
```

Cancel:

```bash
curl -X POST http://127.0.0.1:8000/v1/runs/optional-run-id/cancel \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN"
```

The current implementation uses an in-process run registry and writes trace
summaries plus service event payloads to the JSONL store. It establishes the API
contract, event ordering, and first replay pagination shape. Retry/backoff,
crash recovery, leases, durable replay from storage, retention, redaction, and
migration rules are still product-polish items before daemon 1.0.

## Formal Runtime Configuration

Use a formal runtime config for normal service deployments:

1. `~/.fastreact/config.json`
2. `./.fastreact/config.json`
3. `./config.json`
4. `FASTRACT_*` environment variables

Recommended user-level config:

```json
{
  "llm": {
    "model": "deepseek-v4-flash",
    "api_base": "https://api.deepseek.com",
    "api_key": "replace-with-real-key",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "service": {
    "host": "127.0.0.1",
    "port": 8000,
    "log_level": "info",
    "service_token": "replace-with-local-service-token"
  },
  "react": {
    "max_iterations": 20,
    "max_context_tokens": 128000,
    "sliding_window_size": 15,
    "max_tool_output_chars": 5000,
    "enable_safety": true,
    "auto_approve_safe": true
  },
  "mcp": {
    "servers": []
  }
}
```

Equivalent minimal environment variables:

```bash
export FASTRACT_MODEL='deepseek-v4-flash'
export FASTRACT_API_BASE='https://api.deepseek.com'
export FASTRACT_API_KEY='replace-with-real-key'
export FASTREACT_SERVICE_TOKEN='replace-with-local-service-token'
```

## PSKA MCP Configuration

Configure PSKA as a deployment-scoped MCP server.

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
    "service_token": "replace-with-local-service-token"
  },
  "mcp": {
    "servers": [
      {
        "name": "pska",
        "command": "/Users/xudawei/Documents/personal archive/scripts/pska",
        "args": ["mcp-server"],
        "isolation": "shared",
        "description": "PSKA personal knowledge store tools."
      }
    ]
  }
}
```

Environment-variable form:

```bash
export FASTRACT_MCP_SERVERS='[
  {
    "name": "pska",
    "command": "/Users/xudawei/Documents/personal archive/scripts/pska",
    "args": ["mcp-server"],
    "isolation": "shared",
    "description": "PSKA personal knowledge store tools."
  }
]'
```

FastReAct may expose PSKA tools with a server prefix, such as:

```text
pska_pska_search
pska_pska_agentic_search
pska_pska_index_status
```

## Local Smoke Credentials

`~/api_key.txt` is used by release smoke tests and local credential bootstrap.
It is not the recommended primary service configuration file for a long-running
deployment.

Supported JSON format:

```json
{
  "api_key": "replace-with-real-key",
  "model": "deepseek-v4-flash",
  "base_url": "https://api.deepseek.com",
  "service_token": "optional-local-service-token"
}
```

Supported legacy line format:

```text
replace-with-real-key
deepseek-v4-flash
https://api.deepseek.com
```

Run the real LLM smoke gate:

```bash
python3 run_tests.py release-llm
```

## Readiness Checklist

Before using FastReAct as a service:

```bash
python3 -m py_compile src/fastreact/adapters/http.py
python3 -m pytest tests/contracts/test_http_service_contract.py -q
python3 run_tests.py quick
python3 run_tests.py release-llm
```

For a fuller backend check:

```bash
python3 run_tests.py all
```
