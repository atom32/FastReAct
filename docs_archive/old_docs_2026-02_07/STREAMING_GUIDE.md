# FastReAct V2 流式响应指南

> **版本**: 2.0.0
> **更新时间**: 2026-02-03

## 概述

FastReAct V2 引入了流式响应功能，支持实时输出 `<thinking>` 推理过程、工具调用和执行结果。这大大提升了用户体验，特别是在处理长时间任务时。

### 核心特性

- ✅ **实时输出**: 无需等待完整响应，立即开始显示结果
- ✅ **思考可见**: 显示 AI 的推理过程（`<thinking>` 标签）
- ✅ **工具透明**: 实时显示工具调用和执行结果
- ✅ **双模式支持**: SSE 和 WebSocket 两种流式协议
- ✅ **CLI 集成**: 命令行工具支持 `--stream` 选项

---

## 快速开始

### 1. CLI 流式输出

最简单的方式是在 CLI 中使用 `--stream` 选项：

```bash
python -m fastreact.cli.main run --stream "帮我写一个快速排序算法"
```

**输出示例**:
```
[Start] Processing your query...
[Thinking] I need to write a quick sort algorithm in Python...
[Tool] write_file({"path": "quicksort.py", "content": "...", "create_dirs": true})
[Result] write_file: File written: quicksort.py (1234 bytes)...
[Answer] I've created a quick sort algorithm...
[Complete] Done! (iterations: 1, cache_hits: 0)
```

### 2. Python API - 基础流式

```python
import asyncio
from fastreact import FastReAct, StreamChunkType

async def streaming_example():
    agent = FastReAct(
        api_key="your-api-key",
        base_url="https://api.openai.com/v1",
        model="gpt-4",
    )

    async for chunk in agent.run_streaming("帮我写一个排序算法"):
        if chunk.type == StreamChunkType.THINKING:
            print(f"<thinking>{chunk.content}</thinking>")
        elif chunk.type == StreamChunkType.TOOL_CALL:
            print(f"<tool>{chunk.tool_name}({chunk.tool_params})</tool>")
        elif chunk.type == StreamChunkType.ANSWER:
            print(f"<answer>{chunk.content}</answer>")

asyncio.run(streaming_example())
```

### 3. Python API - 收集结果

```python
from fastreact.core.streaming import AsyncIteratorWrapper

async def collect_streaming_results():
    agent = FastReAct(api_key="...")

    # 收集所有数据块
    wrapper = AsyncIteratorWrapper(agent.run_streaming("你的查询"))
    chunks = await wrapper.to_list()

    # 分析结果
    for chunk in chunks:
        print(f"{chunk.type}: {chunk.content[:50]}...")

asyncio.run(collect_streaming_results())
```

---

## 数据块类型

### StreamChunkType 枚举

| 类型 | 说明 | 用途 |
|------|------|------|
| `METADATA` | 元数据 | 标记开始、结束、统计信息 |
| `THINKING` | 推理过程 | `<thinking>` 标签内容 |
| `TOOL_CALL` | 工具调用开始 | 工具名称和参数 |
| `TOOL_RESULT` | 工具执行结果 | 工具返回值 |
| `ANSWER` | 最终答案 | AI 的最终回答 |
| `ERROR` | 错误信息 | 错误描述 |
| `CONTROL` | 控制信号 | 心跳、停止等 |

### StreamChunk 字段

```python
@dataclass
class StreamChunk:
    type: StreamChunkType      # 数据块类型
    content: str                # 内容
    metadata: dict              # 元数据（可选）
    tool_name: str              # 工具名称（工具相关）
    tool_params: dict           # 工具参数（工具相关）
    tool_status: str            # 工具状态（工具相关）
    tool_error: str             # 工具错误（工具相关）
    timestamp: float            # 时间戳
```

---

## API 使用方式

### SSE (Server-Sent Events)

#### Python Requests

```python
import requests

response = requests.get(
    "http://localhost:8765/v1/chat/stream",
    params={"query": "帮我写个排序算法"},
    stream=True
)

for line in response.iter_lines():
    if line.startswith("data: "):
        data = json.loads(line[6:])
        print(f"[{data['type']}] {data['content']}")
```

#### curl

```bash
curl "http://localhost:8765/v1/chat/stream?query=帮我写个排序算法"
```

### WebSocket

#### Python WebSocket Client

