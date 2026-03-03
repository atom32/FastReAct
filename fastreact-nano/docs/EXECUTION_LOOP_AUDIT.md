# 执行循环 Audit 报告

**日期**: 2025-03-03
**问题**: 用户实时输入处理不足
**影响**: 用户无法及时中断或转向正在执行的任务

---

## 当前执行流程分析

### 1. 消息处理流程

```
用户发送消息 A
    ↓
Feishu SDK 接收 (_handle_message_event_v2)
    ↓
创建新的 async task (loop.create_task)
    ↓
调用 agent.run_event_stream()
    ↓
进入 ReAct 循环:
    1. 检查 pending_messages
    2. LLM 推理 (run_step_stream)
    3. 执行工具 (await tools.execute)
    4. 返回步骤 1 (直到完成)
```

### 2. 关键代码位置

#### Feishu 消息处理 (`feishu_sdk.py:224`)
```python
# 每次收到消息都创建新的独立任务
loop.create_task(self._process_message_async(feishu_event))
```

**问题**: 没有检查是否有活跃的 session，总是创建新执行

#### Agent 执行循环 (`agent.py:1041`)
```python
# 只在每次 LLM 调用前检查 pending_messages
pending_messages = self._session_queues.get(session_id, MessageQueue())

if pending_messages:
    for msg in pending_messages.drain():
        # 处理用户干预
```

**问题**: 检查点太少，工具执行期间无法响应

#### 工具执行 (`agent.py:1188-1193`)
```python
# 完全阻塞，无法中断
result = await self._tools.execute(
    tool_name,
    tool_params,
    user_context=user_context
)
```

**问题**: 长时间运行的工具无法被中断

---

## 🔴 关键问题

### 问题 1: 会话隔离
- **现象**: 每条消息都是独立执行
- **影响**: 用户发"停下"会启动新的执行，而不是中断当前执行
- **根本原因**: Feishu adapter 没有跟踪活跃的 session

### 问题 2: 工具执行期间无检查
- **现象**: 在 `await tools.execute()` 期间完全阻塞
- **影响**: 长时间工具（如下载、大文件处理）无法被中断
- **根本原因**: 工具执行前后都没有检查用户输入

### 问题 3: 检查点不足
- **现象**: 只在每次 LLM 调用前检查 pending_messages
- **影响**: 响应延迟高（最多一个完整迭代）
- **根本原因**: 检查点太少

---

## ✅ 已有的机制（未使用）

Agent 已经实现了完整的消息注入机制：

### 1. 消息注入 API (`agent.py:855-869`)
```python
def inject_message(self, session_id: str, message: Message):
    """Inject message into active session"""
    if session_id not in self._session_queues:
        raise ValueError(f"Session not active: {session_id}")
    self._session_queues[session_id].push(message)
```

### 2. 用户干预支持 (`agent.py:1047-1062`)
```python
# Gateway 用户干预
if msg.metadata.get("source") == "gateway":
    messages.append({
        "role": "user",
        "content": f"[USER INTERVENTION]: {msg.content}"
    })

# Legacy interrupt 信号
if msg.content.startswith("[INTERRUPT]"):
    new_query = msg.metadata.get("new_query", "")
    # 查询切换
```

**问题**: Feishu adapter 没有使用这些机制！

---

## 🛠️ 改进方案

### 方案 1: 会话管理 + 消息注入（推荐）

#### 核心思路
1. 跟踪活跃的 session（`user_key → session_id`）
2. 新消息优先注入到活跃 session
3. 只有在没有活跃 session 时才创建新执行

#### 修改点

**1. FeishuSDKAdapter 添加会话跟踪**

```python
class FeishuSDKAdapter:
    def __init__(self, agent, config):
        # ... 现有代码 ...

        # 活跃 session 跟踪
        self._active_sessions: Dict[str, str] = {}  # user_key → session_id
        self._session_lock = asyncio.Lock()
```

**2. 修改消息处理逻辑**

