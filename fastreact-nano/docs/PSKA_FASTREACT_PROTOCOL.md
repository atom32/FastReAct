# PSKA / FastReAct Layer Protocol

Status: draft v1  
Schema version: `fastreact.agent_event.v1`

FastReAct is the headless agentic service layer. PSKA is the knowledge system.
They communicate only through stable service and tool protocols.

FastReAct must not import PSKA internals. PSKA should not import FastReAct
internals except for local fallback or smoke tests.

## Ownership Boundary

PSKA owns:

- knowledge storage
- ACL and visibility checks
- review workflow
- ingestion and extraction jobs
- citations, source identifiers, and knowledge traces
- PSKA MCP tools

FastReAct owns:

- agent planning loop
- model calls
- tool orchestration
- session and run lifecycle
- event streaming
- runtime traces and tool audit

## What Crosses The Boundary

Only protocol data crosses the boundary:

- invocation request: user/system messages, stream mode, session id, user key, run metadata
- identity context: `user_key`, optional PSKA `user_id`, caller, purpose, tenant/system keys
- agent events: lifecycle, thinking, tool call, tool result, final answer, error, approval request
- tool calls: MCP tool name and JSON arguments
- tool results: JSON/text result, citation ids, trace summaries, errors
- response summary: final answer, events, tool calls, duration, run id, session id
- health/readiness: model config status, MCP readiness, loaded tools, dependency status

The boundary must not carry:

- raw API keys or PATs
- PSKA database handles
- FastReAct Python objects
- unversioned internal event objects
- ACL decisions made by FastReAct on PSKA knowledge

## FastReAct Invocation

Endpoint:

```http
POST /v1/chat/completions
```

