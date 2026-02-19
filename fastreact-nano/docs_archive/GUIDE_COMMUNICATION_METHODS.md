# FastReAct Nano - Gateway 通信方式与复杂用例

**Date**: 2026-02-18
**Status**: ✅ COMPLETE

---

## 目录

1. [Gateway 通信方式总览](#gateway-通信方式总览)
2. [每种 Gateway 详细说明](#每种-gateway-详细说明)
3. [复杂用例场景](#复杂用例场景)
4. [多租户集成](#多租户集成)
5. [完整示例代码](#完整示例代码)

---

## Gateway 通信方式总览

FastReAct Nano 支持 **6 种 Gateway**，每种都有特定的使用场景：

| Gateway | 协议 | 端口 | 多租户 | 复杂度 | 适用场景 |
|---------|------|------|--------|--------|----------|
| **CLI** | 命令行 | - | ❌ | ⭐ | 本地开发、脚本自动化 |
| **REPL** | 交互式 | - | ❌ | ⭐ | 调试、探索性测试 |
| **HTTP** | REST/SSE | 8000 | ❌ | ⭐⭐ | Web API 集成、OpenAI 兼容 |
| **Gateway** | WebSocket | 9000 | ⚠️ | ⭐⭐⭐ | 实时通信、Web UI |
| **Feishu Webhook** | HTTP | 8001 | ✅ | ⭐⭐⭐⭐ | 飞书机器人（需公网） |
| **Feishu SDK** | WebSocket | - | ✅ | ⭐⭐⭐⭐⭐ | 飞书机器人（推荐） |

---

## 1. CLI Gateway (命令行)

### 特点
- ✅ 最简单，单次查询
- ✅ 适合脚本自动化
- ✅ 无需服务器
- ❌ 无状态保持
- ❌ 无多租户

### 安装
```bash
pip install "fastreact-nano[cli]"
```

### 使用方式

#### 方式 A: 命令行调用
```bash
# 单次查询
fastreact "What is 2+2?"

# 指定模型
fastreact "Explain quantum computing" --model gpt-4o

# 从文件读取查询
fastreact "$(cat query.txt)"
```

#### 方式 B: Python 代码
```python
from fastreact.adapters.cli import app

# 直接运行
app()
```

### 复杂用例 1: 批量处理
```bash
#!/bin/bash
# 批量分析多个文件

for file in *.py; do
    echo "Analyzing $file..."
    fastreact "Analyze the file $file, identify bugs and suggest improvements"
    echo "---"
done
```

### 复杂用例 2: 管道集成
```bash
# 与其他工具集成
cat "requirements.txt" | fastreact "Analyze these dependencies for security issues"

# Git 集成
git diff | fastreact "Review this code diff and suggest improvements"
```

---

## 2. REPL Gateway (交互式)

### 特点
- ✅ 交互式对话
- ✅ 会话历史保持
- ✅ 适合调试和探索
- ❌ 无多租户
- ❌ 单用户

### 使用方式

#### 启动 REPL
```python
from fastreact.adapters.repl import ReplSession

# 创建 REPL 会话
repl = ReplSession()
repl.run()
```

### 复杂用例 1: 代码审查会话
```python
# 在 REPL 中
from fastreact.adapters.repl import ReplSession

repl = ReplSession()
repl.run()

# 交互式对话
>>> 帮我审查 src/fastreact/agent.py
[THINK] Let me analyze the code...
[TOOL_CALL] ReadFile("src/fastreact/agent.py")
...
>>> 这个文件有什么问题？
[STEP_END] 根据分析，发现以下问题...
>>> 给出修复建议
...
```

### 复杂用例 2: 交互式调试
```python
repl = ReplSession()
repl.run()

# 调试循环
>>> 测试 MCP 工具
>>> 使用 graphrag_search 搜索 "Python"
>>> 显示搜索结果
>>> 再次搜索 "Machine Learning"
>>> 退出
```

---

## 3. HTTP Gateway (REST API)

### 特点
- ✅ OpenAI 兼容 API
- ✅ SSE 流式响应
- ✅ 状态管理 (session_id)
- ⚠️ 多租户有限 (需要 session_id 包含 user_key)
- ✅ 适合 Web 集成

### 安装
```bash
pip install "fastreact-nano[http]"
```

### 启动
```bash
python -m fastreact.adapters.http
# 访问 http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### API 端点

#### POST /chat - 对话接口
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is 2+2?"}
    ],
    "stream": true
  }'
```

#### POST /chat/completions - OpenAI 兼容
```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "stream": true
  }'
```

### 复杂用例 1: Web 应用集成
```python
import requests

# FastAPI 后端
from fastapi import FastAPI
import httpx

app = FastAPI()

@app.post("/ai/analyze")
async def analyze_code(code: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/chat",
            json={
                "messages": [
                    {"role": "user", "content": f"Analyze this code:\n{code}"}
                ],
                "stream": True
            },
            timeout=60.0
        )
        return StreamingResponse(
            response.aiter_bytes(),
            media_type="text/event-stream"
        )
```

### 复杂用例 2: 多轮对话管理
```python
import requests
import uuid

class ChatSession:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())
        self.history = []

    def chat(self, message: str) -> str:
        # 添加到历史
        self.history.append({"role": "user", "content": message})

        # 调用 API
        response = requests.post(
            f"{self.base_url}/chat",
            json={
                "messages": self.history,
                "session_id": self.session_id
            }
        )

        result = response.json()["content"]

        # 添加到历史
        self.history.append({"role": "assistant", "content": result})

        return result

# 使用
session = ChatSession()
answer1 = session.chat("My name is Alice")
answer2 = session.chat("What is my name?")
print(answer2)  # "Your name is Alice"
```

### 复杂用例 3: 流式响应处理
```python
import requests
import json

def stream_chat(message: str):
    """处理流式响应"""
    response = requests.post(
        "http://localhost:8000/chat",
        json={
            "messages": [{"role": "user", "content": message}],
            "stream": True
        },
        stream=True
    )

    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = json.loads(line[6:])
                if data.get('type') == 'THINK':
                    print(f"[思考] {data['content']}")
                elif data.get('type') == 'STEP_END':
                    print(f"[答案] {data['content']}")

# 使用
stream_chat("Explain async/await in Python")
```

---

## 4. Gateway WebSocket (双向通信)

### 特点
- ✅ 双向实时通信
- ✅ 会话管理
- ✅ 思考过程实时推送
- ⚠️ 多租户有限 (session_id 需包含 user_key)
- ✅ 适合 Web UI

### 安装
```bash
pip install "fastreact-nano[gateway]"
```

### 启动
```bash
python -m fastreact.adapters.gateway
# 访问 http://localhost:9000
```

### WebSocket 协议

#### 客户端发送
```json
{
  "type": "query",
  "content": "What is 2+2?",
  "session_id": "optional-session-id"
}
```

#### 服务端推送 (流式事件)
```json
{"type": "connected", "session_id": "uuid"}
{"type": "THINK", "content": "Let me calculate..."}
{"type": "TOOL_CALL", "content": "calculator.add(2, 2)"}
{"type": "TOOL_RESULT", "content": "4"}
{"type": "STEP_END", "content": "The answer is 4."}
```

### 复杂用例 1: WebSocket 客户端
```python
import asyncio
import websockets
import json

async def chat_with_websocket(message: str):
    uri = "ws://localhost:9000/ws"

    async with websockets.connect(uri) as websocket:
        # 发送消息
        await websocket.send(json.dumps({
            "type": "query",
            "content": message
        }))

        # 接收流式响应
        async for message in websocket:
            event = json.loads(message)

            if event["type"] == "THINK":
                print(f"[思考] {event['content']}")
            elif event["type"] == "TOOL_CALL":
                print(f"[工具调用] {event['content']}")
            elif event["type"] == "STEP_END":
                print(f"[完成] {event['content']}")
                break
            elif event["type"] == "ERROR":
                print(f"[错误] {event['content']}")
                break

# 运行
asyncio.run(chat_with_websocket("Explain microservices"))
```

### 复杂用例 2: 多用户聊天室
```python
import asyncio
import websockets
import uuid

class ChatRoom:
    def __init__(self):
        self.users = {}  # user_id -> websocket

    async def join(self, user_id: str):
        """用户加入聊天室"""
        uri = "ws://localhost:9000/ws"
        ws = await websockets.connect(uri)
        self.users[user_id] = ws
        return ws

    async def broadcast_query(self, user_id: str, message: str):
        """广播查询并收集响应"""
        ws = self.users.get(user_id)
        if not ws:
            return "User not found"

        await ws.send(json.dumps({
            "type": "query",
            "content": message,
            "session_id": user_id
        }))

        responses = []
        async for msg in ws:
            event = json.loads(msg)
            if event["type"] == "STEP_END":
                responses.append(event["content"])
                break

        return responses

# 使用
async def main():
    room = ChatRoom()

    # 3个用户加入
    alice = await room.join("alice")
    bob = await room.join("bob")
    charlie = await room.join("charlie")

    # Alice 提问
    result = await room.broadcast_query(
        "alice",
        "What are the pros and cons of microservices?"
    )

    print(f"Alice 的回复: {result}")

asyncio.run(main())
```

---

## 5. Feishu Webhook (HTTP 推送)

### 特点
- ✅ 飞书官方集成
- ✅ 消息推送接收
- ✅ 支持多租户
- ❌ 需要公网服务器
- ❌ 需要配置 Webhook URL

### 安装
```bash
pip install "fastreact-nano[feishu]"
```

### 配置
```python
# config.json
{
  "feishu": {
    "connection_mode": "webhook",
    "app_id": "cli_xxx",
    "app_secret": "xxx",
    "encrypt_key": "xxx",
    "verification_token": "xxx",
    "host": "0.0.0.0",
    "port": 8001,
    "enable_multitenant": true,
    "base_workspace": "./workspace"
  }
}
```

### 启动 Webhook 服务器
```python
from fastreact.adapters.feishu import FeishuWebhookAdapter
from fastreact import Agent

agent = Agent(multitenant=True)
adapter = FeishuWebhookAdapter(agent)

# 启动服务器
adapter.run()
# 飞书发送消息到: https://your-server.com:8001/webhook/feishu
```

### 复杂用例 1: 飞书机器人 + GraphRAG
```python
from fastreact import Agent
from fastreact.adapters.feishu import FeishuWebhookAdapter

# 创建多租户 Agent
agent = Agent(
    multitenant=True,
    base_workspace="./workspace"
)

# 创建飞书适配器
adapter = FeishuWebhookAdapter(agent)

# 配置飞书事件处理
@adapter.on_message
async def handle_feishu_message(event):
    user_key = f"feishu:{event.sender_id}"
    message = event.content

    # 使用 GraphRAG MCP 工具
    async for response in agent.run_event_stream(
        f"使用 GraphRAG 搜索: {message}",
        user_key=user_key
    ):
        if response.type == EventType.STEP_END:
            # 发送回飞书
            await adapter.reply_text(
                event.message_id,
                response.content
            )

adapter.run()
```

### 复杂用例 2: 飞书卡片交互
```python
@adapter.on_message
async def handle_with_card(event):
    """使用飞书卡片进行交互"""
    user_key = f"feishu:{event.sender_id}"

    # 发送思考中卡片
    await adapter.reply_card(
        event.message_id,
        {
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**🤔 思考中...**"
                    }
                }
            ]
        }
    )

    # 执行查询
    async for resp in agent.run_event_stream(
        event.content,
        user_key=user_key
    ):
        if resp.type == EventType.THINK:
            # 更新卡片：显示思考
            await adapter.update_card(
                event.message_id,
                {
                    "elements": [{
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**💭 思考**\n{resp.content}"
                        }
                    }]
                }
            )

        elif resp.type == EventType.TOOL_CALL:
            # 更新卡片：显示工具调用
            await adapter.update_card(
                event.message_id,
                {
                    "elements": [{
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**🔧 工具调用**\n`{resp.content}`"
                        }
                    }]
                }
            )

        elif resp.type == EventType.STEP_END:
            # 最终答案
            await adapter.update_card(
                event.message_id,
                {
                    "elements": [{
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**✅ 完成**\n{resp.content}"
                        }
                    }]
                }
            )
```

---

## 6. Feishu SDK (WebSocket 长连接) ⭐ 推荐

### 特点
- ✅ **终极形态** - 无需公网服务器
- ✅ WebSocket 长连接
- ✅ 自动重连
- ✅ 完整多租户支持
- ✅ 适合生产环境
- ✅ 无需暴露端口

### 安装
```bash
pip install "fastreact-nano[feishu]"
```

### 启动
```python
from fastreact.adapters.feishu_sdk import FeishuSDKAdapter
from fastreact import Agent

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

### SDK 优势

| 特性 | Webhook | SDK |
|------|---------|-----|
| 公网服务器 | ✅ 需要 | ❌ 不需要 |
| 自动重连 | ❌ 需自己实现 | ✅ 内置 |
| 消息确认 | ❌ 需自己实现 | ✅ 内置 |
| 事件处理 | 手动解析 | 自动分发 |
| 部署复杂度 | 高 | 低 |
| 生产稳定性 | 中 | 高 |

### 复杂用例 1: 多租户 GraphRAG 机器人
```python
from fastreact import Agent
from fastreact.adapters.feishu_sdk import FeishuSDKAdapter
from fastreact.core.config import FeishuConfig

# 创建多租户 Agent（带 GraphRAG MCP）
agent = Agent(
    multitenant=True,
    base_workspace="./workspace"
)

# 配置
config = FeishuConfig(
    app_id="cli_xxx",
    app_secret="xxx",
    enable_multitenant=True,
    base_workspace="./workspace",
    auto_reconnect=True,
    log_level="info"
)

# 创建 SDK 适配器
adapter = FeishuSDKAdapter(agent, config)

# SDK 会自动处理：
# 1. WebSocket 连接管理
# 2. 事件接收和分发
# 3. 多租户用户隔离
# 4. 消息发送和确认
# 5. 自动重连

# 启动
adapter.run()
```

### 复杂用例 2: 实时思考流推送
```python
class StreamingFeishuAdapter(FeishuSDKAdapter):
    """支持实时思考流推送的飞书适配器"""

    async def _process_query_streaming(self, user_key: str, message: str, message_id: str):
        """处理查询并实时推送思考过程"""

        # 发送"正在思考"消息
        await self.send_text(
            message_id,
            "🤔 正在思考，请稍候..."
        )

        # 收集所有事件
        events_buffer = []

        async for event in self.agent.run_event_stream(message, user_key=user_key):
            events_buffer.append(event)

            # 实时推送思考过程
            if event.type == EventType.THINK:
                # 更新消息显示思考
                await self.update_message(
                    message_id,
                    f"💭 **思考**\n{event.content[:100]}..."
                )

            elif event.type == EventType.TOOL_CALL:
                # 显示工具调用
                await self.update_message(
                    message_id,
                    f"🔧 **工具调用**\n`{event.content}`"
                )

        # 最终答案
        final_answer = next(
            (e.content for e in events_buffer if e.type == EventType.STEP_END),
            "抱歉，没有生成答案。"
        )

        await self.update_message(message_id, final_answer)

# 使用
adapter = StreamingFeishuAdapter(agent, config)
adapter.run()
```

### 复杂用例 3: 多用户并发隔离
```python
import asyncio
from fastreact import Agent
from fastreact.adapters.feishu_sdk import FeishuSDKAdapter

class ConcurrentFeishuAdapter(FeishuSDKAdapter):
    """支持高并发的飞书适配器"""

    def __init__(self, agent, config):
        super().__init__(agent, config)
        self._active_queries = {}  # message_id -> task

    async def _handle_message_event_v2(self, event):
        """处理消息事件（支持并发）"""
        sender_id = event.event.sender.sender_id.open_id
        message_id = event.event.message.message_id
        content = self.parse_content(event)

        # 创建任务
        task = asyncio.create_task(
            self._process_query_async(
                user_key=f"feishu:{sender_id}",
                message=content,
                message_id=message_id
            )
        )

        self._active_queries[message_id] = task

    async def _process_query_async(self, user_key: str, message: str, message_id: str):
        """异步处理查询"""
        try:
            full_response = []

            async for event in self.agent.run_event_stream(message, user_key=user_key):
                if event.type == EventType.THINK:
                    # 推送思考
                    await self.send_text(
                        message_id,
                        f"💭 {event.content[:50]}..."
                    )

                elif event.type == EventType.STEP_END:
                    full_response.append(event.content)

            # 发送最终答案
            await self.send_text(
                message_id,
                "\n".join(full_response)
            )

        finally:
            # 清理任务
            if message_id in self._active_queries:
                del self._active_queries[message_id]

# 使用
adapter = ConcurrentFeishuAdapter(agent, config)
adapter.run()  # 支持100+并发用户
```

---

## 多租户集成

### 所有 Gateway 的多租户支持

| Gateway | 多租户支持 | user_key 传递方式 | 隔离级别 |
|---------|-----------|------------------|---------|
| CLI | ❌ | N/A | 无 |
| REPL | ❌ | N/A | 无 |
| HTTP | ⚠️ | session_id | 弱 (需手动) |
| Gateway WebSocket | ⚠️ | session_id | 弱 (需手动) |
| Feishu Webhook | ✅ | 自动 (sender_id) | 强 |
| Feishu SDK | ✅ | 自动 (sender_id) | 强 |

### HTTP Gateway 多租户实现

```python
# 客户端需要在 session_id 中包含 user_key
import requests

# 方式 1: 在 session_id 中编码
session_id = f"feishu:ou_user123:{uuid.uuid4()}"

response = requests.post(
    "http://localhost:8000/chat",
    json={
        "messages": [{"role": "user", "content": "Hello"}],
        "session_id": session_id  # 包含 user_key
    }
)

# HTTP Gateway 解析 session_id
# (需要自定义实现)
```

### Feishu SDK 多租户实现 (自动)

```python
# SDK 自动从事件中提取 sender_id
# 自动创建 user_key = f"feishu:{sender_id}"
# 自动隔离用户工作空间

from fastreact.adapters.feishu_sdk import FeishuSDKAdapter
from fastreact import Agent

agent = Agent(multitenant=True)
adapter = FeishuSDKAdapter(agent, config)

# ✅ 自动多租户，无需手动处理
adapter.run()
```

---

## 完整示例代码

### 示例 1: 企业知识库问答系统

```python
"""
完整示例：飞书 + GraphRAG + 多租户
企业知识库问答系统
"""

from fastreact import Agent, Config
from fastreact.adapters.feishu_sdk import FeishuSDKAdapter
from fastreact.core.config import FeishuConfig

# 1. 创建配置
config = Config(
    llm={
        "model": "gpt-4o-mini",
        "api_key": "sk-xxx",
        "temperature": 0.3
    },
    mcp={
        "servers": [
            {
                "name": "graphrag",
                "command": "python3",
                "args": ["examples/graph_rag_server.py"],
                "isolation": "lazy_per_user",  # 每用户独立
                "idle_timeout": 300,
                "max_instances": 10
            }
        ]
    }
)

feishu_config = FeishuConfig(
    app_id="cli_xxx",
    app_secret="xxx",
    enable_multitenant=True,
    base_workspace="./workspace",
    auto_reconnect=True
)

# 2. 创建多租户 Agent
agent = Agent(
    config=config,
    multitenant=True,
    base_workspace="./workspace"
)

# 3. 创建飞书适配器
adapter = FeishuSDKAdapter(agent, feishu_config)

# 4. 启动
print("🚀 企业知识库问答系统启动中...")
print("📱 飞书机器人已就绪")
print("🔍 支持 GraphRAG 知识图谱搜索")
print("👥 支持多用户隔离")
print("-" * 50)

adapter.run()
```

### 示例 2: Web API + WebSocket

```python
"""
完整示例：FastAPI + WebSocket Gateway
提供完整的 Web API 服务
"""

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, StreamingResponse
from fastreact import Agent
import uvicorn

app = FastAPI()
agent = Agent()

# HTML 页面
@app.get("/")
async def get_home():
    return HTMLResponse("""
    <html>
        <head><title>FastReAct Nano</title></head>
        <body>
            <h1>FastReAct Nano Demo</h1>
            <input id="query" placeholder="Enter query...">
            <button onclick="sendQuery()">Send</button>
            <div id="output"></div>

            <script>
                const ws = new WebSocket("ws://localhost:9000/ws");

                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    const output = document.getElementById("output");
                    output.innerHTML += `<p>[${data.type}] ${data.content}</p>`;
                };

                function sendQuery() {
                    const query = document.getElementById("query").value;
                    ws.send(JSON.stringify({
                        type: "query",
                        content: query
                    }));
                }
            </script>
        </body>
    </html>
    """)

# REST API 端点
@app.post("/chat")
async def chat_api(message: str):
    """REST API 对话接口"""
    response_text = []
    async for event in agent.run_event_stream(message):
        if event.type.name == "STEP_END":
            response_text.append(event.content)

    return {"answer": "".join(response_text)}

# WebSocket 端点
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 双向通信"""
    await websocket.accept()

    async for message in websocket:
        data = json.loads(message)

        # 流式响应
        async for event in agent.run_event_stream(data["content"]):
            await websocket.send_json({
                "type": event.type.name,
                "content": event.content
            })

            if event.type.name == "STEP_END":
                break

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 总结

### Gateway 选择建议

| 场景 | 推荐Gateway | 理由 |
|------|-----------|------|
| 本地开发 | CLI / REPL | 简单直接 |
| Web API 集成 | HTTP Gateway | OpenAI 兼容 |
| 实时 Web UI | Gateway WebSocket | 双向通信 |
| **生产飞书机器人** | **Feishu SDK** ⭐ | 最稳定，无需公网 |
| 多租户企业应用 | Feishu SDK | 自动隔离 |

### 关键要点

1. **CLI/REPL**: 适合开发和简单脚本
2. **HTTP Gateway**: 适合 Web API 集成
3. **Gateway WebSocket**: 适合实时通信
4. **Feishu Webhook**: 需要公网，复杂度高
5. **Feishu SDK**: ⭐ **推荐用于生产**，最简单最稳定

### 下一步

选择适合你的 Gateway，参考完整示例代码开始开发！

---

**文档版本**: v1.0
**最后更新**: 2026-02-18
