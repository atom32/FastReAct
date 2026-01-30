# FastReAct 架构文档

## 概述

FastReAct 是一个高性能的 ReACT (Reasoning + Acting) 框架，专注于多工具协同、安全执行和企业级可扩展性。

## 核心架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastReAct Core                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   ReACT      │────▶│   Tool       │────▶│   Executor   │    │
│  │   Engine     │     │   Manager    │     │   (Docker)   │    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│         │                     │                     │           │
│         ▼                     ▼                     ▼           │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   Event      │     │   Cache      │     │   Retry      │    │
│  │   Stream     │     │   (LRU)      │     │   Executor   │    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                        Integration Layer                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │    MCP      │  │   Gateway   │  │  Channels   │            │
│  │  Client     │  │ (WebSocket) │  │ (Multi)     │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                       Infrastructure                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Bootstrap  │  │   Config    │  │  Observ-    │            │
│  │   System    │  │   Manager   │  │  ability    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. ReACT 引擎 (Engine)

**位置**: `src/fastreact/core/engine.py`

**核心特性**:
- 异步并发工具调用
- 智能思考-行动循环
- 流式响应支持
- 连接池复用

**关键方法**:
```python
async def run_async(
    query: str,
    stream_callback: Optional[Callable] = None,
    step_callback: Optional[Callable] = None,
    session_context: Optional[Dict] = None
) -> Dict[str, Any]
```

**ReACT 循环流程**:
1. **Thought**: LLM 分析当前状态，决定下一步行动
2. **Action**: 选择并执行工具
3. **Observation**: 获取工具执行结果
4. **Iteration**: 重复直到得到最终答案

### 2. 工具系统 (Tools)

**位置**: `src/fastreact/tools/`

**工具类型**:

| 工具 | 文件 | 功能 |
|------|------|------|
| Calculator | `calculator.py` | 数学表达式计算 |
| DateTime | `datetime_tool.py` | 日期时间操作 |
| Sandbox | `sandbox_tools.py` | Docker 沙箱代码执行 |
| Tavily Search | `tavily.py` | AI 优化搜索 |
| MCP Adapter | `mcp_adapter.py` | MCP 服务器集成 |
| HTTP | `http.py` | HTTP 请求工具 |
| GraphRAG | `graph_rag_tools.py` | 知识图谱查询 |

**工具定义方式**:

#### 函数式定义 (推荐)
```python
from fastreact.tools.fn_registry import Tool

async def my_tool(param: str) -> str:
    """工具描述"""
    return f"结果: {param}"

return Tool(
    name="my_tool",
    label="My Tool",
    description="工具描述",
    parameters={...},
    execute=my_tool
)
```

#### 类式定义
```python
from fastreact.core.tool import Tool

class MyTool(Tool):
    async def execute_async(self, param: str) -> str:
        return f"结果: {param}"
```

### 3. 事件流系统 (Event Stream)

**位置**: `src/fastreact/observability/events.py`

**事件类型**:
- `LifecycleEvent`: 生命周期事件
- `AssistantEvent`: 助手事件
- `ToolEvent`: 工具事件
- `AgentEvent`: 代理事件

**使用示例**:
```python
async def handle_event(event: Event):
    if event.type == "tool_call":
        print(f"工具调用: {event.data}")

agent = FastReAct(
    event_callback=handle_event,
    enable_event_stream=True
)
```

### 4. 错误重试机制 (Retry)

**位置**: `src/fastreact/utils/resilience.py`

**重试策略**:
- 指数退避
- 最大重试次数
- 可重试/不可重试错误分类

**配置**:
```python
agent = FastReAct(
    max_tool_retries=3,
    enable_tool_retry=True
)
```

### 5. Bootstrap 配置系统

**位置**: `src/fastreact/bootstrap/`

**特性**:
- 自动加载工作区配置
- JSON 配置文件支持
- 环境变量覆盖
- 配置热重载

**目录结构**:
```
~/.fastreact/
├── config.json
├── tools/
│   ├── custom_tool.py
│   └── ...
└── prompts/
    ├── system_prompt.txt
    └── ...
```

### 6. Gateway 网关

**位置**: `src/fastreact/gateway/`

**功能**:
- WebSocket 实时通信
- 请求去重
- 认证授权
- 协议版本控制

**默认端口**: 18790

### 7. 多通道支持 (Channels)

**位置**: `src/fastreact/channels/`

**支持的通道**:
- WeChat (微信)
- Telegram
- Slack

**扩展方式**:
```python
from fastreact.channels.base import ChannelBase

class MyChannel(ChannelBase):
    async def send_message(self, message: str):
        # 实现发送逻辑
        pass
```

