# moltbot vs nano: Steering Architecture Comparison

## Executive Summary

| Dimension | moltbot | nano (当前) | nano (方案 B) |
|-----------|---------|-------------|---------------|
| **Steering 接口** | Callback | ❌ 无 | ✅ inject_message() |
| **Follow-up 支持** | Callback | ❌ 未实现 | ⚠️ 需要添加 |
| **消息队列** | 数组赋值 | ✅ MessageQueue | ✅ MessageQueue |
| **推送模式** | ❌ 轮询 (Callback) | ✅ push() | ✅ push() |
| **多源合并** | ❌ 单一 Callback | ❌ 无 | ✅ SteeringManager |

## moltbot 核心逻辑分析

```javascript
// 外层循环：处理后续消息队列
while (true) {
    let hasMoreToolCalls = true;
    let steeringAfterTools: AgentMessage[] | null = null;

    // 内层循环：处理工具调用和转向消息
    while (hasMoreToolCalls || pendingMessages.length > 0) {
        // 1. 处理待处理消息（用户新输入或转向消息）
        if (pendingMessages.length > 0) {
            for (const message of pendingMessages) {
                currentContext.messages.push(message);
            }
            pendingMessages = [];
        }

        // 2. 调用LLM获取响应
        const message = await streamAssistantResponse(currentContext, config, signal, stream);

        // 3. 检查是否有工具调用
        const toolCalls = message.content.filter((c) => c.type === "toolCall");
        hasMoreToolCalls = toolCalls.length > 0;

        // 4. 执行工具调用
        if (hasMoreToolCalls) {
            const toolExecution = await executeToolCalls(
                currentContext.tools,
                message,
                signal,
                stream,
                config.getSteeringMessages  // ← Callback 注入点
            );
            for (const result of toolExecution.toolResults) {
                currentContext.messages.push(result);
            }
        }

        // 5. 检查转向消息（实时干预）
        pendingMessages = (await config.getSteeringMessages?.()) || [];
    }

    // 6. 检查后续消息队列
    const followUpMessages = (await config.getFollowUpMessages?.()) || [];
    if (followUpMessages.length > 0) {
        pendingMessages = followUpMessages;
        continue; // 继续外层循环
    }
    break; // 没有更多消息，结束
}
```

### 关键特征

1. **Callback 模式**：
   - `config.getSteeringMessages()` - 获取实时干预
   - `config.getFollowUpMessages()` - 获取后续消息

2. **两次检查点**：
   - 内层循环结束时检查 steering
   - 外层循环开始时检查 follow-up

3. **数组赋值清空**：
   ```javascript
   pendingMessages = [];  // 直接赋值清空
   ```

## nano 当前架构

```python
# react.py:110-344

pending_messages = MessageQueue()  # ← 局部变量，无法外部访问

try:
    # === Outer loop: Process follow-up messages ===
    while True:
        has_more_tool_calls = True

        # === Inner loop: Process tools ===
        while has_more_tool_calls or pending_messages:
            # 1. Process pending messages
            if pending_messages:
                for msg in pending_messages.drain():
                    messages.append(msg.to_llm_format())

            # 2. Build messages for LLM
            # ...

            # 3. Call LLM
            response = await self._llm.chat(...)

            # 4. Stream thinking content
            if response.content:
                yield AgentEvent.think(response.content, session_id)

            # 5. Check for tool calls
            has_more_tool_calls = len(response.tool_calls) > 0

            # 6. Execute tools
            if has_more_tool_calls:
                for tool_call in response.tool_calls:
                    yield AgentEvent.tool_call(...)
                    # Execute tool...
                    yield AgentEvent.tool_result(...)

            # No tool calls - add assistant response
            else:
                messages.append(assistant_msg)

        # 7. 内层循环结束，直接 break
        # No more tool calls and no pending messages, break
        break  # ← 没有检查 follow-up

    # 8. 提取最终答案，结束
    final_answer = ""
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            final_answer = msg.get("content", "")
            break

    yield AgentEvent.session_end(session_id, final_answer)
```

### 问题

1. **pending_messages 是局部变量** - 外部无法访问
2. **无 steering 接口** - 没有注入消息的入口
3. **外层循环无用** - 没有 follow-up 检查
4. **无多源合并** - 无法同时处理 WebSocket + HTTP + CLI

