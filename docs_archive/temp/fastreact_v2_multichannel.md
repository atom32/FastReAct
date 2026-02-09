# FastReAct v2.0：小巧核心 + 多渠道支持

## 执行摘要（更新版）

**核心理念**：完全解耦的核心与渠道

```
极简核心（<2000 行）+ 丰富渠道（<3000 行）= FastReAct v2.0
```

**关键设计**：
- **核心**：纯 ReAct 推理引擎，零渠道依赖
- **渠道**：独立模块，通过统一接口连接
- **桥接**：轻量级适配层，<100 行

---

## 一、解耦架构

### 1.1 核心原则

**核心引擎（Core）**：
- ✅ 只做推理（ReAct 循环）
- ✅ 只依赖工具接口
- ✅ 零渠道依赖
- ✅ <2000 行代码

**渠道层（Channels）**：
- ✅ 完全独立模块
- ✅ 可插拔设计
- ✅ 统一接口
- ✅ 每个渠道 <500 行

**统一接口（Bridge）**：
- ✅ MessageBus 抽象
- ✅ 标准消息格式
- ✅ 协议无关
- ✅ <100 行

### 1.2 架构图

```
┌─────────────────────────────────────────────────────────┐
│                      用户层                              │
├─────────────────────────────────────────────────────────┤
│  CLI    │   Web   │  API   │  IM   │  Email  │  Slack  │
│ (REPL)  │ (HTTP)  │ (REST) │ (Telegram/Discord) │  │
└──────────┼─────────┼────────┼───────┼─────────┼────────┘
           │         │        │       │         │
           └─────────┴────────┴───────┴─────────┘
                     │
        ┌────────────▼────────────┐
        │   MessageBus (Bridge)    │
        │  - 统一消息格式          │
        │  - 会话管理              │
        │  - 事件分发              │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │   ReAct Core Engine      │
        │  - 推理循环              │
        │  - 工具调用              │
        │  - 上下文管理            │
        │  - 记忆系统              │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │     Tool Registry       │
        │  - 文件系统              │
        │  - Shell 执行            │
        │  - Web 工具              │
        │  - 自定义工具            │
        └──────────────────────────┘
```

**关键点**：
- 核心 = 纯推理，不知道"渠道"是什么
- 渠道 = 纯交互，不知道"推理"是什么
- MessageBus = 唯一连接点，完全解耦

---

## 二、核心引擎设计

### 2.1 极简核心

**设计目标**：
- <2000 行代码
- 零渠道依赖
- 纯推理逻辑

**实现**：

```python
class ReActCore:
    """
    极简 ReAct 核心引擎

    职责：
    1. 运行 ReAct 推理循环
    2. 调用工具
    3. 管理会话上下文
    4. 返回推理结果

    不负责：
    - 渠道交互（CLI/Web/API...）
    - 消息格式（文本/语音/图片...）
    - 用户界面（命令行/WebUI...）
    """

    def __init__(
        self,
        provider: LLMProvider,
        tools: ToolRegistry,
        memory: MemoryStore,
        config: CoreConfig,
    ):
        self.provider = provider
        self.tools = tools
        self.memory = memory
        self.config = config

    async def reason(
        self,
        query: str,
        context: dict,
    ) -> ReasoningResult:
        """
        执行推理（核心接口）

        Args:
            query: 用户查询
            context: 会话上下文（历史、用户ID等）

        Returns:
            推理结果（答案、步骤、指标）
        """
        # ReAct 循环
        for iteration in range(self.config.max_iterations):
            # 1. 思考
            thought = await self._think(query, context)

            # 2. 行动
            actions = self._parse_actions(thought)

            # 3. 观察
            observations = await self._execute_actions(actions)

            # 4. 判断
            if self._should_stop(observations):
                break

            # 更新上下文
            context = self._update_context(context, observations)

        # 返回结果
        return ReasoningResult(
            answer=context["last_message"],
            steps=context["history"],
            metrics=self._collect_metrics(),
        )
```

**关键设计**：
- `reason()` 方法 - 唯一对外接口
- 输入：`query` + `context`
- 输出：`ReasoningResult`
- 完全不知道"渠道"是什么

