# FastReAct 工具清单 + 实时控制功能实现

> **日期**: 2026-01-30
> **主题**: 当前工具分析和实时控制功能实现

---

## 📦 FastReAct 当前工具清单

### 核心工具 (4 个)

| 工具 | 功能 | 文件 | 状态 |
|------|------|------|------|
| **CalculatorTool** | 数学计算 | `calculator.py` | ✅ 稳定 |
| **SearchTool** | 信息搜索 | `search.py` | ✅ 模拟实现 |
| **WeatherTool** | 天气查询 | `weather.py` | ✅ 需 API |
| **HTTPTool** | HTTP 请求 | `http.py` | ✅ 稳定 |

### 日期时间工具 (3 个)

| 工具 | 功能 | 文件 | 状态 |
|------|------|------|------|
| **GetCurrentTimeTool** | 获取当前时间 | `datetime_tool.py` | ✅ 稳定 |
| **GetDateInfoTool** | 日期信息 | `datetime_tool.py` | ✅ 稳定 |
| **DateTimeCalcTool** | 日期计算 | `datetime_tool.py` | ✅ 稳定 |

### 高级工具 (6 个)

| 工具 | 功能 | 文件 | 状态 |
|------|------|------|------|
| **TavilySearchTool** | Tavily 搜索 | `tavily.py` | ✅ 需 API Key |
| **GraphRAG 工具** | 知识图谱查询 | `graph_rag_tools.py` | ✅ 需配置 |
| **Python 工具** | Python 代码执行 | `python_tools.py` | ✅ 稳定 |
| **沙箱工具** | Docker 沙箱执行 | `sandbox.py` | ⚠️ 需 Docker |
| **MCP 适配器** | MCP 协议适配 | `mcp_adapter.py` | ✅ 稳定 |
| **MCP 客户端** | MCP 服务器连接 | `mcp_client_manager.py` | ✅ 稳定 |

---

## 🎯 实时控制思考过程功能

### 功能设计

**目标**: 让用户能够：
1. ✅ 实时看到 Agent 的思考过程
2. ✅ 看到工具调用的详细信息
3. ✅ 可以在执行过程中干预（可选）

### 实现方案

#### 步骤 1: 创建回调系统

```python
# src/fastreact/core/callbacks.py

"""
实时控制回调系统
"""

from typing import Callable, Dict, Any, Optional, AsyncIterator
from enum import Enum
import asyncio
from dataclasses import dataclass, field
import json

class Phase(Enum):
    """执行阶段"""
    THINK = "think"
    ACTION = "action"
    OBSERVATION = "observation"
    ANSWER = "answer"
    ERROR = "error"
    END = "end"


@dataclass
class StepEvent:
    """步骤事件"""
    phase: Phase
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "phase": self.phase.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class StreamingCallbacks:
    """流式回调管理器"""

    def __init__(
        self,
        on_thought: Optional[Callable[[str], Any]] = None,
        on_action: Optional[Callable[[Dict], Any]] = None,
        on_observation: Optional[Callable[[str], Any]] = None,
        on_answer_delta: Optional[Callable[[str], Any]] = None,
        on_tool_start: Optional[Callable[[str, Dict], Any]] = None,
        on_tool_end: Optional[Callable[[str, str, str], Any]] = None,
        on_error: Optional[Callable[[str], Any]] = None
    ):
        self.on_thought = on_thought
        self.on_action = on_action
        self.on_observation = on_observation
        self.on_answer_delta = on_answer_delta
        self.on_tool_start = on_tool_start
        self.on_tool_end = on_tool_end
        self.on_error = on_error

    async def emit(self, event: StepEvent):
        """发送事件"""
        if event.phase == Phase.THINK and self.on_thought:
            if asyncio.iscoroutinefunction(self.on_thought):
                await self.on_thought(event.content)
            else:
                self.on_thought(event.content)

        elif event.phase == Phase.ACTION and self.on_action:
            action_data = json.loads(event.content) if isinstance(event.content, str) else event.content
            if asyncio.iscoroutinefunction(self.on_action):
                await self.on_action(action_data)
            else:
                self.on_action(action_data)

        elif event.phase == Phase.OBSERVATION and self.on_observation:
            if asyncio.iscoroutinefunction(self.on_observation):
                await self.on_observation(event.content)
            else:
                self.on_observation(event.content)

        elif event.phase == Phase.ANSWER and self.on_answer_delta:
            if asyncio.iscoroutinefunction(self.on_answer_delta):
                await self.on_answer_delta(event.content)
            else:
                self.on_answer_delta(event.content)

        elif event.phase == Phase.ERROR and self.on_error:
            if asyncio.iscoroutinefunction(self.on_error):
                await self.on_error(event.content)
            else:
                self.on_error(event.content)

        # 工具特定事件
        if event.phase == Phase.ACTION:
            tool_name = event.metadata.get("tool_name")
            if tool_name and self.on_tool_start:
                if asyncio.iscoroutinefunction(self.on_tool_start):
                    await self.on_tool_start(tool_name, event.metadata)
                else:
                    self.on_tool_start(tool_name, event.metadata)

        if event.phase == Phase.OBSERVATION:
            tool_name = event.metadata.get("tool_name")
            if tool_name and self.on_tool_end:
                duration = event.metadata.get("duration", 0)
                if asyncio.iscoroutinefunction(self.on_tool_end):
                    await self.on_tool_end(tool_name, event.content, duration)
                else:
                    self.on_tool_end(tool_name, event.content, duration)
```

