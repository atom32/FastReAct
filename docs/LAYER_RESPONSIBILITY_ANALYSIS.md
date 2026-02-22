# 层间职责分析：FastReAct vs nanobot

**核心问题**：
1. Gateway Adapter 是否有太多逻辑？
2. core-agent-adapter 层间是否存在业务逻辑渗透？
3. 职责划分是否清晰？

---

## 一、nanobot 的分层架构（参考标准）

### 1.1 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                      nanobot Architecture                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Channel Layer (通道层)                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ TelegramChannel / DiscordChannel / ...             │    │
│  │                                                      │    │
│  │ 职责：                                               │    │
│  │ - 平台 SDK 初始化                                   │    │
│  │ - 平台事件监听                                      │    │
│  │ - 消息格式转换（平台格式 → InboundMessage）         │    │
│  │ - 消息发送（OutboundMessage → 平台格式）           │    │
│  │                                                      │    │
│  │ 不负责：                                             │    │
│  │ ❌ 会话管理（由 SessionManager 负责）                │    │
│  │ ❌ Agent 调用（由 AgentLoop 负责）                  │    │
│  │ ❌ 业务逻辑（由 AgentLoop 负责）                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ↓ publish_inbound()                  │
│                                                              │
│  MessageBus (消息总线)                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ - inbound_q: asyncio.Queue[InboundMessage]          │    │
│  │ - outbound_q: asyncio.Queue[OutboundMessage]        │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ↓ consume_inbound()                  │
│                                                              │
│  AgentLoop Layer (Agent 循环层)                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ AgentLoop                                            │    │
│  │                                                      │    │
│  │ 职责：                                               │    │
│  │ - 从 MessageBus 消费消息                             │    │
│  │ - 会话管理（通过 SessionManager）                    │    │
│  │ - 工具管理（ToolRegistry）                           │    │
│  │ - 上下文构建（ContextBuilder）                       │    │
│  │ - Agent 循环控制                                     │    │
│  │ - LLM 调用                                           │    │
│  │ - 工具执行                                           │    │
│  │ - 记忆管理（MemoryStore）                            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 TelegramChannel 的职责（清晰）

**代码量**: ~400 行

**核心逻辑**（仅 200 行）:
```python
class TelegramChannel(BaseChannel):
    async def start(self):
        """启动 Telegram Bot"""
        # 1. SDK 初始化
        self._app = Application.builder().token(self.config.token).build()

        # 2. 注册命令处理器
        self._app.add_handler(CommandHandler("start", self._on_start))

        # 3. 注册消息处理器
        self._app.add_handler(MessageHandler(filters.TEXT, self._on_message))

        # 4. 启动轮询
        await self._app.updater.start_polling()

    async def _on_message(self, update, context):
        """处理消息"""
        # 1. 提取消息数据
        sender_id = update.effective_user.id
        chat_id = update.effective_chat.id
        content = update.message.text

        # 2. 转换为 InboundMessage
        await self._handle_message(
            sender_id=sender_id,
            chat_id=chat_id,
            content=content
        )

    async def send(self, msg: OutboundMessage):
        """发送消息"""
        # 1. 转换格式（Markdown → Telegram HTML）
        html = _markdown_to_telegram_html(msg.content)

        # 2. 分割消息（Telegram 长度限制）
        for chunk in _split_message(html):
            await self._app.bot.send_message(
                chat_id=msg.chat_id,
                text=chunk,
                parse_mode="HTML"
            )
```

**辅助函数**（工具函数，不是业务逻辑）:
```python
# Markdown 转 HTML（100 行，纯格式转换）
def _markdown_to_telegram_html(text: str) -> str:
    # 转换 Markdown 格式到 Telegram HTML
    pass

# 消息分割（20 行，纯工具函数）
def _split_message(content: str, max_len: int = 4000) -> list[str]:
    # 分割长消息
    pass
```

**关键特征**:
- ✅ **职责单一**: 只负责平台 SDK 集成
- ✅ **无业务逻辑**: 不管理会话、不调用 Agent
- ✅ **格式转换**: 只做平台特定的格式转换
- ✅ **薄层**: 逻辑简单，易于理解

### 1.3 AgentLoop 的职责（清晰）

**代码量**: ~400 行

