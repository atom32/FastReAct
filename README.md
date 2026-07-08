# FastReAct

FastReAct 当前主线是 `fastreact-nano`：一个面向 PSKA 和其他上层系统的
多租户 headless agentic service。它的核心形态不是 Web 应用，而是通过
HTTP/SSE 提供 agent loop、工具编排、MCP 调用、审批、run/trace/task
管理、事件流和 workspace/profile 管理。

当前后端版本：`fastreact-nano 2.4.2`。

## Nano Multi-Tenant Snapshot

给其他开发者先看这一段：

- 当前产品入口是 HTTP/SSE daemon，`fastreact.adapters.gateway` 已废弃。
- HTTP daemon 默认以 `Agent(multitenant=True)` 启动；不要把测试里的
  `Agent(config)` 当作服务入口行为。
- 身份来源是外部认证层：`jwt` 或 `trusted_headers`。
  FastReAct 不做用户名密码登录、不保存密码、不维护组织后台。
- 多租户路径固定为
  `{workspaces_root}/tenants/{tenant_key}/users/{safe_user_id}/`，默认根目录是
  `~/FastReAct_workspaces`。
- native file/exec tools 在有 `UserContext` 时会被锁进当前用户 workspace。
  这是应用层隔离，不是 OS/container 沙箱。
- MCP 调用会透传 `tenant_key/user_key`。PSKA 自己负责知识 ACL，FastReAct
  不替 PSKA 判断知识是否可见。
- 各项目运行独立：FastReAct 的 `./start.sh` 只启动 FastReAct，不启动
  AuthNode 或 PSKA；容器部署时也是各自镜像、各自入口。

## Start Here

推荐从仓库根目录启动完整本地服务：

```bash
cd $FASTREACT_REPO
./start.sh
```

首次运行时如果还没有配置，脚本会自动创建
`.fastreact/config.json`。FastReAct 的启动脚本只启动 FastReAct 本身，
不会跨仓库启动 AuthNode 或 PSKA。

默认地址：

```text
Service console: http://127.0.0.1:3000/service
HTTP daemon:     http://127.0.0.1:18741
```

如果配置使用 AuthNode JWT（`auth.mode=jwt` 且 `auth.jwt_issuer=authnode.local`），
请在 AuthNode、FastReAct、PSKA 各自仓库分别运行自己的 `./start.sh`。
本地或容器部署时通过同一个 JWT secret、issuer/audience、反向代理或
AuthNode proxy 把它们接起来；FastReAct 不读取 AuthNode 项目目录。

FastReAct 配置可通过环境变量接收部署层注入的共享 secret：

```json
{
  "auth": {
    "mode": "jwt",
    "jwt_secret_env": "AUTHNODE_JWT_SECRET",
    "jwt_issuer": "authnode.local",
    "jwt_audience": "fastreact",
    "jwt_tenant_claims": ["tenant_key", "tenant_id", "tenant", "org_id"],
    "jwt_user_claim": "sub"
  }
}
```

指定配置运行：

```bash
cd $FASTREACT_REPO
./start.sh ~/.fastreact/config.json
```

完整文档入口：

- [FastReAct Nano README](fastreact-nano/README.md)
- [5-minute quick start](fastreact-nano/GETTING_STARTED.md)
- [HTTP/SSE service manual](fastreact-nano/docs/HEADLESS_SERVICE.md)
- [Multi-tenant guide](fastreact-nano/docs/MULTITENANT_GUIDE.md)
- [Security notes](fastreact-nano/docs/security.md)
- [Documentation index](fastreact-nano/docs/DOCS_INDEX.md)

## Multi-Tenant Model

FastReAct 使用 `tenant_key + user_key` 作为运行态身份边界。

`user_key` 建议使用 `{provider}:{subject}` 格式，例如：

```text
sso:alice
pska:user_primary
local:dev
```

`tenant_key` 来自 AuthNode/JWT/header/metadata。缺失时会从 `user_key` 冒号前缀
推断，以兼容旧调用；正式多租户调用应显式传入 `tenant_key`。

默认 workspace 布局：

```text
~/FastReAct_workspaces/
└── tenants/
    └── tenant_default/
        └── users/
            └── pska_user_primary/
                ├── config.json
                ├── memory.json
                └── skills/
```

配置项：

```json
{
  "paths": {
    "workspaces_root": "~/FastReAct_workspaces",
    "gateway_workspace": "~/FastReAct_workspaces/single/default"
  }
}
```

`paths.gateway_workspace` 只保留为 legacy/single-workspace profile 兼容项；
新运行态数据应放在 `workspaces_root` 下。

## Identity And Auth

FastReAct 的认证边界是“验证外部身份声明”，不是“提供登录系统”。

支持模式：

- `jwt`：验证外部 IdP/AuthNode 签发的 Bearer JWT，推荐生产和 SSO 集成使用。
- `trusted_headers`：平台网关或 AuthNode proxy 注入
  `X-FastReAct-User-Key`、`X-FastReAct-Tenant-Key` 等可信 header。

`service_token` 已废弃且会被拒绝：它无法证明真实 tenant/user，只会把
“拿到服务口令的人可以冒充任意身份”变成隐患。

JWT 配置推荐通过部署层 secret 注入：

```json
{
  "auth": {
    "mode": "jwt",
    "jwt_secret_env": "AUTHNODE_JWT_SECRET",
    "jwt_issuer": "authnode.local",
    "jwt_audience": "fastreact",
    "jwt_tenant_claims": ["tenant_key", "tenant_id", "tenant", "org_id"],
    "jwt_user_claim": "sub"
  }
}
```

开发和部署约定：