#### 步骤 2: 集成到 FastReAct

```python
# src/fastreact/core/engine.py (修改)

from .callbacks import StreamingCallbacks, Phase, StepEvent

class FastReAct:
    async def run_async_streaming(
        self,
        query: str,
        callbacks: Optional[StreamingCallbacks] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        运行 Agent（带实时控制）

        Args:
            query: 用户查询
            callbacks: 回调管理器

        Returns:
            执行结果
        """
        if callbacks is None:
            # 使用默认回调（打印到控制台）
            callbacks = StreamingCallbacks(
                on_thought=lambda s: print(f"🤔 {s}"),
                on_action=lambda a: print(f"🔧 工具: {a.get('tool_name')}"),
                on_observation=lambda o: print(f"📊 结果: {o[:100]}..."),
                on_answer_delta=lambda d: print(d, end="", flush=True),
                on_tool_start=lambda n, m: print(f"⏳ 开始执行 {n}"),
                on_tool_end=lambda n, r, d: print(f"✅ {n} 完成 (耗时 {d:.2f}s)")
            )

        history = []
        total_tokens = 0
        start_time = asyncio.get_event_loop().time()

        try:
            # 开始
            await callbacks.emit(StepEvent(
                phase=Phase.THINK,
                content=f"开始处理查询: {query}",
                metadata={"query": query}
            ))

            for iteration in range(self.max_iterations):
                # 思考阶段
                thought = await self._think(history)

                await callbacks.emit(StepEvent(
                    phase=Phase.THINK,
                    content=f"思考 {iteration + 1}: {thought}",
                    metadata={"iteration": iteration + 1}
                ))

                # 决策阶段
                action = await self._decide_action(thought)

                await callbacks.emit(StepEvent(
                    phase=Phase.ACTION,
                    content=json.dumps({
                        "tool_name": action.tool_name,
                        "parameters": action.parameters
                    }),
                    metadata={"tool_name": action.tool_name, "iteration": iteration + 1}
                ))

                if action.tool_name == "finish":
                    break

                # 执行阶段
                tool_start = asyncio.get_event_loop().time()

                try:
                    observation = await self._execute_tool(action)
                    duration = asyncio.get_event_loop().time() - tool_start

                    await callbacks.emit(StepEvent(
                        phase=Phase.OBSERVATION,
                        content=str(observation),
                        metadata={
                            "tool_name": action.tool_name,
                            "duration": duration,
                            "iteration": iteration + 1
                        }
                    ))

                    history.append({
                        "role": "assistant",
                        "content": f"Thought: {thought}\nAction: {action.tool_name}\nObservation: {observation}"
                    })

                except Exception as e:
                    await callbacks.emit(StepEvent(
                        phase=Phase.ERROR,
                        content=f"工具执行错误: {e}",
                        metadata={"tool_name": action.tool_name, "error": str(e)}
                    ))
                    raise

            # 生成回答
            answer = await self._generate_answer(history)

            await callbacks.emit(StepEvent(
                phase=Phase.ANSWER,
                content=answer,
                metadata={"iterations": iteration + 1}
            ))

            # 结束
            total_time = asyncio.get_event_loop().time() - start_time
            await callbacks.emit(StepEvent(
                phase=Phase.END,
                content="执行完成",
                metadata={
                    "total_time": total_time,
                    "iterations": iteration + 1
                }
            ))

            return {
                "answer": answer,
                "stats": {
                    "iterations": iteration + 1,
                    "total_time": total_time
                }
            }

        except Exception as e:
            await callbacks.emit(StepEvent(
                phase=Phase.ERROR,
                content=str(e),
                metadata={"error_type": type(e).__name__}
            ))
            raise
```

