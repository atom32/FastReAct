# Agent 层会话管理 API 设计

**日期**: 2025-03-03
**原则**: Agent 负责会话管理，Adapter 只负责协议转换

---

## 🎯 设计目标

### Agent 层职责
- ✅ 会话生命周期管理（创建、查询、销毁）
- ✅ 消息路由和注入
- ✅ 并发控制
- ✅ 执行状态跟踪

### Adapter 层职责
- ✅ 协议转换（Feishu/Gateway → 统一格式）
- ✅ 调用 Agent API
- ❌ 不管理会话状态

---

## 📋 当前缺失的 API

### 问题 1: 无法查询活跃会话
```python
# Adapter 需要：
# "用户 ou_xxx 是否有活跃会话？session_id 是什么？"

# 当前 Agent 没有：
active_session = agent.get_active_session("feishu:ou_xxx")
# ❌ 不存在
```

### 问题 2: 没有统一入口
```python
# Adapter 需要：
# "如果用户有活跃会话就注入，否则创建新会话"

# 当前需要 Adapter 自己判断：
if user_key in active_sessions:
    agent.inject_message(session_id, message)
else:
    async for event in agent.run_event_stream(...):
        ...
# ❌ 逻辑复杂，容易出错
```

---

## 🛠️ Agent 层应该提供的 API

### 1. 查询活跃会话

```python
def get_active_session(self, user_key: str) -> Optional[str]:
    """
    获取用户当前活跃的 session_id

    Args:
        user_key: 用户标识 (e.g., "feishu:ou_xxx")

    Returns:
        session_id if active, None if no active session

    Example:
        >>> session_id = agent.get_active_session("feishu:ou_123")
        >>> if session_id:
        ...     print(f"用户有活跃会话: {session_id}")
    """
    # 遍历所有 session，找到属于该用户的活跃 session
    for session_id, session in self._sessions.items():
        if session.user_key == user_key and session.is_active():
            return session_id
    return None
```

### 2. 统一执行入口（推荐）

```python
async def run_or_inject(
    self,
    query: str,
    user_key: str,
    skills: Optional[list[str]] = None,
    history: Optional[list[dict]] = None,
) -> AsyncIterator["AgentEvent"]:
    """
    统一执行入口：自动判断是创建新会话还是注入到活跃会话

    这是 Adapter 应该使用的推荐 API，简化了调用逻辑。

    Args:
        query: 用户消息
        user_key: 用户标识 (e.g., "feishu:ou_xxx")
        skills: 可选的技能列表
        history: 可选的历史消息

    Yields:
        AgentEvent 对象流

    行为:
        - 如果用户有活跃会话：注入消息到会话
        - 如果用户无活跃会话：创建新会话并执行

    Example:
        >>> # Adapter 只需要调用这一个 API
        >>> async for event in agent.run_or_inject(
        ...     query="停下",
        ...     user_key="feishu:ou_123"
        ... ):
        ...     print(f"Event: {event.type}")
    """
    # 检查是否有活跃会话
    active_session_id = self.get_active_session(user_key)

    if active_session_id:
        # 注入消息到活跃会话
        from fastreact.core.messages import Message

        # 判断消息类型
        content_lower = query.strip().lower()
        is_interrupt = content_lower in ("停下", "停止", "stop", "取消", "cancel")

        if is_interrupt:
            # 发送中断消息
            self.inject_message(
                active_session_id,
                Message.user(
                    f"[USER INTERVENTION]: {query}",
                    metadata={"source": "adapter", "interrupt": True}
                )
            )
        else:
            # 发送新任务消息
            self.inject_message(
                active_session_id,
                Message.user(
                    f"[USER INTERVENTION]: {query}",
                    metadata={"source": "adapter"}
                )
            )

        # 返回一个特殊事件表示消息已注入
        from fastreact.core.events import AgentEvent, EventType
        yield AgentEvent.think(
            f"[消息已注入] {query}",
            active_session_id,
            metadata={"injected": True, "session_id": active_session_id}
        )
    else:
        # 创建新会话并执行
        async for event in self.run_event_stream(
            query=query,
            skills=skills,
            history=history,
            user_key=user_key,
        ):
            yield event
```

### 3. 会话状态查询

```python
def list_active_sessions(self) -> dict[str, dict]:
    """
    列出所有活跃会话的信息

    Returns:
        字典，格式: {session_id: {user_key, start_time, status}}

    Example:
        >>> sessions = agent.list_active_sessions()
        >>> for sid, info in sessions.items():
        ...     print(f"{sid}: {info['user_key']} - {info['status']}")
    """
    active = {}
    for session_id, session in self._sessions.items():
        if session.is_active():
            active[session_id] = {
                "user_key": session.user_key,
                "start_time": session.created_at,
                "status": "running",
            }
    return active

def has_active_session(self, user_key: str) -> bool:
    """
    检查用户是否有活跃会话

    Args:
        user_key: 用户标识

    Returns:
        True if user has active session, False otherwise

    Example:
        >>> if agent.has_active_session("feishu:ou_123"):
        ...     print("用户有活跃会话")
    """
    return self.get_active_session(user_key) is not None
```

