# FastReAct

FastReAct 当前主线是 `nano` 分支上的 headless agentic service。它的默认定位不是 Web 前端应用，而是为 PSKA 等上层系统提供持续、高效、快速、安全的单智能体服务层。

核心入口是 HTTP/SSE：

```http
POST /v1/chat/completions
```

主要代码在 [`fastreact-nano/`](fastreact-nano/)。产品壳集中在 [`fastreact-nano-web/app/service`](fastreact-nano-web/app/service)。

## 当前服务形态

FastReAct Nano 现在可以作为无头服务器运行。最小启动方式是：

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

长期服务配置优先放在：

```text
~/.fastreact/config.json
```

FastReAct 默认会依次尝试读取 `~/.fastreact/config.json`、仓库内 `.fastreact/config.json`、当前目录 `config.json`。发布或长期运行时建议显式传入配置文件，避免当前工作目录改变导致读错配置：

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 -m fastreact.adapters.http --config ~/.fastreact/config.json
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
    "service_token": "replace-with-local-service-token"
  },
  "paths": {
    "gateway_workspace": "~/fastreact-workspace"
  },
  "mcp": {
    "servers": []
  }
}
```

`~/api_key.txt` 支持 JSON 或旧的按行格式，主要用于本地 smoke test 和 credential bootstrap；长期服务仍建议把正式设置写入 config。JSON 形式可以包含：

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

本地和 PSKA 联动时，推荐让 PSKA 侧生成 FastReAct 配置：

```bash
cd /Users/xudawei/FastReAct
./start.sh
```

`./start.sh` 会做这些事：

- 读取 `PSKA_ARCHIVE`，默认是 `/Users/xudawei/Documents/personal archive`。
- 调用 `$PSKA_ARCHIVE/scripts/fastreact-pska-service-config` 生成 FastReAct 配置。
- 默认把生成结果写到 `$PSKA_ARCHIVE/.pska/fastreact-pska-http.json`。
- 用这份配置启动 FastReAct HTTP daemon。
- 启动 `fastreact-nano-web` service console。

可覆盖的常用环境变量：

```bash
export PSKA_ARCHIVE="/Users/xudawei/Documents/personal archive"
export PSKA_FASTREACT_CONFIG="$PSKA_ARCHIVE/.pska/fastreact-pska-http.json"
export FASTREACT_SERVICE_HOST="127.0.0.1"
export FASTREACT_SERVICE_PORT="8000"
export WEB_PORT="3000"

./start.sh
```

如果不使用 PSKA 自动生成器，可以从示例配置开始：

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
mkdir -p ~/.fastreact
cp config.pska.example.json ~/.fastreact/config.json
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
export FASTREACT_SERVICE_TOKEN="replace-with-local-service-token"

curl -fsS http://127.0.0.1:8000/ready \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN"

curl -fsS http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN" \
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
