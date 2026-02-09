# FastReAct Universal Agent Design v2
## 融合 Nanobot + Moltbot + FastReAct 的万能智能体方案

**更新日期**: 2026-02-10
**基于真实架构**: D:/moltbot 完整分析

---

## 一、三大框架深度对比

### 1.1 Moltbot - 企业级多平台助手 (82,168行)

| 特性 | 实现 | 优势 |
|------|------|------|
| **规模** | 2,500 TS文件, 82k行代码 | 生产就绪 |
| **渠道** | 7+平台 (WhatsApp, Telegram, Discord, Slack等) | 全覆盖 |
| **架构** | Gateway中心化 + WebSocket | 实时双向通信 |
| **技能** | 53个预构建技能 | 开箱即用 |
| **UI** | Canvas实时界面 + 原生应用 | 极致体验 |
| **Agent** | Pi Agent集成 | 企业级AI |

**核心架构**:
```
┌─────────────────────────────────────────────────────────┐
│                    Moltbot Gateway                       │
│  (WebSocket Server + Session Manager + Plugin Registry) │
└────────────┬────────────────────────────────────────────┘
             │
    ┌────────┼────────┬────────┬────────┬────────┐
    │        │        │        │        │        │
┌───▼───┐ ┌─▼───┐ ┌─▼────┐ ┌─▼─────┐ ┌─▼──────┐
│WhatsApp│ │Telegram│ │Discord│ │Slack │ │iMessage│ ...
└───────┘ └─────┘ └──────┘ └───────┘ └───────┘
    │        │        │        │        │
    └────────┴────────┴────────┴────────┘
                  │
         ┌────────▼────────┐
         │  Pi Agent Core  │
         │  (LLM + Skills) │
         └─────────────────┘
```

**关键特性**:
1. **Gateway模式**: 单一控制平面，所有渠道通过WebSocket连接
2. **实时流式**: 消息即时推送，支持thinking状态
3. **插件系统**: 运行时加载，热重载
4. **原生应用**: Swift (iOS/macOS) + Kotlin (Android)
5. **会话管理**: 跨平台统一会话状态

### 1.2 Nanobot - 轻量级个人助手 (3,510行)

| 特性 | 实现 | 优势 |
|------|------|------|
| **规模** | 52 Python文件, 3.5k行 | 极简 |
| **架构** | MessageBus + 异步队列 | 解耦 |
| **存储** | 文件系统 (JSONL) | 无DB |
| **依赖** | 仅LiteLLM | 轻量 |
| **启动** | <1秒 | 快 |

**关键特性**:
1. **渐进加载**: 按需加载技能
2. **文件存储**: 简单可靠
3. **异步优先**: 全栈async
4. **最小依赖**: 单一外部库

### 1.3 FastReAct v1.1.0 - 企业级ReAct框架 (50,792行)

| 特性 | 实现 | 优势 |
|------|------|------|
| **上下文** | Token监控 + 智能截断 | 精确控制 |
| **流式** | Phase回调 + SSE/WebSocket | 细粒度观察 |
| **Graph** | DAG工作流 + 并行执行 | 复杂任务 |
| **缓存** | LRU + 统计 | 性能优化 |
| **MCP** | 完整协议支持 | 生态兼容 |

---

## 二、新架构设计：FastReAct Nano v2

### 2.1 设计目标

```
[轻量] - Nanobot的简洁 (~3,000行核心代码)
[实时] - Moltbot的Gateway + WebSocket
[多渠] - Moltbot的7+渠道支持
[ReAct] - FastReAct的循环 + 工具系统
[企业] - Token监控 + 缓存 + 错误处理
```

### 2.2 核心架构（Gateway模式）

