# FastReAct

FastReAct 当前主线是 `nano` 分支上的 headless agentic service。它的默认定位不是 Web 前端应用，而是为 PSKA 等上层系统提供持续、高效、快速、安全的单智能体服务层。

核心入口是 HTTP/SSE：

```http
POST /v1/chat/completions
```

主要代码在 [`fastreact-nano/`](fastreact-nano/)。产品壳集中在 [`fastreact-nano-web/app/service`](fastreact-nano-web/app/service)。

## 当前服务形态

FastReAct Nano 现在可以作为无头服务器运行。当前项目启动方式统一为：

1. 把所有启动设置写进一个 JSON config。
2. 运行仓库根目录的 `./start.sh`。

推荐本地配置文件：

```text
/Users/xudawei/FastReAct/.fastreact/config.json
```

推荐启动命令：

```bash
cd /Users/xudawei/FastReAct
./start.sh
```

也可以显式指定配置文件：

```bash
./start.sh /Users/xudawei/FastReAct/.fastreact/config.json
```

启动后默认地址：

```text
Service console: http://127.0.0.1:3000/service
HTTP daemon:     http://127.0.0.1:8000
```

常用端点：

- `POST /v1/chat/completions`：OpenAI-compatible chat style agent loop endpoint，支持 streaming 和 non-streaming。
- `GET /health`：基础存活检查。
- `GET /ready`：服务就绪检查，包含 agent、MCP server 和 MCP tool 状态；启用 service token 时需要认证。
- `GET /v1/tools`：列出工具。
- `GET /v1/skills`：列出技能。

如果配置了 `service.service_token`，调用服务需要带：

```http
X-FastReAct-Service-Token: replace-with-local-service-token
```

完整手册见 [`fastreact-nano/docs/HEADLESS_SERVICE.md`](fastreact-nano/docs/HEADLESS_SERVICE.md)。

## 初始化设置

首次在本机准备 FastReAct 时，建议按这个顺序做：

```bash
cd /Users/xudawei/FastReAct

# backend
cd fastreact-nano
python3 -m pip install -e ".[all]"

# frontend service console
cd ../fastreact-nano-web
npm install
```

本地完整启动只需要一个配置文件，优先放在仓库根目录：

```text
/Users/xudawei/FastReAct/.fastreact/config.json
```

长期 daemon-only 部署也可以把同一份 config 放在：

```text
~/.fastreact/config.json
```

`./start.sh` 会优先读取仓库根目录 `.fastreact/config.json`，然后再找 `~/.fastreact/config.json`。发布或长期运行时也可以显式传入配置文件，避免当前工作目录改变导致读错配置：

```bash
cd /Users/xudawei/FastReAct
./start.sh /Users/xudawei/FastReAct/.fastreact/config.json
```

一个最小可运行配置：

```json
{
  "llm": {
    "model": "deepseek-v4-flash",
    "api_base": "https://api.deepseek.com",
    "api_key": "replace-with-real-key"
  },
  "service": {
    "host": "127.0.0.1",
    "port": 8000,
    "log_level": "info",
    "service_token": "replace-with-local-service-token",
    "cors_origins": [
      "http://127.0.0.1:3000",
      "http://localhost:3000"
    ]
  },
  "web": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 3000
  },
  "logs": {
    "http": "/tmp/fastreact-http.log",
    "web": "/tmp/fastreact-web.log"
  },
  "pska": {
    "enabled": false,
    "archive": "/Users/xudawei/Documents/personal archive",
    "refresh_config": false,
    "config_file": null,
    "mcp_transport": "http"
  },
  "paths": {
    "gateway_workspace": "~/fastreact-workspace"
  },
  "mcp": {
    "servers": []
  }
}
```

`~/api_key.txt` 仍支持 JSON 或旧的按行格式，主要用于本地 smoke test 和 credential bootstrap。正常启动建议直接把 `llm.api_key` 写在 config，或在 config 中用 `llm.api_key_file` 明确指向 key 文件。JSON key 文件形式可以包含：

```json
{
  "api_key": "replace-with-real-key",
  "model": "deepseek-v4-flash",
  "base_url": "https://api.deepseek.com",
  "service_token": "replace-with-local-service-token"
}
```

