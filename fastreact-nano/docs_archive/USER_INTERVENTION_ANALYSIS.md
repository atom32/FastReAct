# 用户干预机制分析与改进

**日期**: 2025-03-04
**核心原则**: 不硬编码用户输入，所有输入都应能立即生效

---

## 当前干预机制分析

### 系统已有的干预机制

从 `src/fastreact/agent.py` 可以看到系统已经有完整的干预机制：

#### 1. 工具调用前检查点（line 1422-1463）

```python
# User input checkpoint: check for pending messages before tool execution
pending = self._session_queues.get(session_id, MessageQueue())
if pending:
    for msg in pending.drain():
        if msg.role == "steering":
            # 用户干预：跳过工具执行
            yield AgentEvent.think(f"[USER INTERVENTION] {msg.content}", ...)
            has_more_tool_calls = False
            break
```

#### 2. Inner Loop 开始检查点（line 1269-1334）

```python
# Process pending messages (steering/interrupt/followup)
if pending_messages:
    for msg in pending_messages.drain():
        if msg.role == "steering":
            messages.append({
                "role": "user",
                "content": f"[USER INTERVENTION]: {msg.content}"
            })
            # 继续执行，不设置中断标志
            break
```

#### 3. 队列机制

- 用户的任何输入都会作为 `steering` 消息进入队列
- 队列在每次检查点被清空（`drain()`）
- `steering` 消息被添加到 LLM 上下文，影响后续决策

---

## 问题分析

### 从日志看到的执行流程

```
[TOOL] Calling graphrag_get_entity        ← 工具 1 开始执行
                                            ← 用户发送"停止"（消息进入队列）
[TOOL] Calling graphrag_query_relationships  ← 工具 2 开始执行
[DEBUG] Tool execution checkpoint: found 2 messages  ← 在工具 2 之前检查队列
[DEBUG] Tool checkpoint processing: role=steering, content=停止
[THINK] [USER INTERVENTION] 停下...        ← 干预生效！
[DEBUG] Tools executed in this iteration, will continue to next iteration
                                            ← 进入下一次 inner loop
[DEBUG] Inner loop start: queue has 1 messages
[MESSAGE_QUEUE] drain() called, returning 1 messages
[DEBUG] Processing message: role=steering, content=你好  ← 处理"你好"
```

### 关键发现

1. ✅ **干预机制已经工作**
   - 工具执行检查点（line 1422）已经捕获到"停止"消息
   - 正确处理为 `[USER INTERVENTION]`
   - 跳过了后续工具执行

2. ❌ **但时机不够理想**
   - 用户在工具 1 执行期间发送"停止"
   - 工具 1 无法中断（阻塞操作）
   - 工具 2 开始前的检查点才处理"停止"
   - 实际上工具 2 也被跳过了（干预生效）

3. ⚠️  **工具执行后缺少检查**
   - 工具执行完成后（line 1490）
   - 只设置了 `executed_tools_this_iteration = True`
   - **没有立即检查队列**
   - 导致延迟到下一次 inner loop 才处理新消息

---

## 根本限制

### Python 异步函数无法中断

```python
result = await self._tools.execute(...)  # 阻塞直到完成
```

**问题**：
- 一旦开始执行，无法从外部强制取消
- 必须等待函数完成
- 这是 Python 异步编程的根本限制

### 工具调用是黑盒

从 Agent 角度：
- 不知道工具内部在做什么
- 不知道工具还需要多久完成
- 无法检查工具内部状态

---

## 改进方案

### 方案 1：工具执行后立即检查队列（推荐）

**位置**: `src/fastreact/agent.py:1490`

**改进**:
```python
# 工具执行完成后
messages.append(Message.tool(...).to_llm_format())

# ✅ 新增：立即检查队列
pending = self._session_queues.get(session_id, MessageQueue())
if pending and pending._messages:
    import sys
    print(
        f"[DEBUG] Post-tool checkpoint: found {len(pending._messages)} messages",
        file=sys.stderr
    )
    # 继续下一次 inner loop 来处理这些消息
    # 不要等待 LLM 生成新的 tool_calls

executed_tools_this_iteration = True
has_more_tool_calls = False
```

**效果**：
- ✅ 工具执行完成后立即检查队列
- ✅ 如果有新消息，快速进入下一次 inner loop 处理
- ✅ 减少响应延迟

