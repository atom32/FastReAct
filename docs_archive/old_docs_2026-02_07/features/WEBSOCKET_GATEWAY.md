# WebSocket Gateway 使用指南

> **Phase 1 完成** - 实时双向通信接口

---

## 概述

WebSocket Gateway 为 FastReAct 提供了实时双向通信能力，支持：

- ✅ **实时通信** - WebSocket 双向流式通信
- ✅ **会话管理** - 多用户会话隔离和恢复
- ✅ **进度追踪** - 实时展示思考、行动、观察步骤
- ✅ **历史记录** - 自动保存和恢复对话历史
- ✅ **健康检查** - `/health` 端点监控服务状态

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

新增依赖：
- `fastapi>=0.104.0` - Web 框架
- `uvicorn[standard]>=0.24.0` - ASGI 服务器
- `websockets>=12.0` - WebSocket 支持

### 2. 启动服务器

```bash
# 设置 API Key
export OPENAI_API_KEY="your-api-key"

# 启动网关
python scripts/run_gateway.py
```

服务器将在 `http://localhost:8080` 启动。

### 3. 打开前端

在浏览器中打开 `public/index.html`，你会看到一个实时对话界面。

---

## API 端点

### WebSocket 端点

**连接**：`ws://localhost:8080/ws/{session_id}`

**发送消息**：
```json
{
  "query": "用户查询内容"
}
```

**接收消息类型**：

#### 1. 系统消息
```json
{
  "type": "system",
  "message": "会话已创建: abc123...",
  "session_id": "abc123..."
}
```

#### 2. 历史消息
```json
{
  "type": "history",
  "message": {
    "role": "user",
    "content": "之前的消息",
    "timestamp": "2026-01-28T10:30:00"
  }
}
```

#### 3. 状态更新
```json
{
  "type": "status",
  "status": "thinking",
  "message": "正在思考..."
}
```

#### 4. 思考过程
```json
{
  "type": "thought",
  "iteration": 1,
  "content": "需要搜索最新信息"
}
```

#### 5. 工具调用
```json
{
  "type": "action",
  "iteration": 1,
  "tool_calls": [
    {
      "name": "SearchTool",
      "parameters": {"query": "AI 新闻"}
    }
  ]
}
```

#### 6. 观察结果
```json
{
  "type": "observation",
  "iteration": 1,
  "content": "✅ 搜索结果: ..."
}
```

#### 7. 最终答案
```json
{
  "type": "answer",
  "answer": "最终答案内容",
  "stats": {
    "tool_calls": 3,
    "cache_hits": 1,
    "total_time": 5.2
  },
  "iteration": 3
}
```

#### 8. 错误消息
```json
{
  "type": "error",
  "error": "错误描述",
  "details": "ErrorType"
}
```

### HTTP 端点

#### 健康检查
```
GET /health
```

**响应**：
```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T10:30:00",
  "active_sessions": 3
}
```

#### 会话列表
```
GET /sessions
```

**响应**：
```json
{
  "sessions": [
    {
      "session_id": "abc123...",
      "message_count": 15,
      "created_at": "2026-01-28T10:00:00",
      "last_active": "2026-01-28T10:30:00"
    }
  ],
  "total": 1
}
```

---

## 编程使用

### 客户端示例（Python）

```python
import asyncio
import websockets
import json

async def chat_with_agent(session_id: str, query: str):
    uri = f"ws://localhost:8080/ws/{session_id}"

    async with websockets.connect(uri) as ws:
        # 发送查询
        await ws.send(json.dumps({"query": query}))

        # 接收响应
        while True:
            response = await ws.recv()
            data = json.loads(response)

            if data["type"] == "answer":
                print(f"答案: {data['answer']}")
                break
            elif data["type"] == "thought":
                print(f"思考: {data['content']}")
            elif data["type"] == "action":
                print(f"行动: {data['tool_calls']}")
            elif data["type"] == "error":
                print(f"错误: {data['error']}")
                break

# 使用
asyncio.run(chat_with_agent("my-session", "今天天气怎么样？"))
```

### 客户端示例（JavaScript）

```javascript
const sessionId = crypto.randomUUID();
const ws = new WebSocket(`ws://localhost:8080/ws/${sessionId}`);

