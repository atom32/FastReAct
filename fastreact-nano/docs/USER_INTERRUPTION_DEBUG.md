# 用户中断功能调试说明

## 问题现象

从日志中观察到：
1. 用户发送"用知识图谱查询机器学习"
2. 在工具执行过程中，用户发送"停下来吧"
3. 系统显示 `[INFO] Injecting into running session` 和 `[FINAL ANSWER] [INJECTED]`
4. **但原始任务继续执行，没有检测到用户干预**

## 可能的原因

### 时序问题

观察到的日志时序：
```
[TOOL] Calling graphrag_search_graph
[RESULT] { ... }
[DEBUG] Tools executed in this iteration, will continue to next iteration

[INFO] Injecting into running session ...  ← "停下来吧"在这里注入

[THINK] Using graphrag_get_entity, graphrag_query_relationships tools... ← 没有显示 [USER INTERVENTION]
[TOOL] Calling graphrag_get_entity
```

关键发现：`[DEBUG] Tools executed in this iteration` 出现在 `[INFO] Injecting]` **之前**！

这意味着：
1. 第一个工具调用完成后，代码检查 `has_followup`（队列为空）
2. 决定继续下一次迭代
3. **然后**第二个任务才注入"停下来吧"消息
4. 第二次迭代开始，检查 `pending_messages`（可能已经太晚）

### 调试验证

添加了额外的调试日志：
```python
# 在 inner loop 开始时
if pending_messages:
    print(f"[DEBUG] Found {len(pending_messages._messages)} pending messages")

# 在 has_followup 检查时
if has_followup:
    print(f"[DEBUG] Found {len(followup_queue._messages)} follow-up messages")
```

## 预期行为 vs 实际行为

### 预期

```
[TOOL] Calling graphrag_search_graph
[INFO] Injecting into running session ...  ← 消息注入
[DEBUG] Found 1 follow-up messages         ← 下次迭代应该检测到
[USER INTERVENTION] 停下来吧               ← 应该显示干预事件
[SESSION_END] 用户中断                     ← 应该结束
```

### 实际

```
[TOOL] Calling graphrag_search_graph
[DEBUG] Tools executed in this iteration  ← 已经决定继续
[INFO] Injecting into running session ...
[THINK] Using graphrag_get_entity ...     ← 继续执行，没有检测到干预
```

## 解决方案

### 方案 1：在工具执行后立即检查队列

在 `run_event_stream()` 的工具执行循环后，再次检查是否有新消息：

```python
# After tools executed, check for new messages
if executed_tools_this_iteration:
    # Check again for newly injected messages
    late_messages = self._session_queues.get(session_id, MessageQueue())
    if late_messages:
        # Process them immediately
        ...
```

### 方案 2：使用事件通知

使用 `asyncio.Event` 来通知运行中的任务有新消息：

```python
# In run_or_inject()
if active_session.get_status() == "running":
    # Set event to notify running task
    self._intervention_events[session_id].set()

# In run_event_stream()
# Wait for event before next tool call
if await self._intervention_events[session_id].wait(timeout=0):
    # Check for new messages
    ...
```

### 方案 3：让注入的消息立即生效

修改 `run_or_inject()`，不要立即返回，而是等待被注入的消息被处理：

```python
# Inject into running session and wait for it to be processed
self._session_queues[...].push(...)

# Wait for message to be processed (check session state or queue)
while active_session.get_status() == "running":
    await asyncio.sleep(0.1)
    # Check if message was processed
    ...
```

## 测试步骤

1. 重新启动 Feishu bot
2. 发送一个会触发工具调用的消息（如"用知识图谱查询机器学习"）
3. 在工具执行过程中，发送"停下来吧"
4. 观察日志中的 `[DEBUG]` 信息：
   - 是否检测到待处理消息？
   - 消息在什么时候被检测到？
   - 用户干预事件是否被触发？

## 当前状态

- ✅ 消息注入到正确的队列（`Agent._session_queues`）
- ✅ 消息格式正确（`Message.steering` with `source="feishu"`）
- ✅ 消息检查逻辑支持 "feishu" 来源
- ❌ 时序问题：消息注入太晚，没有被及时检测

## 下一步

使用新的调试日志重新测试，收集更多时序信息，确定最佳的修复方案。