```python
async def _process_message_async(self, event: dict):
    sender_id = event["sender_id"]
    chat_id = event["chat_id"]
    content = event["content"]

    user_key = f"feishu:{sender_id}"

    # 检查是否有活跃 session
    async with self._session_lock:
        active_session_id = self._active_sessions.get(user_key)

    if active_session_id:
        # 注入消息到活跃 session
        try:
            from fastreact.core.messages import Message

            # 检查是否是中断命令
            if content.strip().lower() in ("停下", "停止", "stop"):
                # 发送用户干预消息
                self.agent.inject_message(
                    active_session_id,
                    Message.user(
                        f"[USER INTERVENTION]: {content}",
                        metadata={"source": "feishu", "interrupt": True}
                    )
                )
                await self._send_text_message(chat_id, f"[INFO] 已发送中断指令")
            else:
                # 发送新任务消息
                self.agent.inject_message(
                    active_session_id,
                    Message.user(
                        f"[USER INTERVENTION]: {content}",
                        metadata={"source": "feishu"}
                    )
                )
                await self._send_text_message(chat_id, f"[INFO] 已注入到当前会话")
        except ValueError as e:
            # Session 不存在，创建新会话
            await self._start_new_session(user_key, content, chat_id)
    else:
        # 没有活跃 session，创建新会话
        await self._start_new_session(user_key, content, chat_id)
```

**3. 启动新会话时记录**

```python
async def _start_new_session(self, user_key: str, content: str, chat_id: str):
    """启动新的执行会话"""
    session_id = None

    await self._send_thinking_message(chat_id, content)

    async for event in self.agent.run_event_stream(
        query=content,
        user_key=user_key,
    ):
        # 记录 session_id
        if session_id is None and event.session_id:
            session_id = event.session_id
            async with self._session_lock:
                self._active_sessions[user_key] = session_id

        # ... 处理事件 ...

        # 会话结束时清理
        if event.type == EventType.SESSION_END:
            async with self._session_lock:
                if user_key in self._active_sessions:
                    del self._active_sessions[user_key]
```

---

### 方案 2: 工具执行期间增加检查点

#### 核心思路
在工具执行前后都检查用户输入

#### 修改点

**Agent 执行循环 (`agent.py:1161`)**

```python
# 2. Body: Execute tools (if any)
if step_end and step_end.metadata.get("has_tool_calls") and tool_calls:
    for tool_call in tool_calls:
        tool_name = tool_call.get("name", "")
        tool_params = tool_call.get("arguments", {})
        call_id = tool_call.get("id", "")

        # *** 新增：工具执行前检查 ***
        pending_messages = self._session_queues.get(session_id, MessageQueue())
        if pending_messages:
            for msg in pending_messages.drain():
                if msg.metadata.get("source") == "feishu":
                    if msg.metadata.get("interrupt"):
                        # 用户要求中断
                        yield AgentEvent.think(
                            f"[INTERRUPTED] 用户中断: {msg.content}",
                            session_id
                        )
                        has_more_tool_calls = False  # 退出工具循环
                        break

        # Safety check
        if self._safety_policy:
            decision = self._safety_policy.check(...)
            if decision.level == SafetyLevel.FORBIDDEN:
                result = f"[SAFETY_BLOCKED] {decision.reason}"
                yield AgentEvent.tool_result(tool_name, result, session_id)
                messages.append(Message.tool(...).to_llm_format())
                continue

        # Execute tool
        try:
            result = await self._tools.execute(
                tool_name,
                tool_params,
                user_context=user_context
            )
        except Exception as e:
            result = f"[ERROR] {str(e)}"

        # *** 新增：工具执行后检查 ***
        pending_messages = self._session_queues.get(session_id, MessageQueue())
        if pending_messages:
            for msg in pending_messages.drain():
                if msg.metadata.get("source") == "feishu":
                    if msg.metadata.get("interrupt"):
                        # 发送工具结果，然后中断
                        yield AgentEvent.tool_result(tool_name, result, session_id)
                        yield AgentEvent.think(
                            f"[INTERRUPTED] 用户中断: {msg.content}",
                            session_id
                        )
                        has_more_tool_calls = False  # 退出工具循环
                        break

        # 如果没有中断，继续正常流程
        if has_more_tool_calls:
            yield AgentEvent.tool_result(tool_name, result, session_id)
            messages.append(Message.tool(...).to_llm_format())
```

---

### 方案 3: 可中断的工具执行（高级）

#### 核心思路
使用 `asyncio.Task` 和 `asyncio.Event` 实现可中断的工具执行

#### 修改点