```python
import asyncio
import websockets
import json

async def websocket_chat():
    uri = "ws://localhost:8765/ws/chat"

    async with websockets.connect(uri) as websocket:
        # 发送查询
        await websocket.send_json({
            "type": "query",
            "query": "帮我写个排序算法",
            "enable_thinking": True,
        })

        # 接收流式响应
        while True:
            message = await websocket.recv_json()
            print(f"[{message['type']}] {message.get('content', '')}")

asyncio.run(websocket_chat())
```

#### JavaScript (Browser)

```javascript
const ws = new WebSocket('ws://localhost:8765/ws/chat');

ws.onopen = () => {
    // 发送查询
    ws.send(JSON.stringify({
        type: 'query',
        query: '帮我写个排序算法',
        enable_thinking: true
    });
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    switch (message.type) {
        case 'thinking':
            console.log(`[思考] ${message.content}`);
            break;
        case 'tool_call':
            console.log(`[工具] ${message.tool_name}(${message.tool_params})`);
            break;
        case 'answer':
            console.log(`[答案] ${message.content}`);
            break;
        case 'error':
            console.error(`[错误] ${message.content}`);
            break;
    }
};
```

---

## CLI 命令

### run 命令

```bash
# 基础查询
python -m fastreact.cli.main run "What's 2 + 2?"

# 显示推理过程
python -m fastreact.cli.main run --show-thoughts "解释一下快速排序"

# 流式输出
python -m fastreact.cli.main run --stream "帮我写一个 Python 脚本"
```

### chat 命令

```bash
# 交互式对话（暂不支持流式）
python -m fastreact.cli.main chat
```

### Gateway 启动

```bash
# 启动 Gateway 服务器
python -m fastreact.cli.main gateway start --port 8765

# 端点访问
# SSE: http://localhost:8765/v1/chat/stream
# WebSocket: ws://localhost:8765/ws/chat
```

---

## 高级用法

### 1. 自定义流式处理

```python
from fastreact import FastReAct, StreamChunkType

class MyStreamProcessor:
    def __init__(self):
        self.thinking_buffer = []
        self.tool_calls = []

    async def process(self, agent, query: str):
        async for chunk in agent.run_streaming(query):
            if chunk.type == StreamChunkType.THINKING:
                self.thinking_buffer.append(chunk.content)
            elif chunk.type == StreamChunkType.TOOL_CALL:
                self.tool_calls.append({
                    "name": chunk.tool_name,
                    "params": chunk.tool_params
                })
            elif chunk.type == StreamChunkType.ANSWER:
                # 处理完成
                return {
                    "thinking": self.thinking_buffer,
                    "tools": self.tool_calls,
                    "answer": chunk.content
                }

# 使用
processor = MyStreamProcessor()
result = await processor.process(agent, "你的查询")
```

### 2. 过滤特定类型的数据块

```python
async def filter_thinking_only(agent, query: str):
    """只显示思考过程"""
    async for chunk in agent.run_streaming(query):
        if chunk.type == StreamChunkType.THINKING:
            print(f"{chunk.content}")

asyncio.run(filter_thinking_only(agent, "计算斐波那契数列"))
```

### 3. 超时控制

```python
import asyncio

async def streaming_with_timeout(agent, query: str, timeout=30):
    """带超时的流式执行"""
    try:
        async for chunk in asyncio.wait_for(
            agent.run_streaming(query),
            timeout=timeout
        ):
            yield chunk
    except asyncio.TimeoutError:
        yield StreamChunk(
            type=StreamChunkType.ERROR,
            content=f"执行超时（{timeout}秒）"
        )

asyncio.run(streaming_with_timeout(agent, "你的查询"))
```

---

## 配置说明

### 环境变量

```bash
# 启用流式响应（V2 默认启用）
export FASTREACT_STREAMING_ENABLED=true

# 默认显示思考过程
export FASTREACT_SHOW_THINKING=true
```

### config.json

```json
{
  "streaming": {
    "mode": "sse",
    "enable_thinking": true,
    "timeout": 30,
    "chunk_size": 1000
  }
}
```

---

## 性能优化

### 1. 批量 vs 流式

| 场景 | 推荐模式 | 原因 |
|------|----------|------|
| 短查询（<5秒） | 批量模式 | 延迟更低 |
| 长查询（>5秒） | 流式模式 | 用户体验更好 |
| 代码生成 | 流式模式 | 实时反馈 |
| 数据分析 | 流式模式 | 显示进度 |

### 2. 缓存策略

流式模式下仍然支持缓存：

```python
agent = FastReAct(
    api_key="...",
    enable_cache=True,  # 流式模式下仍然有效
)

async for chunk in agent.run_streaming("重复查询"):
    # 如果缓存命中，会快速返回结果
    pass
```

### 3. 并发流式处理