#### 步骤 3: 创建便捷 API

```python
# src/fastreact/core/api.py

"""
FastReAct 便捷 API
"""

from typing import Callable, Optional, Dict, Any
from .engine import FastReAct
from .callbacks import StreamingCallbacks

class FastReActStreaming(FastReAct):
    """支持流式输出的 FastReAct"""

    async def chat_streaming(
        self,
        message: str,
        on_thought: Optional[Callable[[str], Any]] = None,
        on_action: Optional[Callable[[Dict], Any]] = None,
        on_observation: Optional[Callable[[str], Any]] = None,
        on_delta: Optional[Callable[[str], Any]] = None
    ) -> str:
        """
        流式对话（简化版 API）

        Args:
            message: 用户消息
            on_thought: 思考回调
            on_action: 行动回调
            on_observation: 观察回调
            on_delta: 回复增量回调

        Returns:
            最终回答
        """
        callbacks = StreamingCallbacks(
            on_thought=on_thought,
            on_action=on_action,
            on_observation=on_observation,
            on_answer_delta=on_delta
        )

        result = await self.run_async_streaming(
            message,
            callbacks=callbacks
        )

        return result["answer"]
```

#### 步骤 4: 使用示例

```python
# examples/streaming_demo.py

import asyncio
from fastreact import FastReAct

async def demo():
    # 创建 Agent
    agent = FastReAct(
        api_key="your-api-key",
        tools=[CalculatorTool(), SearchTool()]
    )

    # 自定义回调
    async def on_thought(thought: str):
        print(f"\n🤔 思考: {thought}\n")

    async def on_action(action: dict):
        tool_name = action["tool_name"]
        params = action["parameters"]
        print(f"🔧 调用工具: {tool_name}")
        print(f"   参数: {params}\n")

    async def on_observation(observation: str):
        print(f"📊 观察结果: {observation[:200]}...\n")

    async def on_delta(delta: str):
        print(delta, end="", flush=True)

    # 运行
    print("=" * 60)
    print("FastReAct 实时控制演示")
    print("=" * 60)
    print()

    result = await agent.chat_streaming(
        "北京天气怎么样？然后计算 25 * 18",
        on_thought=on_thought,
        on_action=on_action,
        on_observation=on_observation,
        on_delta=on_delta
    )

    print()
    print("=" * 60)
    print(f"\n最终答案: {result}")

if __name__ == "__main__":
    asyncio.run(demo())
```

---

## 🚀 使用示例

### 示例 1: 基础流式输出

```python
from fastreact import FastReAct

agent = FastReAct(api_key="xxx")

# 启用流式思考
result = await agent.chat_streaming(
    "帮我计算 123 * 456",
    on_thought=lambda s: print(f"思考: {s}"),
    on_action=lambda a: print(f"工具: {a['tool_name']}")
)
```

### 示例 2: 详细事件监控