```python
# Agent 添加中断支持
class Agent:
    def __init__(self, ...):
        # ... 现有代码 ...
        self._interrupt_flags: Dict[str, asyncio.Event] = {}

    async def run_event_stream(self, ...):
        # 创建中断标志
        interrupt_event = asyncio.Event()
        self._interrupt_flags[session_id] = interrupt_event

        try:
            # ... 执行循环 ...

            # 执行工具时检查中断
            for tool_call in tool_calls:
                # 使用 create_task 和 wait 实现可中断执行
                tool_task = asyncio.create_task(
                    self._tools.execute(tool_name, tool_params, user_context)
                )

                # 等待工具完成或中断信号
                done, pending = await asyncio.wait(
                    [tool_task, interrupt_event.wait()],
                    return_when=asyncio.FIRST_COMPLETED
                )

                if interrupt_event.is_set():
                    # 用户中断，取消工具执行
                    tool_task.cancel()
                    try:
                        await tool_task
                    except asyncio.CancelledError:
                        pass

                    yield AgentEvent.think("[INTERRUPTED] 工具执行被取消", session_id)
                    break
                else:
                    # 工具正常完成
                    result = tool_task.result()
                    yield AgentEvent.tool_result(tool_name, result, session_id)

        finally:
            # 清理中断标志
            if session_id in self._interrupt_flags:
                del self._interrupt_flags[session_id]

    def interrupt_session(self, session_id: str):
        """中断会话执行"""
        if session_id in self._interrupt_flags:
            self._interrupt_flags[session_id].set()
```

---

## 📋 实施建议

### 优先级

1. **高优先级**: 方案 1（会话管理 + 消息注入）
   - **影响**: 解决用户无法中断的根本问题
   - **工作量**: 中等（需要修改 Feishu adapter）
   - **风险**: 低（使用已有的机制）

2. **中优先级**: 方案 2（工具执行检查点）
   - **影响**: 减少响应延迟
   - **工作量**: 小（只修改 Agent 执行循环）
   - **风险**: 低

3. **低优先级**: 方案 3（可中断的工具执行）
   - **影响**: 支持真正实时的工具中断
   - **工作量**: 大（需要修改工具执行机制）
   - **风险**: 中（需要处理并发和清理）

### 实施步骤

#### 第一步：实施方案 1（会话管理）
1. 在 `FeishuSDKAdapter` 添加会话跟踪
2. 修改 `_process_message_async` 检查活跃 session
3. 添加 `_start_new_session` 方法处理新会话
4. 测试中断命令（"停下"、"停止"）

#### 第二步：实施方案 2（检查点）
1. 在工具执行前添加 pending_messages 检查
2. 在工具执行后添加 pending_messages 检查
3. 测试长时间工具执行期间的中断

#### 第三步：优化用户体验
1. 添加更多中断命令（"取消"、"别做这个"等）
2. 支持任务替换（"去做X而不是Y"）
3. 显示当前执行状态（"正在执行工具Y，预计剩余时间Z"）

---

## 🧪 测试用例

### 测试场景 1: 基本中断
```
用户: 用知识图谱查询机器学习
Bot: 正在思考... [开始执行]
用户: 停下
Bot: [INFO] 已发送中断指令
Bot: [INTERRUPTED] 用户中断: 停下
```

### 测试场景 2: 任务替换
```
用户: 下载一个 1GB 的文件
Bot: 正在执行工具: download_file...
用户: 别下载了，去查询天气
Bot: [INFO] 已注入到当前会话
Bot: [USER INTERVENTION] 别下载了，去查询天气
Bot: 调用 weather_query 工具...
```

### 测试场景 3: 长时间工具中断
```
用户: 处理这个大文件
Bot: 正在执行工具: process_large_file...
      [工具执行中...]
用户: 停止
Bot: [INTERRUPTED] 工具执行被取消
```

---

## 📊 性能影响

### 方案 1
- **内存**: 每个活跃 session 增加 ~100 bytes（session_id 存储）
- **延迟**: 消息注入延迟 < 1ms
- **并发**: 支持多用户并发

### 方案 2
- **CPU**: 每次工具执行增加 2 次检查（~0.1ms）
- **延迟**: 最大响应延迟从 1 个迭代降到 < 1 个工具执行
- **可靠性**: 显著提升用户体验

### 方案 3
- **内存**: 每个 session 增加 1 个 asyncio.Event
- **CPU**: 每次工具执行增加 1 个 asyncio.wait 调用
- **延迟**: 响应延迟 < 10ms

---

## 🎯 总结

### 当前状态
- ❌ 每条消息都是独立执行
- ❌ 工具执行期间无法中断
- ❌ 检查点太少
- ✅ Agent 已有消息注入机制（未使用）

### 改进后状态
- ✅ 跟踪活跃 session，支持消息注入
- ✅ 工具执行前后都有检查点
- ✅ 支持实时中断和任务替换
- ✅ 响应延迟显著降低

### 建议实施顺序
1. **第一阶段**: 方案 1（会话管理）→ 解决根本问题
2. **第二阶段**: 方案 2（检查点）→ 优化响应速度
3. **第三阶段**: 方案 3（可中断工具）→ 完善实时中断

---

**文档版本**: 1.0
**作者**: FastReAct Team
**最后更新**: 2025-03-03
