# FastReAct Nano - Gateway 通信方式完整指南

**创建日期**: 2026-02-18
**状态**: ✅ COMPLETE

---

## 📋 快速参考

### 6 种 Gateway 对比

| Gateway | 协议 | 端口 | 多租户 | 复杂度 | 推荐场景 |
|---------|------|------|--------|--------|----------|
| **CLI** | 命令行 | - | ❌ | ⭐ | 本地开发、脚本 |
| **REPL** | 交互式 | - | ❌ | ⭐ | 调试、探索 |
| **HTTP** | REST/SSE | 8000 | ⚠️ | ⭐⭐ | Web API、OpenAI 兼容 |
| **Gateway WebSocket** | WebSocket | 9000 | ⚠️ | ⭐⭐⭐ | 实时通信、Web UI |
| **Feishu Webhook** | HTTP | 8001 | ✅ | ⭐⭐⭐⭐ | 飞书（需公网） |
| **Feishu SDK** | WebSocket | - | ✅ | ⭐⭐⭐⭐⭐ | **飞书（推荐）** |

---

## 1. CLI Gateway (命令行)

### 核心特点
```python
# 最简单的方式
from fastreact.adapters.cli import app
app()  # 启动 CLI
```

### 复杂用例
```bash
# 批量处理文件
for file in *.py; do
    fastreact "分析 $file 的代码质量"
done

# Git 集成
git diff | fastreact "审查这个 PR"

# 管道操作
cat code.py | fastreact "优化这段代码"
```

---

## 2. HTTP Gateway (REST API)

### 核心特点
- OpenAI 兼容 API
- SSE 流式响应
- 会话管理

### 启动
```bash
python -m fastreact.adapters.http
# http://localhost:8000
# http://localhost:8000/docs (API 文档)
```

### API 调用
```python
import requests

# REST API
response = requests.post("http://localhost:8000/chat", json={
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": False  # 或 True 流式
})

answer = response.json()["content"]
print(answer)
```

### 复杂用例：多轮对话
```python
class ChatSession:
    def __init__(self):
        self.history = []
        self.session_id = str(uuid.uuid4())

    def chat(self, message: str) -> str:
        self.history.append({"role": "user", "content": message})

        response = requests.post(
            "http://localhost:8000/chat",
            json={
                "messages": self.history,
                "session_id": self.session_id
            }
        )

        answer = response.json()["content"]
        self.history.append({"role": "assistant", "content": answer})
        return answer

# 使用
session = ChatSession()
print(session.chat("我叫 Alice"))
print(session.chat("我叫什么名字？"))  # "你的名字是 Alice"
```

---

## 3. Gateway WebSocket (双向通信)

### 核心特点
- 实时双向通信
- 会话管理
- 思考过程推送

### 启动
```bash
python -m fastreact.adapters.gateway
# ws://localhost:9000/ws
```

### WebSocket 协议
```javascript
// 客户端发送
ws.send(JSON.stringify({
    type: "query",
    content: "What is 2+2?",
    session_id: "optional-session-id"
}));

// 服务端推送（流式）
{"type": "THINK", "content": "Let me calculate..."}
{"type": "TOOL_CALL", "content": "calculator.add(2, 2)"}
{"type": "TOOL_RESULT", "content": "4"}
{"type": "STEP_END", "content": "The answer is 4."}
```

### 复杂用例：Python WebSocket 客户端
```python
import asyncio
import websockets
import json

async def chat_with_websocket(message: str):
    uri = "ws://localhost:9000/ws"

    async with websockets.connect(uri) as ws:
        # 发送查询
        await ws.send(json.dumps({
            "type": "query",
            "content": message
        }))

        # 接收流式响应
        async for msg in ws:
            event = json.loads(msg)

            if event["type"] == "THINK":
                print(f"[思考] {event['content']}")
            elif event["type"] == "STEP_END":
                print(f"[完成] {event['content']}")
                break

asyncio.run(chat_with_websocket("解释微服务架构"))
```

---

## 4. Feishu SDK (⭐ 生产推荐)

### 核心特点
- ✅ 无需公网服务器
- ✅ WebSocket 长连接
- ✅ 自动重连
- ✅ 完整多租户支持
- ✅ 生产就绪

