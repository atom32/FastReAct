# FastReAct Universal Agent Design
## 融合 Nanobot + Moltbot + FastReAct v1 的万能智能体方案

**创建日期**: 2026-02-10
**目标**: 打造一个轻量、快速、多渠道的ReAct智能体框架

---

## 一、框架对比分析

### 1.1 Nanobot - 核心优势：轻量与快速

| 特性 | 实现 | 优势 |
|------|------|------|
| **代码量** | 3,510行 | 开发快、调试快、部署快 |
| **Message Bus** | 异步队列解耦 | 渠道与核心逻辑分离 |
| **渐进加载** | 按需加载技能 | 启动快、内存占用低 |
| **文件存储** | JSONL会话 | 简单可靠、无需数据库 |
| **单一依赖** | LiteLLM | 无依赖冲突 |

**速度来源**:
- 无中间层：直接处理消息
- 无数据库：文件操作更快
- 无复杂配置：智能默认值
- 异步优先：全async实现

### 1.2 Moltbot - 核心优势：多渠道架构

| 特性 | 实现 | 优势 |
|------|------|------|
| **Channel抽象** | 统一的Channel基类 | 易扩展新渠道 |
| **ChannelManager** | 集中式管理 | 统一消息路由 |
| **Gateway模式** | 中央Agent架构 | 分布式支持 |
| **优雅启停** | 独立通道隔离 | 单个失败不影响整体 |

**渠道支持**:
- Telegram (完整实现)
- WeChat (部分实现)
- Slack (引用)
- 可扩展到Discord、WhatsApp等

### 1.3 FastReAct v1.1.0 - 核心优势：企业级特性

| 特性 | 文件 | 价值 |
|------|------|------|
| **Context监控** | `context/monitor.py` | 实时token跟踪、智能截断 |
| **流式回调** | `core/callbacks.py` | 细粒度阶段回调、SSE/WebSocket |
| **Graph Agent** | `graph/agent.py` | 规划与执行分离、DAG工作流 |
| **LRU缓存** | `core/cache.py` | 减少重复LLM调用 |
| **错误分类** | `exceptions.py` | 可重试vs不可重试 |

**精华模式**:
- Async-first设计
- Token-aware上下文管理
- 进度回调模式
- 流式输出架构

---

## 二、新架构设计：FastReAct Nano

### 2.1 设计原则

```
[速度] - Nanobot的轻量，启动<1秒，响应<2秒
[渠道] - Moltbot的多渠道，统一Channel接口
[企业] - FastReAct的监控、缓存、错误处理
[简单] - 单一职责，清晰边界，易于测试
```

### 2.2 核心架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      Channels Layer                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Telegram │  │  WeChat  │  │   CLI    │  │   HTTP   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       └──────────────┴──────────────┴──────────────┘       │
│                           │                                 │
│                   ┌───────▼────────┐                        │
│                   │ ChannelManager │                        │
│                   └───────┬────────┘                        │
└───────────────────────────┼─────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  MessageBus    │  (Nanobot pattern)
                    │  (async queue) │
                    └───────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                                       │
┌───────▼────────┐                    ┌────────▼─────────┐
│  ReActCore     │                    │  ReActStream     │
│  (主循环)       │                    │  (流式处理)       │
│                │                    │                  │
│  - run_loop()  │◄───────────────────│ - stream_loop()  │
│  - execute()   │                    │ - yield chunks   │
└───────┬────────┘                    └──────────────────┘
        │
        ├────────────────┬────────────────┬──────────────┐
        │                │                │              │
┌───────▼──────┐  ┌──────▼───────┐  ┌───▼──────┐  ┌───▼─────────┐
│ ContextMgr   │  │  ToolRegistry│  │ LLMCache │  │ CallbackMgr  │
│              │  │              │  │          │  │              │
│ - build()    │  │ - register() │  │ - get()  │  │ - on_think() │
│ - prune()    │  │ - execute()  │  │ - set()  │  │ - on_action()│
│ - monitor    │  │ - validate() │  │ - stats  │  │ - on_obs()   │
└──────────────┘  └──────────────┘  └──────────┘  └──────────────┘
        │                │                              │
        └────────────────┴──────────────────────────────┘
                           │
                    ┌──────▼────────┐
                    │  Providers    │
                    │  (LiteLLM)    │
                    └───────────────┘
