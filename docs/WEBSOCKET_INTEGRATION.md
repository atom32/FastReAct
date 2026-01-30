# FastReAct WebSocket 集成指南

> 日期: 2026-01-30
> 版本: v1.0

---

## 📡 Gateway 服务端

### 启动服务

```bash
# 方式 1: 使用启动脚本
python scripts/run_gateway.py

# 方式 2: 自定义启动
python -c "
from fastreact import FastReAct
from fastreact.gateway import GatewayServer
import uvicorn

agent = FastReAct(api_key='your-key', base_url='...', model='...')
gateway = GatewayServer(agent)

uvicorn.run(gateway.app, host='0.0.0.0', port=8080)
"
```

### 服务信息

- **WebSocket 端点**: `ws://localhost:8080/ws/{session_id}`
- **HTTP 端点**:
  - `GET /health` - 健康检查
  - `GET /sessions` - 会话列表
- **CORS**: 已启用（允许所有来源）

---

## 🔌 WebSocket 协议

### 连接

```typescript
const sessionId = 'my-session-123' // 生成或使用 UUID
const ws = new WebSocket(`ws://localhost:8080/ws/${sessionId}`);
```

### 消息格式

#### 1. 客户端发送消息

**类型**: `message`

```json
{
  "type": "message",
  "content": "帮我计算 25 * 18",
  "timestamp": "2026-01-30T12:00:00Z"
}
```

#### 2. 服务端推送事件

**思考事件** (`thought`):
```json
{
  "type": "thought",
  "content": "我需要使用计算器工具",
  "metadata": {
    "iteration": 1,
    "timestamp": "2026-01-30T12:00:01Z"
  }
}
```

**行动事件** (`action`):
```json
{
  "type": "action",
  "content": "正在调用工具...",
  "metadata": {
    "iteration": 1,
    "tool_name": "Calculator",
    "parameters": {"expression": "25 * 18"},
    "timestamp": "2026-01-30T12:00:02Z"
  }
}
```

**观察事件** (`observation`):
```json
{
  "type": "observation",
  "content": "**Calculator**: [OK] 450",
  "metadata": {
    "iteration": 1,
    "tool_name": "Calculator",
    "duration": 0.05,
    "timestamp": "2026-01-30T12:00:02Z"
  }
}
```

**答案事件** (`answer`):
```json
{
  "type": "answer",
  "content": "25 * 18 = 450",
  "metadata": {
    "is_final": true,
    "iteration": 1,
    "timestamp": "2026-01-30T12:00:03Z"
  }
}
```

**最终响应** (`final`):
```json
{
  "type": "final",
  "content": "计算完成，结果是 450",
  "stats": {
    "iterations": 1,
    "total_time": 2.5,
    "tool_calls": 1
  }
}
```

**错误事件** (`error`):
```json
{
  "type": "error",
  "content": "工具执行失败: ...",
  "metadata": {
    "error_type": "ToolExecutionError",
    "timestamp": "2026-01-30T12:00:00Z"
  }
}
```

---

## 🔄 事件流程

```
客户端发送消息
    ↓
[thought] 思考中...
    ↓
[action] 调用工具
    ↓
[observation] 工具返回结果
    ↓
[thought] 继续思考...
    ↓
[answer] 给出答案
    ↓
[final] 完成（带统计）
```

---

## 💻 前端集成示例

### React Hook

```typescript
import { useState, useEffect, useRef } from 'react';

interface Event {
  type: 'thought' | 'action' | 'observation' | 'answer' | 'final' | 'error';
  content: string;
  metadata?: Record<string, any>;
}

interface UseWebSocketReturn {
  connected: boolean;
  events: Event[];
  sendMessage: (content: string) => void;
  error: Error | null;
}

