# Gateway Adapter 重构方案 - BaseAdapter 设计

> Historical analysis: this document was moved from the old root `docs/`
> directory during the 2026-06-23 documentation cleanup. Treat it as design
> background, not current implementation truth. For current service behavior,
> see [../HEADLESS_SERVICE.md](../HEADLESS_SERVICE.md).

**问题**: Gateway Adapter 有太多逻辑（807 行），职责混乱
**目标**: 提取共享逻辑，设计统一的 BaseAdapter 接口

---

## 一、当前问题分析

### 1.1 代码量统计

```
gateway.py: 807 行
  ├─ Session 类: ~240 行
  ├─ SessionManager 类: ~40 行
  └─ create_gateway_app(): ~500+ 行
```

### 1.2 Session 类职责过多

**当前 Session 类做的事情**:
1. ✅ WebSocket 连接管理（应该保留）
2. ✅ 消息队列处理（应该保留）
3. ✅ Agent 调用和事件流处理（**应该提取**）
4. ✅ 会话历史管理（**应该提取**）
5. ✅ 中断处理（**应该提取**）
6. ✅ 跟随查询检测（**应该提取**）

### 1.3 代码重复问题

**Telegram、Discord 等通道也需要**:
- ❌ 会话历史管理
- ❌ Agent 调用逻辑
- ❌ 事件流处理
- ❌ 中断处理（可选）

**但是 Gateway Session 的逻辑无法直接复用**，因为：
- Telegram 没有 WebSocket，而是 HTTP API
- Discord 有自己的 WebSocket SDK
- 每个平台的连接方式不同

---

## 二、重构方案：分层架构

### 2.1 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                    Adapter Architecture                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  BaseAdapter (抽象基类)                              │  │
│  │  - 生命周期管理 (start/stop)                         │  │
│  │  - 通用工具方法                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│           ▲            ▲            ▲                         │
│           │            │            │                         │
│  ┌────────┴────────┐   │   ┌────────┴────────┐              │
│  │ GatewayAdapter  │   │   │ ChannelAdapter  │              │
│  │ (WebSocket 服务器)│   │   │ (Telegram等)    │              │
│  └────────┬────────┘   │   └────────┬────────┘              │
│           │            │            │                         │
│  ┌────────┴────────┐   │   ┌────────┴────────┐              │
│  │ SessionManager  │   │   │ ChannelSession  │              │
│  │ (管理多个Session)│   │   │ (管理单个会话)   │              │
│  └────────┬────────┘   │   └────────┬────────┘              │
│           │            │            │                         │
│  ┌────────┴────────┐   │   ┌────────┴────────┐              │
│  │ Session         │   │   │ SessionMixin    │              │
│  │ (Gateway 特定)  │   │   │ (共享逻辑)      │              │
│  └─────────────────┘   │   └─────────────────┘              │
│                        │                                       │
│  ┌─────────────────────┴─────────────────────────────────┐  │
│  │         SessionMixin (共享业务逻辑)                    │  │
│  │  - 会话历史管理                                       │  │
│  │  - Agent 调用                                         │  │
│  │  - 事件流处理                                         │  │
│  │  - 跟随查询检测                                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、详细设计

### 3.1 SessionMixin - 共享业务逻辑