```
┌─────────────────────────────────────────────────────────────┐
│                      FastReAct Gateway                       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │WebSocket Server│  │Session Manager│  │Plugin Registry│   │
│  │  (Hono/FastAPI)│  │  (Memory/Cache)│  │  (Skills/Tools)│ │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │   MessageBus   │  (async queue)
                    └───────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼───────┐  ┌────────▼─────────┐
│  ReActCore     │  │  StreamCore  │  │  PluginManager   │
│  (主循环)       │  │  (流式处理)   │  │  (插件管理)       │
│                │  │              │  │                  │
│  - run_loop()  │  │ - stream()   │  │ - load()         │
│  - execute()   │  │ - yield()    │  │ - hot_reload()   │
└───────┬────────┘  └──────┬───────┘  └──────────────────┘
        │                   │
        └─────────┬─────────┘
                  │
    ┌─────────────┼─────────────┬──────────────┬────────────┐
    │             │             │              │            │
┌───▼─────┐  ┌───▼──────┐  ┌───▼──────┐  ┌───▼─────┐  ┌──▼──────┐
│Context  │  │  Tools   │  │  LLM     │  │  Cache   │  │Callback │
│Manager  │  │Registry  │  │Provider  │  │  (LRU)   │  │Manager  │
└─────────┘  └──────────┘  └──────────┘  └──────────┘  └─────────┘
```

### 2.3 模块设计

#### 2.3.1 Gateway (Moltbot模式)

```python
class FastReActGateway:
    """FastReAct Gateway - 中央控制平面"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.app = FastAPI()  # 或 Hono (如果用Python)
        self.sessions: dict[str, Session] = {}
        self.message_bus = MessageBus()
        self.plugin_manager = PluginManager()

        # WebSocket routes
        @self.app.websocket("/ws/{channel}/{user_id}")
        async def websocket_endpoint(websocket: WebSocket, channel: str, user_id: str):
            await self._handle_ws_connection(websocket, channel, user_id)

    async def _handle_ws_connection(self, ws: WebSocket, channel: str, user_id: str):
        """处理WebSocket连接"""
        await ws.accept()

        # 创建或获取会话
        session_id = f"{channel}:{user_id}"
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(
                id=session_id,
                channel=channel,
                user_id=user_id,
                message_bus=self.message_bus
            )

        session = self.sessions[session_id]

        # 消息循环
        while True:
            data = await ws.receive_json()
            await session.handle_message(data)

            # 流式响应
            async for chunk in session.stream_response():
                await ws.send_json({
                    "type": "chunk",
                    "content": chunk
                })
```

#### 2.3.2 Channel插件系统 (Moltbot模式)

```python
class ChannelPlugin(ABC):
    """渠道插件基类"""

    id: str
    meta: ChannelMeta

    @abstractmethod
    async def start(self, gateway_url: str): pass

    @abstractmethod
    async def send(self, user_id: str, content: str): pass

    @abstractmethod
    async def monitor(self, handler: Callable): pass

class ChannelRegistry:
    """渠道注册表"""

    _channels: dict[str, type[ChannelPlugin]] = {}

    @classmethod
    def register(cls, channel_cls: type[ChannelPlugin]):
        cls._channels[channel_cls.id] = channel_cls

    @classmethod
    def get(cls, channel_id: str) -> type[ChannelPlugin]:
        return cls._channels.get(channel_id)

    @classmethod
    def list_all(cls) -> list[str]:
        return list(cls._channels.keys())

# 使用示例
class TelegramChannel(ChannelPlugin):
    id = "telegram"
    meta = ChannelMeta(
        label="Telegram",
        docs_path="/channels/telegram"
    )

    async def start(self, gateway_url: str):
        # 连接到Gateway的WebSocket
        self.ws = await connect_ws(f"{gateway_url}/ws/telegram")

    async def send(self, user_id: str, content: str):
        # 通过Gateway发送
        await self.ws.send_json({
            "user_id": user_id,
            "content": content
        })

    async def monitor(self, handler: Callable):
        # 监听Telegram消息并转发到Gateway
        async for update in self.bot.stream():
            await handler({
                "channel": "telegram",
                "user_id": str(update.message.chat_id),
                "content": update.message.text
            })

# 注册渠道
ChannelRegistry.register(TelegramChannel)
```

#### 2.3.3 ReActCore (Nanobot + FastReAct v1)