```python
from fastreact import FastReAct
from fastreact.core.callbacks import StreamingCallbacks, Phase
import json

async def detailed_callback(event):
    """详细事件处理"""
    if event.phase == Phase.THINK:
        print(f"[THOUGHT] {event.content}")

    elif event.phase == Phase.ACTION:
        action = json.loads(event.content)
        print(f"[ACTION] {action['tool_name']}")
        print(f"  参数: {action.get('parameters', {})}")

    elif event.phase == Phase.OBSERVATION:
        print(f"[RESULT] {event.content[:100]}...")

    elif event.phase == Phase.ERROR:
        print(f"[ERROR] {event.content}")

agent = FastReAct(api_key="xxx")
result = await agent.chat_streaming(
    "查询天气并计算温度",
    on_thought=detailed_callback,
    on_action=detailed_callback,
    on_observation=detailed_callback
)
```

### 示例 3: Web UI 集成

```python
from fastapi import FastAPI, WebSocket
from fastreact import FastReAct

app = FastAPI()
agent = FastReAct(api_key="xxx")

@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()

    async def send_thought(thought: str):
        await websocket.send_json({
            "type": "thought",
            "content": thought
        })

    async def send_action(action: dict):
        await websocket.send_json({
            "type": "action",
            "data": action
        })

    async def send_observation(observation: str):
        await websocket.send_json({
            "type": "observation",
            "content": observation
        })

    async def send_delta(delta: str):
        await websocket.send_json({
            "type": "delta",
            "content": delta
        })

    # 接收消息
    data = await websocket.receive_json()
    message = data["message"]

    # 运行 Agent
    result = await agent.chat_streaming(
        message,
        on_thought=send_thought,
        on_action=send_action,
        on_observation=send_observation,
        on_delta=send_delta
    )

    await websocket.send_json({
        "type": "done",
        "answer": result
    })
```

---

## 📊 输出示例

### 控制台输出示例

```
============================================================
FastReAct 实时控制演示
============================================================

🤔 思考: 我需要查询天气，然后进行数学计算

🔧 调用工具: search
   参数: {'query': '北京天气'}

⏳ 开始执行 search
✅ search 完成 (耗时 1.23s)

📊 观察结果: 北京今天晴，温度 15-25°C...

🤔 思考: 我已经知道天气了，现在需要计算 25 * 18

🔧 调用工具: calculator
   参数: {'expression': '25 * 18'}

⏳ 开始执行 calculator
✅ calculator 完成 (耗时 0.01s)

📊 观察结果: 450

🤔 思考: 我已经完成了所有任务，可以给出最终答案了

根据查询结果，北京今天晴，温度 15-25°C。计算结果 25 * 18 = 450。

============================================================

最终答案: 根据查询结果，北京今天晴，温度 15-25°C。计算结果 25 * 18 = 450。
```

### Web UI 输出示例

```json
{"type": "thought", "content": "我需要查询天气"}
{"type": "action", "data": {"tool_name": "search", "parameters": {...}}}
{"type": "observation", "content": "北京今天晴..."}
{"type": "thought", "content": "现在计算数学"}
{"type": "action", "data": {"tool_name": "calculator", "parameters": {...}}}
{"type": "delta", "content": "根据查询结果"}
{"type": "delta", "content": "北京今天晴"}
{"type": "delta", "content": "，计算结果"}
{"type": "delta", "content": " = 450"}
{"type": "done", "answer": "北京今天晴，温度 15-25°C。计算结果 25 * 18 = 450。"}
```

---

## 🎯 下一步

我可以帮你：

1. **立即实现** - 将上述代码集成到 FastReAct
   - 创建 `callbacks.py` 文件
   - 修改 `engine.py` 添加流式支持
   - 创建 `streaming_demo.py` 示例

2. **增强功能** - 添加更多特性
   - 保存思考历史到日志
   - 支持中断和恢复
   - 性能分析（每个步骤耗时）

3. **Web UI** - 创建完整的前端界面
   - React + FastAPI
   - 实时显示思考过程
   - 可视化工具调用

**你想从哪个开始？** 我建议先实现基础版本（步骤 1-4），然后根据需要增强功能。
