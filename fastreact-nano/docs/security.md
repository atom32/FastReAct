# Security Model

Phase 1 uses confirmation plus audit. It does not provide OS-level sandboxing.

## Secrets

Secrets must stay out of the repository and frontend bundle.

- LLM keys: backend environment or `~/api_key.txt` for release smoke tests.
- GitHub PAT: `~/Github_PAT.txt`, read only after release gates pass and a push is needed.
- Admin key: `GATEWAY_ADMIN_KEY`, or entered locally in the Admin Config tab.

The store sanitizes common sensitive keys such as `api_key`, `token`, `pat`, `password`, `secret`, and `authorization`.

## Admin API

Set:

```bash
FASTREACT_ADMIN_API_AUTH=true
GATEWAY_ADMIN_KEY=replace-me
```

Protected APIs require:

```text
X-Admin-Key: $GATEWAY_ADMIN_KEY
```

`/health` and `/api/status` remain public for health probes. Control-plane APIs such as sessions, tasks, audit, traces, config, tools, metrics, and dependency health are protected when admin auth is enabled.

## Tool Permissions

All native and MCP tools must flow through `ToolExecutionService`:

1. schema validation
2. permission decision
3. optional user approval
4. execution
5. output truncation
6. audit JSONL append

Safe read-only tools may be auto-approved. Risky tools such as writes, edits, and shell execution can emit `ASK_USER` and wait for approve/deny.

## Audit

Audit records include:

- tool name
- decision level and reason
- approval status
- duration
- sanitized parameter/result summaries
- session id

Audit data is designed for operational review, not for storing raw secrets or long sensitive content.

## Current Limits

- No OS-level sandbox.
- No database row-level access control.
- No remote worker isolation.
- No multi-agent worktree isolation.

Use OS/container permissions, least-privilege workspaces, and `FASTREACT_ADMIN_API_AUTH=true` for deployments beyond local development.