```python
class ReActCore:
    """ReAct核心循环 - 简洁但强大"""

    def __init__(
        self,
        llm: LLMProvider,
        tools: ToolRegistry,
        context: ContextManager,
        cache: Optional[LRUCache] = None,
        callbacks: Optional[CallbackManager] = None,
    ):
        self._llm = llm
        self._tools = tools
        self._context = context
        self._cache = cache
        self._callbacks = callbacks
        self._max_iterations = 20

    async def run_loop(
        self,
        user_id: str,
        message: str,
        stream: Optional[AsyncIterator[str]] = None
    ) -> AsyncIterator[str]:
        """主循环 - 支持流式输出"""

        # 1. 构建上下文 (Token-aware)
        ctx = await self._context.build(user_id, message)
        await self._callbacks.on_phase(Phase.THINK)

        # 2. 检查缓存
        if self._cache:
            cached = await self._cache.get(message)
            if cached:
                yield cached
                return

        # 3. ReAct迭代
        for i in range(self._max_iterations):
            # LLM调用
            response = await self._llm.chat(
                messages=ctx.messages,
                tools=self._tools.schemas()
            )

            # 流式输出
            if response.content:
                async for chunk in self._stream_content(response.content):
                    await self._callbacks.on_stream(chunk)
                    yield chunk

            # 工具调用
            if response.tool_calls:
                await self._callbacks.on_phase(Phase.ACTION)
                for tool_call in response.tool_calls:
                    await self._callbacks.on_tool_call(tool_call)

                    result = await self._tools.execute(
                        tool_call.name,
                        tool_call.params
                    )

                    await self._callbacks.on_phase(Phase.OBSERVATION)
                    ctx.add_tool_result(tool_call, result)
            else:
                break

        # 4. 更新缓存
        final_response = response.content
        if self._cache:
            await self._cache.set(message, final_response)
```

#### 2.3.4 ContextManager (FastReAct v1精华)

```python
class ContextManager:
    """智能上下文管理 - Token监控 + 渐进加载"""

    def __init__(
        self,
        max_tokens: int = 8000,
        reserve_tokens: int = 2000,
        memory_path: Optional[Path] = None,
        skills_path: Optional[Path] = None,
    ):
        self._max_tokens = max_tokens
        self._reserve = reserve_tokens
        self._memory_path = memory_path
        self._skills_path = skills_path
        self._monitor = ContextMonitor(max_tokens, reserve_tokens)

    async def build(self, user_id: str, message: str) -> Context:
        """构建上下文"""
        messages = []

        # 1. 系统提示词
        system = await self._build_system_prompt()
        messages.append({"role": "system", "content": system})
        self._monitor.track(system)

        # 2. 加载记忆 (Nanobot模式 - 文件存储)
        if self._memory_path:
            memory = await self._load_memory(user_id)
            if memory:
                messages.append({"role": "system", "content": memory})
                self._monitor.track(memory)

        # 3. 技能列表 (渐进加载)
        if self._skills_path:
            skills = await self._list_skills()
            always_skills, available_skills = self._categorize_skills(skills)
            skill_prompt = self._build_skill_prompt(always_skills, available_skills)
            messages.append({"role": "system", "content": skill_prompt})
            self._monitor.track(skill_prompt)

        # 4. 历史消息 (智能截断 - FastReAct v1)
        history = await self._load_history(user_id)
        budget = self._monitor.calculate_budget()
        pruned = self._prune_by_importance(history, budget)
        messages.extend(pruned)

        # 5. 当前消息
        messages.append({"role": "user", "content": message})
        self._monitor.track(message)

        # 6. Token警告
        if self._monitor.usage_percent > 90:
            logger.warning(f"[Context] Token usage at {self._monitor.usage_percent}%")

        return Context(messages=messages)

    async def _build_system_prompt(self) -> str:
        """构建系统提示词 - 从bootstrap文件"""
        # 类似Nanobot的AGENTS.md, SOUL.md等
        parts = []

        bootstrap_files = ["AGENTS.md", "SOUL.md", "IDENTITY.md"]
        for filename in bootstrap_files:
            path = Path.cwd() / filename
            if path.exists():
                content = path.read_text(encoding="utf-8")
                parts.append(content)

        return "\n\n".join(parts)

    def _prune_by_importance(self, messages: list, budget: int) -> list:
        """按重要性智能截断"""
        # 优先级: 系统消息 > 工具结果 > 用户消息 > 助手消息
        # 截断长文本
        # 移除低重要性对话
        pruned = []
        current_tokens = 0

        for msg in reversed(messages):
            tokens = self._estimate_tokens(msg["content"])
            if current_tokens + tokens > budget:
                # 截断而不是丢弃
                truncated = self._truncate_content(msg["content"], budget - current_tokens)
                pruned.insert(0, {**msg, "content": truncated})
                break
            pruned.insert(0, msg)
            current_tokens += tokens

        return pruned
```

