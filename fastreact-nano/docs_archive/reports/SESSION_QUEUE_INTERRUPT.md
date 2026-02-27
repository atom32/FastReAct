# Session Queue Interrupt Implementation

## 概述

实现了 Gateway 的会话中断机制，允许用户在 Agent 执行过程中发送新的查询，Agent 会立即中断当前执行并处理新查询。

## 问题

**之前的行为**：
- 用户的查询按 FIFO 顺序在 `_message_queue` 中排队
- Agent 执行是阻塞的，必须完全完成后才能处理下一个查询
- 如果 Agent 正在执行第一个查询（需要 30 秒），用户发送的第二个查询会等待 30 秒

**期望的行为**：
- 用户可以在 Agent 执行过程中随时发送新查询
- Agent 收到新查询后立即中断当前执行
- Agent 开始处理新的查询

## 解决方案

### 架构设计

```
Gateway Session
    ├─ _message_queue (asyncio.Queue)  ← 存储 WebSocket 接收的消息
    ├─ _is_running (bool)               ← 追踪 Agent 运行状态
    └─ agent._session_queues (dict)    ← Agent 内部的消息队列

消息处理流程：
    WebSocket 消息 → enqueue_message() → _message_queue
                                              ↓
                                        process_queue()
                                              ↓
                                        _handle_message()
                                              ↓
                                        检查 _is_running？
                                              ├─ True  → 发送 [INTERRUPT] 到 session_queues
                                              └─ False → 正常启动 run_event_stream()
```

### 关键修改

#### 1. Session.__init__()

```python
# 添加运行状态追踪
self._is_running = False

# 初始化 session queue
from fastreact.core.messages import MessageQueue
if session_id not in self.agent._session_queues:
    self.agent._session_queues[session_id] = MessageQueue()
```

#### 2. Session._handle_message()

```python
elif msg_type == "query":
    query = message.get("content", "")

    # 检查 Agent 是否正在运行
    if self._is_running:
        # Agent 正在运行，发送中断信号
        self.agent._session_queues[self.session_id].push(
            Message.steering(
                f"[INTERRUPT] 用户有新请求: {query}",
                metadata={"source": "gateway", "new_query": query}
            )
        )

        # 通知用户
        await self.send({
            "type": "info",
            "content": f"[中断] 正在处理新请求: {query[:50]}",
        })
        return  # ← 立即返回，不阻塞

    # Agent 空闲，正常启动
    self._is_running = True
    try:
        async for event in self.agent.run_event_stream(...):
            # 处理事件...
    finally:
        self._is_running = False  # ← 总是重置状态
```

### Agent 内部处理

Agent 的 `run_event_stream()` 已经内置了中断处理：

```python
# 每个 iteration 检查 session_queues
pending_messages = self._session_queues.get(session_id, MessageQueue())

if pending_messages:
    for msg in pending_messages.drain():
        if msg.content.startswith("[INTERRUPT]"):
            # 停止当前执行
            interrupted = True
            has_more_tool_calls = False
            break
```

## 使用场景

### 场景 1：用户纠正

```
用户: "分析整个代码库"
  ↓
Agent: 开始执行（ls -R, find, cat...）
  ↓
用户: "等等！只看 src/ 目录"
  ↓
Gateway: 发送 [INTERRUPT] 到 session_queues
  ↓
Agent: 收到中断，停止当前执行
  ↓
Agent: 重新开始处理 "只看 src/ 目录"
```

### 场景 2：优先级任务

```
用户: "运行所有测试（需要 10 分钟）"
  ↓
Agent: 开始执行测试
  ↓
用户: "紧急！检查生产服务器日志"
  ↓
Gateway: 发送 [INTERRUPT] + 新查询
  ↓
Agent: 立即中断测试，开始处理日志查询
```

## 技术细节

### 消息优先级

```
优先级从高到低：

1. [INTERRUPT] 消息（通过 session_queues）
   - 立即中断当前执行
   - 优先级最高

2. Control 消息（通过 _message_queue）
   - 绕过队列限制
   - 直接处理

3. Query 消息（通过 _message_queue）
   - 如果 Agent 空闲：立即执行
   - 如果 Agent 忙：转换为 [INTERRUPT]
```

### 状态管理

```python
_is_running = False  # 初始状态

收到新查询时：
    if _is_running:
        # 转换为 INTERRUPT
        发送到 session_queues
    else:
        # 正常执行
        _is_running = True
        try:
            执行 Agent
        finally:
            _is_running = False  # ← 确保重置
```

## 测试

### 单元测试

```python
# 测试 Session 状态管理
session = Session('test-id', websocket)
assert session._is_running == False

# 模拟 Agent 运行中收到新查询
session._is_running = True
session._handle_message({"type": "query", "content": "新查询"})

# 验证 INTERRUPT 被发送到 session_queues
assert len(session.agent._session_queues['test-id']) > 0
```

### 集成测试

```bash
# 运行中断测试
python3 /tmp/test_interrupt_simple.py

# 预期输出：
# ✅ 检测到中断信号
# ✅ 测试通过：中断机制正常工作
```

## 限制和注意事项

### 1. 非抢占式中断

- 中断不是立即的，而是 **协作式** 的
- Agent 只在 **下一个 iteration** 检查 session_queues
- 如果 Agent 正在执行一个耗时的 tool（如 30 秒的 HTTP 请求），中断会等待 tool 完成

### 2. Tool 状态

- 中断后，已经执行的 tool 结果不会被回滚
- History 包含中断前的 tool 执行结果
- 新查询会基于之前的结果继续

### 3. 多用户隔离

- 当前实现：单租户模式（Gateway）
- 每个用户的 session 是独立的
- 用户的 `_is_running` 状态不影响其他用户

## 未来改进

### 1. 立即中断（抢占式）

```python
# 使用 asyncio.Task.cancel()
task = asyncio.create_task(agent.run_event_stream(...))
if new_query:
    task.cancel()  # 立即取消
```

### 2. 中断点

```python
# 在 tool 执行前检查中断
if self._interrupted:
    raise InterruptedError()

result = await tool.execute(...)
```

### 3. 中断恢复

```python
# 保存执行状态
state = agent.save_state()

# 中断...

# 恢复执行
agent.restore_state(state)
```

## 相关文件

- `/Users/xudawei/FastReAct/fastreact-nano/src/fastreact/adapters/gateway.py`
  - `Session.__init__()`: 初始化 session_queues
  - `Session._handle_message()`: 实现中断逻辑
  - `Session._is_running`: 追踪 Agent 状态

- `/Users/xudawei/FastReAct/fastreact-nano/src/fastreact/agent.py`
  - `Agent.run_event_stream()`: 检查 session_queues 中的中断

- `/Users/xudawei/FastReAct/fastreact-nano/src/fastreact/core/messages.py`
  - `Message.steering()`: 创建 steering 消息
  - `MessageQueue`: 消息队列实现

## 测试脚本

- `/tmp/test_interrupt.py` - WebSocket 中断测试
- `/tmp/test_interrupt_simple.py` - 单元测试