## PSKA 集成

FastReAct 和 PSKA 的边界是服务层协议，而不是代码互相 import。

- PSKA 负责知识库、ACL、review、jobs、citations 和 MCP tools。
- FastReAct 负责 agent planning、LLM calls、tool orchestration、session/runtime control 和 event streaming。
- FastReAct 不直接访问 PSKA DB，也不替 PSKA 做知识 ACL 决策。

互联协议见 [`fastreact-nano/docs/PSKA_FASTREACT_PROTOCOL.md`](fastreact-nano/docs/PSKA_FASTREACT_PROTOCOL.md)。

本地和 PSKA 联动时，推荐先把 PSKA 配置写进同一个 FastReAct config：

```bash
cd /Users/xudawei/FastReAct
mkdir -p .fastreact
cp fastreact-nano/config.pska.example.json .fastreact/config.json
```

然后编辑 `.fastreact/config.json` 里的这些字段：

- `llm.*`：模型、provider base URL、API key 或 `api_key_file`。
- `service.*`：daemon host、port、service token、CORS origins。
- `web.*`：本地 service console 是否启动、host、port。
- `logs.*`：daemon 和 web console 日志路径。
- `pska.*`：是否启用 PSKA 联动、PSKA archive 路径、是否刷新生成配置。
- `mcp.servers`：PSKA MCP HTTP endpoint，默认是 `http://127.0.0.1:8765/mcp`。
- `policy.tenant_rules.pska.tools`：PSKA tenant 可调用的工具策略。

如果 `pska.refresh_config=false`，`./start.sh` 直接使用这份 config。若要让 PSKA 侧生成最终 FastReAct config，在同一份 config 中显式设置：

```json
{
  "pska": {
    "enabled": true,
    "archive": "/Users/xudawei/Documents/personal archive",
    "refresh_config": true,
    "config_file": "/Users/xudawei/Documents/personal archive/.pska/fastreact-pska-http.json",
    "mcp_transport": "http"
  }
}
```

启动：

```bash
cd /Users/xudawei/FastReAct
./start.sh
```

`./start.sh` 会做这些事：

- 从 `.fastreact/config.json` 或你传入的 config 路径读取所有启动设置。
- 按 `pska.refresh_config` 决定是否调用 PSKA 生成器。
- 用 config 中的 `service.*` 启动 FastReAct HTTP daemon。
- 用 config 中的 `web.*` 启动 `fastreact-nano-web` service console。
- 用 config 中的 `logs.*` 写入本地日志。

如果不使用 PSKA 自动生成器，可以从示例配置开始：

```bash
cd /Users/xudawei/FastReAct
mkdir -p .fastreact
cp fastreact-nano/config.pska.example.json .fastreact/config.json
```

然后确认：

- `llm.api_key` 或 `llm.api_key_file` 能读到真实 LLM key。
- `service.service_token` 和 PSKA 调用 FastReAct 时使用的 token 一致。
- `mcp.servers[0].url` 指向 PSKA MCP HTTP endpoint，默认是 `http://127.0.0.1:8765/mcp`。
- `policy.tenant_rules.pska.tools` 只允许 PSKA 知识工具，危险的 shell/file tools 应保持 `deny` 或 `require_approval`。

PSKA 调用 FastReAct 时使用服务协议，不 import FastReAct 代码。典型请求：

```json
{
  "messages": [
    {"role": "system", "content": "Use PSKA MCP tools and cite evidence."},
    {"role": "user", "content": "Question"}
  ],
  "stream": true,
  "user_key": "pska:user_primary",
  "metadata": {
    "caller": "pska",
    "purpose": "qa",
    "pska_user_id": "user_primary"
  }
}
```

## 启动方式

日常本地全栈启动：

```bash
cd /Users/xudawei/FastReAct
./start.sh
```

也可以显式传入配置文件：

```bash
./start.sh /Users/xudawei/FastReAct/.fastreact/config.json
```

启动成功后：

```text
Service console: http://127.0.0.1:3000/service
Daemon health:   http://127.0.0.1:8000/health
Daemon ready:    http://127.0.0.1:8000/ready
```