**核心逻辑**:
```python
class AgentLoop:
    async def run(self):
        """运行 Agent 循环"""
        while self._running:
            # 1. 从 MessageBus 消费消息
            msg = await self.bus.consume_inbound()

            # 2. 处理消息
            response = await self._process_message(msg)

            # 3. 发布响应到 MessageBus
            await self.bus.publish_outbound(response)

    async def _process_message(self, msg: InboundMessage):
        # 1. 获取或创建会话
        session = self.sessions.get_or_create(msg.session_key)

        # 2. 构建上下文（历史 + 记忆 + 技能）
        messages = self.context.build_messages(
            history=session.get_history(),
            current_message=msg.content,
        )

        # 3. 运行 Agent 循环
        final_content, tools_used = await self._run_agent_loop(messages)

        # 4. 更新会话
        session.add_message("user", msg.content)
        session.add_message("assistant", final_content)

        # 5. 返回响应
        return OutboundMessage(...)
```

**关键特征**:
- ✅ **职责清晰**: 处理消息、调用 LLM、执行工具
- ✅ **会话管理**: 通过 SessionManager
- ✅ **工具管理**: 通过 ToolRegistry
- ✅ **厚层**: 包含所有业务逻辑

---

## 二、FastReAct 的分层架构（问题分析）

### 2.1 当前架构

```
┌─────────────────────────────────────────────────────────────┐
│                   FastReAct Architecture                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Adapter Layer (适配器层)                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ GatewayAdapter                                       │    │
│  │                                                      │    │
│  │ 职责：                                               │    │
│  │ - FastAPI 服务器管理                                │    │
│  │ - WebSocket 连接管理                                │    │
│  │ - Session 管理（SessionManager）                     │    │
│  │ - 会话历史管理（_history, _max_history） ❌ 渗透     │    │
│  │ - 跟随查询检测（_last_response_time） ❌ 渗透       │    │
│  │ - Agent 调用（agent.run_event_stream） ❌ 渗透      │    │
│  │ - 事件流处理（async for event） ❌ 渗透             │    │
│  │ - 消息队列（_message_queue）                        │    │
│  │ - 中断处理（_interrupted） ❌ 渗透                  │    │
│  │                                                      │    │
│  │ 问题：                                               │    │
│  │ ❌ 业务逻辑渗透到 Adapter 层                        │    │
│  │ ❌ Session 职责过重（240 行）                       │    │
│  │ ❌ 与 nanobot 的 Channel 相比，逻辑太多             │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ↓ 直接调用                            │
│                                                              │
│  Agent Layer (Agent 层)                                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Agent                                                │    │
│  │                                                      │    │
│  │ 职责：                                               │    │
│  │ - Agent 循环控制                                     │    │
│  │ - 调用 Core（ReActCore）                            │    │
│  │ - 工具执行                                           │    │
│  │ - 安全检查                                           │    │
│  │ - 上下文监控                                         │    │
│  │ - 状态持久化                                         │    │
│  │                                                      │    │
│  │ 问题：                                               │    │
│  │ ❌ 会话历史由 Adapter 管理，不是 Agent               │    │
│  │ ❌ Agent 不知道历史，需要 Adapter 传入              │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ↓ 调用                               │
│                                                              │
│  Core Layer (Core 层)                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ReActCore                                            │    │
│  │                                                      │    │
│  │ 职责：                                               │    │
│  │ - 纯推理引擎                                         │    │
│  │ - LLM 调用                                           │    │
│  │ - 生成事件（THINK, TOOL_CALL, STEP_END）             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Gateway Session 的职责（混乱）

**代码量**: 240 行

**当前职责**（混杂）:
```python
class Session:
    """Gateway Session"""

    def __init__(self, session_id, websocket):
        # 1. 连接管理（✅ 应该在这里）
        self.websocket = websocket
        self._message_queue = asyncio.Queue()

        # 2. 会话状态（✅ 可以在这里）
        self._interrupted = False
        self._is_running = False

        # 3. Agent 实例（⚠️ 可选）
        self.agent = Agent()

        # 4. 会话历史（❌ 应该在 Agent 层）
        self._history: list[dict] = []
        self._max_history = 50

        # 5. 跟随查询检测（❌ 应该在 Agent 层）
        self._last_response_time: Optional[datetime] = None
        self._followup_window_seconds = 30

    async def _handle_message(self, message):
        """处理消息（❌ 业务逻辑，应该在 Agent 层）"""
        # 1. 跟随查询检测（❌ 业务逻辑）
        is_followup = self._is_followup()

        # 2. 检查 Agent 是否运行（❌ 业务逻辑）
        if self._is_running:
            # 发送用户干预信号（❌ 业务逻辑）
            self.agent._session_queues[...].push(
                Message.steering(...)
            )

        # 3. 调用 Agent（❌ 业务逻辑）
        async for event in self.agent.run_event_stream(
            query,
            history=self._history,  # ❌ Adapter 管理历史
        ):
            # 4. 发送事件（✅ Adapter 的职责）
            await self.send({"type": "event", ...})

            # 5. 跟踪最终响应（❌ 业务逻辑）
            if event.type == EventType.SESSION_END:
                final_response = event.content

        # 6. 更新历史（❌ 应该在 Agent 层）
        self._update_history(query, final_response)
