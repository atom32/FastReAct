# PSKA Integration TODO

FastReAct is intended as a reusable headless agentic service layer. PSKA and
other systems should call FastReAct through stable service APIs instead of
importing FastReAct internals.

## Priority Rule

Product polish is higher priority than another release cut.

Before treating FastReAct Nano as a 1.0-quality single-agent service layer, the
items in "Product Polish Before Release" should be handled ahead of release
packaging, version bumps, or new surface area.

## Current Contract

- Stable HTTP/SSE endpoint: `POST /v1/chat/completions`.
- Public event schema: `fastreact.agent_event.v1`.
- Contractual event fields: `type`, `content`, `tool_name`, `tool_args`,
  `tool_call_id`, `session_id`, `run_id`, `event_id`, `timestamp`, `metadata`.
- Contractual event types: `session_start`, `think`, `tool_call`,
  `tool_result`, `session_end`, `error`, `ask_user`.
- Non-streaming summarized response with `run_id`, `session_id`, `events`,
  `tool_calls`, `duration_ms`, `content`.
- Service auth for `/ready`, `/v1/chat/completions`, and `/v1/approvals/*`
  through `FASTREACT_SERVICE_TOKEN` or `service.service_token` in config.
- Readiness endpoint: `GET /ready`, including model config state, MCP readiness,
  MCP server status, and loaded MCP tool names.
- Config-based service wrapping: `python3 -m fastreact.adapters.http --config <path>`
  or default `~/.fastreact/config.json`.
- MCP stdio server env can be declared per server in `mcp.servers[].env`.
- Headless approval round trip: `ask_user` events include
  `approval_request_id`, and clients can call `GET /v1/approvals`,
  `GET /v1/approvals/{id}`, `POST /v1/approvals/{id}/approve`, or
  `POST /v1/approvals/{id}/deny`.

## Validation

PSKA repo E2E command that starts real FastReAct HTTP/SSE and a real PSKA MCP
JSON-RPC subprocess:

```bash
cd core
python3 scripts/fastreact_http_sse_e2e.py --python ../.pska/venvs/pska-py312/bin/python
```

## Product Polish Before Release

These items are more important than shipping another release. They determine
whether FastReAct Nano feels complete as a single-agent framework rather than
just feature-rich.

- Make context compression verifiable and replayable.
  Current context window and truncation support are useful, but compression
  should preserve a traceable summary chain, cite what was compressed, and make
  it possible to inspect why a later agent step still has enough context.

- Productize run trace persistence and replay through a public service API.
  Traces and audit data exist as infrastructure, but operators and PSKA clients
  need stable endpoints to fetch a completed run, inspect event order, replay
  tool decisions, and diagnose failures without reading internal files.

- Finish approval policy at the product layer.
  The headless approval API exists, but PSKA still needs a UI or policy client
  that consumes `ask_user`, applies caller/user/tool policy, and resolves
  `/v1/approvals/*`. FastReAct should document safe defaults for no-client,
  deny-by-default, timeout, and operator-approved modes.

- Add per-tool, per-user, and per-tenant policy controls.
  Current safety is mainly rule based. A production service layer needs explicit
  policy configuration for shell tools, write/edit tools, MCP tools, PSKA tools,
  and tenant/user contexts.

- Strengthen task/TODO as durable single-agent workflow state.
  TaskService is enough for multi-step planning, but release-quality behavior
  should define persistence, recovery, status transitions, cancellation, and how
  tasks relate to sessions and run traces.

- Improve service observability.
  Keep audit logs, but expose stable health/readiness, run metrics, latency,
  token/model usage where available, tool duration, approval duration, and error
  summaries without requiring Web/Gateway internals.

- Keep the single-agent core small and explicit.
  Continue separating headless service/runtime from optional adapters, Web,
  Feishu/Telegram/WeChat, and admin surfaces so "Nano" remains an architecture
  boundary rather than an accidental bundle of every integration.

- Make PSKA/FastReAct cross-repo E2E a first-class gate.
  The manual E2E exists, but the shared service contract should be protected by
  a repeatable gate whenever both repositories are available.

## Remaining Integration Work

- Provide packaged deployment examples for binding PSKA MCP servers without
  importing PSKA internals.
- Decide whether request/session-scoped MCP binding is needed.
- Add production examples for service token rotation and tenant isolation.
- Add CI wiring for PSKA/FastReAct cross-repo E2E.
- Add PSKA-side approval UI or policy client that consumes `ask_user` and
  resolves `/v1/approvals/*`.

## Ownership Boundary

PSKA owns knowledge storage, ACL, review, jobs, citations, and MCP tools.

FastReAct owns agent planning, model calls, tool orchestration, session/runtime
control, and event streaming.

FastReAct must not directly access the PSKA DB or make PSKA knowledge ACL
decisions.