## nano 方案 B 实现

### 架构改动

```
┌─────────────────────────────────────────────────────────┐
│                   Adapter Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │WebSocket │  │   HTTP   │  │   CLI    │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │             │             │                    │
│       └─────────────┴─────────────┴──────┬────────────┘
│                                            │ steer()     │
┌───────────────────────────────────────────▼────────────┘
│              SteeringManager                    │
│  - register_source(name, priority)              │
│  - inject(session_id, source, content)          │
│  - get_messages(session_id) -> List[Message]   │
└───────────────────────────────────────────┬────────────┘
│                                            │ get_messages()│
┌───────────────────────────────────────────▼────────────┐
│                   Agent Layer                     │
│  - inject_message(session_id, message)             │
└───────────────────────────────────────────┬────────────┘
│                                            │ delegates  │
┌───────────────────────────────────────────▼────────────┐
│                    ReActCore                        │
│  - _session_queues: Dict[str, MessageQueue]         │
│  - inject_message(session_id, message)              │
│  - run_event_stream(..., check_interval: float)     │
└──────────────────────────────────────────────────────┘
```

### 核心代码改动

#### 1. ReActCore 添加注入接口

```python
# react.py

class ReActCore:
    def __init__(self, ...):
        # ... existing code ...

        # NEW: Session queues for steering
        self._session_queues: dict[str, MessageQueue] = {}

    def inject_message(self, session_id: str, message: Message):
        """
        Inject message into active session

        Args:
            session_id: Target session
            message: Message to inject (steering/followup)

        Raises:
            ValueError: If session not active
        """
        if session_id not in self._session_queues:
            raise ValueError(f"Session not active: {session_id}")

        self._session_queues[session_id].push(message)

    async def run_event_stream(
        self,
        query: str,
        session_id: str,
        history: Optional[list[dict]] = None,
        check_interval: float = 0.1,  # NEW: Check steering interval
    ):
        """
        Run ReAct loop with steering support

        Args:
            query: User query
            session_id: Session identifier
            history: Optional conversation history
            check_interval: How often to check for steering (seconds)
        """
        from fastreact.core.events import AgentEvent, EventType

        # NEW: Create session queue
        self._session_queues[session_id] = MessageQueue()
        pending_messages = self._session_queues[session_id]

        # Track session for cleanup
        session_active = True

        try:
            yield AgentEvent.session_start(query, session_id)

            messages = list(history or [])
            messages.append(Message.user(query).to_llm_format())

            # === Outer loop: Process follow-up messages ===
            while True:
                has_more_tool_calls = True

                # === Inner loop: Process tools ===
                while has_more_tool_calls or pending_messages:
                    # 1. Process pending messages (steering/followup)
                    if pending_messages:
                        for msg in pending_messages.drain():
                            messages.append(msg.to_llm_format())
                            # Emit steering event for visibility
                            if msg.role in ("steering", "followup"):
                                yield AgentEvent.think(
                                    f"[{msg.role.upper()}] {msg.content}",
                                    session_id,
                                    metadata={"source": msg.metadata.get("source", "unknown")}
                                )

                    # 2. Build messages for LLM
                    # ... existing code ...

                    # 3. Call LLM
                    # ... existing code ...

                    # 4. Execute tools
                    # ... existing code ...

                    # 5. Check for steering (NEW)
                    # Note: Already checked in pending_messages above

                    # 6. Check for follow-up (NEW)
                    if not has_more_tool_calls:
                        await asyncio.sleep(check_interval)
                        if pending_messages:
                            # Got follow-up messages, continue inner loop
                            continue

                # 7. No more tool calls and no pending messages
                # Check one more time for follow-up before exiting
                await asyncio.sleep(check_interval)
                if pending_messages:
                    # Got follow-up messages, continue outer loop
                    continue

                # 8. Really done, break
                break

            # Extract final answer
            final_answer = ""
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    final_answer = msg.get("content", "")
                    break

            yield AgentEvent.session_end(session_id, final_answer)

        finally:
            # Cleanup session queue
            if session_id in self._session_queues:
                del self._session_queues[session_id]
```

#### 2. Agent 层包装