### 启动
```python
from fastreact import Agent
from fastreact.adapters.feishu_sdk import FeishuSDKAdapter

# 创建多租户 Agent
agent = Agent(multitenant=True)

# 配置
config = {
    "app_id": "cli_xxx",
    "app_secret": "xxx",
    "enable_multitenant": True,
    "base_workspace": "./workspace"
}

# 创建适配器
adapter = FeishuSDKAdapter(agent, config)

# 启动（阻塞运行）
adapter.run()
```

### 自动多租户隔离
```python
# ✅ SDK 自动处理：
# 1. 接收飞书消息
# 2. 提取 sender_id
# 3. 创建 user_key = f"feishu:{sender_id}"
# 4. 创建用户专属工作空间
# 5. 调用 Agent.run_event_stream(user_key=user_key)
# 6. 发送回复

# 无需手动处理多租户逻辑！
```

### 完整示例：企业知识库问答
```python
from fastreact import Agent, Config
from fastreact.adapters.feishu_sdk import FeishuSDKAdapter

# 配置 GraphRAG MCP
config = Config(
    llm={"model": "gpt-4o-mini", "api_key": "sk-xxx"},
    mcp={
        "servers": [{
            "name": "graphrag",
            "command": "python3",
            "args": ["examples/graph_rag_server.py"],
            "isolation": "lazy_per_user"  # 每用户独立
        }]
    }
)

# 创建多租户 Agent
agent = Agent(config=config, multitenant=True)

# 飞书配置
feishu_config = {
    "app_id": "cli_xxx",
    "app_secret": "xxx",
    "enable_multitenant": True,
    "auto_reconnect": True
}

# 启动机器人
adapter = FeishuSDKAdapter(agent, feishu_config)

print("🚀 企业知识库问答机器人启动...")
adapter.run()
```

---

## 5. 多租户对比

### Gateway 的多租户支持

| Gateway | 多租户支持 | 实现方式 | 隔离级别 |
|---------|-----------|---------|---------|
| CLI | ❌ | 不支持 | 无 |
| REPL | ❌ | 不支持 | 无 |
| HTTP | ⚠️ | 手动实现 session_id 编码 | 弱 |
| Gateway WebSocket | ⚠️ | 手动实现 session_id 编码 | 弱 |
| Feishu Webhook | ✅ | 自动从 sender_id 提取 | 强 |
| **Feishu SDK** | ✅ | **自动，无需代码** | **强** |

### HTTP Gateway 多租户实现
```python
# ⚠️ 需要手动实现
session_id = f"feishu:ou_user123:{uuid.uuid4()}"

response = requests.post(
    "http://localhost:8000/chat",
    json={
        "messages": [{"role": "user", "content": "Hello"}],
        "session_id": session_id  # 需要包含 user_key
    }
)
```

### Feishu SDK 多租户实现（自动）
```python
# ✅ 自动实现，无需手动处理
agent = Agent(multitenant=True)
adapter = FeishuSDKAdapter(agent, config)
adapter.run()  # 自动多租户隔离
```

---

## 6. 复杂用例场景

### 用例 1: 企业知识库 + 多租户
```python
"""
场景：企业内部知识库问答系统
需求：100+ 员工并发查询，每人数据隔离
推荐：Feishu SDK
"""

from fastreact import Agent
from fastreact.adapters.feishu_sdk import FeishuSDKAdapter

# Agent 配置
agent = Agent(
    multitenant=True,
    base_workspace="./workspace"
)

# 每个员工有独立工作空间
# Alice 的查询不会看到 Bob 的数据
adapter = FeishuSDKAdapter(agent, feishu_config)
adapter.run()
```

### 用例 2: Web 应用 + 实时通信
```python
"""
场景：Web 应用需要实时显示思考过程
需求：用户输入后实时显示 AI 思考、工具调用
推荐：Gateway WebSocket
"""

from fastapi import FastAPI, WebSocket
import uvicorn

app = FastAPI()

@app.websocket("/ws")
async def chat_endpoint(ws: WebSocket):
    await ws.accept()

    # 接收查询
    msg = await ws.receive_json()
    query = msg["content"]

    # 流式推送事件
    async for event in agent.run_event_stream(query):
        await ws.send_json({
            "type": event.type.name,
            "content": event.content
        })
```

