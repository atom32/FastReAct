# Security Model

FastReAct Nano security is policy plus service authentication plus audit. It is not an OS sandbox.

## Service Authentication

Set `service.service_token` in JSON config:

```json
{
  "service": {
    "service_token": "replace-with-local-service-token"
  }
}
```

Clients authenticate with either:

```http
X-FastReAct-Service-Token: replace-with-local-service-token
Authorization: Bearer replace-with-local-service-token
```

`GET /health`, `GET /v1/tools`, and `GET /v1/skills` are currently public. Operational endpoints such as `/ready`, setup, metrics, runs, traces, tasks, approvals, policy, and workspace profile require service auth when configured.

## Secrets

Secrets must stay out of the repository and frontend bundle.

- LLM keys: local JSON config or `llm.api_key_file`.
- MCP service tokens: local credentials file referenced by `auth_token_ref`.
- Service token: local JSON config or local key file.
- GitHub PATs and other provider tokens: local-only files or external secret managers.

The store and audit path sanitize common sensitive keys such as `api_key`, `token`, `pat`, `password`, `secret`, and `authorization`.

## Tool Policy

All native and MCP tool calls should flow through the tool execution service:

1. schema validation
2. policy decision
3. optional approval
4. execution
5. output truncation
6. audit append

Policy actions:

```text
allow
caution
require_approval
deny
```

Recommended defaults for local development:

```json
{
  "policy": {
    "default_action": "caution",
    "tool_rules": {
      "exec": "require_approval",
      "write_file": "require_approval",
      "edit_file": "require_approval"
    }
  }
}
```

Recommended PSKA posture:

- Allow PSKA read/search/citation tools explicitly.
- Deny broad shell and file write tools for PSKA tenants unless there is a dedicated approval UI.
- Keep knowledge ACL decisions in PSKA, not FastReAct.

## Headless Approvals

Dangerous tool calls can emit `ask_user` and create an approval request:

```http
GET /v1/approvals
POST /v1/approvals/{request_id}/approve
POST /v1/approvals/{request_id}/deny
```

If no caller can decide safely, deny or let the request expire. The default approval timeout is 300 seconds.

## MCP Isolation

MCP server isolation modes are deployment choices:

- `shared`: one server instance for all callers.
- `per_user`: per-user instance where supported.
- `lazy_per_user`: per-user instance with idle cleanup where supported.

HTTP MCP servers are remote trust boundaries. Use TLS, service tokens, network allowlists, and least-privilege tool policies for remote deployments.

## Current Limits

- No OS-level sandbox.
- No database row-level access control inside FastReAct.
- No remote worker isolation.
- No multi-agent worktree isolation.
- No automatic token rotation.
- Policy reload API is not productized.

Use OS/container permissions, private networks, explicit service tokens, and conservative tool policy for deployments beyond local development.