```python
# fastreact/core/session_mixin.py

from typing import Optional, List, Dict, Any
from datetime import datetime
from fastreact import Agent, EventType


class SessionMixin:
    """
    会话业务逻辑 Mixin（可被多个类复用）

    提供的功能：
    - 会话历史管理
    - Agent 调用和事件流处理
    - 跟随查询检测
    """

    def __init__(
        self,
        agent: Agent,
        max_history: int = 50,
        followup_window_seconds: int = 30,
    ):
        self.agent = agent
        self._history: List[Dict[str, Any]] = []
        self._max_history = max_history
        self._last_response_time: Optional[datetime] = None
        self._followup_window_seconds = followup_window_seconds

    def get_history(self) -> List[Dict[str, Any]]:
        """获取会话历史"""
        return self._history.copy()

    def is_followup(self) -> bool:
        """检查当前是否是跟随查询"""
        if self._last_response_time is None:
            return False

        time_since_response = (
            datetime.utcnow() - self._last_response_time
        ).total_seconds()

        return time_since_response < self._followup_window_seconds

    def update_history(self, user_query: str, assistant_response: str):
        """更新会话历史"""
        self._history.append({
            "role": "user",
            "content": user_query
        })
        self._history.append({
            "role": "assistant",
            "content": assistant_response
        })

        # 自动裁剪历史
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # 更新最后响应时间
        self._last_response_time = datetime.utcnow()

    async def process_query(
        self,
        query: str,
        session_id: str,
        on_event: callable,  # 事件回调
        skills: Optional[List[str]] = None,
    ) -> str:
        """
        处理查询（核心逻辑）

        Args:
            query: 用户查询
            session_id: 会话 ID
            on_event: 事件回调函数 async def on_event(event)
            skills: 可选的 SKILL 列表

        Returns:
            最终响应文本
        """
        final_response = None
        is_followup = self.is_followup()

        # 如果是跟随查询，提示日志
        if is_followup and len(self._history) > 0:
            import sys
            print(
                f"[INFO] Follow-up query detected "
                f"(last {len(self._history)} messages)",
                file=sys.stderr
            )

        # 调用 Agent
        async for event in self.agent.run_event_stream(
            query,
            skills=skills,
            session_id=session_id,
            history=self._history if is_followup else [],
        ):
            # 触发事件回调
            await on_event(event)

            # 记录最终响应
            if event.type == EventType.SESSION_END:
                final_response = event.content

        # 更新历史
        if final_response:
            self.update_history(query, final_response)

        return final_response
```

---

### 3.2 BaseAdapter - 统一适配器接口

```python
# fastreact/adapters/base.py

from abc import ABC, abstractmethod
from typing import Optional, Any
from fastreact import Agent, Config


class BaseAdapter(ABC):
    """
    适配器基类（统一接口）

    所有适配器（Gateway、Telegram、Discord等）都应该继承此类
    """

    name: str = "base"

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """启动适配器"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止适配器"""
        pass

    @property
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running
```

**关键设计**:
- ✅ **极简接口**: 只有 `start()` 和 `stop()`
- ✅ **无约束**: 不强制继承者如何实现会话管理
- ✅ **灵活性**: 每个适配器可以有自己的 Session 实现

---

### 3.3 GatewayAdapter - 重构后

```python
# fastreact/adapters/gateway.py

from fastreact.adapters.base import BaseAdapter
from fastreact.core.session_mixin import SessionMixin


class GatewaySession:
    """
    Gateway 会话（使用 SessionMixin）
    """

    def __init__(
        self,
        session_id: str,
        websocket: WebSocket,
        config: Optional[Config] = None,
        max_queue_size: int = 5,
    ):
        self.session_id = session_id
        self.websocket = websocket
        self.created_at = datetime.utcnow()

        # 消息队列
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.max_queue_size = max_queue_size

        # 中断状态
        self._interrupted = False
        self._is_running = False

        # ✅ 使用 SessionMixin（复用业务逻辑）
        self.agent = Agent(config=config, multitenant=False)

        # ✅ 继承 SessionMixin
        self._session_mixin = SessionMixin(
            agent=self.agent,
            max_history=50,
            followup_window_seconds=30,
        )

        # 初始化 Agent 的会话队列
        from fastreact.core.messages import MessageQueue
        if session_id not in self.agent._session_queues:
            self.agent._session_queues[session_id] = MessageQueue()

    async def send(self, message: dict):
        """发送消息到客户端（Gateway 特定）"""
        try:
            await self.websocket.send_json(message)
        except Exception:
            pass

    def interrupt(self):
        """中断当前执行"""
        self._interrupted = True

    def reset_interrupt(self):
        """重置中断标志"""
        self._interrupted = False

    async def enqueue_message(self, message: dict) -> bool:
        """将消息加入队列"""
        if self._message_queue.qsize() >= self.max_queue_size:
            return False

        await self._message_queue.put(message)
        return True

    async def process_queue(self):
        """后台任务：处理消息队列"""
        while True:
            message = await self._message_queue.get()
            await self._handle_message(message)

    async def _handle_message(self, message: dict):
        """处理单条消息"""
        msg_type = message.get("type")

        if msg_type == "control":
            action = message.get("action")
            if action == "interrupt":
                self.interrupt()
                await self.send({
                    "type": "info",
                    "content": "Execution interrupted",
                })

        elif msg_type == "query":
            query = message.get("content", "")
            skills = message.get("skills")

            # ✅ 使用 SessionMixin 处理查询（复用逻辑）
            final_response = await self._session_mixin.process_query(
                query=query,
                session_id=self.session_id,
                on_event=self._on_agent_event,  # 事件回调
                skills=skills,
            )

    async def _on_agent_event(self, event):
        """Agent 事件回调（Gateway 特定）"""
        # 检查中断
        if self._interrupted:
            return

        # 发送事件到客户端
        await self.send({
            "type": "event",
            "event_type": event.type.value,
            "content": event.content,
            "tool_name": event.tool_name,
            "tool_args": event.tool_args,
            "session_id": event.session_id,
            "metadata": event.metadata,
        })

        # 检查会话结束
        if event.type == EventType.SESSION_END:
            if "[INTERRUPTED]" in event.content:
                self._interrupted = True


class GatewayAdapter(BaseAdapter):
    """
    Gateway 适配器（继承 BaseAdapter）
    """

    name = "gateway"

    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self.session_manager = SessionManager()

    async def start(self):
        """启动 Gateway（FastAPI 服务器）"""
        self._running = True
        # 启动 FastAPI 服务器
        # ...

    async def stop(self):
        """停止 Gateway"""
        self._running = False
        # 关闭所有会话
        # ...
```

