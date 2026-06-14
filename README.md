# FastReAct

FastReAct 当前主线是 `nano` 分支上的 headless agentic service。它的默认定位不是 Web 前端应用，而是为 PSKA 等上层系统提供持续、高效、快速、安全的单智能体服务层。

核心入口是 HTTP/SSE：

```http
POST /v1/chat/completions
```

主要代码在 [`fastreact-nano/`](fastreact-nano/)。产品壳集中在 [`fastreact-nano-web/app/service`](fastreact-nano-web/app/service)。

## 当前服务形态

FastReAct Nano 现在可以作为无头服务器运行：

```bash
cd fastreact-nano
python3 -m fastreact.adapters.http
```

默认地址：

```text
http://127.0.0.1:8000
```

常用端点：

- `POST /v1/chat/completions`：OpenAI-compatible chat style agent loop endpoint，支持 streaming 和 non-streaming。
- `GET /health`：基础存活检查。
- `GET /ready`：服务就绪检查，包含 agent、MCP server 和 MCP tool 状态；启用 service token 时需要认证。
- `GET /v1/tools`：列出工具。
- `GET /v1/skills`：列出技能。

如果配置了 `FASTREACT_SERVICE_TOKEN` 或 `service.service_token`，调用服务需要带：

```http
X-FastReAct-Service-Token: replace-with-local-service-token
```

完整手册见 [`fastreact-nano/docs/HEADLESS_SERVICE.md`](fastreact-nano/docs/HEADLESS_SERVICE.md)。

## PSKA 集成

FastReAct 和 PSKA 的边界是服务层协议，而不是代码互相 import。

- PSKA 负责知识库、ACL、review、jobs、citations 和 MCP tools。
- FastReAct 负责 agent planning、LLM calls、tool orchestration、session/runtime control 和 event streaming。
- FastReAct 不直接访问 PSKA DB，也不替 PSKA 做知识 ACL 决策。

互联协议见 [`fastreact-nano/docs/PSKA_FASTREACT_PROTOCOL.md`](fastreact-nano/docs/PSKA_FASTREACT_PROTOCOL.md)。

## 正式配置

长期服务建议使用：

```text
~/.fastreact/config.json
```

示例：

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
    "service_token": "replace-with-local-service-token"
  },
  "mcp": {
    "servers": []
  }
}
```

也可以显式指定配置文件：

```bash
cd fastreact-nano
python3 -m fastreact.adapters.http --config ~/.fastreact/config.json
```

`~/api_key.txt` 支持 JSON 格式，主要用于本地 smoke test 和 credential bootstrap；长期运行服务仍建议使用正式 config。

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

## 开发与验证

```bash
cd fastreact-nano
python3 run_tests.py quick
python3 run_tests.py integration
python3 run_tests.py all
python3 run_tests.py release-llm
python3 run_tests.py release-full
```

默认测试不会访问真实 LLM。`release-llm` 会读取 `~/api_key.txt` 做真实 LLM smoke test 和 LLM Judge。

## Service 控制台

需要控制台时再启动完整本地开发栈：

```bash
cd fastreact-nano
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
cp .env.example .env

cd ../fastreact-nano-web
npm install
cp .env.example .env.local

cd ..
./fastreact-nano/scripts/dev_full.sh
```

Service 控制台：

```text
http://localhost:3000/service
```

HTTP daemon 健康检查：

```text
http://localhost:8000/health
```

## 文档

- [`fastreact-nano/README.md`](fastreact-nano/README.md)
- [`fastreact-nano/docs/HEADLESS_SERVICE.md`](fastreact-nano/docs/HEADLESS_SERVICE.md)
- [`fastreact-nano/docs/PSKA_FASTREACT_PROTOCOL.md`](fastreact-nano/docs/PSKA_FASTREACT_PROTOCOL.md)
- [`fastreact-nano/docs/DOCS_INDEX.md`](fastreact-nano/docs/DOCS_INDEX.md)

历史资料集中在 `docs_archive/`，不代表当前产品状态。