---

## 🔄 改进的 AgentSession

需要在 AgentSession 中添加状态跟踪：

```python
class AgentSession:
    """
    Agent 会话对象

    跟踪会话的完整生命周期
    """

    def __init__(
        self,
        session_id: str,
        user_key: Optional[str] = None,
        agent: "Agent" = None,
        max_history: int = 50,
        followup_window_seconds: int = 300,
        max_queue_size: int = 100,
    ):
        self.session_id = session_id
        self.user_key = user_key  # 用户标识
        self.agent = agent
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.status = "running"  # running, idle, closed

        # 消息队列
        self.queue = MessageQueue(maxsize=max_queue_size)

        # 历史消息
        self.history: list[dict] = []
        self.max_history = max_history

        # Followup 窗口
        self.followup_window_seconds = followup_window_seconds

        # 统计信息
        self.iterations = 0
        self.tool_calls = 0

    def is_active(self) -> bool:
        """检查会话是否活跃"""
        if self.status == "closed":
            return False

        # 检查最后活动时间
        idle_time = (datetime.now() - self.last_activity).total_seconds()
        if idle_time > self.followup_window_seconds:
            return False

        return True

    def touch(self):
        """更新最后活动时间"""
        self.last_activity = datetime.now()

    def close(self):
        """关闭会话"""
        self.status = "closed"
```

---

## 📝 Adapter 层的使用示例

### 改进前（当前）

```python
# feishu_sdk.py (当前实现)
async def _process_message_async(self, event: dict):
    user_key = f"feishu:{sender_id}"
    content = event["content"]

    # ❌ 需要自己管理会话状态
    if user_key in self._active_sessions:
        session_id = self._active_sessions[user_key]
        # 注入消息...
    else:
        # 创建新会话...
        async for event in self.agent.run_event_stream(...):
            # 记录 session_id...
            if event.type == EventType.SESSION_END:
                # 清理...
```

### 改进后（使用 Agent API）

```python
# feishu_sdk.py (简化后)
async def _process_message_async(self, event: dict):
    user_key = f"feishu:{sender_id}"
    content = event["content"]

    # ✅ 只需调用一个 API
    async for event in self.agent.run_or_inject(
        query=content,
        user_key=user_key,
    ):
        # 处理事件
        await self._handle_agent_event(event, chat_id)

    # 无需管理会话状态，Agent 层负责
```

---

## 🎯 Gateway Adapter 的使用

### 改进前

```python
# gateway.py (当前实现)
@app.post("/chat")
async def chat(request: ChatRequest):
    user_key = f"gateway:{request.session_id}"

    # ❌ 需要手动检查会话
    if user_key in active_sessions:
        # 注入消息...
    else:
        # 创建新会话...
```

### 改进后

```python
# gateway.py (简化后)
@app.post("/chat")
async def chat(request: ChatRequest):
    user_key = f"gateway:{request.session_id}"

    # ✅ 统一 API
    async for event in agent.run_or_inject(
        query=request.message,
        user_key=user_key,
    ):
        # Stream events to client
        yield event
```

---

## 📊 实施步骤

### 第一步：扩展 AgentSession
1. 添加 `user_key` 字段
2. 添加 `status` 字段（running, idle, closed）
3. 添加 `is_active()` 方法
4. 添加 `touch()` 方法

### 第二步：添加 Agent API
1. 实现 `get_active_session(user_key)`
2. 实现 `has_active_session(user_key)`
3. 实现 `list_active_sessions()`
4. 实现 `run_or_inject(query, user_key)`

### 第三步：更新执行流程
1. 在 `run_event_stream` 开始时设置 session 状态
2. 每次活动时调用 `session.touch()`
3. 会话结束时设置 `session.status = "closed"`

### 第四步：简化 Adapter
1. Feishu adapter 改用 `run_or_inject()`
2. Gateway adapter 改用 `run_or_inject()`
3. 移除 Adapter 中的会话管理逻辑

---

## 🧪 测试用例

### 测试 1: 基本功能
```python
# 创建会话
async for event in agent.run_or_inject("查询天气", "feishu:ou_123"):
    pass

# 检查活跃会话
assert agent.has_active_session("feishu:ou_123")
session_id = agent.get_active_session("feishu:ou_123")
assert session_id is not None
```

### 测试 2: 消息注入
```python
# 创建会话
async for event in agent.run_or_inject("下载文件", "feishu:ou_123"):
    if event.type == EventType.TOOL_CALL:
        break

# 注入中断消息
async for event in agent.run_or_inject("停下", "feishu:ou_123"):
    assert event.metadata.get("injected") == True
```

