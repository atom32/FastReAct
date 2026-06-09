# FastReAct

FastReAct 当前主线是 `nano` 分支上的 **FastReAct Nano 单智能体工作台**。它不是 demo，也不是多智能体平台；第一阶段目标是把一个单智能体产品做完整：稳定事件流、WebSocket Gateway、Admin 控制台、JSONL 持久化、任务工具、权限审批、审计、traces 和发布门槛。

## 当前状态

- 后端：`fastreact-nano/`
- 前端：`fastreact-nano-web/`
- 分支：`nano`
- 持久化：JSONL，默认在 `$FASTRACT_GATEWAY_WORKSPACE/.fastreact/`
- 安全策略：确认 + 审计，不做 OS 级沙箱
- 发布门槛：`python3 fastreact-nano/run_tests.py release-full`

## 快速启动

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

访问：

- Web 控制台：http://localhost:3000
- Gateway 健康检查：http://localhost:9000/health
- Gateway 状态：http://localhost:9000/api/status

## 一键生产式本地启动

```bash
./fastreact-nano/scripts/start_full.sh
```

该脚本会在缺少 `.next` 时构建前端，然后启动 Gateway 和 Next production server。

## 测试

```bash
cd fastreact-nano

python3 run_tests.py quick
python3 run_tests.py integration
python3 run_tests.py all
python3 run_tests.py release-llm
python3 run_tests.py release-full
```

默认测试不会访问真实 LLM。`release-llm` 会读取 `~/api_key.txt` 做真实 LLM 烟测和 LLM Judge；只有 `release-full` 通过后，才允许读取 `~/Github_PAT.txt` 进行 push。

## 运维入口

JSONL store 维护：

```bash
cd fastreact-nano
python3 scripts/store_maintenance.py stats
python3 scripts/store_maintenance.py backup
python3 scripts/store_maintenance.py export --output .fastreact/export.json
python3 scripts/store_maintenance.py compact --keep-last 5000
```

控制面鉴权：

```bash
FASTREACT_ADMIN_API_AUTH=true
GATEWAY_ADMIN_KEY=replace-me
```

启用后，Admin HTTP API 需要 `X-Admin-Key`。

## 文档

- [FastReAct Nano README](fastreact-nano/README.md)
- [部署说明](fastreact-nano/docs/deployment.md)
- [架构说明](fastreact-nano/docs/architecture.md)
- [安全模型](fastreact-nano/docs/security.md)

历史资料集中在 `docs_archive/`，不代表当前产品状态。
