# FastReAct Nano

FastReAct Nano 是 FastReAct 当前主线实现。当前版本的首要形态是 headless agentic service：以 HTTP/SSE 对外提供单智能体循环、工具编排、MCP 调用和事件流服务。Web Gateway 和 Admin 控制台是可选控制面，不是运行 PSKA 集成的必要条件。

## 快速启动无头服务

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 -m fastreact.adapters.http
```

默认服务地址：

```text
http://127.0.0.1:8000
```

基础请求：

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "messages": [
      {"role": "user", "content": "Say hello from FastReAct."}
    ],
    "stream": false
  }'
```

如果配置了 service token：

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN" \
  -d '{
    "messages": [
      {"role": "user", "content": "Say hello from FastReAct."}
    ],
    "stream": false
  }'
```

完整服务手册见 [`docs/HEADLESS_SERVICE.md`](docs/HEADLESS_SERVICE.md)。

## 服务端点

- `POST /v1/chat/completions`：主 agent loop endpoint，支持 SSE streaming 和 non-streaming summary。
- `GET /health`：基础存活检查。
- `GET /ready`：部署就绪检查，包含 agent、MCP server 和 MCP tool 状态；启用 service token 时需要认证。
- `GET /v1/tools`：工具列表。
- `GET /v1/skills`：技能列表。

Streaming event schema：

```text
fastreact.agent_event.v1
```

常见事件：

```text
session_start
think
tool_call
tool_result
session_end
error
ask_user
```

## 正式配置

推荐长期运行使用：

```text
~/.fastreact/config.json
```

也可以通过 `--config` 指定：

```bash
python3 -m fastreact.adapters.http --config ~/.fastreact/config.json
```

最小配置：

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

PSKA MCP 示例：

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
    "service_token": "replace-with-local-service-token"
  },
  "mcp": {
    "servers": [
      {
        "name": "pska",
        "command": "/Users/xudawei/Documents/personal archive/scripts/pska",
        "args": ["mcp-server"],
        "isolation": "shared",
        "description": "PSKA personal knowledge store tools."
      }
    ]
  }
}
```

`~/api_key.txt` 支持 JSON：

```json
{
  "api_key": "replace-with-real-key",
  "model": "deepseek-v4-flash",
  "base_url": "https://api.deepseek.com",
  "service_token": "optional-local-service-token"
}
```

这个文件主要服务于本地真实 LLM smoke gate；长期运行服务建议使用正式 config。

## PSKA 集成边界

FastReAct 是 PSKA 的 agentic service layer，而不是 PSKA 内部模块。

PSKA 负责：

- knowledge storage
- ACL / tenant policy
- review / jobs
- citations
- PSKA MCP tools

FastReAct 负责：

- agent planning
- LLM calls
- tool orchestration
- session/runtime control
- event streaming
- service authentication
- MCP server lifecycle

FastReAct 不直接访问 PSKA DB，不绕过 PSKA MCP tools，也不替 PSKA 做知识 ACL 决策。

协议文档见 [`docs/PSKA_FASTREACT_PROTOCOL.md`](docs/PSKA_FASTREACT_PROTOCOL.md)。

## 当前能力边界

当前版本可以作为单 agent headless service 使用，具备：

- OpenAI-compatible chat style service endpoint。
- SSE streaming agent events。
- non-streaming summarized response。
- ReAct loop、工具调用、工具结果回传和最终回答。
- headless approval round trip：`ask_user` 事件和 `/v1/approvals/*` approve/deny API。
- MCP stdio server 集成。
- per-server MCP `env` 透传。
- skills 加载和工具列表。
- session、task、TODO、trace、context window 相关基础设施。
- context compression / sliding window 配置能力。
- service token 认证。
- release smoke test 读取真实 LLM API。

当前版本的明确边界：

- 仍是单 agent，不是多 agent 协作平台。
- Web UI 不是核心服务依赖。
- MCP server 主要是部署级绑定；request/session-scoped MCP binding 仍待定。
- run trace 持久化和 replay 的公共服务 API 还未完整产品化。
- PSKA/FastReAct 跨 repo E2E 还没有变成通用 CI 必跑项。
- 生产级公网暴露还需要外层 TLS、网络隔离、token rotation、租户隔离和审计策略。
- 危险工具的业务级自动审批策略应由调用方显式实现，不能默认放行。

## 长期方向

FastReAct 的最终目标是长期稳定、高并发的 agentic service daemon。Nano
阶段先坚持单 agent，是为了把服务协议和产品边界打磨稳：run/job、trace
replay、approval policy、tenant/user/tool policy、observability、PSKA
互联互通都应该先稳定。

等这些边界稳定后，再逐步考虑局部使用 Rust 或其他更高效实现。优先候选
不是 agent 思考逻辑本身，而是事件 fanout、durable run/job queue、trace
index/replay、policy hot path、MCP transport supervision 等高并发或高
可靠性基础设施。

## 可选 Web/Gateway 控制面

需要 Admin 控制台或 Gateway 调试时：

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
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

启动后访问：

- Web 控制台：http://localhost:3000
- Gateway 健康检查：http://localhost:9000/health
- Gateway 状态：http://localhost:9000/api/status

控制面鉴权：

```bash
FASTREACT_ADMIN_API_AUTH=true
GATEWAY_ADMIN_KEY=replace-me
```

启用后，Admin HTTP API 需要 `X-Admin-Key`。

## 测试与发布门槛

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 -m compileall -q src/fastreact scripts run_tests.py
python3 run_tests.py quick
python3 run_tests.py integration
python3 run_tests.py all
python3 run_tests.py release-llm
python3 run_tests.py release-full
```

默认测试不会访问真实 LLM。`release-llm` 会读取 `~/api_key.txt`，记录首个事件耗时和最终完成耗时，并通过 LLM Judge 判断回答是否有效。

## JSONL 存储维护

控制面数据以 JSONL 存在：

```text
$FASTRACT_GATEWAY_WORKSPACE/.fastreact/
```

维护命令：

```bash
python3 scripts/store_maintenance.py stats
python3 scripts/store_maintenance.py backup
python3 scripts/store_maintenance.py export --output .fastreact/export.json
python3 scripts/store_maintenance.py compact --keep-last 5000
```

`compact` 默认会先创建备份，然后保留最新 session/task 快照，并裁剪 append-only stream。

## 文档

- [`docs/HEADLESS_SERVICE.md`](docs/HEADLESS_SERVICE.md)
- [`docs/PSKA_FASTREACT_PROTOCOL.md`](docs/PSKA_FASTREACT_PROTOCOL.md)
- [`docs/DOCS_INDEX.md`](docs/DOCS_INDEX.md)
- [`docs/deployment.md`](docs/deployment.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/security.md`](docs/security.md)
