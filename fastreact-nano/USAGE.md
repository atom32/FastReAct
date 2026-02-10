# FastReAct Nano v2.0 - 完整使用指南

## 安装

### 1. 核心安装 (最小依赖)

```bash
pip install fastreact-nano
```

**核心依赖**: 仅 `litellm` 和 `pyyaml`

**适用场景**: 作为库嵌入你的Python应用

### 2. CLI使用

```bash
pip install fastreact-nano[cli]
```

**额外依赖**: `typer`, `rich`

### 3. HTTP服务

```bash
pip install fastreact-nano[http]
```

**额外依赖**: `fastapi`, `uvicorn`

### 4. 完整Gateway

```bash
pip install fastreact-nano[gateway]
```

**额外依赖**: `fastapi`, `websockets`, `aiofiles`

### 5. 全功能开发

```bash
pip install fastreact-nano[all]
```

---

## 使用方式

### 方式1: Python API (核心)

```python
from fastreact import ask_sync

# 最简单 - 一行代码
response = ask_sync("分析这个代码库")
print(response)
```

```python
import asyncio
from fastreact import Agent

async def main():
    agent = Agent()

    # 使用skills
    response = await agent.run(
        "创建git分支feature-xyz",
        skills=["git_workflow"]
    )

    print(response)

asyncio.run(main())
```

### 方式2: CLI命令

```bash
# 安装
pip install fastreact-nano[cli]

# 单行命令
fastreact "分析这个代码库"

# 使用skill
fastreact "创建新分支" --skill git_workflow

# 指定模型
fastreact "解释这段代码" --model gpt-4o

# 交互模式
fastreact interactive
```

**CLI命令**:
- `fastreact run "query"` - 执行查询
- `fastreact interactive` - 交互模式
- `fastreact skills` - 列出skills
- `fastreact tools` - 列出tools
- `fastreact version` - 版本信息

### 方式3: HTTP API

```bash
# 安装
pip install fastreact-nano[http]

# 启动服务
python -m fastreact.adapters.http

# 或使用uvicorn
uvicorn fastreact.adapters.http:create_app
```

**API端点**:

```bash
# 运行查询
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"query": "分析代码"}'

# 列出skills
curl http://localhost:8000/skills

# 列出tools
curl http://localhost:8000/tools

# 健康检查
curl http://localhost:8000/health
```

**Python示例**:

```python
import requests

response = requests.post("http://localhost:8000/run", json={
    "query": "分析这个代码库",
    "model": "gpt-4o-mini",
    "skills": ["code_review"]
})

print(response.json())
```

### 方式4: WebSocket Gateway

```bash
# 安装
pip install fastreact-nano[gateway]

# 启动gateway
python -m fastreact.adapters.gateway

# 访问 http://localhost:9000 使用Web界面
```

**WebSocket协议**:

```python
import asyncio
import websockets
import json

async def gateway_client():
    uri = "ws://localhost:9000/ws"
    async with websockets.connect(uri) as ws:
        # 发送查询
        await ws.send(json.dumps({
            "type": "query",
            "content": "分析这个代码库"
        }))

        # 接收响应
        while True:
            response = await ws.recv()
            data = json.loads(response)
            print(f"[{data['type']}] {data['content']}")

asyncio.run(gateway_client())
```

---

## 配置

### 环境变量

```bash
# LLM配置
export FASTRACT_MODEL=gpt-4o-mini
export FASTRACT_API_BASE=https://api.openai.com/v1
export FASTRACT_API_KEY=sk-xxx
export FASTRACT_TEMPERATURE=0.7
export FASTRACT_MAX_TOKENS=4096

# 工具配置
export FASTRACT_MAX_FILE_SIZE=1048576  # 1MB
export FASTRACT_EXEC_TIMEOUT=30
export FASTRACT_WORKING_DIR=/path/to/workspace

# ReAct配置
export FASTRACT_MAX_ITERATIONS=20
export FASTRACT_ENABLE_STEERING=true
export FASTRACT_ENABLE_FOLLOWUP=true
export FASTRACT_STEERING_FILE=.steering.jsonl
```

### Python配置

```python
from fastreact import Config, Agent

config = Config()
config.llm.model = "gpt-4o"
config.llm.api_key = "sk-xxx"
config.react.max_iterations = 30

agent = Agent(config=config)
```

### 配置文件 (config.json)