#### 2.3.5 PluginManager (Moltbot模式)

```python
class PluginManager:
    """插件管理器 - 技能/工具热加载"""

    def __init__(self, plugins_dir: Path):
        self._plugins_dir = plugins_dir
        self._skills: dict[str, Skill] = {}
        self._tools: dict[str, Tool] = {}

    async def load_all(self):
        """加载所有插件"""
        # 加载技能 (Markdown)
        await self._load_skills()

        # 加载工具 (Python)
        await self._load_tools()

    async def _load_skills(self):
        """加载技能 (类似Nanobot)"""
        skills_dir = self._plugins_dir / "skills"
        for skill_file in skills_dir.glob("**/*.md"):
            skill = await self._parse_skill(skill_file)
            self._skills[skill.name] = skill

    async def _parse_skill(self, path: Path) -> Skill:
        """解析技能文件"""
        content = path.read_text(encoding="utf-8")

        # 解析frontmatter
        frontmatter, body = split_frontmatter(content)
        metadata = yaml.safe_load(frontmatter)

        return Skill(
            name=metadata.get("name", path.stem),
            description=metadata.get("description", ""),
            content=body,
            metadata=metadata
        )

    async def reload_skill(self, name: str):
        """热重载技能"""
        if name in self._skills:
            skill_file = self._skills[name].file
            new_skill = await self._parse_skill(skill_file)
            self._skills[name] = new_skill
```

### 2.4 代码结构（估算）

```
fastreact/
├── gateway/
│   ├── server.py           # FastAPI Gateway (200行)
│   ├── websocket.py        # WebSocket处理 (150行)
│   └── session.py          # Session管理 (100行)
├── channels/
│   ├── base.py             # Channel基类 (80行)
│   ├── registry.py         # 注册表 (60行)
│   ├── telegram.py         # Telegram实现 (150行)
│   ├── whatsapp.py         # WhatsApp实现 (200行)
│   └── discord.py          # Discord实现 (150行)
├── core/
│   ├── react.py            # ReActCore (300行)
│   ├── context.py          # ContextManager (250行)
│   ├── tools.py            # Tool + Registry (150行)
│   └── bus.py              # MessageBus (50行)
├── plugins/
│   ├── manager.py          # PluginManager (200行)
│   ├── skill.py            # Skill类 (80行)
│   └── loader.py           # 加载器 (100行)
├── providers/
│   └── litellm.py          # LiteLLM封装 (100行)
├── cache/
│   └── lru.py              # LRU缓存 (80行)
├── callbacks/
│   ├── manager.py          # CallbackManager (100行)
│   └── events.py           # 事件定义 (50行)
├── tools/                  # 内置工具
│   ├── file.py
│   ├── shell.py
│   └── web.py
└── utils/
    ├── config.py
    └── memory.py

总计: ~3,000行核心代码
```

### 2.5 核心特性对比

| 特性 | Nanobot | Moltbot | FR v1 | **新设计** |
|------|---------|---------|-------|----------|
| 代码量 | 3,510行 | 82,168行 | 50,792行 | **~3,000行** |
| 架构 | MessageBus | Gateway + WS | Graph | **Gateway + Bus** |
| 渠道 | 1 | 7+ | 3+ | **7+** |
| 技能 | Markdown | 插件系统 | 工具类 | **插件系统** |
| 存储 | 文件 | 数据库 | 文件 | **文件** |
| 实时 | 无 | WebSocket | SSE | **WebSocket** |
| Token监控 | 无 | 无 | 有 | **有** |
| 缓存 | 无 | 有 | 有 | **有** |

---

## 三、关键技术决策

### 3.1 为什么选择Gateway模式？

**决策**: 采用Moltbot的Gateway中心化架构

