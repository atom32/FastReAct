# FastReAct

FastReAct 当前主线是 `fastreact-nano`：一个面向 PSKA 和其他上层系统的 headless agentic service。它的核心形态不是 Web 应用，而是通过 HTTP/SSE 提供单智能体循环、工具编排、MCP 调用、审批、run/trace/task 管理和事件流。

当前后端版本：`fastreact-nano 2.4.2`。

## Start Here

推荐从仓库根目录启动完整本地服务：

```bash
cd /Users/xudawei/FastReAct
./start.sh
```

首次运行时如果还没有配置，脚本会自动创建
`.fastreact/config.json`。FastReAct 的启动脚本只启动 FastReAct 本身，
不会跨仓库启动 AuthNode 或 PSKA。

默认地址：

```text
Service console: http://127.0.0.1:3000/service
HTTP daemon:     http://127.0.0.1:8000
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
cd /Users/xudawei/FastReAct
./start.sh /Users/xudawei/.fastreact/config.json
```

完整文档入口：

- [FastReAct Nano README](fastreact-nano/README.md)
- [5-minute quick start](fastreact-nano/GETTING_STARTED.md)
- [HTTP/SSE service manual](fastreact-nano/docs/HEADLESS_SERVICE.md)
- [Documentation index](fastreact-nano/docs/DOCS_INDEX.md)

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

If `service.service_token` is configured, protected endpoints require either:

```http
X-FastReAct-Service-Token: replace-with-local-service-token
```

or:

```http
Authorization: Bearer replace-with-local-service-token
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
2. `/Users/xudawei/FastReAct/.fastreact/config.json`
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