```json
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_key": "sk-xxx",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "react": {
    "max_iterations": 20,
    "enable_steering": true,
    "enable_followup": true
  },
  "tools": {
    "max_file_size": 1048576,
    "exec_timeout": 30
  }
}
```

---

## 内置Skills

### file_ops (文件操作)

```python
from fastreact import Agent

agent = Agent()
response = await agent.run(
    "找出所有Python文件并统计行数",
    skills=["file_ops"]
)
```

### code_review (代码审查)

```python
response = await agent.run(
    "审查这个文件的代码质量",
    skills=["code_review"]
)
```

### git_workflow (Git工作流)

```python
response = await agent.run(
    "创建新分支并推送到远程",
    skills=["git_workflow"]
)
```

### 自定义Skills

在 `skills/` 目录创建SKILL.md:

```markdown
---
name: my_skill
description: 我的自定义技能
---

# My Skill

## When to Use
使用场景

## Instructions
使用说明
```

```python
response = await agent.run(
    "使用我的技能",
    skills=["my_skill"]
)
```

---

## 工具使用

### 4个核心工具

```python
from fastreact import Agent

agent = Agent()

# Agent会自动使用这些工具:
# - read_file: 读取文件
# - write_file: 写入文件
# - exec: 执行Shell命令
# - edit_file: 编辑文件

response = await agent.run(
    "读取README.md,统计行数,然后写入summary.txt"
)
```

### 工具配置

```python
from fastreact import Config, Agent, ExecTool

config = Config()
config.tools.exec_timeout = 60  # 增加超时
config.tools.working_dir = "/path/to/project"

agent = Agent(config=config)
```

---

## 高级用法

### 流式输出

```python
from fastreact import Agent

async def stream_callback(chunk):
    print(chunk, end="", flush=True)

agent = Agent()
response = await agent.run(
    "解释这段代码",
    stream_callback=stream_callback
)
```

### 实时干预 (Steering)

```bash
# 创建转向文件
echo '{"content": "停止，改用另一种方法"}' > .steering.jsonl

# Agent会在下次循环时读取并应用
```

### 异步任务 (Follow-up)

```python
from fastreact.core.callbacks import QueueFollowUpCallback

# 创建带follow-up的agent
agent = Agent()
response = await agent.run("启动后台任务")

# 后续任务可以通过follow-up继续
```

---

## 测试

```bash
# 安装开发依赖
pip install fastreact-nano[dev]

# 运行测试
pytest tests/ -v

# 运行特定测试
pytest tests/unit/test_tools.py -v

# 测试覆盖率
pytest --cov=fastreact --cov-report=html
```

---

## 故障排除

### ImportError: No module named 'fastreact'

```bash
# 确保从正确目录安装
cd fastreact-nano
pip install -e .
```

### CLI命令不可用

```bash
# 安装CLI适配器
pip install fastreact-nano[cli]

# 检查安装
fastreact --help
```

### LLM连接错误

```bash
# 设置API Key
export FASTRACT_API_KEY=sk-xxx

# 或在代码中设置
from fastreact import Config
config = Config()
config.llm.api_key = "sk-xxx"
```

---

## 示例项目

查看 `examples/` 目录获取更多示例:

- `agent_demo.py` - 完整Agent使用
- `http_client.py` - HTTP API客户端
- `gateway_client.py` - WebSocket客户端

---

## 性能优化

### 1. 使用本地模型

```bash
# 使用Ollama
export FASTRACT_MODEL=ollama/llama3
export FASTRACT_API_BASE=http://localhost:11434
```

### 2. 限制迭代次数

```bash
export FASTRACT_MAX_ITERATIONS=10
```

### 3. 禁用不需要的功能

```python
config = Config()
config.react.enable_steering = False
config.react.enable_followup = False
```

---

## 生产部署

### Docker (推荐)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

# 安装核心依赖
RUN pip install fastreact-nano

# 或安装完整版
# RUN pip install fastreact-nano[gateway]

CMD ["python", "-m", "fastreact.adapters.gateway"]
```

### Systemd服务

```ini
[Unit]
Description=FastReAct Nano Gateway
After=network.target

[Service]
Type=simple
User=fastreact
WorkingDirectory=/opt/fastreact
ExecStart=/opt/fastreact/venv/bin/python -m fastreact.adapters.gateway
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 支持

- GitHub: https://github.com/atom32/FastReAct
- Issues: https://github.com/atom32/FastReAct/issues

---

**享受FastReAct Nano带来的极速体验！** ⚡