export function useFastReAct(sessionId: string): UseWebSocketReturn {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<Event[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8080/ws/${sessionId}`);

    ws.onopen = () => {
      setConnected(true);
      setError(null);
    };

    ws.onclose = () => {
      setConnected(false);
    };

    ws.onerror = (e) => {
      setError(new Error('WebSocket connection failed'));
    };

    ws.onmessage = (e) => {
      try {
        const event: Event = JSON.parse(e.data);
        setEvents(prev => [...prev, event]);
      } catch (err) {
        console.error('Failed to parse event:', err);
      }
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [sessionId]);

  const sendMessage = (content: string) => {
    if (!connected || !wsRef.current) {
      throw new Error('WebSocket not connected');
    }

    const message = {
      type: 'message',
      content,
      timestamp: new Date().toISOString()
    };

    wsRef.current.send(JSON.stringify(message));
  };

  return { connected, events, sendMessage, error };
}
```

### 组件使用

```typescript
import { useFastReAct } from './hooks/useFastReAct';
import { EventCard } from './components/EventCard';

export default function ChatInterface() {
  const sessionId = 'session-' + Date.now();
  const { connected, events, sendMessage } = useFastReAct(sessionId);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const message = formData.get('message') as string;
    sendMessage(message);
  };

  return (
    <div className="flex h-screen">
      {/* Chat Panel */}
      <div className="w-3/5 p-4">
        <form onSubmit={handleSubmit}>
          <input
            name="message"
            type="text"
            placeholder="输入消息..."
            disabled={!connected}
          />
          <button type="submit" disabled={!connected}>
            发送
          </button>
        </form>
      </div>

      {/* Event Panel */}
      <div className="w-2/5 p-4 bg-gray-50 overflow-y-auto">
        {events.map((event, index) => (
          <EventCard key={index} event={event} />
        ))}
      </div>
    </div>
  );
}
```

### Event Card 组件

```typescript
interface EventCardProps {
  event: Event;
}

export function EventCard({ event }: EventCardProps) {
  const icons = {
    thought: '💭',
    action: '🔧',
    observation: '📊',
    answer: '✅',
    final: '🎉',
    error: '❌'
  };

  const colors = {
    thought: 'bg-blue-50 border-blue-200',
    action: 'bg-purple-50 border-purple-200',
    observation: 'bg-green-50 border-green-200',
    answer: 'bg-orange-50 border-orange-200',
    final: 'bg-gray-100 border-gray-300',
    error: 'bg-red-50 border-red-200'
  };

  return (
    <div className={`p-3 mb-2 rounded border ${colors[event.type]}`}>
      <div className="flex items-center gap-2 mb-1">
        <span>{icons[event.type]}</span>
        <span className="font-semibold capitalize">{event.type}</span>
        {event.metadata?.duration && (
          <span className="text-sm text-gray-500">
            {event.metadata.duration.toFixed(2)}s
          </span>
        )}
      </div>
      <p className="text-gray-700">{event.content}</p>

      {event.metadata?.tool_name && (
        <div className="mt-2 text-sm">
          <span className="font-medium">Tool:</span> {event.metadata.tool_name}
        </div>
      )}

      {event.metadata?.parameters && (
        <details className="mt-2">
          <summary className="cursor-pointer text-sm">Parameters</summary>
          <pre className="mt-1 text-xs bg-white p-2 rounded">
            {JSON.stringify(event.metadata.parameters, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
```

---

## 🔑 认证（可选）

Gateway 支持三种认证方式：

### 1. Token 认证
```typescript
const ws = new WebSocket(`ws://localhost:8080/ws/${sessionId}?token=YOUR_TOKEN`);
```

### 2. API Key 认证
```typescript
const ws = new WebSocket(`ws://localhost:8080/ws/${sessionId}?api_key=YOUR_API_KEY`);
```

### 3. 密码认证
```typescript
const ws = new WebSocket(`ws://localhost:8080/ws/${sessionId}?password=YOUR_PASSWORD`);
```

---

## 🧪 测试

### 使用现有前端测试

```bash
# 1. 启动 Gateway
python scripts/run_gateway.py

# 2. 打开 public/index.html
# 浏览器会自动连接并发送测试消息
```

### 使用 WebSocket 客户端测试

```python
# test_websocket.py
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8080/ws/test-session"
    async with websockets.connect(uri) as ws:
        # 发送消息
        await ws.send(json.dumps({
            "type": "message",
            "content": "你好",
            "timestamp": "2026-01-30T12:00:00Z"
        }))

        # 接收响应
        async for message in ws:
            event = json.loads(message)
            print(f"[{event['type']}] {event['content']}")

            if event['type'] == 'final':
                break

asyncio.run(test())
```

---

## 📝 注意事项

1. **Session ID**: 每个会话使用唯一的 ID，建议使用 UUID
2. **重连**: 实现 WebSocket 自动重连机制
3. **错误处理**: 监听 `error` 和 `close` 事件
4. **性能**: 大量事件时考虑虚拟滚动
5. **安全性**: 生产环境配置 CORS 和认证

---

## 🚀 部署

### 前端部署

```bash
# 构建生产版本
npm run build

# 静态文件部署到 Gateway
# 或使用独立服务器（Nginx, Vercel, Netlify）
```

### Gateway 部署

```bash
# 使用环境变量
export OPENAI_API_KEY="your-key"
export PORT=8080
export HOST="0.0.0.0"

python scripts/run_gateway.py
```

### Docker 部署（可选）

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["python", "scripts/run_gateway.py"]
```

---

## 📚 相关文档

- [Gateway 设计文档](../src/fastreact/gateway/README.md)
- [协议规范](../src/fastreact/gateway/protocol.py)
- [认证系统](../src/fastreact/gateway/auth.py)

---

## 🆘 调试

### 启用 Gateway 日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 浏览器调试

```javascript
// 浏览器控制台
ws.addEventListener('message', (e) => {
  console.log('Received:', JSON.parse(e.data));
});
```

### 常见问题

1. **连接失败**: 检查 Gateway 是否启动
2. **认证错误**: 检查 token/api_key 配置
3. **CORS 错误**: 检查 Gateway CORS 配置
4. **消息未响应**: 检查 LLM API Key 是否有效

---

生成的前端项目应该放在 `frontend/` 目录，与 `public/` 区分开。