### 方案 2：多个工具调用之间都检查（更好）

**位置**: `src/fastreact/agent.py:1490`

**改进**:
```python
# Execute tools
for tool_call in tool_calls:
    # ... 工具执行 ...

    # ✅ 新增：每个工具执行后都检查队列
    pending = self._session_queues.get(session_id, MessageQueue())
    if pending and pending._messages:
        print(f"[DEBUG] Tool {tool_name} done, checking queue: {len(pending._messages)} messages")
        # 立即跳出工具执行循环
        # 下一次 inner loop 会处理这些消息
        break
```

**效果**：
- ✅ 每个工具执行后都检查
- ✅ 更快响应干预
- ✅ 更好的用户体验

### 方案 3：添加工具超时（辅助）

**位置**: `src/fastreact/agent.py:1467`

**改进**:
```python
# Execute tool with timeout
try:
    result = await asyncio.wait_for(
        self._tools.execute(tool_name, tool_params, user_context),
        timeout=10.0  # 10 秒超时
    )
except asyncio.TimeoutError:
    result = "[TIMEOUT] Tool execution exceeded 10 seconds, interrupted"
    # 超时后自动中断
```

**效果**：
- ✅ 防止工具无限期执行
- ✅ 提供最大延迟保证
- ⚠️  但需要为每个工具设置合理超时

---

## 用户体验改进

### 当前体验

```
用户：用知识图谱查询机器学习
Bot：⏳ 调用工具 1...
用户：停止
Bot：（工具 1 执行中...）← 无响应
Bot：（工具 2 执行前检查...）
Bot：⚠️ [USER INTERVENTION] 停下...
```

**延迟**：3-5 秒（取决于工具执行时间）

### 改进后体验

```
用户：用知识图谱查询机器学习
Bot：⏳ 调用工具 1...
用户：停止
Bot：（工具 1 完成）
Bot：✅ 工具完成，检查队列... ← 新增
Bot：⚠️ [USER INTERVENTION] 停下... ← 更快
```

**延迟**：1-2 秒（工具 1 完成后立即响应）

---

## 实施优先级

### 高优先级（立即可做）

✅ **工具执行后立即检查队列**（方案 1）
- 代码改动最小
- 效果明显
- 不改变现有行为

### 中优先级（推荐实施）

✅ **每个工具执行后都检查**（方案 2）
- 响应更快
- 更好的用户体验
- 代码改动适中

### 低优先级（可选）

⚠️  **添加工具超时**（方案 3）
- 需要为每个工具设置超时
- 可能误中断正常的长时操作
- 需要测试和调优

---

## 关键原则

### ✅ 正确的设计

1. **不假设用户输入**
   - 不硬编码"停止"、"取消"等关键词
   - 任何用户输入都作为 `steering` 消息处理
   - 让 LLM 理解用户意图

2. **统一的干预机制**
   - 所有用户输入进入队列
   - 在检查点统一处理
   - 不需要特殊 case

3. **渐进式响应**
   - 工具执行无法立即中断（技术限制）
   - 但可以在工具执行后尽快响应
   - 每个工具后检查队列

### ❌ 错误的设计

1. **硬编码关键词**
   - "停止"、"取消"等特定词汇
   - 无法适应不同表达
   - 违反通用性原则

2. **绕过队列机制**
   - 直接调用 `session.interrupt()`
   - 破坏统一的消息流
   - 难以维护和扩展

3. **试图中断阻塞操作**
   - `task.cancel()` 无法取消工具执行
   - 技术上不可行
   - 会导致资源泄漏

---

## 总结

### 当前状态

- ✅ 系统已经有完整的干预机制（steering 消息 + 队列 + 检查点）
- ✅ 干预机制已经工作（从日志可见）
- ⚠️  但响应延迟较大（工具执行后才检查）

### 改进方向

1. **立即实施**：工具执行后立即检查队列
2. **推荐实施**：每个工具执行后都检查
3. **可选实施**：添加工具超时机制

### 关键洞察

> **不应假设用户会有什么输入，无论是停止还是更改执行内容，都应该在 session 执行中可以生效**

这意味着：
- 不需要特殊的"停止"处理
- 所有用户输入都通过统一的 steering 机制
- 改进响应速度，而不是改变机制本身

---

**文档作者**: Claude (FastReAct Team)
**最后更新**: 2025-03-04
