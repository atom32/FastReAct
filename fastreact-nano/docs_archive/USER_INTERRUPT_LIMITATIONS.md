# 用户中断功能的限制与改进

**日期**: 2025-03-04
**问题**: 用户发送"停止"指令后，Agent 不会立即停止

---

## 问题分析

### 当前行为

从实际测试日志可以看到：

```
[FEISHU] Received message: 停止
[INFO] Injecting into running session
[DEBUG] Pushing intervention message to queue
[TOOL] Calling graphrag_get_entity  ← 继续执行工具
[TOOL] Calling graphrag_query_relationships  ← 继续执行工具
[DEBUG] Tool checkpoint processing: role=steering, content=停止  ← 工具完成后才处理
```

**问题**：
1. 用户发送"停止"消息
2. 消息被放入队列（`Pushing intervention message to queue`）
3. **Agent 继续执行当前的工具调用**（阻塞操作）
4. 工具执行完成后才处理队列中的"停止"消息

### 根本原因

#### 1. 队列机制 vs 立即中断

**当前实现**：
```python
# 用户消息进入队列
await self._message_queue.put(message)

# Agent 在每次迭代开始时检查队列
message = await self._message_queue.get()
```

**问题**：如果 Agent 正在执行工具调用（这是阻塞的），不会立即检查队列。

#### 2. 中断标志检查频率

**当前实现**：
```python
# 只在每次事件迭代开始时检查中断
for agent_event in self.agent.run_or_inject(...):
    if self._interrupted:
        break
    # 处理事件...
```

**问题**：如果正在执行 `async for agent_event` 循环，而 Agent 正在调用工具（阻塞操作），不会立即检查中断标志。

#### 3. 工具调用是阻塞操作

**当前实现**：
```python
# Agent 内部调用工具
result = await tool.execute(**args)  # 阻塞直到完成
```

**问题**：即使设置了 `_interrupted` 标志，正在执行的工具调用也不会立即取消。

---

## 已实施的改进

### ✅ 飞书 SDK：停止关键词识别

**文件**: `src/fastreact/adapters/feishu_sdk.py`

**改进内容**：
```python
# 识别停止关键词
stop_keywords = ["停下", "停止", "stop", "cancel", "取消", "中断"]
if content.lower().strip() in [kw.lower() for kw in stop_keywords]:
    # 立即中断所有活动会话
    user_sessions = self.agent.list_sessions(user_key=user_key)
    for session_info in user_sessions:
        if session_info.get("status") == "running":
            session = self.agent.get_session(session_info["session_id"])
            session.interrupt()  # 设置中断标志
```

**效果**：
- ✅ 立即识别停止指令
- ✅ 不将停止消息放入队列
- ✅ 立即设置会话的中断标志
- ⚠️  **但不能立即取消正在执行的工具调用**

---

## 限制说明

### 1. 工具调用无法立即取消

**原因**：
- Python 异步函数一旦开始执行，无法从外部强制取消
- 必须等待函数完成或自行检查中断标志

**影响**：
- 如果 Agent 正在调用 MCP 工具（如 `graphrag_search_graph`）
- 即使收到"停止"指令，工具调用也会完成
- 然后才会检查中断标志并停止

**典型场景**：
```
时间线：
t=0s: 用户发送"用知识图谱查询机器学习"
t=1s: Agent 开始调用 graphrag_search_graph
t=2s: 用户发送"停止"
t=3s: 设置中断标志 ✅
t=5s: graphrag_search_graph 完成（继续执行） ❌
t=6s: 检查中断标志，停止循环 ✅
```

### 2. 中断检查点有限

**当前中断检查点**：
1. 每次事件迭代开始（`for agent_event in ...`）
2. 每次 ReAct 循环开始

**不在检查点**：
- 工具调用执行过程中
- LLM API 调用过程中
- 消息队列处理过程中

### 3. 队列积压问题

**场景**：
```
1. Agent 正在执行（调用工具）
2. 用户发送"停止" → 放入队列
3. 用户发送"你好" → 放入队列
4. 工具执行完成，处理队列
5. 先处理"停止"，但工具已经完成
6. 再处理"你好"，继续执行
```

**结果**："停止"指令被队列延迟，加上后续消息干扰，导致停止不彻底。

---

## 解决方案

### 方案 1：更频繁的中断检查（部分解决）

**实现**：
在 Agent 的事件循环中，每次事件处理后都检查中断标志。

**代码位置**: `src/fastreact/core/session.py:415`

**当前**:
```python
for agent_event in self.agent.run_or_inject(...):
    if self._interrupted:
        break
    # 处理事件...
```