### 2.2 标准消息格式

**设计目标**：
- 渠道无关
- 支持多种消息类型
- 可扩展

**实现**：

```python
@dataclass
class StandardMessage:
    """标准消息格式（渠道无关）"""

    # 基础字段
    session_id: str                      # 会话 ID
    content: str                         # 消息内容

    # 元数据
    user_id: str | None = None           # 用户 ID
    channel_type: str | None = None      # 渠道类型（cli/web/api...）
    channel_metadata: dict = field(default_factory=dict)

    # 附件
    attachments: list[Attachment] = field(default_factory=list)

    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Attachment:
    """消息附件"""
    type: str  # "image", "file", "audio", "video"...
    uri: str   # 文件路径或 URL
    metadata: dict = field(default_factory=dict)

@dataclass
class ReasoningResult:
    """推理结果"""
    answer: str                          # 最终答案
    steps: list[dict]                    # 推理步骤
    metrics: dict                        # 性能指标
    attachments: list[Attachment] = field(default_factory=list)  # 可返回文件
```

**关键点**：
- `StandardMessage` - 统一输入格式
- `ReasoningResult` - 统一输出格式
- 任何渠道都可以转换到这个格式

---

## 三、渠道层设计

### 3.1 统一渠道接口

**设计目标**：
- 所有渠道实现同一接口
- 插件化注册
- 独立开发和测试

**实现**：

```python
class Channel(ABC):
    """
    渠道接口

    所有渠道（CLI、Web、API、IM...）都必须实现此接口
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """渠道名称"""
        pass

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """渠道类型（cli/web/api/im/email...）"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动渠道"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止渠道"""
        pass

    @abstractmethod
    async def send(self, message: ReasoningResult, recipient: str) -> None:
        """发送消息到用户"""
        pass

    @abstractmethod
    async def receive(self) -> StandardMessage | None:
        """接收用户消息（非阻塞）"""
        pass
```

### 3.2 渠道实现示例

#### **CLI 渠道**（~400 行）

```python
class CLIChannel(Channel):
    """命令行渠道"""

    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self.running = False

    @property
    def name(self) -> str:
        return "cli"

    @property
    def channel_type(self) -> str:
        return "cli"

    async def start(self) -> None:
        """启动 CLI REPL"""
        self.running = True
        while self.running:
            # 1. 读取用户输入
            user_input = await self._read_input()

            # 2. 转换为标准消息
            message = StandardMessage(
                session_id="cli-session",
                content=user_input,
                channel_type="cli",
            )

            # 3. 发送到 MessageBus
            result = await self.message_bus.process(message)

            # 4. 显示结果
            print(result.answer)

    async def stop(self) -> None:
        """停止 CLI"""
        self.running = False

    async def send(self, result: ReasoningResult, recipient: str) -> None:
        """发送消息（CLI 就是打印）"""
        print(result.answer)

    async def receive(self) -> StandardMessage | None:
        """接收消息（异步读取）"""
        # 使用 aiofiles 实现非阻塞读取
        ...
```

#### **Web 渠道**（~500 行）

```python
class WebChannel(Channel):
    """Web 渠道（FastAPI + WebSocket）"""

    def __init__(self, message_bus: MessageBus, host: str = "0.0.0.0", port: int = 8000):
        self.message_bus = message_bus
        self.host = host
        self.port = port
        self.app = FastAPI()
        self.websocket_manager = WebSocketManager()

    @property
    def name(self) -> str:
        return "web"

    @property
    def channel_type(self) -> str:
        return "web"

    async def start(self) -> None:
        """启动 Web 服务器"""
        # WebSocket 端点
        @self.app.websocket("/ws/{session_id}")
        async def websocket_endpoint(websocket: WebSocket, session_id: str):
            await websocket.accept()
            self.websocket_manager.connect(session_id, websocket)

            # 接收消息
            while True:
                data = await websocket.receive_text()

                # 转换为标准消息
                message = StandardMessage(
                    session_id=session_id,
                    content=data,
                    channel_type="web",
                )

                # 发送到 MessageBus
                result = await self.message_bus.process(message)

                # 发送回客户端
                await websocket.send_json({
                    "answer": result.answer,
                    "steps": result.steps,
                })

        # 启动服务器
        import uvicorn
        config = uvicorn.Config(self.app, host=self.host, port=self.port)
        server = uvicorn.Server(config)
        await server.serve()

    async def send(self, result: ReasoningResult, recipient: str) -> None:
        """发送消息到 WebSocket 客户端"""
        websocket = self.websocket_manager.get(recipient)
        if websocket:
            await websocket.send_json({
                "answer": result.answer,
                "steps": result.steps,
            })

    async def receive(self) -> StandardMessage | None:
        """接收消息（通过 WebSocket 回调）"""
        # WebSocket 通过回调处理，这里返回 None
        return None
```