```

### 2.3 模块设计

#### 2.3.1 MessageBus (Nanobot模式)

```python
class MessageBus:
    """异步消息总线 - 解耦渠道与核心"""

    def __init__(self):
        self._inbound = asyncio.Queue()
        self._outbound = asyncio.Queue()

    async def publish_inbound(self, msg: InboundMessage):
        """渠道 -> Agent"""
        await self._inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage:
        """Agent接收消息"""
        return await self._inbound.get()

    async def publish_outbound(self, msg: OutboundMessage):
        """Agent -> 渠道"""
        await self._outbound.put(msg)

    async def consume_outbound(self) -> OutboundMessage:
        """渠道发送消息"""
        return await self._outbound.get()
```

#### 2.3.2 Channel抽象 (Moltbot模式)

```python
class Channel(ABC):
    """统一渠道接口"""

    @abstractmethod
    async def start(self): pass

    @abstractmethod
    async def stop(self): pass

    @abstractmethod
    async def send(self, user_id: str, content: str): pass

    def set_inbound(self, queue: asyncio.Queue):
        """设置入站消息队列"""
        self._inbound = queue

    async def _forward_inbound(self, user_id: str, content: str, metadata: dict):
        """转发消息到MessageBus"""
        await self._inbound.put(InboundMessage(
            channel=self.name,
            user_id=user_id,
            content=content,
            metadata=metadata
        ))
```

#### 2.3.3 ReActCore (核心循环)

```python
class ReActCore:
    """轻量级ReAct循环 - Nanobot速度 + FastReAct质量"""

    def __init__(
        self,
        provider: LLMProvider,
        tools: ToolRegistry,
        context: ContextManager,
        cache: Optional[LLMCache] = None,
        callbacks: Optional[CallbackManager] = None,
    ):
        self._provider = provider
        self._tools = tools
        self._context = context
        self._cache = cache
        self._callbacks = callbacks
        self._max_iterations = 20

    async def run_loop(self, message: InboundMessage) -> OutboundMessage:
        """主处理循环"""
        # 1. 构建上下文
        context = await self._context.build(
            user_id=message.user_id,
            content=message.content
        )

        # 2. 检查缓存
        if self._cache:
            cached = await self._cache.get(message.content)
            if cached:
                return OutboundMessage(content=cached)

        # 3. ReAct循环
        for i in range(self._max_iterations):
            # 调用LLM
            await self._callbacks.on_phase(Phase.THINK)
            response = await self._provider.chat(
                messages=context.messages,
                tools=self._tools.schemas()
            )

            # 执行工具
            if response.tool_calls:
                await self._callbacks.on_phase(Phase.ACTION)
                for tool_call in response.tool_calls:
                    await self._callbacks.on_tool_call(tool_call)
                    result = await self._tools.execute(tool_call)
                    await self._callbacks.on_phase(Phase.OBSERVATION)
                    context.add_tool_result(result)
            else:
                break

        # 4. 缓存结果
        result = response.content
        if self._cache:
            await self._cache.set(message.content, result)

        return OutboundMessage(content=result)
```

#### 2.3.4 ContextManager (FastReAct v1精华)

```python
class ContextManager:
    """智能上下文管理 - Token-aware + 渐进加载"""

    def __init__(
        self,
        max_tokens: int = 8000,
        system_prompt: str = "",
        memory_path: Optional[Path] = None,
    ):
        self._max_tokens = max_tokens
        self._system_prompt = system_prompt
        self._memory_path = memory_path
        self._monitor = ContextMonitor(max_tokens)

    async def build(self, user_id: str, content: str) -> Context:
        """构建上下文"""
        messages = []

        # 1. 系统提示词
        messages.append({"role": "system", "content": self._system_prompt})

        # 2. 加载记忆 (渐进加载)
        if self._memory_path:
            memory = await self._load_memory(user_id)
            if memory:
                messages.append({"role": "system", "content": memory})

        # 3. 历史消息 (智能截断)
        history = await self._get_history(user_id)
        budget = self._monitor.calculate_budget()
        pruned = self._prune_by_importance(history, budget)
        messages.extend(pruned)

        # 4. 当前消息
        messages.append({"role": "user", "content": content})

        return Context(messages=messages)

    def _prune_by_importance(self, messages: list, budget: int) -> list:
        """按重要性智能截断"""
        # 保留系统消息、工具结果
        # 截断长文本
        # 移除低重要性对话
        # 目标: 40-60% token节省
        pass