```

**职责混乱**:
1. ❌ **会话历史管理**: 应该在 Agent 层，不是 Adapter
2. ❌ **跟随查询检测**: 应该在 Agent 层，不是 Adapter
3. ❌ **Agent 调用逻辑**: 应该在 Agent 层，不是 Adapter
4. ❌ **事件流处理**: 应该简化为回调
5. ✅ **WebSocket 管理**: 正确，应该在 Adapter
6. ✅ **消息队列**: 正确，应该在 Adapter

---

## 三、层间渗透分析

### 3.1 业务逻辑渗透到 Adapter 层

| 业务逻辑 | 当前位置 | 应该位置 | 问题 |
|---------|---------|----------|------|
| 会话历史管理 | Gateway Session._history | Agent 或 SessionMixin | Adapter 管理业务数据 |
| 跟随查询检测 | Gateway Session._is_followup() | Agent 或 SessionMixin | Adapter 管理业务逻辑 |
| Agent 调用循环 | Gateway Session._handle_message() | Agent | Adapter 包含核心循环 |
| 事件流处理 | Gateway Session async for event | Agent 或简化回调 | Adapter 处理流式逻辑 |
| 中断处理 | Gateway Session.interrupt() | Agent | Adapter 管理 Agent 状态 |

### 3.2 与 nanobot 对比

| 维度 | nanobot | FastReAct | 评价 |
|------|---------|-----------|------|
| **Channel 职责** | 平台 SDK + 格式转换 | WebSocket + **业务逻辑** | ❌ FastReAct 职责过多 |
| **Channel 代码量** | ~400 行（工具函数多） | ~807 行（业务逻辑多） | ❌ FastReAct 过重 |
| **会话管理** | AgentLoop 负责 | Gateway Session 负责 | ⚠️ 分层不同 |
| **Agent 调用** | AgentLoop 负责 | Gateway Session 负责 | ❌ Adapter 不应调用 |
| **历史管理** | AgentLoop 负责 | Gateway Session 负责 | ❌ Adapter 不应管理 |

---

## 四、正确分层方案

### 4.1 理想架构

```
┌─────────────────────────────────────────────────────────────┐
│                  Correct Layering Architecture               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Adapter Layer (适配器层)                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ GatewayAdapter / TelegramAdapter                   │    │
│  │                                                      │    │
│  │ 职责（仅连接管理）：                                 │    │
│  │ ✅ 平台 SDK 初始化                                  │    │
│  │ ✅ 连接管理（WebSocket/HTTP/Discord SDK）           │    │
│  │ ✅ 消息接收（平台格式 → 统一格式）                  │    │
│  │ ✅ 消息发送（统一格式 → 平台格式）                  │    │
│  │ ✅ 事件回调（on_event）                             │    │
│  │                                                      │    │
│  │ 不负责（业务逻辑）：                                 │    │
│  │ ❌ 会话历史管理                                      │    │
│  │ ❌ Agent 调用循环                                    │    │
│  │ ❌ 跟随查询检测                                      │    │
│  │ ❌ 业务逻辑                                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ↓ 纯事件流                           │
│                                                              │
│  Agent Layer (Agent 层)                                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Agent                                                │    │
│  │                                                      │    │
│  │ 职责（核心业务）：                                   │    │
│  │ ✅ 会话历史管理（_history）                         │    │
│  │ ✅ 会话状态管理（Session）                          │    │
│  │ ✅ Agent 循环控制                                    │    │
│  │ ✅ 跟随查询检测（_is_followup）                     │    │
│  │ ✅ Core 调用                                        │    │
│  │ ✅ 工具执行                                          │    │
│  │ ✅ 安全检查                                          │    │
│  │ ✅ 状态持久化                                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ↓ 纯推理                            │
│                                                              │
│  Core Layer (Core 层)                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ReActCore                                            │    │
│  │                                                      │    │
│  │ 职责（纯推理）：                                     │    │
│  │ ✅ LLM 调用                                          │    │
│  │ ✅ 生成事件（THINK, TOOL_CALL）                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 重新设计的 SessionMixin