#### **IM 渠道**（~600 行）

```python
class TelegramChannel(Channel):
    """Telegram 渠道"""

    def __init__(self, message_bus: MessageBus, token: str):
        self.message_bus = message_bus
        self.token = token
        self.bot = Bot(token)

    @property
    def name(self) -> str:
        return "telegram"

    @property
    def channel_type(self) -> str:
        return "im"

    async def start(self) -> None:
        """启动 Telegram Bot"""
        @self.bot.message_handler()
        async def handle_message(message):
            # 提取图片
            attachments = []
            if message.photo:
                # 获取最大尺寸的图片
                photo = message.photo[-1]
                file = await self.bot.get_file(photo.file_id)
                attachments.append(Attachment(
                    type="image",
                    uri=file.file_path,
                ))

            # 转换为标准消息
            std_message = StandardMessage(
                session_id=str(message.chat.id),
                content=message.text or "",
                user_id=str(message.from_user.id),
                channel_type="im",
                channel_metadata={
                    "platform": "telegram",
                    "chat_id": message.chat.id,
                },
                attachments=attachments,
            )

            # 发送到 MessageBus
            result = await self.message_bus.process(std_message)

            # 发送回 Telegram
            await message.reply(result.answer)

        await self.bot.infinity_polling()

    async def send(self, result: ReasoningResult, recipient: str) -> None:
        """发送消息到 Telegram"""
        chat_id = int(recipient)
        await self.bot.send_message(chat_id, result.answer)

    async def receive(self) -> StandardMessage | None:
        """接收消息（通过回调）"""
        return None
```

---

## 四、MessageBus 桥接层

### 4.1 统一消息总线

**设计目标**：
- 连接核心和渠道
- 会话管理
- 事件分发
- <100 行代码

**实现**：

```python
class MessageBus:
    """
    消息总线 - 连接核心和渠道

    职责：
    1. 接收来自渠道的 StandardMessage
    2. 调用核心引擎进行推理
    3. 返回 ReasoningResult 给渠道
    4. 管理会话状态
    """

    def __init__(
        self,
        core: ReActCore,
        session_manager: SessionManager,
    ):
        self.core = core
        self.sessions = session_manager

    async def process(
        self,
        message: StandardMessage,
    ) -> ReasoningResult:
        """
        处理消息（主入口）

        Args:
            message: 标准消息

        Returns:
            推理结果
        """
        # 1. 获取或创建会话
        session = self.sessions.get_or_create(message.session_id)

        # 2. 构建上下文
        context = {
            "history": session.get_history(),
            "user_id": message.user_id,
            "channel_type": message.channel_type,
            "attachments": message.attachments,
        }

        # 3. 调用核心推理
        result = await self.core.reason(
            query=message.content,
            context=context,
        )

        # 4. 保存会话
        session.add_message({
            "role": "user",
            "content": message.content,
        })
        session.add_message({
            "role": "assistant",
            "content": result.answer,
        })

        # 5. 返回结果
        return result
```

### 4.2 会话管理

**设计目标**：
- 简单的会话持久化
- 支持多会话并发
- 内存 + 文件双重存储

**实现**：

