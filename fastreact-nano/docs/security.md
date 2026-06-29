# Security Model

FastReAct Nano security is policy plus service authentication plus audit. It is not an OS sandbox.

## Service Authentication

FastReAct does not implement password login, user registration, or an
organization admin console. It accepts identity that has already been verified
by a caller, gateway, customer platform, or lightweight identity broker.

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

For user-facing deployments, configure `auth.mode`:

- `service_token`: local/headless service calls; body `user_key` remains compatible.
- `trusted_headers`: a trusted gateway injects `X-FastReAct-User-Key`,
  `X-FastReAct-Tenant-Key`, roles, groups, and profile headers.
- `jwt`: FastReAct verifies a JWT from an external platform or identity broker
  and maps claims into `tenant_key` and `user_key`.

For local PSKA/FastReAct development, AuthNode is the preferred identity
broker. Configure FastReAct with `auth.mode=jwt`, issuer `authnode.local`,
audience `fastreact`, and tenant claim order
`tenant_key,tenant_id,tenant,org_id`. AuthNode's `sub` claim remains the full
FastReAct `user_key`, for example `pska:user_primary`.

If `service.service_token` is configured, service-to-service callers such as
PSKA may use `X-FastReAct-Service-Token` with `auth.mode=trusted_headers` or
`auth.mode=jwt`. This bypass is only for trusted backends that already verified
the browser session; the request body must carry `user_key` and, for explicit
tenant isolation, `metadata.tenant_key`. FastReAct records this as
`auth_provider=service_token` in run metadata.

Customer SSO should live outside FastReAct. Use the customer's existing platform
or a small OIDC/SAML/LDAP identity broker to authenticate users, then send
FastReAct verified headers or a JWT. PSKA receives the same `tenant_key` and
`user_key`; PSKA remains responsible for knowledge ACLs.

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

## Lightweight Tenant Isolation

FastReAct uses lightweight tenant isolation rather than a SaaS-style tenant
control plane. Workspace roots default to `~/FastReAct_workspaces`. When a
request carries a `tenant_key`/`user_key` in multi-tenant mode:

- the user gets a dedicated workspace, skills directory, memory file, and
  optional user-scoped MCP configuration;
- multi-tenant workspace paths use
  `{workspaces_root}/tenants/{tenant_key}/users/{safe_user_id}/`;
- if `tenant_key` is omitted, FastReAct infers it from the prefix before `:` in
  `user_key`; local single-user mode falls back to
  `{workspaces_root}/single/default/`;
- native file tools resolve relative paths inside that user workspace and reject
  absolute or relative paths that escape it;
- native shell commands run with the user workspace as their working directory;
- user-scoped MCP tools reject calls from other `user_key` values.

This isolation is a runtime guardrail, not an OS/container sandbox. Shell
commands can still reach resources allowed by the host operating system, so
deployments beyond local development should combine this with OS/container
permissions and conservative tool policy.

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