### 测试 3: 会话清理
```python
# 创建会话
session_id = agent.create_session("feishu:ou_123")

# 关闭会话
agent.close_session(session_id)

# 检查已清理
assert not agent.has_active_session("feishu:ou_123")
```

---

## 📈 收益

### 简化 Adapter 代码
- **Feishu adapter**: 减少 ~50 行会话管理代码
- **Gateway adapter**: 减少 ~30 行会话管理代码
- **未来 adapters**: 无需重复实现会话管理

### 统一用户体验
- 所有渠道使用相同的会话管理逻辑
- 一致的中断/注入行为
- 统一的状态查询

### 更好的可测试性
- Agent 层会话管理可独立测试
- Adapter 测试不需要 mock 会话状态

---

## 🎯 总结

### 当前问题
- Agent 有会话管理基础，但缺少查询 API
- Adapter 需要自己实现会话管理逻辑
- 各 Adapter 实现不一致

### 解决方案
- Agent 层提供 `run_or_inject()` 统一入口
- Agent 层提供会话查询 API
- Agent 负责会话生命周期管理

### 架构原则
- **Agent**: 会话管理、执行控制、状态跟踪
- **Adapter**: 协议转换、消息路由

---

**文档版本**: 1.0
**作者**: FastReAct Team
**最后更新**: 2025-03-03

---

## ✅ 实施状态（2025-03-03 完成）

### 已实现功能

#### 1. AgentSession 扩展 ✅
- ✅ 添加 `user_key` 字段
- ✅ 添加 `status` 字段（idle/running/closed）
- ✅ 实现 `get_status()` 方法
- ✅ 实现 `set_status()` 方法（带验证）
- ✅ 实现 `get_metadata()` 方法
- ✅ `set_running()` 自动同步 status

#### 2. Agent 查询 API ✅
- ✅ `find_active_session(user_key)` - 查找用户活跃会话
- ✅ `list_sessions(user_key=None)` - 列出所有会话（可按用户过滤）
- ✅ `get_session_status(session_id)` - 获取会话状态
- ✅ `create_session()` 接受 `user_key` 参数

#### 3. 统一执行入口 ✅
```python
async def run_or_inject(
    query: str,
    user_key: str,
    skills: Optional[list[str]] = None,
    force_new: bool = False,
) -> AsyncIterator["AgentEvent"]
```
- ✅ 自动创建新会话或注入到活跃会话
- ✅ 返回 `metadata["injected"]` 标志
- ✅ 完整的事件流

#### 4. 会话状态跟踪 ✅
- ✅ `run_event_stream()` 开始时设置 status="running"
- ✅ finally 块中重置 status="idle"
- ✅ user_key 自动设置到 session

#### 5. 工具执行中断检查点 ✅
- ✅ 每个工具执行前检查用户输入
- ✅ 检测到干预时中断工具执行
- ✅ 发送 `tool_interrupted` 元数据事件

#### 6. Feishu Adapter 简化 ✅
- ✅ 使用 `agent.run_or_inject()` 替代直接调用
- ✅ 减少 ~50 行会话管理代码
- ✅ 处理注入事件通知

#### 7. 测试覆盖 ✅
- ✅ 19 个新测试用例
- ✅ 所有 372 个单元测试通过
- ✅ 测试文件: `tests/unit/test_session_management_api.py`

### API 使用示例

```python
# 查找活跃会话
session = agent.find_active_session("feishu:ou_123")
if session:
    print(f"Session {session.session_id} is {session.get_status()}")

# 列出会话
all_sessions = agent.list_sessions()
user_sessions = agent.list_sessions("feishu:ou_123")

# 统一执行入口（推荐）
async for event in agent.run_or_inject("停下", "feishu:ou_123"):
    if event.metadata.get("injected"):
        await notify_user("Message added to active session")
    await send_to_user(event)
```

### 架构改进

**改进前:**
```
Adapter (创建 session_id) → Agent.run_event_stream() → Core
```

**改进后:**
```
Adapter → Agent.run_or_inject() → Agent 管理会话 → Core
```

### 修改的文件

1. `src/fastreact/core/session.py` - AgentSession 扩展
2. `src/fastreact/agent.py` - 查询 API 和 run_or_inject
3. `src/fastreact/adapters/feishu_sdk.py` - 简化适配器
4. `src/fastreact/core/events.py` - 增强 session_start 事件
5. `tests/unit/test_session_management_api.py` - 新测试套件

### 向后兼容性

所有更改都是向后兼容的：
- ✅ 现有 `run_event_stream()` API 未改变
- ✅ 新 `run_or_inject()` API 是可选的
- ✅ 现有测试继续通过（353/353）