**改进**:
```python
for agent_event in self.agent.run_or_inject(...):
    # 每次事件后都检查
    if self._interrupted:
        break

    # 处理事件
    await on_event(...)

    # 处理后再次检查
    if self._interrupted:
        break
```

**效果**：稍微快一点，但仍然无法中断正在执行的工具调用。

### 方案 2：工具超时机制（推荐）

**实现**：
为每个工具调用设置超时，超时后自动中断。

**代码示例**:
```python
import asyncio

try:
    # 设置 5 秒超时
    result = await asyncio.wait_for(
        tool.execute(**args),
        timeout=5.0
    )
except asyncio.TimeoutError:
    # 超时后中断
    self._interrupted = True
```

**效果**：
- ✅ 可以限制工具执行时间
- ✅ 超时后立即停止
- ❌ 但需要为每个工具设置合理的超时时间

### 方案 3：会话级别的任务取消（最佳）

**实现**：
在会话级别维护后台任务的引用，收到停止指令时直接取消任务。

**代码示例**:
```python
class AgentSession:
    def __init__(self, ...):
        self._current_task: Optional[asyncio.Task] = None

    async def process_query(self, query):
        self._current_task = asyncio.current_task()

        try:
            # 执行查询
            async for event in self.agent.run_or_inject(...):
                ...
        except asyncio.CancelledError:
            # 任务被取消
            return

    def interrupt(self):
        """立即取消当前任务"""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
        self._interrupted = True
```

**效果**：
- ✅ 立即取消后台任务
- ✅ 不需要等待工具完成
- ✅ 真正的立即中断

---

## 临时解决方案

### 对用户：明确停止时机

**建议用户**：
1. **等待工具调用完成后再发送停止**
   - 看到 `🔧 正在调用工具: xxx` 时等待
   - 看到 `📊 工具结果: xxx` 时立即发送停止

2. **使用明确的停止指令**
   - "停下" / "停止" / "cancel"
   - 避免使用模糊的表达

3. **如果停止不彻底，再发一次**
   - 第一次停止：中断当前循环
   - 第二次停止：中断新启动的循环

### 对开发：添加状态提示

**实现**：
在 Agent 执行过程中，定期发送状态更新。

**代码**:
```python
async def _process_agent_stream(...):
    await self._send_text_message(chat_id, "⏳ 正在执行...")

    for event in agent.run_or_inject(...):
        # 每次工具调用后发送状态
        if event.type == EventType.TOOL_RESULT:
            await self._send_text_message(
                chat_id,
                "✅ 工具执行完成，可以发送停止指令"
            )
```

**效果**：用户知道何时可以安全地发送停止指令。

---

## 未来改进方向

### 1. 实现真正的异步任务取消

- 使用 `asyncio.Task.cancel()` 机制
- 在工具调用中添加协程式检查点
- 支持 `CancelledError` 异常处理

### 2. 添加工具调用超时

- 为每个 MCP 工具设置超时时间
- 超时后自动中断并回滚
- 防止长时间运行的工具阻塞

### 3. 优化队列优先级

- Control 消息优先级最高
- 使用优先级队列而不是 FIFO
- 确保停止指令立即处理

### 4. 用户界面改进

- 添加"停止"按钮（前端）
- 显示当前执行状态
- 允许用户撤销停止指令

---

## 总结

### 当前状态

| 功能 | 状态 | 说明 |
|------|------|------|
| **停止关键词识别** | ✅ 已实现 | 立即识别"停下"、"停止"等 |
| **设置中断标志** | ✅ 已实现 | 立即设置 `_interrupted` |
| **中断检查** | ⚠️  部分实现 | 只在循环开始时检查 |
| **立即停止工具调用** | ❌ 未实现 | 工具调用无法取消 |
| **任务取消机制** | ❌ 未实现 | 后台任务无法取消 |

### 用户体验

- **理想情况**：发送停止 → 立即停止（< 100ms）
- **当前情况**：发送停止 → 等待工具完成 → 停止（1-5 秒）
- **改进后预期**：发送停止 → 取消任务 → 停止（< 500ms）

### 技术难点

1. **Python 异步函数无法强制取消**
2. **工具调用是黑盒操作**
3. **中断检查点有限**

### 推荐方案

1. **短期**：添加工具调用超时（方案 2）
2. **中期**：实现任务取消机制（方案 3）
3. **长期**：重构为协程式检查点

---

**文档作者**: Claude (FastReAct Team)
**最后更新**: 2025-03-04
**版本**: v2.4.2