```python
class SessionManager:
    """会话管理器"""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.sessions: dict[str, Session] = {}

    def get_or_create(self, session_id: str) -> Session:
        """获取或创建会话"""
        if session_id not in self.sessions:
            # 尝试从文件加载
            session_file = self.storage_path / f"{session_id}.jsonl"
            if session_file.exists():
                self.sessions[session_id] = self._load_session(session_file)
            else:
                self.sessions[session_id] = Session(session_id)

        return self.sessions[session_id]

    def _load_session(self, path: Path) -> Session:
        """从文件加载会话"""
        session = Session(path.stem)
        for line in path.read_text().splitlines():
            message = json.loads(line)
            session.add_message(message)
        return session

    def save_all(self) -> None:
        """保存所有会话"""
        for session_id, session in self.sessions.items():
            session_file = self.storage_path / f"{session_id}.jsonl"
            with open(session_file, "w") as f:
                for message in session.get_history():
                    f.write(json.dumps(message) + "\n")
```

---

## 五、完整目录结构

```
fastreact/
├── core/                          # 核心引擎 (~2000 行)
│   ├── __init__.py
│   ├── engine.py                  # ReAct 核心推理 (~500 行)
│   ├── context.py                 # 上下文构建 (~300 行)
│   ├── memory.py                  # 记忆系统 (~200 行)
│   ├── tools.py                   # 工具注册表 (~200 行)
│   └── session.py                 # 会话管理 (~200 行)
│
├── channels/                      # 渠道层 (~2500 行)
│   ├── __init__.py
│   ├── base.py                    # 渠道基类 (~100 行)
│   ├── cli.py                     # CLI 渠道 (~400 行)
│   ├── web.py                     # Web 渠道 (~500 行)
│   ├── api.py                     # API 渠道 (~400 行)
│   ├── telegram.py                # Telegram 渠道 (~500 行)
│   ├── discord.py                 # Discord 渠道 (~400 行)
│   └── email.py                   # Email 渠道 (~200 行)
│
├── bridge/                        # 桥接层 (~200 行)
│   ├── __init__.py
│   ├── messagebus.py              # 消息总线 (~100 行)
│   ├── message.py                 # 标准消息格式 (~50 行)
│   └── session.py                 # 会话管理 (~50 行)
│
├── tools/                         # 工具实现 (~1500 行)
│   ├── base.py                    # 工具基类 (~100 行)
│   ├── registry.py                # 工具注册表 (~200 行)
│   ├── filesystem.py              # 文件操作 (~400 行)
│   ├── shell.py                   # Shell 执行 (~300 行)
│   ├── web.py                     # Web 工具 (~300 行)
│   └── custom/                    # 自定义工具目录
│
├── providers/                     # LLM 提供商 (~800 行)
│   ├── __init__.py
│   ├── base.py                    # 提供商基类 (~100 行)
│   ├── openai.py                  # OpenAI (~150 行)
│   ├── anthropic.py               # Anthropic (~150 行)
│   ├── deepseek.py                # DeepSeek (~100 行)
│   └── registry.py                # 提供商注册表 (~100 行)
│
├── plugins/                       # 可选插件
│   ├── observability/             # 可观测性 (~500 行)
│   │   ├── tracker.py
│   │   ├── metrics.py
│   │   └── logger.py
│   ├── storage/                   # 存储插件 (~600 行)
│   │   ├── vector.py
│   │   └── checkpoint.py
│   └── channels/                  # 渠道插件（用户自定义）
│       └── slack.py               # Slack 渠道示例
│
├── cli/                           # 命令行工具 (~500 行)
│   ├── main.py                    # CLI 入口
│   ├── commands.py                # CLI 命令
│   └── repl.py                    # REPL 实现
│
├── server/                        # Web 服务器 (~300 行)
│   ├── main.py                    # FastAPI 入口
│   └── routes.py                  # API 路由
│
├── templates/                     # 模板文件
│   ├── config.yaml                # 配置模板
│   ├── agents/                    # Agent 定义模板
│   │   └── default/
│   │       ├── AGENTS.md
│   │       ├── TOOLS.md
│   │       └── CONSTRAINTS.md
│   └── skills/                    # 技能模板
│       └── example/SKILL.md
│
└── tests/                         # 测试
    ├── test_core/                 # 核心测试
    ├── test_channels/             # 渠道测试
    └── test_integration/          # 集成测试
```