```python
async def process_multiple_queries():
    queries = [
        "问题1",
        "问题2",
        "问题3",
    ]

    tasks = [
        agent.run_streaming(q) for q in queries
    ]

    # 并发执行多个流式查询
    for task in asyncio.as_completed(tasks):
        async for chunk in task:
            print(f"[{chunk.type}] {chunk.content[:50]}")

asyncio.run(process_multiple_queries())
```

---

## 故障排除

### 问题 1: 流式输出卡住

**原因**: WebSocket 连接断开或超时

**解决**:
```python
# 添加超时控制
async for chunk in asyncio.wait_for(
    agent.run_streaming(query),
    timeout=30
):
    print(chunk)
```

### 问题 2: 接收不到 `<thinking>` 内容

**原因**: 模型不支持 `<thinking>` 标签

**解决**:
```python
# 检查响应内容
async for chunk in agent.run_streaming(
    query="你的问题",
    enable_thinking=True  # 确保启用
):
    print(chunk)
```

### 问题 3: SSE 连接断开

**原因**: Nginx 或代理服务器超时配置

**解决**:
```nginx
# nginx.conf
location /v1/chat/stream {
    proxy_pass http://backend:8765;
    proxy_read_timeout 300s;
    proxy_buffering off;
}
```

---

## 示例代码

### 示例 1: 简单流式对话

```python
# examples/streaming_simple.py

import asyncio
from fastreact import FastReAct, StreamChunkType

async def main():
    agent = FastReAct(
        api_key="your-api-key",
        model="gpt-4",
    )

    query = "帮我写一个冒泡排序算法"

    print(f"Query: {query}\n")

    async for chunk in agent.run_streaming(query):
        if chunk.type == StreamChunkType.THINKING:
            print(f"💭 {chunk.content}")
        elif chunk.type == StreamChunkType.TOOL_CALL:
            print(f"🔧 {chunk.tool_name}({chunk.tool_params})")
        elif chunk.type == StreamChunkType.TOOL_RESULT:
            print(f"✅ {chunk.tool_name}: {chunk.content[:80]}...")
        elif chunk.type == StreamChunkType.ANSWER:
            print(f"💡 {chunk.content}")

asyncio.run(main())
```

### 示例 2: 流式写入文件

```python
# examples/streaming_file_writing.py

import asyncio
from fastreact import FastReAct, StreamChunkType

async def main():
    agent = FastReAct(
        api_key="your-api-key",
        model="gpt-4",
    )

    query = "创建一个 Python 文件 hello.py，打印 'Hello World'"

    print(f"Query: {query}\n")

    async for chunk in agent.run_streaming(query):
        if chunk.type == StreamChunkType.TOOL_CALL:
            if chunk.tool_name == "write_file":
                print(f"📝 Creating {chunk.tool_params.get('path', 'file')}")
        elif chunk.type == StreamChunkType.TOOL_RESULT:
            if "written" in chunk.content:
                print(f"✅ {chunk.content}")

asyncio.run(main())
```

---

## API 参考

### FastReAct.run_streaming()

```python
async def run_streaming(
    self,
    query: str,
    enable_thinking: bool = True,
) -> AsyncIterator[StreamChunk]:
    """
    流式执行

    Args:
        query: 用户查询
        enable_thinking: 是否输出思考过程

    Yields:
        StreamChunk: 流式数据块
    """
```

### StreamChunk.to_sse()

```python
def to_sse(self) -> str:
    """
    转换为 SSE 格式

    Returns:
        SSE 格式字符串

    示例:
        "event: thinking\ndata: {...}\n\n"
    """
```

### StreamChunk.to_dict()

```python
def to_dict(self) -> Dict[str, Any]:
    """
    转换为字典（用于 JSON 序列化）

    Returns:
        dict: 可 JSON 序列化的字典
    """
```

---

## 更新日志

### v2.0.0 (2026-02-03)

- ✅ 新增流式响应功能
- ✅ 支持 SSE 和 WebSocket
- ✅ CLI 添加 `--stream` 选项
- ✅ 添加 StreamChunk 和 StreamingContext
- ✅ 添加 Gateway SSE 和 WebSocket 端点
- ✅ 添加完整测试和文档

---

## 相关文档

- **[ARCHITECTURE_V2_ROADMAP.md](ARCHITECTURE_V2_ROADMAP.md)** - V2 架构设计
- **[USAGE_GUIDE.md](docs/USAGE_GUIDE.md)** - 完整使用指南
- **[CLI_REFERENCE.md](docs/CLI_REFERENCE.md)** - CLI 命令参考（待更新）