### 8. Docker 沙箱

**位置**: `src/fastreact/sandbox/docker.py`

**支持的语言**:
- Python 3.11
- JavaScript (Node.js 18)
- Bash 5.2
- Java 17

**安全特性**:
- 容器隔离
- 资源限制 (512MB 内存, 50% CPU)
- 关键词黑名单 (denylist)
- 超时控制

## 数据流

```
User Query
    │
    ▼
┌─────────────────┐
│   ReACT Engine  │
└────────┬────────┘
         │
         ├──▶ Thought (LLM 分析)
         │
         ├──▶ Tool Call (工具调用)
         │        │
         │        ├──▶ Executor (执行)
         │        │        │
         │        │        ├──▶ Success → Result
         │        │        │
         │        │        └──▶ Error → Retry
         │        │
         │        └──▶ Observation (结果)
         │
         ├──▶ Is Final? (完成判断)
         │        │
         │        ├──▶ No → Continue Loop
         │        │
         │        └──▶ Yes → Final Answer
         │
         └──▶ Response
                  │
                  ▼
            User Answer
```

## 并发模型

**异步并发工具调用**:
```python
# 同时调用多个工具
async def call_tools_concurrently():
    results = await asyncio.gather(
        tool1.execute(),
        tool2.execute(),
        tool3.execute()
    )
    return results
```

**最大并发数**: `max_concurrent_tools=3` (默认)

## 缓存策略

**LRU 缓存**:
- 默认大小: 1000 条
- 基于 query + tools 的缓存键
- TTL: 可配置

**配置**:
```python
agent = FastReAct(
    enable_cache=True,
    cache_size=1000
)
```

## 去重机制

**请求去重**:
- 时间窗口: 10 秒 (默认)
- 基于 query 的指纹
- 自动过滤重复请求

**配置**:
```python
agent = FastReAct(
    enable_deduplication=True,
    dedup_window_seconds=10.0
)
```

## 配置管理

**配置文件结构**:
```json
{
  "llm": {
    "providers": {
      "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key": "...",
        "model": "deepseek-ai/DeepSeek-V3"
      }
    },
    "default_provider": "siliconflow"
  },
  "react": {
    "max_iterations": 10,
    "max_concurrent_tools": 3,
    "enable_cache": true,
    "enable_streaming": false
  },
  "tools": {
    "builtin_enabled": true,
    "available_tools": ["Calculator", "DateTime", "Sandbox"]
  }
}
```

## 扩展点

### 1. 自定义工具

```python
from fastreact.tools.fn_registry import Tool

async def custom_tool(input: str) -> str:
    """自定义工具逻辑"""
    return f"处理: {input}"

tool = Tool(
    name="custom_tool",
    label="Custom Tool",
    description="工具描述",
    parameters={
        "type": "object",
        "properties": {
            "input": {"type": "string"}
        }
    },
    execute=custom_tool
)
```

### 2. 事件处理器

```python
async def my_event_handler(event):
    if event.type == "tool_call":
        print(f"工具调用: {event.tool_name}")
    elif event.type == "error":
        print(f"错误: {event.error}")

agent = FastReAct(
    event_callback=my_event_handler
)
```

### 3. 自定义通道

```python
from fastreact.channels.base import ChannelBase

class CustomChannel(ChannelBase):
    async def send_message(self, message: str):
        # 发送消息到自定义平台
        pass

    async def receive_message(self) -> str:
        # 接收消息
        pass
```

## 性能优化

1. **连接池复用**: httpx.AsyncClient
2. **LRU 缓存**: 减少重复计算
3. **并发执行**: 多工具并行调用
4. **请求去重**: 避免重复处理
5. **流式响应**: 实时输出

## 安全特性

1. **Docker 沙箱**: 隔离代码执行
2. **关键词过滤**: denylist 保护
3. **资源限制**: 防止资源耗尽
4. **超时控制**: 避免无限等待
5. **错误重试**: 智能容错

## 监控和可观测性

**事件流**: 实时监控所有操作
**统计信息**: 工具调用次数、缓存命中率、平均响应时间
**日志记录**: 结构化日志输出

## 测试覆盖

- 单元测试: 核心组件
- 集成测试: 工具系统
- E2E 测试: 完整流程
- 性能测试: 并发和缓存

**测试结果**: 7/7 测试通过 (100%)

## 未来规划

- [ ] 更多 LLM 提供商支持
- [ ] 分布式缓存 (Redis)
- [ ] 更多沙箱语言
- [ ] 工具市场
- [ ] 可视化配置界面
