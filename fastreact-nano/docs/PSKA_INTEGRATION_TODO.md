# PSKA Integration TODO

FastReAct is intended as a reusable headless agentic service layer. PSKA and
other systems should call FastReAct through stable service APIs instead of
importing FastReAct internals.

## Priority Rule

Product polish is higher priority than another release cut.

Before treating FastReAct Nano as a 1.0-quality single-agent service layer, the
items in "Product Polish Before Release" should be handled ahead of release
packaging, version bumps, or new surface area.

## Long-Term Direction

The long-term target is a stable, high-concurrency agentic service daemon.
The current single-agent Nano version is a deliberate staging point, not the
final architecture.

The order matters:

1. Stabilize the single-agent headless protocol and product boundary.
2. Productize run, job, trace, approval, and policy contracts.
3. Make the daemon observable, resumable, and safe under concurrent clients.
4. Only then consider implementation-level optimization and partial rewrites.

Rust or other lower-level, higher-efficiency components should be introduced
only after the service contracts are stable. Good future candidates include
SSE/event fanout, durable run/job queues, trace indexing/replay, policy
evaluation hot paths, and MCP transport supervision. The Python agent runtime
can remain the reference implementation until those boundaries are clear.

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
- MCP HTTP servers can be declared with `mcp.servers[].transport="http"` and
  `mcp.servers[].url`. URLs with a path, such as `http://127.0.0.1:8765/mcp`,
  are treated as full MCP endpoints; root URLs keep the legacy `/message`
  default for local test servers.
- In multi-tenant mode, a user's workspace `config.json` may declare
  `mcp.servers`. FastReAct loads those servers on that user's run with a stable
  `user_<channel>_<user>_<server>` namespace and rejects execution by other
  `user_key` values.
- Headless approval round trip: `ask_user` events include
  `approval_request_id`, and clients can call `GET /v1/approvals`,
  `GET /v1/approvals/{id}`, `POST /v1/approvals/{id}/approve`, or
  `POST /v1/approvals/{id}/deny`. Approval records now include timeout fields;
  unresolved requests expire as denied by default.
- Background run contract: clients can call `POST /v1/runs`,
  `GET /v1/runs`, `GET /v1/runs/{id}`, `GET /v1/runs/{id}/events`, and
  `POST /v1/runs/{id}/cancel`. The first implementation is in-process and not
  yet a durable worker queue.
- Trace summary API: clients can call `GET /v1/traces`, `GET /v1/traces/{id}`,
  and `GET /v1/traces/{id}/events`. The current implementation persists run
  summaries and service event payloads, but still needs replay formalization.
- Tool policy config: `policy.tool_rules`, `policy.user_rules`, and
  `policy.tenant_rules` can map tools to `allow`, `caution`,
  `require_approval`, or `deny`. Formal config loading now validates policy
  shape and action names.
- Policy inspection and dry-run: clients can call `GET /v1/policy` and
  `POST /v1/policy/check` before executing a tool. Dry-run, approval records,
  service events, and audit entries include `policy_scope`, `policy_action`,
  and `policy_matched` when a configured policy rule made the decision.

## Validation

PSKA repo E2E command that starts real FastReAct HTTP/SSE and a real PSKA MCP
JSON-RPC subprocess:

```bash
cd core
python3 scripts/fastreact_http_sse_e2e.py --python ../.pska/venvs/pska-py312/bin/python
```

FastReAct-side wrapper:

```bash
cd fastreact-nano
python3 run_tests.py pska-e2e
```

## Product Polish Before Release

These items are more important than shipping another release. They determine
whether FastReAct Nano feels complete as a single-agent framework rather than
just feature-rich.

- Productize run/job contracts for durable background execution.
  Durable JSONL run snapshots, leases, stale-run recovery, cancellation, and
  replay events now exist for the single-process daemon. Remaining work is
  clearer retry/backoff policy, concurrency limits, and multi-worker leasing
  semantics before treating it as a high-concurrency daemon.

- Formalize the first run/trace implementation.
  The `/v1/runs/*` and `/v1/traces/*` contracts now read durable replay events
  ordered by ascending `sequence`, with pagination through `limit`,
  `after_sequence`, `next_after_sequence`, and `has_more`. Remaining work is
  retention policy, migration behavior, and deeper replay consistency checks
  across future multi-worker deployments.

- Make context compression verifiable and replayable.
  Compression now emits auditable metadata about preserved message indices,
  dropped count, truncation count, and estimated token counts. Remaining work is
  a true summary chain that cites what was compressed and why the later step has
  enough context.

- Productize run trace persistence and replay through a public service API.
  Public trace endpoints can fetch completed run summaries and replay ordered
  events without reading internal files. Remaining work is richer operator
  diagnosis around policy decisions, retention, and redaction previews.

- Finish approval policy at the product layer.
  The headless approval API, deny-by-timeout default, and approval metadata
  exist, and FastReAct now supports configurable timeout defaults plus
  operator-approved HTTP resolution. PSKA still needs a UI or policy client that
  consumes `ask_user`, applies caller/user/tool policy, and resolves
  `/v1/approvals/*`.

- Add per-tool, per-user, and per-tenant policy controls.
  The config, validation errors, dry-run contracts, and first policy audit
  fields exist. Productize them further with an update/reload workflow,
  versioned policy snapshots in traces, and PSKA-side policy client behavior
  for shell tools, write/edit tools, MCP tools, PSKA tools, and tenant/user
  contexts.

- Strengthen task/TODO as durable single-agent workflow state.
  TaskService is enough for multi-step planning, but release-quality behavior
  should define persistence, recovery, status transitions, cancellation, and how
  tasks relate to sessions and run traces.

- Improve service observability.
  Stable health/readiness, JSONL store stats, run metrics, latency, tool
  duration, approval duration, and error summaries are now exposed through
  `/v1/metrics` without requiring legacy WebSocket internals. Provider token usage is
  now captured from LLM responses when available and summarized in trace and
  metrics payloads. Remaining work is cost accounting and model/provider
  breakdowns.

- Keep the single-agent core small and explicit.
  Continue separating headless service/runtime from optional UI and integration
  presets so "Nano" remains an architecture
  boundary rather than an accidental bundle of every integration.

- Make PSKA/FastReAct cross-repo E2E a first-class gate.
  FastReAct now provides `python3 run_tests.py pska-e2e`, which delegates to
  PSKA's `core/scripts/fastreact_http_sse_e2e.py` when the PSKA checkout is
  available. Remaining work is CI wiring across both repositories.

## Remaining Integration Work

- Provide packaged deployment examples for binding PSKA MCP servers without
  importing PSKA internals.
- Decide whether request/session-scoped MCP binding is needed beyond the
  current global plus user-workspace config model.
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