---

### 3.4 ChannelAdapter - Telegram 示例

```python
# fastreact/adapters/telegram.py

from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from fastreact.adapters.base import BaseAdapter
from fastreact.core.session_mixin import SessionMixin


class TelegramChannelSession:
    """
    Telegram 通道会话（也使用 SessionMixin）
    """

    def __init__(self, chat_id: str, agent: Agent):
        self.chat_id = chat_id

        # ✅ 使用 SessionMixin（复用业务逻辑）
        self._session_mixin = SessionMixin(
            agent=agent,
            max_history=50,
            followup_window_seconds=30,
        )

    async def handle_message(
        self,
        update: Update,
        send_message: callable,  # Telegram 发送消息函数
    ):
        """处理 Telegram 消息"""

        query = update.message.text
        chat_id = str(update.effective_chat.id)

        # ✅ 使用 SessionMixin 处理查询（复用逻辑）
        final_response = await self._session_mixin.process_query(
            query=query,
            session_id=f"telegram:{chat_id}",
            on_event=lambda event: self._on_agent_event(
                event,
                send_message=send_message
            ),
        )

        # 发送最终响应（Telegram 特定）
        if final_response:
            await send_message(
                chat_id=chat_id,
                text=final_response
            )

    async def _on_agent_event(self, event, send_message: callable):
        """Agent 事件回调（Telegram 特定）"""
        # 可选：发送"正在思考"消息
        if event.type == EventType.THINK:
            # await send_message(
            #     chat_id=self.chat_id,
            #     text=f"💭 {event.content}"
            # )
            pass


class TelegramAdapter(BaseAdapter):
    """
    Telegram 适配器（继承 BaseAdapter）
    """

    name = "telegram"

    def __init__(self, token: str):
        super().__init__()
        self.token = token
        self._app: Optional[Application] = None
        self._sessions: dict[str, TelegramChannelSession] = {}

    async def start(self):
        """启动 Telegram Bot"""
        self._running = True

        self._app = Application.builder().token(self.token).build()

        # 添加消息处理器
        self._app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self._on_message
        ))

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()

    async def stop(self):
        """停止 Bot"""
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

    async def _on_message(self, update: Update, context):
        """处理消息"""
        chat_id = str(update.effective_chat.id)

        # 获取或创建会话
        if chat_id not in self._sessions:
            from fastreact import Agent
            agent = Agent()
            self._sessions[chat_id] = TelegramChannelSession(
                chat_id=chat_id,
                agent=agent
            )

        # 处理消息
        await self._sessions[chat_id].handle_message(
            update=update,
            send_message=self._send_message
        )

    async def _send_message(self, chat_id: str, text: str):
        """发送消息到 Telegram"""
        await self._app.bot.sendMessage(chat_id, text)
```

---

## 四、重构前后对比

### 4.1 重构前

```python
# Session 类：240 行，职责混乱
class Session:
    def __init__(...):
        self.websocket = ...        # 连接管理
        self._message_queue = ...   # 队列管理
        self.agent = ...            # Agent 管理
        self._history = ...         # 历史管理
        self._last_response_time = ...  # 跟随查询

    async def _handle_message(...):
        # 100+ 行的业务逻辑
        # - 跟随查询检测
        # - Agent 调用
        # - 事件流处理
        # - WebSocket 发送
```