停止：

```bash
cd /Users/xudawei/FastReAct
./stop.sh
```

只启动无头 daemon：

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 -m fastreact.adapters.http --config ~/.fastreact/config.json
```

带 service token 的 smoke test：

```bash
export SERVICE_TOKEN="replace-with-local-service-token"

curl -fsS http://127.0.0.1:8000/ready \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN"

curl -fsS http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN" \
  -d '{
    "messages": [{"role": "user", "content": "Say hello from FastReAct."}],
    "stream": false,
    "user_key": "pska:smoke"
  }'
```

## 发布检查

发布前建议跑完整 release gate：

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 run_tests.py quick
python3 run_tests.py integration
python3 run_tests.py release-llm
python3 run_tests.py release-full
```

默认测试不会访问真实 LLM。`release-llm` 和 `release-full` 会读取 `~/api_key.txt` 做真实 LLM smoke test 和 LLM Judge。

发布前还应手工确认：

- `~/.fastreact/config.json` 或 PSKA 生成的 `fastreact-pska-http.json` 不含占位 token。
- `/ready` 返回 agent、MCP server 和 MCP tool 就绪。
- PSKA MCP HTTP endpoint 已启动，并且 FastReAct 的 `/v1/tools` 能看到 PSKA tools。
- policy 没有放开不该给 PSKA tenant 使用的 `exec`、`read_file`、`write_file`、`edit_file`。
- service token 只通过 header 或本地安全配置传递，不写入公开文档和 release artifact。

## 当前能力边界

当前版本已经具备：

- 单 agent ReAct loop。
- LLM 调用与真实 LLM release smoke gate。
- HTTP/SSE 服务入口。
- streaming agent event contract：`fastreact.agent_event.v1`。
- tool call / tool result / session end 等事件流。
- headless approval round trip：`ask_user`、`/v1/approvals/*` approve/deny。
- background run 初版协议：`/v1/runs/*` 创建、查询、事件和取消。
- trace summary 初版协议：`/v1/traces/*` 查询 run trace。
- policy 初版配置：per-tool / per-user / per-tenant allow/caution/approval/deny。
- policy inspection/dry-run：`/v1/policy` 和 `/v1/policy/check`。
- MCP stdio server 接入。
- per-server MCP `env` 透传。
- service token 保护。
- skills、tasks、TODO、session、context window 和 trace 相关基础设施。
- JSONL 控制面存储和运维脚本。

当前仍然不是：

- 多 agent 编排系统。
- PSKA 知识库本体。
- PSKA ACL/权限决策层。
- 长期 run trace 公共回放 API 的完整产品化版本。
- durable worker queue / retry / crash recovery。
- persisted event replay / pagination / retention / redaction。
- 跨 repo CI 中强制启动 PSKA + FastReAct 的完整流水线。
- 面向公众互联网的托管 SaaS 安全边界。
- 危险工具的业务级自动审批策略；默认应由调用方或操作员显式 approve/deny。
- policy 更新/重载 API、审计字段和配置校验的完整产品化版本。

## 长期方向

最终目标是长期稳定、高并发的 agentic service daemon。当前 Nano 阶段先保持单 agent，是为了把 headless 协议、run/job/trace/policy、approval 和 PSKA 边界打磨稳定。

在这些服务契约稳定前，不急于重写或扩大架构。等 run、job、trace、policy 和并发 daemon 边界清楚后，可以逐步把事件分发、任务队列、trace replay、policy hot path、MCP transport supervision 等局部组件迁移到 Rust 或其他更高效的实现。

## 文档

- [`fastreact-nano/README.md`](fastreact-nano/README.md)
- [`fastreact-nano/docs/HEADLESS_SERVICE.md`](fastreact-nano/docs/HEADLESS_SERVICE.md)
- [`fastreact-nano/docs/PSKA_FASTREACT_PROTOCOL.md`](fastreact-nano/docs/PSKA_FASTREACT_PROTOCOL.md)
- [`fastreact-nano/docs/DOCS_INDEX.md`](fastreact-nano/docs/DOCS_INDEX.md)

历史资料集中在 `docs_archive/`，不代表当前产品状态。
