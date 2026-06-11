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