- 客户已有平台/SSO：平台登录，FastReAct 验证平台 JWT 或可信 header。
- 客户没有统一平台：外置 AuthNode/Identity Broker，FastReAct 只验证它签发的身份。
- 不要让 FastReAct 读取 AuthNode 或 PSKA 的本地配置文件；用环境变量、secret、
  URL、反向代理把服务接起来。
- `/ready` 会暴露 `auth.mode`、`multitenant.enabled` 和 `multitenant.workspaces_root`，
  可用于部署排查。

## Service Contract

Primary endpoint:

```http
POST /v1/chat/completions
```

Common service endpoints:

- `GET /health`
- `GET /ready`
- `GET /v1/setup`
- `GET /v1/metrics`
- `POST /v1/chat/completions`
- `POST /v1/runs`
- `GET /v1/runs`
- `GET /v1/traces`
- `GET /v1/tasks`
- `GET /v1/approvals`
- `GET /v1/policy`
- `GET /v1/tools`
- `GET /v1/skills`
- `GET /v1/workspace/profile`

Protected endpoints require a verified identity. In JWT mode, send:

```http
Authorization: Bearer <authnode-or-idp-jwt>
```

User-facing `POST /v1/chat/completions` and `POST /v1/runs` bind the run to
the verified identity. Request-body `user_key` / `metadata.tenant_key` are
metadata only and must not override JWT or trusted-header claims.

## Prompt Layers

`fastreact-nano` separates framework instructions from workspace/persona
instructions at prompt assembly time:

```text
core_framework
-> safety/tool policy note
-> workspace AGENTS.md / .fastreact/AGENT.md
-> persona SOUL.md / .fastreact/SOUL.md
-> tools and skills
-> task context
```

Rules for developers:

- Core framework and safety policy cannot be overridden by workspace or persona text.
- `AGENTS.md` is for project/framework instructions.
- `SOUL.md` is for voice, tone, expression density, and interaction style only.
- Prompt files are still text inputs, so treat them as untrusted and keep policy checks
  in code, not in prompt conventions.

## Tool And MCP Boundaries

Native tools:

- `read_file`, `write_file`, and `edit_file` resolve relative paths inside the
  current user workspace when `UserContext` exists.
- absolute paths are accepted only if they remain inside that workspace.
- `exec` runs with the current user workspace as cwd in multi-tenant mode.

MCP:

- FastReAct passes `user_key` and `tenant_key` to HTTP MCP tool calls.
- PSKA MCP should treat FastReAct identity as caller context, then enforce PSKA's
  own ACLs. Do not trust LLM-supplied `tenant_id/user_id` over FastReAct-supplied
  context.

Policy and approval:

- Policy actions are `allow`, `caution`, `require_approval`, and `deny`.
- Evaluation order is built-in forbidden exec patterns, then configured
  `user_rules`, `tenant_rules`, `tool_rules`, `tool:*`, `default_action`, and
  finally built-in safety classification.
- Approval requests are persisted and must be resolved through HTTP in headless use.

## Developer Checklist

Before changing multi-tenant behavior:

- Verify normal daemon startup, not only direct `Agent(...)` tests.
- Keep `tenant_key` explicit in HTTP/JWT/header/MCP contracts.
- Add tests for both positive isolation and negative cross-tenant access.
- Do not add cross-repo startup coupling. `./start.sh` must only start this repo.
- Do not bring back `fastreact.adapters.gateway` compatibility shims.
- Prefer adding small contract tests under `fastreact-nano/tests/contracts/`.

Useful checks:

```bash
PYTHONPATH=fastreact-nano/src pytest fastreact-nano/tests -q
git diff --check
```

## Project Layout

```text
FastReAct/
├── README.md                  # Repository entry point
├── start.sh                   # Starts daemon and optional service console from one JSON config
├── docs/                      # Pointer only; current docs live under fastreact-nano/docs
├── docs_archive/              # Pre-nano, v1, migration, and historical project docs
├── fastreact-nano/            # Current Python service implementation
├── fastreact-nano/docs/       # Current maintained documentation
├── fastreact-nano/docs_archive/ # Nano-era historical reports and implementation notes
└── fastreact-nano-web/        # Optional Next.js service console
```

Runtime/test generated text such as `fastreact-nano/MagicMock/...`, `workspaces/default/HISTORY.md`, and `workspaces/default/MEMORY.md` is not part of the maintained documentation set.

## Configuration

`./start.sh` resolves config in this order:

1. Explicit path passed to `./start.sh /path/to/config.json`
2. `.fastreact/config.json`
3. `~/.fastreact/config.json`
4. `fastreact-nano/.fastreact/config.json`
5. `fastreact-nano/config.json`

The backend `Config.load()` also supports `--config`, then falls back to `~/.fastreact/config.json`, `./.fastreact/config.json`, and `./config.json` relative to the backend working directory.

See [configuration file locations](fastreact-nano/docs/CONFIG_FILE_LOCATIONS.md) for details.

## PSKA Boundary

FastReAct and PSKA integrate through service and tool protocols, not direct imports.

PSKA owns knowledge storage, ACLs, review/jobs, citations, and PSKA MCP tools. FastReAct owns agent planning, LLM calls, tool orchestration, session/runtime control, approvals, runs, traces, and event streaming.

Protocol details live in [PSKA_FASTREACT_PROTOCOL.md](fastreact-nano/docs/PSKA_FASTREACT_PROTOCOL.md).

## Documentation Policy

Current docs belong in `fastreact-nano/docs/`. Short-lived implementation notes, sprint summaries, and historical audits belong in the appropriate archive. Before adding a new document, check [DOCS_INDEX.md](fastreact-nano/docs/DOCS_INDEX.md) and update an existing page when possible.