```python
# agent.py

class Agent:
    def inject_message(self, session_id: str, message: Message):
        """
        Inject steering message into active session

        Args:
            session_id: Target session ID
            message: Message to inject

        Example:
            agent = Agent()
            task = asyncio.create_task(
                agent.run_event_stream("分析代码", "session-123")
            )

            # Later, inject steering
            agent.inject_message(
                "session-123",
                Message.steering("不对，先看 README")
            )
        """
        self._core.inject_message(session_id, message)
```

#### 3. SteeringManager (多源支持)

```python
# steering.py

class SteeringManager:
    """
    Manages multiple steering sources

    Sources:
    - WebSocket from web UI
    - HTTP endpoint from monitoring
    - CLI input from terminal
    - Test harness

    Priority: Higher priority sources processed first
    """

    def __init__(self):
        self._sources: dict[str, asyncio.Queue] = {}
        self._session_queues: dict[str, dict[str, asyncio.Queue]] = defaultdict(
            lambda: defaultdict(asyncio.Queue)
        )

    def register_source(self, name: str, priority: int = 0) -> asyncio.Queue:
        """Register a steering source, returns queue for injecting"""
        queue = asyncio.Queue()
        self._sources[name] = queue
        return queue

    async def get_messages(self, session_id: str) -> list[Message]:
        """Get all pending steering messages for session"""
        if session_id not in self._session_queues:
            return []

        messages = []
        for source_name, queue in self._sources.items():
            session_queue = self._session_queues[session_id][source_name]

            # Drain all messages from this source
            while not session_queue.empty():
                try:
                    content, metadata = session_queue.get_nowait()
                    messages.append(Message.steering(content, **metadata))
                except asyncio.QueueEmpty:
                    break

        # Sort by priority
        messages.sort(key=lambda m: m.metadata.get("priority", 0), reverse=True)
        return messages
```

## 使用示例对比

### moltbot 风格

```javascript
// 配置时注册回调
const config = {
    getSteeringMessages: async () => {
        // 从 WebSocket 获取消息
        return await wsClient.getSteeringMessages();
    },
    getFollowUpMessages: async () => {
        // 从任务队列获取消息
        return await taskQueue.getFollowUpMessages();
    }
};

// Agent 自动调用回调
const response = await agent.run(query, config);
```

### nano 方案 B 风格

```python
# 1. 注册 steering 源
manager = SteeringManager()
ws_queue = manager.register_source("websocket", priority=10)

# 2. 启动 agent
agent = Agent()
task = asyncio.create_task(
    agent.run_event_stream("分析代码", "session-123")
)

# 3. 从 WebSocket 注入消息
async def websocket_handler():
    while True:
        msg = await websocket.receive()
        if msg.type == "steering":
            await manager.inject("session-123", "websocket", msg.content)

# 4. 或者直接注入
agent.inject_message("session-123", Message.steering("不对，先看 README"))
```

## 架构优劣对比

### Callback (moltbot)

**优点**：
- ✅ 简单直接
- ✅ 配置时注册，运行时自动调用
- ✅ 适合单一消息源

**缺点**：
- ❌ 被动轮询（每次 LLM 调用前检查）
- ❌ 单一消息源（难以支持多源）
- ❌ 无法主动推送（依赖 Core 主动调用）
- ❌ 优先级控制困难（需要 callback 内部排序）

### Push (nano 方案 B)

**优点**：
- ✅ 主动推送（有消息立即注入）
- ✅ 多源支持（WebSocket + HTTP + CLI）
- ✅ 优先级控制（按 priority 排序）
- ✅ 更符合异步编程直觉
- ✅ 易于测试（直接调用 inject）

**缺点**：
- ❌ 稍复杂（需要管理队列）
- ❌ 需要轮询检查（check_interval）

## 总结

### moltbot 的优势

1. **简单直接** - Callback 模式容易理解
2. **自动调用** - 不需要外部管理

### nano 的优势

1. **MessageQueue 更优雅** - 专门的队列类
2. **Event 流更完善** - 统一的事件协议
3. **多源支持** - 可以同时处理多个输入源
4. **推送模式** - 更主动，更灵活

### 建议

nano 应该采用 **方案 B (Expose MessageQueue)**，但要注意：

1. **添加 check_interval** - 定期检查新消息
2. **优先级控制** - 不同消息源可以设置优先级
3. **Session 生命周期** - 自动清理队列
4. **向后兼容** - steering 是可选功能

这样既保持了 nano 的架构优势，又实现了 moltbot 的 steering 能力。