```python
# fastreact/core/session.py

from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from fastreact import Agent, EventType


class AgentSession:
    """
    Agent 会话（核心业务逻辑）

    职责：
    - 会话历史管理
    - 跟随查询检测
    - Agent 循环控制
    """

    def __init__(
        self,
        agent: Agent,
        session_id: str,
        max_history: int = 50,
        followup_window_seconds: int = 30,
    ):
        self.agent = agent
        self.session_id = session_id

        # ✅ 会话历史（核心业务数据）
        self._history: List[Dict[str, Any]] = []
        self._max_history = max_history

        # ✅ 跟随查询检测（核心业务逻辑）
        self._last_response_time: Optional[datetime] = None
        self._followup_window_seconds = followup_window_seconds

        # ✅ 会话状态
        self._is_running = False
        self._interrupted = False

    def get_history(self) -> List[Dict[str, Any]]:
        """获取会话历史"""
        return self._history.copy()

    def is_followup(self) -> bool:
        """检查是否是跟随查询"""
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

        # 自动裁剪
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # 更新时间
        self._last_response_time = datetime.utcnow()

    async def process_query(
        self,
        query: str,
        on_event: Callable,  # 事件回调
        skills: Optional[List[str]] = None,
    ) -> str:
        """
        处理查询（核心业务逻辑）

        Args:
            query: 用户查询
            on_event: 事件回调 async def on_event(event: AgentEvent)
            skills: 可选 SKILL 列表

        Returns:
            最终响应文本
        """
        self._is_running = True
        final_response = None
        is_followup = self.is_followup()

        try:
            # 调用 Agent
            async for event in self.agent.run_event_stream(
                query,
                skills=skills,
                session_id=self.session_id,
                history=self._history if is_followup else [],
            ):
                # 检查中断
                if self._interrupted:
                    break

                # 触发事件回调
                await on_event(event)

                # 记录最终响应
                if event.type == EventType.SESSION_END:
                    final_response = event.content

            # 更新历史
            if final_response and not self._interrupted:
                self.update_history(query, final_response)

            return final_response

        finally:
            self._is_running = False

    def interrupt(self):
        """中断当前执行"""
        self._interrupted = True

    def reset_interrupt(self):
        """重置中断标志"""
        self._interrupted = False
```

### 4.3 简化的 Gateway Session

```python
# fastreact/adapters/gateway.py

class GatewaySession:
    """
    Gateway 会话（仅连接管理）

    职责：
    - WebSocket 连接管理
    - 消息队列
    - 事件发送
    """

    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket

        # ✅ 连接管理（Adapter 的职责）
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=5)

        # ✅ 使用 AgentSession（业务逻辑在 Agent 层）
        from fastreact.core.session import AgentSession
        self.agent_session = AgentSession(
            agent=Agent(),
            session_id=session_id
        )

    async def send(self, message: dict):
        """发送消息到客户端（Adapter 的职责）"""
        try:
            await self.websocket.send_json(message)
        except Exception:
            pass

    async def enqueue_message(self, message: dict) -> bool:
        """将消息加入队列（Adapter 的职责）"""
        if self._message_queue.qsize() >= 5:
            return False
        await self._message_queue.put(message)
        return True

    async def process_queue(self):
        """处理消息队列（Adapter 的职责）"""
        while True:
            message = await self._message_queue.get()
            await self._handle_message(message)

    async def _handle_message(self, message: dict):
        """处理消息（简化为委托）"""
        msg_type = message.get("type")

        if msg_type == "control":
            if message.get("action") == "interrupt":
                self.agent_session.interrupt()
                await self.send({"type": "info", "content": "Interrupted"})

        elif msg_type == "query":
            query = message.get("content", "")
            skills = message.get("skills")

            # ✅ 委托给 AgentSession（业务逻辑在 Agent 层）
            final_response = await self.agent_session.process_query(
                query=query,
                on_event=self._on_agent_event,  # 回调
                skills=skills,
            )

    async def _on_agent_event(self, event):
        """Agent 事件回调（Adapter 的职责：发送事件）"""
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
```

