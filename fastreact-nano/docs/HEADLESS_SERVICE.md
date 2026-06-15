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
GET /v1/skills/diagnostics
```

Approval list:

```http
GET /v1/approvals
```

Metrics:

```http
GET /v1/metrics
```

Setup and workspace profile:

```http
GET /v1/setup
GET /v1/setup/presets
POST /v1/setup/config-draft
GET /v1/workspace/profile
PUT /v1/workspace/profile
```

Durable tasks:

```http
GET /v1/tasks
POST /v1/tasks
GET /v1/tasks/{task_id}
PATCH /v1/tasks/{task_id}
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
Approval requests include `timeout_seconds`, `expires_at`, `resolved_at`, and
`resolution_reason`. The default timeout is 300 seconds and can be changed with
`service.approval_timeout_seconds` or `FASTREACT_APPROVAL_TIMEOUT_SECONDS`.
Timeout marks the request `expired`, sets `approved=false`, and denies the tool
execution. In headless service mode, operator decisions should come through the
approval HTTP API rather than an interactive terminal prompt.

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

Background runs are backed by JSONL snapshots and append-only replay events.
The in-process worker task is only the current executor; run status, event
sequence, cancellation, trace summaries, and replay pagination are durable.
Daemon startup recovers queued runs and stale running leases when
`service.recover_queued_runs=true`.

Transient worker failures are retried by re-queueing the run until
`service.run_max_attempts` is reached. Retry delay uses exponential backoff
bounded by `service.run_retry_base_seconds` and
`service.run_retry_max_seconds`; queued runs are not scheduled before
`retry_after`. `service.run_concurrency` limits how many background runs one
daemon process starts at the same time. This is a single-process concurrency
limit, not a distributed multi-worker lease protocol.

Run snapshots may include additive daemon fields such as:

```text
attempts
lease_expires_at
retry_after
worker_id
last_error
```

Run and trace event APIs read durable replay events ordered by ascending
`sequence`; they do not depend on an in-memory run registry.

## Observability

Use `/v1/metrics` for headless service diagnostics:

```bash
curl http://127.0.0.1:8000/v1/metrics \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN"
```

The first metrics contract is `fastreact.metrics.v1`. It summarizes run status,
trace latency, event errors, tool audit duration, approval state, approval
resolution duration, durable run queue counts, stale leases, replay event count,
provider token usage when available, and JSONL store stats.

## Skill Diagnostics

Use `/v1/skills/diagnostics` to inspect loaded skills, declared dependencies,
recommended tools, MCP server requirements, and missing runtime dependencies:

```bash
curl http://127.0.0.1:8000/v1/skills/diagnostics \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN"
```

The endpoint is read-only and returns `fastreact.skill_diagnostics.v1`.

## Durable Tasks

The headless service exposes the same JSONL-backed task board that agents can
use through `task_create`, `task_update`, `task_list`, and `task_get`. This gives
the product shell and external clients a durable planning surface without adding
a database.

Create a task:

```bash
curl -X POST http://127.0.0.1:8000/v1/tasks \
  -H "Authorization: Bearer $FASTREACT_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Review PSKA citations",
    "description": "Check source ids and evidence fields",
    "priority": "high",
    "owner": "pska"
  }'
```

List and update tasks:

```bash
curl http://127.0.0.1:8000/v1/tasks?status=in_progress \
  -H "Authorization: Bearer $FASTREACT_SERVICE_TOKEN"

curl -X PATCH http://127.0.0.1:8000/v1/tasks/task-abc123 \
  -H "Authorization: Bearer $FASTREACT_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"completed"}'
```

Task detail includes related durable runs and traces when a run was launched with
`metadata.task_id` or reused the task session id.

## Product Shell

The optional Next.js console is the OpenClaw-like product shell for the daemon
API. It is not required for protocol-only PSKA integration, but it gives an
operator a practical UI for:

- Chat/Run creation through durable `/v1/runs`.
- Run and trace event replay from `/v1/runs/{run_id}/events`.
- Durable task board creation, status updates, and task-linked run launch.
- Skill diagnostics, MCP server status, missing tool dependencies.
- Workspace profile viewing and editing for `AGENTS.md` and `SOUL.md`.
- Approval queue handling and policy checks.
- Setup status for model, service token, MCP servers, and the PSKA preset.
- Draft-only configuration wizard for model, service token, workspace, MCP
  servers, and PSKA policy preset.

Start the HTTP service and the console separately:

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 -m fastreact.adapters.http

cd /Users/xudawei/FastReAct/fastreact-nano-web
NEXT_PUBLIC_FASTREACT_SERVICE_HTTP_URL=http://127.0.0.1:8000 npm run dev
```

Open:

```text
http://127.0.0.1:3000/service
```

If service auth is enabled, paste the service token in the console header. The
token is stored in browser local storage for local operator use.

The setup wizard intentionally generates a config draft only. It does not write
`~/.fastreact/config.json`, and it does not accept or emit raw LLM API keys. Use
`api_key_file` or environment variables for provider secrets.

## Workspace Profile

FastReAct can load optional workspace profile files into the variable system
prompt section. This is the low-risk OpenClaw-style customization path for a
single-agent daemon. The following files are detected from the gateway
workspace, tool working directory, and current working directory:

```text
AGENTS.md
SOUL.md
.fastreact/AGENT.md
.fastreact/SOUL.md
```

Files are truncated before prompt injection. The service console can edit the
top-level `AGENTS.md` and `SOUL.md`; nested `.fastreact/*` files are shown for
inspection. These files should define workspace conventions, personality/profile
guidance, or project-specific operating notes; they should not contain secrets.

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
    "service_token": "replace-with-local-service-token",
    "approval_timeout_seconds": 300,
    "run_lease_seconds": 300,
    "run_max_attempts": 3,
    "run_retry_base_seconds": 5,
    "run_retry_max_seconds": 300,
    "run_concurrency": 4,
    "recover_queued_runs": true
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

The repository also includes a complete preset:

```text
config.pska.example.json
```

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
        "transport": "http",
        "url": "http://127.0.0.1:8765/mcp",
        "auth_token_ref": "mcp_api_keys.pska",
        "isolation": "shared",
        "description": "PSKA HTTP MCP endpoint."
      }
    ]
  }
}
```

Credential file:

```json
{
  "mcp_api_keys": {
    "pska": "replace-with-pska-service-token"
  }
}
```

Environment-variable form:

```bash
export FASTRACT_MCP_SERVERS='[
  {
    "name": "pska",
    "transport": "http",
    "url": "http://127.0.0.1:8765/mcp",
    "auth_token_ref": "mcp_api_keys.pska",
    "isolation": "shared",
    "description": "PSKA HTTP MCP endpoint."
  }
]'
```

FastReAct may expose PSKA tools with a server prefix, such as:

```text
pska_pska_search
pska_pska_agentic_search
pska_pska_index_status
```

## PSKA Digest Worker

Run one digest job or the next ready `digest_via_fastreact` job:

```bash
python3 scripts/pska_digest_worker.py \
  --pska-url http://127.0.0.1:8765 \
  --fastreact-url http://127.0.0.1:8000 \
  --batch-limit 20
```

The worker leases the PSKA job, reads digest batches through PSKA HTTP API,
creates durable `/v1/runs` with the `pska_digest` skill, polls run status/events,
and marks the PSKA job complete or failed. It never reads the PSKA database
directly.

This worker intentionally lives in FastReAct, not PSKA. FastReAct owns LLM
execution, skills, tool policy, run lifecycle, and traces. PSKA owns durable
jobs, ACL, source refs, review, audit, and candidate persistence. Keeping the
worker here prevents PSKA from importing FastReAct internals while still letting
PSKA stay executor-agnostic through HTTP API/MCP contracts.

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