**问题**:
- ❌ Session 类无法被其他通道复用（耦合了 WebSocket）
- ❌ 业务逻辑和连接管理混在一起
- ❌ Telegram/Discord 需要重复写相同的逻辑

---

### 4.2 重构后

```python
# SessionMixin：60 行，纯业务逻辑
class SessionMixin:
    def __init__(self, agent, ...):
        self._history = ...
        self._last_response_time = ...

    async def process_query(self, query, session_id, on_event):
        # 30 行的核心逻辑
        # - 跟随查询检测
        # - Agent 调用
        # - 事件流回调
        # - 历史更新

# GatewaySession：80 行，只管理 WebSocket
class GatewaySession:
    def __init__(...):
        self.websocket = ...
        self._message_queue = ...
        self._session_mixin = SessionMixin(...)  # ✅ 复用

    async def _handle_message(...):
        # 20 行的 Gateway 特定逻辑
        await self._session_mixin.process_query(...)

# TelegramChannelSession：50 行，只管理 Telegram
class TelegramChannelSession:
    def __init__(...):
        self._session_mixin = SessionMixin(...)  # ✅ 复用

    async def handle_message(...):
        # 15 行的 Telegram 特定逻辑
        await self._session_mixin.process_query(...)
```

**优点**:
- ✅ SessionMixin 可被所有通道复用
- ✅ 业务逻辑和连接管理分离
- ✅ 代码重复减少 70%+
- ✅ 易于测试（SessionMixin 是纯逻辑，无需 WebSocket）

---

## 五、BaseAdapter 的价值

### 5.1 统一接口

```python
# 所有适配器都有相同的接口
adapters = [
    GatewayAdapter(config),
    TelegramAdapter(token="..."),
    DiscordAdapter(token="..."),
]

# 统一启动
for adapter in adapters:
    await adapter.start()

# 统一停止
for adapter in adapters:
    await adapter.stop()
```

### 5.2 灵活的实现

**BaseAdapter 不强制**:
- ❌ 不强制如何管理会话
- ❌ 不强制如何处理消息
- ❌ 不强制如何发送响应

**每个适配器可以**:
- ✅ 自己决定 Session 的实现
- ✅ 自己决定是否使用 SessionMixin
- ✅ 自己决定消息处理流程

---

## 六、重构步骤

### Step 1: 提取 SessionMixin

```bash
# 创建新文件
touch fastreact/core/session_mixin.py
```

### Step 2: 创建 BaseAdapter

```bash
# 创建新文件
touch fastreact/adapters/base.py
```

### Step 3: 重构 GatewaySession

```python
# 修改 fastreact/adapters/gateway.py
# - 将业务逻辑移到 SessionMixin
# - GatewaySession 使用 SessionMixin
```

### Step 4: 实现 TelegramAdapter

```python
# 创建新文件
touch fastreact/adapters/telegram.py
# - 使用 SessionMixin
# - 实现 BaseAdapter 接口
```

### Step 5: 测试

```bash
# 确保功能不变
pytest tests/

# 手动测试
# - WebSocket Gateway
# - Telegram Bot
```

---

## 七、总结

### 7.1 核心答案

**问题**: 其他通道用得上 BaseAdapter 吗？

**答案**: **部分用得上**

- ✅ **BaseAdapter 接口**: 统一 start/stop 接口，有价值
- ✅ **SessionMixin**: 所有通道都需要，价值巨大
- ❌ **GatewaySession**: 无法直接复用（耦合了 WebSocket）

### 7.2 最佳实践

**推荐架构**:
```
BaseAdapter (统一接口)
    ↓
SessionMixin (共享业务逻辑)
    ↓
GatewaySession / TelegramSession (特定实现)
```

**关键原则**:
1. ✅ 提取共享逻辑到 SessionMixin
2. ✅ 保持 BaseAdapter 简单（只有 start/stop）
3. ✅ 每个适配器可以有自己的 Session 实现
4. ✅ SessionMixin 是可选项，不是强制

### 7.3 代码减少预估

| 文件 | 重构前 | 重构后 | 减少 |
|------|--------|--------|------|
| gateway.py | 807 行 | ~400 行 | 50% |
| telegram.py | 0 行 | ~200 行 | 新增 |
| session_mixin.py | 0 行 | ~100 行 | 新增 |
| base.py | 0 行 | ~30 行 | 新增 |
| **总计** | 807 行 | ~730 行 | 代码重复减少 70%+ |

---

**文档版本**: v1.0
**创建日期**: 2026-02-22