**代码分布**：
- 核心：2000 行
- 渠道：2500 行
- 桥接：200 行
- 工具：1500 行
- 提供商：800 行
- **总计：~7000 行**（v1.0 的 14%，仍然极简！）

---

## 六、使用示例

### 6.1 单渠道启动

**CLI 模式**：
```python
from fastreact import ReActCore, MessageBus
from fastreact.channels import CLIChannel

# 创建核心
core = ReActCore(
    provider=OpenAIProvider(),
    tools=ToolRegistry(),
    memory=MemoryStore(),
)

# 创建消息总线
bus = MessageBus(core)

# 创建渠道
cli = CLIChannel(bus)

# 启动
await cli.start()
```

**Web 模式**：
```python
from fastreact.channels import WebChannel

# 创建 Web 渠道
web = WebChannel(
    message_bus=bus,
    host="0.0.0.0",
    port=8000,
)

# 启动
await web.start()
```

### 6.2 多渠道启动

**同时启动多个渠道**：
```python
import asyncio

async def main():
    # 创建核心和总线
    core = ReActCore(...)
    bus = MessageBus(core)

    # 创建多个渠道
    channels = [
        CLIChannel(bus),
        WebChannel(bus, port=8000),
        TelegramChannel(bus, token="..."),
    ]

    # 并发启动所有渠道
    await asyncio.gather(*[
        channel.start() for channel in channels
    ])

asyncio.run(main())
```

**效果**：
- 同一个核心引擎
- 支持多个渠道同时接入
- 会话完全独立
- 资源共享（工具、记忆）

---

## 七、关键优势

### 7.1 完全解耦

| 层次 | 职责 | 依赖 |
|------|------|------|
| **核心** | 推理 | 只依赖工具 |
| **桥接** | 连接 | 依赖核心 |
| **渠道** | 交互 | 只依赖桥接 |
| **工具** | 能力 | 只依赖接口 |

**关键点**：
- 核心不知道"渠道"是什么
- 渠道不知道"推理"是什么
- 两者通过 MessageBus 解耦

### 7.2 极易扩展

**添加新渠道**（3 步）：

1. **实现 Channel 接口**
```python
class SlackChannel(Channel):
    @property
    def name(self) -> str: return "slack"

    async def start(self) -> None: ...

    async def send(self, result, recipient) -> None: ...
```

2. **注册到系统**
```python
# config.yaml
channels:
  - type: slack
    token: ${SLACK_TOKEN}
```

3. **启动**
```bash
fastreact --channels slack,cli,web
```

**完成！** 无需修改核心代码

### 7.3 资源共享

**所有渠道共享**：
- ✅ 同一个核心引擎
- ✅ 同一套工具
- ✅ 同一个记忆系统
- ✅ 同一个 LLM 连接

**各自独立**：
- ✅ 各自的会话
- ✅ 各自的用户 ID
- ✅ 各自的配置

---

## 八、性能优化

### 8.1 并发处理

**多用户并发**：
```python
class MessageBus:
    async def process(self, message: StandardMessage) -> ReasoningResult:
        # 使用任务键实现并发安全
        async with self._lock(message.session_id):
            # 处理消息
            result = await self.core.reason(...)

        return result
```

**关键点**：
- 同一会话串行处理
- 不同会话并行处理
- 无锁竞争

### 8.2 资源池化

**LLM 连接池**：
```python
class LLMProviderPool:
    """LLM 提供商池"""

    def __init__(self, providers: list[LLMProvider]):
        self.providers = providers
        self.current = 0

    async def chat(self, messages, tools):
        # 轮询选择提供商
        provider = self.providers[self.current]
        self.current = (self.current + 1) % len(self.providers)

        return await provider.chat(messages, tools)
```

**工具执行池**：
```python
class ToolExecutor:
    """工具执行器（线程池）"""

    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def execute(self, tool_name: str, args: dict) -> str:
        # 在线程池中执行工具
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.tools.get(tool_name).execute,
            args,
        )
```

---

## 九、代码量对比（更新）