### 用例 3: OpenAI 兼容 API
```python
"""
场景：替换 OpenAI API，无缝迁移
需求：现有代码只需改 URL
推荐：HTTP Gateway
"""

# 原始代码（OpenAI）
from openai import OpenAI
client = OpenAI(api_key="sk-xxx")
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)

# 迁移后（HTTP Gateway）
import requests
response = requests.post(
    "http://localhost:8000/chat/completions",  # 只改 URL
    json={
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hello"}]
)
```

### 用例 4: 批量脚本处理
```python
"""
场景：自动化脚本批量处理任务
需求：简单、快速、无需服务器
推荐：CLI Gateway
"""

import subprocess

files = ["file1.py", "file2.py", "file3.py"]

for file in files:
    print(f"分析 {file}...")
    result = subprocess.run([
        "fastreact",
        f"分析 {file} 的代码质量和性能问题"
    ], capture_output=True, text=True)

    print(result.stdout)
```

---

## 7. 选择建议

### 按场景选择

| 你的需求 | 推荐Gateway | 理由 |
|---------|------------|------|
| 本地快速测试 | CLI | 最简单 |
| 调试代码 | REPL | 交互式 |
| Web API 集成 | HTTP Gateway | OpenAI 兼容 |
| 实时 Web UI | Gateway WebSocket | 双向通信 |
| **生产飞书机器人** | **Feishu SDK** ⭐ | 最稳定 |
| 多租户企业应用 | Feishu SDK | 自动隔离 |

### 按复杂度选择

| 复杂度 | Gateway | 学习曲线 |
|--------|---------|---------|
| ⭐ | CLI | 5 分钟 |
| ⭐ | REPL | 5 分钟 |
| ⭐⭐ | HTTP Gateway | 30 分钟 |
| ⭐⭐⭐ | Gateway WebSocket | 1 小时 |
| ⭐⭐⭐⭐ | Feishu Webhook | 2 小时 |
| ⭐⭐⭐⭐⭐ | Feishu SDK | 2 小时（配置最简单） |

---

## 8. 完整测试

### 运行复杂用例测试
```bash
# 运行所有 Gateway 测试
python3 test_gateway_complex_use_cases.py
```

### 测试覆盖
- ✅ CLI Gateway 单次查询
- ✅ HTTP Gateway 多轮对话
- ✅ WebSocket Gateway 流式事件
- ✅ 多租户用户隔离
- ✅ Feishu SDK 事件处理
- ✅ MCP 工具集成（GraphRAG）
- ✅ 并发用户（10+ 用户）

---

## 9. 文件清单

### 新创建的文件

1. **GUIDE_COMMUNICATION_METHODS.md**
   - 完整的 Gateway 通信方式指南
   - 每种 Gateway 的详细说明
   - 复杂用例示例

2. **test_gateway_complex_use_cases.py**
   - 7 个复杂用例测试
   - 涵盖所有 Gateway 类型
   - 可执行验证脚本

### 相关文档

- `src/fastreact/adapters/__init__.py` - Gateway 列表
- `src/fastreact/adapters/gateway.py` - Gateway 实现
- `src/fastreact/adapters/http.py` - HTTP Gateway
- `src/fastreact/adapters/feishu_sdk.py` - Feishu SDK
- `examples/gateway_client.py` - Gateway 客户端示例
- `examples/http_client.py` - HTTP 客户端示例
- `examples/feishu_sdk_bot.py` - 飞书机器人示例

---

## 10. 下一步

### 立即可用
```bash
# 1. 运行测试
python3 test_gateway_complex_use_cases.py

# 2. 启动 HTTP Gateway
python -m fastreact.adapters.http

# 3. 启动 Gateway WebSocket
python -m fastreact.adapters.gateway

# 4. 启动 Feishu SDK（推荐）
python examples/feishu_sdk_bot.py
```

### 选择适合你的 Gateway

1. **开发测试**: CLI / REPL
2. **Web 集成**: HTTP Gateway
3. **实时 UI**: Gateway WebSocket
4. **生产飞书**: Feishu SDK ⭐

---

**总结**: FastReAct Nano 提供了 6 种 Gateway 通信方式，覆盖从简单到复杂的所有场景。选择最适合你的需求即可！

**推荐**: 对于生产环境的飞书机器人，强烈推荐使用 **Feishu SDK** - 最简单、最稳定、无需公网服务器！

---

**文档版本**: v1.0
**最后更新**: 2026-02-18