**理由**:
1. **统一控制**: 单一控制平面管理所有渠道
2. **实时通信**: WebSocket支持双向流式通信
3. **会话管理**: 跨平台统一会话状态
4. **扩展性**: 易于添加新渠道
5. **生产就绪**: Moltbot已验证此模式

### 3.2 为什么保留MessageBus？

**决策**: Gateway内部使用MessageBus解耦

**理由**:
1. **缓冲**: 处理突发流量
2. **解耦**: WebSocket与Core逻辑分离
3. **测试**: 易于单元测试
4. **灵活**: 可替换实现

### 3.3 为什么文件存储？

**决策**: 采用Nanobot的文件系统存储

**理由**:
1. **简单**: 无需数据库配置
2. **快速**: 文件IO比数据库快
3. **可靠**: JSONL可读、可追加
4. **便携**: 易于备份和迁移

### 3.4 为什么渐进加载？

**决策**: 按需加载技能和工具

**理由**:
1. **启动快**: 不加载所有内容
2. **内存少**: 只加载使用的
3. **灵活**: 可动态添加
4. **热重载**: 支持插件更新

---

## 四、实施路线图（更新）

### Phase 1: Gateway基础设施 (2天)
- [ ] FastAPI服务器
- [ ] WebSocket路由
- [ ] Session管理
- [ ] MessageBus集成

### Phase 2: ReAct核心 (2天)
- [ ] ReActCore循环
- [ ] LLM Provider (LiteLLM)
- [ ] Tool Registry
- [ ] 基础工具集

### Phase 3: 上下文管理 (1天)
- [ ] ContextManager
- [ ] Token监控
- [ ] 智能截断
- [ ] 文件存储

### Phase 4: 渠道系统 (3天)
- [ ] Channel抽象
- [ ] Channel Registry
- [ ] Telegram实现
- [ ] WhatsApp实现 (可选)

### Phase 5: 插件系统 (2天)
- [ ] PluginManager
- [ ] 技能加载 (Markdown)
- [ ] 工具加载 (Python)
- [ ] 热重载

### Phase 6: 企业特性 (1-2天)
- [ ] LRU缓存
- [ ] CallbackManager
- [ ] 流式输出
- [ ] 错误处理

### Phase 7: 测试与文档 (1天)
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能测试
- [ ] 文档完善

**总估算: 12-14天完成完整版**
**MVP (Phase 1-4): 7天**

---

## 五、技术栈

```yaml
核心:
  - fastapi: Web框架
  - websockets: WebSocket支持
  - litellm: LLM统一接口
  - pydantic: 数据验证

渠道:
  - python-telegram-bot: Telegram
  - baileys (via node): WhatsApp (可选)
  - discord.py: Discord (可选)

存储:
  - aiofiles: 异步文件操作
  - jsonl: 会话存储格式

开发:
  - pytest: 测试
  - pytest-asyncio: 异步测试
  - black: 格式化
  - mypy: 类型检查
```

---

## 六、预期成果

### 6.1 代码量对比

| 框架 | 核心代码 | 功能 |
|------|---------|------|
| Nanobot | 3,510行 | 轻量助手 |
| Moltbot | 82,168行 | 企业平台 |
| FastReAct v1 | 50,792行 | ReAct框架 |
| **新设计** | **~3,000行** | **轻量+多渠+ReAct** |

### 6.2 性能目标

- **启动时间**: <1秒
- **首响延迟**: <2秒
- **流式延迟**: <100ms
- **内存占用**: <100MB
- **并发用户**: 100+

### 6.3 功能完整性

- [x] ReAct循环
- [x] 工具系统
- [x] Token监控
- [x] 流式输出
- [x] LRU缓存
- [x] 多渠道 (7+)
- [x] 技能系统
- [x] 插件热加载
- [x] WebSocket实时
- [x] 会话管理

---

**结论**: 新设计融合了三个框架的精华：
- **Nanobot的轻量** (3k行代码)
- **Moltbot的架构** (Gateway + 7渠道)
- **FastReAct的企业特性** (Token监控 + 缓存)

产出：**轻量级、多渠道、实时、企业就绪**的万能智能体框架。
