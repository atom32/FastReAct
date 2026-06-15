# Architecture

FastReAct Nano is currently a single-agent workbench, not a multi-agent platform.

## Stable Public Surface

- `Agent.run_event_stream(...)`
- `Agent.run_or_inject(...)`
- `AgentEvent` fields and event types
- WebSocket `query`, `control interrupt`, `list_skills`, `approve_tool`, `deny_tool`, `resume_session`

Internal APIs may change as long as those surfaces remain compatible.

## Runtime Boundaries

- `Agent`: facade for configuration, provider setup, tool registration, and compatibility helpers.
- `AgentRuntime`: owns the ReAct loop, context assembly, LLM steps, tool loop, interrupt handling, final answer extraction, and timing spans.
- `SessionService`: creates, lists, resumes, closes, and replays sessions.
- `ToolExecutionService`: validates tool calls, applies permission rules, emits approval requests, executes native/MCP tools, truncates output, and writes audit records.
- `SkillResolver`: loads skills, selects relevant skills, and injects skill prompt context.
- `MCPBootstrapper`: lazy-loads MCP servers and refreshes tool registrations when needed.
- `RunService`: stores durable background run snapshots, leases, replay events, recovery state, and trace summaries.
- `TaskService`: stores lightweight durable tasks and injects task context.
- `StoreService`: append-only JSONL storage for sessions, runs, events, tasks, audit, approvals, runtime spans, and traces.
- `HTTP adapter`: transport boundary for HTTP/SSE. It delegates business state to services.

## Control Plane

Admin APIs read from runtime services and JSONL records:

- sessions and event replay
- tasks
- audit and approvals
- traces and timing spans
- tool/MCP schema summaries
- metrics and dependency health

`FASTREACT_ADMIN_API_AUTH=true` protects control-plane APIs with `X-Admin-Key`.

## Persistence

The JSONL store is intentionally simple:

```text
$FASTRACT_GATEWAY_WORKSPACE/.fastreact/
  sessions.jsonl
  runs.jsonl
  events.jsonl
  run_events.jsonl
  tasks.jsonl
  approvals.jsonl
  audit.jsonl
  runtime_spans.jsonl
  traces.jsonl
```

This keeps Phase 1 deployable without database migrations. Long-running
deployments should schedule `scripts/store_maintenance.py backup` and periodic
`compact`. Use `compact --dry-run --retain-days <days>` before enabling
append-only retention in production; snapshot streams keep the latest record per
id, while append-only streams are pruned by record timestamp.

## Performance Position

The project stays Python-first. Optimization order:

1. timing spans and baseline data
2. caching skills, schemas, prompts, and MCP state
3. async concurrency and connection reuse
4. profiling with `cProfile` or `py-spy`
5. Rust/PyO3 only for proven CPU hotspots with Python fallback

Network and LLM latency are expected to dominate most workloads, so a broad Rust rewrite is not part of this phase.