| 模块 | v1.0 | v2.0 | 说明 |
|------|------|------|------|
| **核心** | 30,000 | 2,000 | 只保留 ReAct |
| **GraphAgent** | 2,500 | 0 | 移除 |
| **IEL** | 2,000 | 0 | 移除 |
| **渠道** | 2,000 | 2,500 | 保留并增强 |
| **工具** | 4,000 | 1,500 | 简化 |
| **桥接** | 0 | 200 | 新增 |
| **插件** | 0 | 1,100 | 可选 |
| **其他** | 10,292 | 300 | 简化 |
| **总计** | **50,792** | **~7,100** | **7.2x 精简** |

**关键点**：
- 核心极简（2000 行）
- 渠道丰富（2500 行）
- 总量仍然很小（7100 行）

---

## 十、迁移计划（更新）

### 10.1 阶段 1：核心提取（1 周）

**目标**：提取极简核心

**任务**：
1. ✅ 创建 `core/` 目录
2. ✅ 实现 `ReactCore` (<500 行)
3. ✅ 实现 `MessageBus` (<100 行)
4. ✅ 实现 `StandardMessage` (<50 行)
5. ✅ 单元测试

**输出**：
- `core/engine.py` (~500 行)
- `bridge/messagebus.py` (~100 行)
- `bridge/message.py` (~50 行)

### 10.2 阶段 2：渠道重构（2 周）

**目标**：重构所有渠道

**任务**：
1. ✅ 实现 `Channel` 接口
2. ✅ 重构 CLI 渠道
3. ✅ 重构 Web 渠道
4. ✅ 实现 Telegram 渠道
5. ✅ 实现 Discord 渠道
6. ✅ 集成测试

**输出**：
- `channels/base.py` (~100 行)
- `channels/cli.py` (~400 行)
- `channels/web.py` (~500 行)
- `channels/telegram.py` (~500 行)
- `channels/discord.py` (~400 行)

### 10.3 阶段 3：插件系统（1 周）

**目标**：实现插件架构

**任务**：
1. ✅ 设计插件接口
2. ✅ 实现插件加载器
3. ✅ 迁移可观测性
4. ✅ 迁移存储

**输出**：
- `plugins/` 目录
- 插件开发文档

### 10.4 阶段 4：测试和发布（2 周）

**目标**：全面测试和发布

**任务**：
1. ✅ 集成测试
2. ✅ 性能测试
3. ✅ 压力测试
4. ✅ 文档更新
5. ✅ 发布 v2.0

---

## 十一、最终总结

### 11.1 核心价值

**FastReAct v2.0 = 极简核心 + 丰富渠道**

1. **极简核心** - <2000 行实现完整 ReAct
2. **丰富渠道** - 支持 CLI、Web、API、IM...
3. **完全解耦** - 核心和渠道零依赖
4. **易于扩展** - 添加新渠道只需 3 步
5. **生产就绪** - 并发、池化、可观测

### 11.2 与竞品对比

| 特性 | nanobot | Claude Code | FastReAct v1 | FastReAct v2 |
|------|---------|-------------|--------------|---------------|
| **代码行数** | 7,095 | 未知 | 50,792 | **~7,100** |
| **核心大小** | ~2000 | 未知 | ~30000 | **~2,000** |
| **渠道支持** | ✅ (多) | ❌ (1) | ✅ (多) | **✅ (多)** |
| **企业特性** | ❌ | ✅ | ✅ | **✅** |
| **可扩展性** | ⚠️ | ❌ | ⚠️ | **✅** |
| **解耦架构** | ⚠️ | ❌ | ❌ | **✅** |

### 11.3 关键创新

1. **完全解耦架构**
   - 核心只做推理
   - 渠道只做交互
   - MessageBus 连接

2. **标准消息格式**
   - 渠道无关
   - 类型安全
   - 易于扩展

3. **插件化渠道**
   - 热插拔
   - 独立开发
   - 按需加载

### 11.4 满足所有需求

✅ **小巧且强大的核心** - <2000 行实现完整 ReAct
✅ **多种渠道支持** - CLI、Web、API、IM...
✅ **企业级特性** - 可观测、可靠、可扩展
✅ **易于维护** - 清晰的模块边界
✅ **易于扩展** - 添加新渠道只需 3 步

---

**这就是你想要的"贪心"方案！** 🚀