### 4.4 代码量对比

| 文件 | 重构前 | 重构后 | 说明 |
|------|--------|--------|------|
| Gateway Session | 240 行 | 80 行 | 只管理连接 |
| AgentSession | 0 行 | 150 行 | 新增，业务逻辑 |
| **总计** | 240 行 | 230 行 | 逻辑更清晰 |

---

## 五、层间职责清单

### 5.1 Adapter 层（薄层）

**职责**（✅ 应该做的）:
- ✅ 平台 SDK 初始化（Telegram/Discord SDK）
- ✅ 连接管理（WebSocket/HTTP 连接）
- ✅ 消息接收（平台格式 → 统一格式）
- ✅ 消息发送（统一格式 → 平台格式）
- ✅ 格式转换（Markdown → Telegram HTML）
- ✅ 消息分割（处理平台限制）
- ✅ 事件回调（on_event）
- ✅ 消息队列（可选，用于并发控制）

**职责**（❌ 不应该做的）:
- ❌ 会话历史管理
- ❌ 跟随查询检测
- ❌ Agent 循环控制
- ❌ 业务逻辑
- ❌ 状态持久化

**代码量**: 应该在 100-200 行（工具函数除外）

### 5.2 Agent 层（厚层）

**职责**（✅ 应该做的）:
- ✅ 会话历史管理（_history）
- ✅ 会话状态管理（Session）
- ✅ 跟随查询检测（_is_followup）
- ✅ Agent 循环控制
- ✅ Core 调用
- ✅ 工具执行
- ✅ 安全检查
- ✅ 状态持久化
- ✅ SKILL 加载
- ✅ MCP 管理

**职责**（❌ 不应该做的）:
- ❌ 平台特定逻辑
- ❌ 消息格式转换
- ❌ 连接管理

**代码量**: 可以在 500-1000 行（包含所有业务逻辑）

### 5.3 Core 层（纯推理）

**职责**（✅ 应该做的）:
- ✅ LLM 调用
- ✅ 生成事件（THINK, TOOL_CALL）
- ✅ 工具 Schema 生成

**职责**（❌ 不应该做的）:
- ❌ 工具执行
- ❌ 状态管理
- ❌ 历史管理
- ❌ 业务逻辑

**代码量**: 应该在 200 行以内（纯推理）

---

## 六、总结

### 6.1 核心问题

**问题 1**: Gateway Adapter 有太多逻辑吗？
- ✅ **是的**，240 行，包含大量业务逻辑

**问题 2**: 层间存在渗透吗？
- ✅ **是的**，业务逻辑渗透到 Adapter 层

**问题 3**: 职责划分清晰吗？
- ❌ **不清晰**，Adapter 承担了 Agent 的职责

### 6.2 根本原因

**当前问题**:
1. Gateway Session 管理会话历史（应该是 Agent）
2. Gateway Session 检测跟随查询（应该是 Agent）
3. Gateway Session 调用 Agent 循环（应该是 Agent）
4. Agent 不知道历史（需要 Adapter 传入）

**nanobot 的优势**:
1. Channel 只做平台集成
2. AgentLoop 包含所有业务逻辑
3. 职责清晰，易于理解

### 6.3 正确分层原则

**核心原则**: **Adapter 是薄层，Agent 是厚层，Core 是纯层**

```
Adapter (薄层) ← nanobot 做对了
  ↓ 只负责连接
Agent (厚层)   ← FastReAct 需要改进
  ↓ 包含业务逻辑
Core (纯层)   ← FastReAct 已经做得很好
  ↓ 只负责推理
```

### 6.4 改进建议

**优先级 1（立即执行）**:
1. ✅ 提取 AgentSession 类（包含历史、跟随查询检测）
2. ✅ 简化 Gateway Session（只管理连接）
3. ✅ 移除业务逻辑从 Adapter 层

**优先级 2（1-2 周）**:
4. ✅ 所有 Adapter 使用统一的 AgentSession
5. ✅ Agent 管理 Session，不是 Adapter

**预期收益**:
- ✅ 职责清晰，易于理解
- ✅ Adapter 可复用（Telegram、Discord）
- ✅ 测试更容易（AgentSession 可独立测试）

---

**文档版本**: v1.0
**创建日期**: 2026-02-22
