# FastReAct Nano

FastReAct Nano 是一个单智能体工作台：保留稳定的事件流 API，提供 WebSocket Gateway、JSONL 控制面存储、任务工具、工具权限审批、运行时 traces 和 Admin 控制台。

当前阶段的产品边界很明确：只做单智能体，不引入数据库，不做 OS 级沙箱，也不进入多智能体 worker 平台。危险工具通过“用户确认 + 审计记录”控制。

## 快速开始

```bash
cd fastreact-nano
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"

cp .env.example .env
# 编辑 .env，设置 FASTRACT_API_KEY 或 OPENAI_API_KEY。

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

## 配置

后端配置优先从环境变量读取；部分配置也会从 `~/.fastreact/config.json`、`./.fastreact/config.json` 或 `./config.json` 读取。

后端配置模板见 [`.env.example`](.env.example)，重点字段：

- `FASTRACT_MODEL`、`FASTRACT_API_BASE`、`FASTRACT_API_KEY`
- `FASTRACT_GATEWAY_WORKSPACE`
- `GATEWAY_HOST`、`GATEWAY_PORT`、`GATEWAY_ADMIN_KEY`
- `FASTREACT_ADMIN_API_AUTH`
- `FASTREACT_CORS_ORIGINS`
- `FASTRACT_MCP_SERVERS`

前端配置模板见 [`../fastreact-nano-web/.env.example`](../fastreact-nano-web/.env.example)，重点字段：

- `NEXT_PUBLIC_FASTREACT_GATEWAY_HTTP_URL`
- `NEXT_PUBLIC_FASTREACT_GATEWAY_WS_URL`
- `NEXT_PUBLIC_FASTREACT_ADMIN_KEY`

不要把真实 LLM key、GitHub PAT 或私有 token 放进前端环境变量。

## 运行时接口

稳定 Python 入口：

```python
async for event in agent.run_event_stream(
    query,
    skills=None,
    session_id=None,
    history=None,
    user_key=None,
):
    ...
```

稳定 WebSocket 控制消息：

- `query`
- `control interrupt`
- `list_skills`
- `approve_tool`
- `deny_tool`
- `resume_session`

Admin HTTP API 覆盖 sessions、tasks、audit、traces、tools、config、metrics 和 dependency health。设置 `FASTREACT_ADMIN_API_AUTH=true` 后，控制面 API 需要 `X-Admin-Key`。

## 测试与发布门槛

```bash
cd fastreact-nano

python3 -m compileall -q src/fastreact scripts run_tests.py
python3 run_tests.py quick
python3 run_tests.py integration
python3 run_tests.py all
python3 run_tests.py release-llm
python3 run_tests.py release-full
```

`release-llm` 会读取 `~/api_key.txt`，记录首个事件耗时和最终完成耗时，并通过 LLM Judge 判断回答是否有效。`release-full` 会串起后端测试、前端构建、生产依赖审计、浏览器 E2E 和真实 LLM gate。

`~/Github_PAT.txt` 只在 release gate 通过后、确实需要 push 时读取。

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

## 运维文档

- [部署说明](docs/deployment.md)
- [架构说明](docs/architecture.md)
- [安全模型](docs/security.md)