ws.onopen = () => {
    console.log('已连接');

    // 发送消息
    ws.send(JSON.stringify({
        query: "帮我搜索最新 AI 新闻"
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
        case 'system':
            console.log('系统:', data.message);
            break;
        case 'thought':
            console.log('思考:', data.content);
            break;
        case 'action':
            console.log('行动:', data.tool_calls);
            break;
        case 'answer':
            console.log('答案:', data.answer);
            console.log('统计:', data.stats);
            break;
        case 'error':
            console.error('错误:', data.error);
            break;
    }
};

ws.onerror = (error) => {
    console.error('连接错误:', error);
};

ws.onclose = () => {
    console.log('连接已关闭');
};
```

---

## 会话管理

### 会话生命周期

```
1. 连接 → 创建/恢复会话
2. 发送消息 → 添加到会话历史
3. 接收响应 → 实时展示步骤
4. 断开连接 → 会话保留在内存
5. 重新连接 → 恢复历史记录
```

### 会话上下文

每个会话包含：

```python
{
    "messages": [
        {
            "role": "user",
            "content": "用户消息",
            "timestamp": "2026-01-28T10:00:00"
        },
        {
            "role": "assistant",
            "content": "助手回复",
            "timestamp": "2026-01-28T10:00:05",
            "stats": {...}
        }
    ],
    "context": {
        # 会话级别的上下文数据
        # 可以在下一步添加持久化
    },
    "metadata": {
        "created_at": "2026-01-28T10:00:00",
        "last_active": "2026-01-28T10:30:00"
    }
}
```

---

## 配置选项

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | 必填 | OpenAI API 密钥 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API 基础 URL |
| `OPENAI_MODEL` | `gpt-4` | 模型名称 |
| `PORT` | `8080` | 服务器端口 |
| `HOST` | `0.0.0.0` | 服务器主机 |

### 自定义工具

```python
# scripts/run_gateway.py

from fastreact import FastReAct
from fastreact.tools import SearchTool, CalculatorTool
from fastreact.core.tool import Tool

# 自定义工具
class MyTool(Tool):
    def _get_description(self):
        return "我的自定义工具"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            }
        }

    async def execute_async(self, input: str) -> str:
        return f"处理结果: {input}"

# 使用自定义工具
agent = FastReAct(
    api_key="your-api-key",
    tools=[
        SearchTool(),
        CalculatorTool(),
        MyTool(),  # 添加自定义工具
    ]
)

gateway = GatewayServer(agent)
```

---

## 生产部署

### 使用 Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "scripts/run_gateway.py"]
```

**构建和运行**：
```bash
docker build -t fastreact-gateway .
docker run -p 8080:8080 -e OPENAI_API_KEY="your-key" fastreact-gateway
```

### 使用 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  gateway:
    build: .
    ports:
      - "8080:8080"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=gpt-4
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

### 使用 systemd（Linux）

```ini
# /etc/systemd/system/fastreact-gateway.service
[Unit]
Description=FastReAct Gateway
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/fastreact
Environment="OPENAI_API_KEY=your-key"
ExecStart=/opt/fastreact/venv/bin/python scripts/run_gateway.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl enable fastreact-gateway
sudo systemctl start fastreact-gateway
```

---

## 性能优化

### 1. 启用缓存

```python
agent = FastReAct(
    enable_cache=True,        # 启用 LRU 缓存
    cache_size=1000,          # 缓存 1000 条记录
    enable_deduplication=True, # 启用去重
)
```

### 2. 并发工具调用

```python
agent = FastReAct(
    max_concurrent_tools=5,  # 最多并发 5 个工具
)
```

### 3. 使用 Redis（Phase 2）

```python
# 即将支持
from fastreact.session import RedisStore

gateway = GatewayServer(
    agent,
    session_store=RedisStore("redis://localhost:6379")
)
```

---

## 故障排除

### 问题 1: WebSocket 连接失败

**错误**：`WebSocket connection failed`

**解决**：
1. 检查服务器是否运行：`curl http://localhost:8080/health`
2. 检查防火墙设置
3. 确认端口未被占用

### 问题 2: API 密钥错误

**错误**：`Incorrect API key provided`

**解决**：
```bash
export OPENAI_API_KEY="your-actual-key"
python scripts/run_gateway.py
```

### 问题 3: 工具调用失败

**错误**：`Tool execution error`

**解决**：
1. 检查工具是否正确注册
2. 查看服务器日志
3. 测试工具独立功能

---

## 下一步

- [ ] **Phase 2**: 会话持久化（SQLite/PostgreSQL）
- [ ] **Phase 3**: 多代理路由
- [ ] **Phase 4**: 监控和指标（Prometheus）

---

## 相关文件

- **核心代码**：`src/fastreact/gateway/server.py`
- **启动脚本**：`scripts/run_gateway.py`
- **前端示例**：`public/index.html`
- **测试**：`tests/test_gateway.py`（即将添加）

---

**完成时间**: 2026-01-28
**状态**: ✅ Phase 1 完成
**向后兼容**: ✅ 完全兼容
