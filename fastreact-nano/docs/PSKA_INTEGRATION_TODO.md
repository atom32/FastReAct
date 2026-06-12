# PSKA Integration TODO

FastReAct is intended to serve as a reusable headless agentic service layer. PSKA and other systems should call FastReAct through stable service APIs instead of importing FastReAct internals.

## Current Contract

- Stable HTTP/SSE endpoint: `POST /v1/chat/completions`.
- Public event schema: `fastreact.agent_event.v1`.
- Contractual event fields: `type`, `content`, `tool_name`, `tool_args`, `tool_call_id`, `session_id`, `run_id`, `event_id`, `timestamp`, `metadata`.
- Contractual event types: `session_start`, `think`, `tool_call`, `tool_result`, `session_end`, `error`, `ask_user`.
- Non-streaming summarized response with `run_id`, `session_id`, `events`, `tool_calls`, `duration_ms`, `content`.
- Service auth for `/ready` and `/v1/chat/completions` through `FASTREACT_SERVICE_TOKEN` or `service.service_token` in config.
- Readiness endpoint: `GET /ready`, including model config state, MCP readiness, MCP server status, and loaded MCP tool names.
- Config-based service wrapping: `python3 -m fastreact.adapters.http --config <path>` or default `~/.fastreact/config.json`.
- MCP stdio server env can be declared per server in `mcp.servers[].env`.
- Headless approval round trip: `ask_user` events include `approval_request_id`, and clients can call `GET /v1/approvals`, `GET /v1/approvals/{id}`, `POST /v1/approvals/{id}/approve`, or `POST /v1/approvals/{id}/deny`.

## Validation

PSKA repo E2E command that starts real FastReAct HTTP/SSE and a real PSKA MCP JSON-RPC subprocess:

```bash
cd core
python3 scripts/fastreact_http_sse_e2e.py --python ../.pska/venvs/pska-py312/bin/python
```

## Remaining Work

- Provide packaged deployment examples for binding PSKA MCP servers without importing PSKA internals.
- Decide whether request/session-scoped MCP binding is needed.
- Persist and replay completed run traces through a public service API.
- Add production examples for service token rotation and tenant isolation.
- Add CI wiring for PSKA/FastReAct cross-repo E2E.
- Add PSKA-side approval UI or policy client that consumes `ask_user` and resolves `/v1/approvals/*`.

## Ownership Boundary

PSKA owns knowledge storage, ACL, review, jobs, citations, and MCP tools.

FastReAct owns agent planning, model calls, tool orchestration, session/runtime control, and event streaming.

FastReAct must not directly access the PSKA DB or make PSKA knowledge ACL decisions.