```

#### 2.3.5 ToolRegistry (简化但强大)

```python
class Tool:
    """简洁的工具抽象"""
    name: str
    description: str
    parameters: dict  # JSON Schema

    async def execute(self, **kwargs) -> str:
        """执行工具"""
        pass

class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册工具"""
        self._tools[tool.name] = tool

    async def execute(self, name: str, params: dict) -> str:
        """执行工具"""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"

        # 验证参数
        errors = validate_json_schema(params, tool.parameters)
        if errors:
            return f"Error: Invalid parameters: {errors}"

        return await tool.execute(**params)

    def schemas(self) -> list[dict]:
        """返回工具schema (用于LLM)"""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters
            }
            for t in self._tools.values()
        ]
```

#### 2.3.6 CallbackManager (细粒度观察)

```python
class Phase(Enum):
    """执行阶段"""
    THINK = "think"       # LLM思考
    ACTION = "action"     # 调用工具
    OBSERVE = "observe"   # 工具结果

class CallbackManager:
    """回调管理器 - 流式观察"""

    def __init__(self):
        self._callbacks: list[Callable] = []

    def on_phase(self, phase: Phase):
        """阶段回调"""
        for cb in self._callbacks:
            asyncio.create_task(cb(PhaseEvent(phase=phase)))

    def on_tool_call(self, tool_call: ToolCall):
        """工具调用回调"""
        for cb in self._callbacks:
            asyncio.create_task(cb(ToolCallEvent(tool_call=tool_call)))

    def on_stream_chunk(self, chunk: str):
        """流式块回调"""
        for cb in self._callbacks:
            asyncio.create_task(cb(StreamChunkEvent(content=chunk)))
```

### 2.4 关键特性实现

#### 2.4.1 速度优化 (来自Nanobot)

1. **渐进加载**: 按需加载技能/工具
2. **文件存储**: JSONL会话，无需数据库
3. **异步优先**: 全栈async
4. **智能缓存**: LRU缓存LLM响应
5. **最小依赖**: 仅LiteLLM + 标准库

#### 2.4.2 多渠道支持 (来自Moltbot)

1. **统一Channel接口**: 易扩展新渠道
2. **ChannelManager**: 集中管理所有渠道
3. **优雅隔离**: 单个渠道失败不影响其他
4. **消息路由**: 自动路由到对应handler

#### 2.4.3 企业级特性 (来自FastReAct v1)

1. **Token监控**: 实时跟踪，智能截断
2. **流式输出**: SSE/WebSocket支持
3. **错误分类**: 可重试vs不可重试
4. **进度回调**: 细粒度观察执行过程
5. **LRU缓存**: 减少重复调用

### 2.5 代码结构预估

```
fastreact/
├── core/
│   ├── engine.py        # ReActCore (200行)
│   ├── context.py       # ContextManager (300行)
│   ├── tools.py         # Tool + ToolRegistry (150行)
│   └── bus.py           # MessageBus (50行)
├── channels/
│   ├── base.py          # Channel抽象 (100行)
│   ├── manager.py       # ChannelManager (150行)
│   ├── telegram.py      # Telegram实现 (200行)
│   └── cli.py           # CLI渠道 (100行)
├── providers/
│   └── litellm.py       # LiteLLM封装 (100行)
├── cache/
│   └── lru.py           # LRU缓存 (80行)
├── callbacks/
│   ├── manager.py       # CallbackManager (100行)
│   └── stream.py        # 流式处理 (150行)
├── tools/
│   ├── file.py          # 文件操作
│   ├── shell.py         # Shell执行
│   └── web.py           # Web搜索
└── utils/
    ├── config.py        # 配置加载
    └── memory.py        # 记忆存储

总计: ~2,000行核心代码
```

**对比**:
- Nanobot: 3,510行
- FastReAct v1: 50,792行
- **新设计: ~2,000行** (更轻量!)

---

## 三、实施路线图

### Phase 1: 核心引擎 (1-2天)
- [ ] MessageBus实现
- [ ] ReActCore核心循环
- [ ] Tool + ToolRegistry
- [ ] LiteLLM集成

### Phase 2: 上下文管理 (1天)
- [ ] ContextManager
- [ ] Token监控
- [ ] 智能截断
- [ ] 文件存储

### Phase 3: 渠道系统 (2天)
- [ ] Channel抽象
- [ ] ChannelManager
- [ ] CLI渠道
- [ ] Telegram渠道

### Phase 4: 企业特性 (1-2天)
- [ ] LRU缓存
- [ ] CallbackManager
- [ ] 流式输出
- [ ] 错误处理

### Phase 5: 测试与优化 (1天)
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能测试
- [ ] 文档完善

**总估算: 6-8天完成MVP**

---

## 四、技术栈

```yaml
核心依赖:
  - litellm: 多LLM提供商支持

开发依赖:
  - pytest: 测试
  - pytest-asyncio: 异步测试
  - black: 代码格式化
  - mypy: 类型检查

Python版本: 3.11+
```

**为什么这样选择?**
- **LiteLLM**: 统一接口，支持OpenAI/Claude/DeepSeek等
- **无额外依赖**: 保持轻量，避免冲突
- **异步优先**: Python 3.11+ async性能优秀

---

## 五、设计决策记录

### 5.1 为什么选MessageBus而非直接调用?

**决策**: 使用异步队列解耦渠道和核心

**理由**:
- 解耦: 渠道和核心完全独立
- 缓冲: 处理突发流量
- 扩展: 易于添加新渠道

### 5.2 为什么文件存储而非数据库?

**决策**: 使用JSONL文件存储会话

**理由**:
- 简单: 无需数据库配置
- 快速: 文件读写更快
- 可读: 人类可阅读调试
- 可靠: 原子性写入

### 5.3 为什么渐进加载?

**决策**: 按需加载技能/工具

**理由**:
- 启动快: 不加载所有内容
- 内存少: 只加载使用的
- 灵活: 可动态添加工具

### 5.4 为什么保留Token监控?

**决策**: 从FastReAct v1保留ContextMonitor

**理由**:
- 成本: 精确控制token使用
- 性能: 避免超长请求
- 透明: 实时可见消耗

---

## 六、与现有方案对比

| 特性 | Nanobot | Moltbot | FastReAct v1 | **新设计** |
|------|---------|---------|--------------|-----------|
| 代码量 | 3,510行 | 未知 | 50,792行 | **~2,000行** |
| 启动速度 | 快 | 中 | 慢 | **<1秒** |
| 多渠道 | 基础 | **强** | 强 | **强** |
| Token监控 | 无 | 无 | **有** | **有** |
| 流式输出 | 有 | 无 | **有** | **有** |
| 缓存 | 无 | 无 | **有** | **有** |
| 依赖数 | 1 | 未知 | 多 | **1** |
| 企业特性 | 基础 | 中 | **强** | **精选** |

---

## 七、下一步行动

1. **Review本文档** - 确认设计方向
2. **创建PoC** - 验证核心概念
3. **迭代开发** - 按Phase实施
4. **持续测试** - 保证质量

---

**结论**: 这个设计融合了三个框架的优点：
- Nanobot的**速度和轻量**
- Moltbot的**多渠道能力**
- FastReAct v1的**企业级特性**

预计产出：**~2,000行代码**、**<1秒启动**、**支持多渠道**、**生产就绪**的万能智能体框架。