Request:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "Use PSKA MCP tools and cite evidence."
    },
    {
      "role": "user",
      "content": "Question"
    }
  ],
  "stream": true,
  "session_id": "optional-session-id",
  "user_key": "pska:user_primary",
  "skills": ["optional-skill-name"],
  "metadata": {
    "caller": "pska",
    "run_id": "optional-report-run-id",
    "purpose": "qa|report|review|memory|job",
    "pska_user_id": "user_primary"
  }
}
```

Rules:

- `messages` must include a non-empty user message.
- `stream=true` returns Server-Sent Events.
- `stream=false` returns one summarized JSON response.
- `metadata.run_id` is optional; FastReAct generates one when absent.
- `user_key` identifies the caller/user context for FastReAct session and workspace isolation.
- PSKA-specific identity should be duplicated in `metadata.pska_user_id` when PSKA tools need it.

## Streaming Event

SSE frame:

```text
event: tool_call
data: {"schema":"fastreact.agent_event.v1","type":"tool_call"}
```

Payload:

```json
{
  "schema": "fastreact.agent_event.v1",
  "type": "session_start|think|tool_call|tool_result|session_end|error|ask_user",
  "event_id": "run-id:0",
  "parent_event_id": null,
  "run_id": "run-id",
  "session_id": "session-id",
  "timestamp": "2026-06-11T00:00:00+00:00",
  "content": "human-readable event content",
  "tool_name": "pska_pska_search",
  "tool_args": {
    "query": "Question",
    "user_id": "user_primary",
    "top_k": 5
  },
  "tool_call_id": "call-id",
  "duration_ms": null,
  "cited_source_ids": ["source-id-1"],
  "metadata": {}
}
```

The stream ends with:

```text
event: done
data: [DONE]
```

Consumer rules:

- Consumers must ignore unknown fields.
- Consumers must tolerate new `type` values.
- Consumers should use `schema` to select parser behavior.
- Consumers must not parse FastReAct internal Python objects.
- Tool result payloads may be text or JSON encoded by the MCP tool.

## Non-Streaming Response

When `stream=false`, FastReAct returns:

```json
{
  "type": "chat.completion",
  "run_id": "run-id",
  "session_id": "session-id",
  "content": "final answer",
  "events": [],
  "tool_calls": [
    {
      "event_id": "run-id:1",
      "tool_call_id": "call-id",
      "tool_name": "pska_pska_search",
      "tool_args": {}
    }
  ],
  "duration_ms": 1234.56,
  "metadata": {
    "schema": "fastreact.agent_event.v1",
    "event_count": 4
  }
}
```

Errors use the same shape with `type="error"` and an `error` field.

## Headless Approval Round Trip

Dangerous tools must not rely on an interactive terminal in headless mode. When a
tool requires human or caller approval, FastReAct emits an `ask_user` event and
keeps a pending approval request in the service runtime.

Approval request event:

```json
{
  "schema": "fastreact.agent_event.v1",
  "type": "ask_user",
  "event_id": "run-id:3",
  "run_id": "run-id",
  "session_id": "session-id",
  "timestamp": "2026-06-12T00:00:00+00:00",
  "content": "Dangerous command requires confirmation",
  "approval_request_id": "approval-123",
  "tool_name": "exec",
  "tool_args": {
    "command": "rm test.txt"
  },
  "metadata": {
    "request_id": "approval-123",
    "decision_level": "danger"
  }
}
```

Clients should use `approval_request_id` as the canonical ID. `metadata.request_id`
is retained for backward compatibility.

Approval APIs:

```http
GET /v1/approvals
GET /v1/approvals/{approval_request_id}
POST /v1/approvals/{approval_request_id}/approve
POST /v1/approvals/{approval_request_id}/deny
```

Approve or deny body:

```json
{
  "reason": "operator approved in PSKA review UI"
}
```

All approval APIs use the same service token as `/ready` and
`/v1/chat/completions` when service auth is enabled.

Client rules:

- Treat unknown approval statuses as non-approved.
- Do not auto-approve shell, write, edit, or external side-effect tools unless the caller has an explicit policy for that tool and user.
- If the client cannot safely present or decide an approval request, call `deny` or let it expire.
- PSKA remains responsible for knowledge ACL; FastReAct approval only governs tool execution inside the agent runtime.

## Tool Policy Contract

FastReAct service policy controls whether a tool call is allowed, logged with
caution, routed through approval, or denied. It does not replace PSKA knowledge
ACLs; PSKA still owns source visibility and knowledge-level decisions.

Policy config shape:

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

Rule priority is:

```text
user_rules -> tenant_rules -> tool_rules -> default_action -> built-in safety heuristics
```

Tenant is inferred from the prefix before `:` in `user_key`, such as `pska` in
`pska:user_primary`, unless a future transport provides an explicit tenant key.

Inspection APIs:

```http
GET /v1/policy
POST /v1/policy/check
```

Dry-run request:

```json
{
  "tool_name": "exec",
  "tool_args": {"command": "ls"},
  "user_key": "pska:user_primary",
  "tenant_key": "pska"
}
```

Dry-run response:

```json
{
  "tool_name": "exec",
  "user_key": "pska:user_primary",
  "tenant_key": "pska",
  "level": "danger",
  "reason": "Policy tool:exec requires approval",
  "pattern_matched": null,
  "policy_scope": "tool:exec",
  "policy_action": "require_approval",
  "policy_matched": true,
  "requires_confirmation": true,
  "should_allow": true
}
```

Policy decisions also copy `policy_scope`, `policy_action`, and
`policy_matched` into approval records, service event metadata, and audit JSONL
records. Built-in forbidden exec patterns still override configured policy
unless the runtime is explicitly started with `allow_all`.

## Background Run Contract

`POST /v1/chat/completions` remains the direct request/response endpoint. For
longer work, clients can create a background run and poll its status and events.

Create run:

```http
POST /v1/runs
```

The request body is the same shape as `/v1/chat/completions`.

```json
{
  "messages": [
    {"role": "user", "content": "Generate the report."}
  ],
  "session_id": "optional-session-id",
  "user_key": "pska:user_primary",
  "metadata": {
    "run_id": "optional-run-id",
    "caller": "pska",
    "purpose": "report"
  }
}
```

Run status APIs:

```http
GET /v1/runs
GET /v1/runs/{run_id}
GET /v1/runs/{run_id}/events
POST /v1/runs/{run_id}/cancel
GET /v1/traces
GET /v1/traces/{run_id}
GET /v1/traces/{run_id}/events
```

Run status values:

```text
queued
running
completed
failed
cancelled
```

The current implementation uses an in-process run registry and writes background
run trace summaries plus service event payloads to the JSONL store. It
establishes the HTTP contract and a replayable event shape, but it is not yet a
durable job queue. Release-quality daemon work still needs retry/backoff, crash
recovery, leases, pagination, retention, and migration rules.

Formalization requirements for this first version:

- Define event replay ordering and pagination.
- Define retention, compaction, and redaction behavior for traces.
- Add retry/backoff and lease semantics before introducing external workers.
- Preserve this HTTP contract when the storage/worker implementation changes.

## PSKA Tool Binding

FastReAct loads PSKA through deployment configuration, usually MCP:

```json
{
  "name": "pska",
  "command": "/path/to/personal archive/scripts/pska",
  "args": ["mcp-server"],
  "isolation": "shared",
  "description": "PSKA personal knowledge store tools."
}
```

Expected PSKA tools:

- `pska_search`
- `pska_agentic_search`
- `pska_index_status`
- `pska_ingest_channel_payload`
- `pska_extract_all`
- `pska_review_items`

FastReAct may expose these with server-name prefixes such as
`pska_pska_search`.

## Identity And ACL

FastReAct forwards identity; PSKA enforces knowledge access.

FastReAct may pass:

- `user_key`
- `metadata.pska_user_id`
- tool argument `user_id`
- tool argument `owner_user_id`

PSKA decides:

- whether the user can read a source/chunk/entity
- whether the user can ingest or extract
- whether a review item can be approved, rejected, or applied
- which citation/source ids can be returned

## Health, Readiness, And Service Auth

`GET /health` is a public lightweight liveness check. It should expose the
service contract version and whether the agent object can be created.

`GET /ready` is the deployment readiness contract. When
`FASTREACT_SERVICE_TOKEN` is configured, callers must pass either:

```http
Authorization: Bearer <token>
X-FastReAct-Service-Token: <token>
```

`/ready` actively ensures MCP loading and returns:

- `agent_ready`
- `service_contract=fastreact.agent_event.v1`
- `auth.required`
- `model.name`, `model.api_base_configured`, `model.api_key_configured`
- `mcp.ready`
- `mcp.servers[].name/alive`
- `mcp.tools`, including PSKA tools such as `pska_pska_search`

`POST /v1/chat/completions` uses the same service token when auth is enabled.
The service token is separate from admin/control-plane keys.

PSKA should use readiness only for deployment and diagnostics, not for knowledge
access decisions.

## Versioning

- The current event schema is `fastreact.agent_event.v1`.
- Additive fields are allowed without a major version bump.
- Removing or renaming fields requires a new schema version.
- PSKA consumers should pin expected schema versions in tests.

## Test Contract

The minimum interop test should:

1. Start PSKA MCP server.
2. Configure FastReAct with the PSKA MCP server.
3. Call authenticated `GET /ready`.
4. Call authenticated `POST /v1/chat/completions`.
5. Assert event sequence includes `session_start`, `tool_call`, `tool_result`, `session_end`, and SSE `done`.
6. Assert the final response includes `run_id`, `session_id`, and citation/source evidence when PSKA tools return it.

PSKA repo command:

```bash
cd core
python3 scripts/fastreact_http_sse_e2e.py --python ../.pska/venvs/pska-py312/bin/python
```
