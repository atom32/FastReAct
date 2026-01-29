# p-mono Agent Runtime 深度分析

## 研究目标

1. 理解 p-mono 如何实现思维框架（vs ReAct）
2. 分析 moltbot 如何调用工具
3. 对比 Gateway 架构
4. 总结 FastReAct 可以借鉴的优点

---

## 1. p-mono vs ReAct 核心区别

### ReAct 的显式循环

```python
# FastReAct (ReAct)
while not done:
    # 1. 模型生成推理
    thought = llm.generate(f"Question: {query}\nThought:")

    # 2. 解析动作
    action = parse_action(thought)  # "Action: search(...)"

    # 3. 执行工具
    observation = execute(action)

    # 4. 添加到历史
    history.append(f"Thought: {thought}")
    history.append(f"Observation: {observation}")
```

**特点：**
- ✅ 清晰的步骤边界
- ✅ 易于调试和监控
- ✅ 显式的推理链
- ❌ 串行执行（阻塞）
- ❌ 多次模型调用

### p-mono 的流式架构

```typescript
// moltbot (p-mono)
// 单次模型调用，流式输出
const session = await createAgentSession({
  systemPrompt,
  tools: [...],
  thinkingLevel: "medium"
});

// 一次性提示，流式返回
await session.prompt(userQuery, {
  onEvent: (evt) => {
    if (evt.type === "assistant.delta") {
      // 文本流式输出
      sendToUser(evt.text);
    }
    if (evt.type === "tool.start") {
      // 工具开始执行
      notifyUser(`Running ${evt.name}...`);
    }
    if (evt.type === "tool.result") {
      // 工具结果自动注入回上下文
    }
  }
});
```

**特点：**
- ✅ 单次模型调用
- ✅ 并发执行（文本和工具）
- ✅ 更自然的对话流
- ❌ 推理过程不透明
- ❌ 难以调试

---

## 2. p-mono 的思维框架实现

### 核心机制：系统提示注入 + 流式生成

#### 2.1 Bootstrap 文件系统

```typescript
// D:\moltbot\src\agents\bootstrap-files.ts
const bootstrapFiles = await resolveBootstrapFilesForRun({
  workspaceDir: "~/.clawdbot/moltbot.json",
  config: moltbotConfig
});

// 加载并注入到系统提示
const systemPrompt = `
${bootstrapFiles.AGENTS.md}     // 操作指令
${bootstrapFiles.SOUL.md}       // 人格、边界
${bootstrapFiles.TOOLS.md}      // 工具使用指南
${skills.join('\n')}             // 技能提示
`;
```

**效果：**
- 一次性注入所有上下文
- 模型"知道"如何思考和行动
- 无需显式的 "Thought:" 提示

#### 2.2 流式事件处理

```typescript
// D:\moltbot\src\agents\pi-embedded-subscribe.handlers.tools.ts
// 订阅 session 事件流
subscribeEmbeddedPiSession(session, {
  onAssistantDelta: (delta) => {
    // 文本生成
    sendToClient({ type: "text", data: delta });
  },

  onToolStart: (toolCall) => {
    // 工具开始
    notifyClient({ type: "tool_start", name: toolCall.name });
  },

  onToolResult: (result) => {
    // 工具结果自动注入回 session
    // 不需要显式添加到历史
    session.ingestToolResult(result);
  },

  onLifecycleEnd: () => {
    // 完成
    finalize();
  }
});
```

**关键差异：**
- **ReAct**: 手动管理历史 `[Thought, Action, Observation]`
- **p-mono**: session 自动管理上下文，工具结果自动注入

---

## 3. 工具调用机制对比

### ReAct: 显式工具调用

```python
# FastReAct
class SearchTool(Tool):
    async def execute_async(self, query: str) -> str:
        results = await search_api(query)
        return json.dumps(results)

# Agent 循环
action = parse_action("Action: SearchTool(query='...')")
observation = await action.tool.execute_async(**action.params)
history.append(f"Observation: {observation}")
```

**流程：**
1. 模型生成 `"Action: SearchTool(...)"`
2. 解析工具名和参数
3. 手动调用 `execute_async()`
4. 手动添加结果到历史
5. 下一轮循环继续

### p-mono: 事件驱动工具调用

```typescript
// moltbot
// 1. 工具注册
const tools = createMoltbotCodingTools({
  exec: { command: "bash" },
  sandbox: dockerSandbox,
  messageProvider: channel
});

// 2. 创建 session
const session = await createAgentSession({
  tools,
  toolExecutionTimeout: 30000
});

// 3. 流式执行（工具自动触发）
await session.prompt(userQuery);

// 4. 事件处理器接收工具事件
onToolEvent: async (evt) => {
  if (evt.phase === "start") {
    // 工具开始
    trackToolCall(evt.toolCallId, evt.name);
  }
  if (evt.phase === "result") {
    // 工具完成 - 结果自动注入
    trackToolResult(evt.toolCallId, evt.result);
  }
}
```

**流程：**
1. 模型在生成文本时决定调用工具
2. p-mono 运行时自动执行工具
3. 工具结果自动注入回 session
4. 模型继续生成（可能基于工具结果）

**关键差异：**
- **ReAct**: 手动解析和执行工具
- **p-mono**: 模型自主决策，运行时自动执行

---

## 4. Gateway 架构分析

### FastReAct: 有 Gateway 吗？

**答案：FastReAct 有 Gateway，但架构不同！**

```python
# FastReAct Gateway
src/fastreact/gateway/
├── gateway.py           # WebSocket 服务器
├── session_manager.py   # 会话管理
├── message_router.py    # 消息路由
└── protocol.py          # 协议定义

# 简单的 Gateway 实现
class Gateway:
    def __init__(self):
        self.sessions = {}
        self.channels = {}

    async def handle_message(self, session_id, message):
        # 路由到 agent
        session = self.sessions[session_id]
        result = await session.agent.run_async(message)

        # 发送到通道
        await session.channel.send(result)
```

**FastReAct Gateway 特点：**
- ✅ WebSocket 服务器
- ✅ 会话管理
- ✅ 多通道支持（WeChat, WebSocket, etc.）
- ❌ 缺少协议版本控制
- ❌ 缺少请求帧序列化
- ❌ 缺少设备认证

### Moltbot Gateway: 生产级架构

```typescript
// D:\moltbot\src\gateway\client.ts
export class GatewayClient {
  private ws: WebSocket | null = null;
  private pending = new Map<string, Pending>();
  private lastSeq: number | null = null;

  // 请求-响应协议
  async request<T>(method: string, params?: unknown): Promise<T> {
    const id = randomUUID();
    const frame: RequestFrame = {
      type: "req",
      id,
      method,
      params
    };

    // 发送请求帧
    this.ws.send(JSON.stringify(frame));

    // 等待响应
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject, timeout: 30000 });
    });
  }

  // 处理响应帧
  private handleFrame(frame: Frame) {
    if (frame.type === "res") {
      const pending = this.pending.get(frame.id);
      pending?.resolve(frame.result);
    }
  }
}
```

**Moltbot Gateway 特点：**
- ✅ 请求-响应帧协议
- ✅ 序列号管理（防止乱序）
- ✅ 超时处理
- ✅ 设备认证（TLS 指纹）
- ✅ 心跳检测
- ✅ 自动重连
- ✅ 会话车道序列化

---

## 5. Session Lane 并发控制

### Moltbot 的 Lane 系统

```typescript
// D:\moltbot\src\gateway\session-manager.ts
// 为每个会话创建"车道"（序列）
const lane = sessionManager.getLane(sessionKey);

// 同一会话的消息串行执行
await lane.run(async () => {
  const result = await agent.prompt(message);
  return result;
});

// 不同会话可以并发
// session-1 lane-1 (独立序列)
// session-1 lane-2 (独立序列)
// session-2 lane-3 (独立序列)
```

**防止的问题：**
- 会话状态竞态（两个消息同时修改会话）
- 工具调用冲突（同时修改文件系统）
- 历史记录不一致

### FastReAct 的队列系统

```python
# FastReAct 队列（简单实现）
class FastReAct:
    def __init__(self):
        self._queue = asyncio.Queue()
        self._processing = False

    async def run_async(self, query):
        # 加入队列
        future = asyncio.Future()
        await self._queue.put((query, future))

        # 串行处理
        if not self._processing:
            self._processing = True
            while not self._queue.empty():
                query, future = await self._queue.get()
                result = await self._process(query)
                future.set_result(result)
            self._processing = False

        return await future
```

**差异：**
- **Moltbot**: 按会话隔离（会话级串行，全局并发）
- **FastReAct**: 全局串行（更保守）

---

## 6. FastReAct 可以借鉴的优点

### 6.1 Bootstrap 文件系统 ✅ 强烈推荐

**实现建议：**

```python
# FastReAct 改进
class FastReAct:
    def __init__(self, workspace: str = None):
        self.workspace = workspace or "~/.fastreact"
        self.bootstrap_files = self._load_bootstrap_files()

    def _load_bootstrap_files(self):
        """加载工作区配置文件"""
        return {
            "AGENTS.md": self._read_file("AGENTS.md"),
            "SOUL.md": self._read_file("SOUL.md"),
            "TOOLS.md": self._read_file("TOOLS.md"),
        }

    def _build_system_prompt(self):
        """构建系统提示（注入 bootstrap）"""
        base = "You are a helpful assistant."

        # 注入 bootstrap 文件
        for name, content in self.bootstrap_files.items():
            if content:
                base += f"\n\n=== {name} ===\n{content}\n"

        # 注入工具描述
        base += "\n\nAvailable tools:\n"
        base += self._format_tools()

        return base
```

**收益：**
- 用户可以自定义 agent 人格
- 无需修改代码即可调整行为
- 更灵活的上下文注入

### 6.2 Lane-Based 并发 ⚠️ 可选

**实现建议：**

```python
# FastReAct 改进
class SessionLane:
    """会话车道 - 串行执行同一会话的消息"""
    def __init__(self):
        self._queue = asyncio.Queue()
        self._running = False

    async def run(self, coro):
        future = asyncio.Future()
        await self._queue.put((coro, future))

        if not self._running:
            self._running = True
            while not self._queue.empty():
                coro, future = await self._queue.get()
                result = await coro
                future.set_result(result)
            self._running = False

        return await future

class FastReAct:
    def __init__(self):
        self.lanes = {}  # session_id -> SessionLane

    async def run_async(self, query, session_id="default"):
        if session_id not in self.lanes:
            self.lanes[session_id] = SessionLane()

        lane = self.lanes[session_id]
        return await lane.run(self._process(query))
```

**收益：**
- 会话隔离（防止竞态）
- 更好的并发性能
- 更清晰的状态管理

**成本：**
- 增加复杂度
- 需要会话清理机制

### 6.3 协议帧序列化 ✅ 推荐

**实现建议：**

```python
# FastReAct Gateway 改进
class GatewayProtocol:
    """Gateway 通信协议"""
    VERSION = "1.0"

    @dataclass
    class RequestFrame:
        type: str = "req"
        id: str = ""
        method: str = ""
        params: dict = None

    @dataclass
    class ResponseFrame:
        type: str = "res"
        id: str = ""
        result: Any = None
        error: str = None

class GatewayClient:
    """Gateway 客户端"""
    def __init__(self, url: str):
        self.ws = WebSocket(url)
        self.pending = {}  # id -> Future

    async def request(self, method: str, params: dict = None):
        frame = GatewayProtocol.RequestFrame(
            id=str(uuid4()),
            method=method,
            params=params
        )

        future = asyncio.Future()
        self.pending[frame.id] = future

        await self.ws.send(json.dumps(asdict(frame)))
        return await future
```

**收益：**
- 更可靠的通信
- 支持超时和重试
- 便于调试和监控

### 6.4 事件流系统 ✅ 强烈推荐

**实现建议：**

```python
# FastReAct 改进
class AgentEvent:
    """Agent 事件"""
    type: str  # "lifecycle" | "assistant" | "tool"

class LifecycleEvent(AgentEvent):
    phase: str  # "start" | "end" | "error"

class AssistantEvent(AgentEvent):
    delta: str  # 文本增量

class ToolEvent(AgentEvent):
    phase: str  # "start" | "result" | "error"
    name: str
    tool_call_id: str
    args: dict = None
    result: Any = None

class FastReAct:
    async def run_async(self, query, event_callback=None):
        # 发送生命周期开始
        await event_callback(LifecycleEvent(phase="start"))

        # 执行循环
        for step in self._run_loop(query):
            if step["type"] == "thought":
                await event_callback(AssistantEvent(delta=step["text"]))

            if step["type"] == "action":
                await event_callback(ToolEvent(
                    phase="start",
                    name=step["tool"],
                    args=step["params"]
                ))

            if step["type"] == "observation":
                await event_callback(ToolEvent(
                    phase="result",
                    result=step["result"]
                ))

        # 发送生命周期结束
        await event_callback(LifecycleEvent(phase="end"))
```

**收益：**
- 更好的调试体验
- 实时进度反馈
- 便于监控和日志

---

## 7. FastReAct 应该保持的优势

### 7.1 简洁性 ✅

- 核心代码 < 600 行
- 易于理解和修改
- 适合学习

**不要引入过度设计：**
- ❌ 复杂的插件系统
- ❌ 抽象层过多
- ❌ 配置文件地狱

### 7.2 显式循环 ✅

```python
# 保持这个清晰的结构
while not done:
    thought = self._think(history)
    action = self._act(thought)
    observation = await self._observe(action)
    history.add(thought, action, observation)
```

**优势：**
- 调试友好
- 容易扩展
- 透明度高

### 7.3 Python 优先 ✅

- 更易读
- 生态丰富
- 社区活跃

---

## 8. 总结：如何学习 moltbot 的优点

### 立即可实施（P0）

1. **Bootstrap 文件系统** ✅
   - 简单实现，巨大价值
   - 用户可自定义 agent 人格
   - 类似 Moltbot 的 AGENTS.md, SOUL.md

2. **事件流回调** ✅
   - 改进现有的 `step_callback`
   - 支持 `lifecycle`, `assistant`, `tool` 三种事件
   - 实时反馈

3. **协议帧改进** ✅
   - 为 WebSocket Gateway 添加帧序列化
   - 支持超时和错误处理

### 中期改进（P1）

4. **Lane-Based 并发** ⚠️
   - 如果需要多用户支持
   - 增加复杂度，但收益明显

5. **自动上下文压缩** ⚠️
   - 长对话时自动压缩历史
   - 保持关键信息

### 长期考虑（P2）

6. **会话持久化** 📋
   - 保存对话历史到磁盘
   - 支持会话恢复

7. **技能系统** 📋
   - 从文件加载工具定义
   - 动态工具注册

---

## 9. 对比表

| 特性 | ReAct (FastReAct) | p-mono (Moltbot) | 建议 |
|------|-------------------|------------------|------|
| **推理模式** | 显式 Thought→Action→Observation | 隐式推理 + 工具调用 | 保持 ReAct |
| **工具调用** | 手动解析和执行 | 模型自主决策 | 保持 ReAct |
| **会话管理** | 简单历史 | 复杂状态机 | 可选改进 |
| **并发控制** | 队列序列化 | Lane-based | 可选改进 |
| **上下文注入** | 对话历史 | Bootstrap 文件 | ✅ 强烈推荐 |
| **事件流** | step_callback | 分层事件流 | ✅ 强烈推荐 |
| **Gateway** | 简单实现 | 生产级协议 | 可选改进 |
| **代码复杂度** | 简单 (~600 行) | 复杂 (~10k+ 行) | 保持简洁 |

---

## 10. 结论

**p-mono 不是 ReAct 的改进版，而是不同的范式：**

- **ReAct**: 显式推理循环，适合学习和调试
- **p-mono**: 流式生成，适合生产环境

**FastReAct 的策略：**

1. **保持核心简洁** - 继续使用 ReAct 模式
2. **借鉴优秀特性** - Bootstrap 文件、事件流、Lane 并发
3. **渐进式改进** - 不破坏现有架构，逐步添加功能

**推荐优先级：**

1. ✅ Bootstrap 文件系统（高价值，低成本）
2. ✅ 事件流改进（高价值，中成本）
3. ⚠️ Lane 并发（中价值，高成本）
4. ⚠️ 协议改进（中价值，中成本）

---

## 参考代码位置

- **p-mono agent runner**: `D:\moltbot\src\agents\pi-embedded-runner\run\attempt.ts`
- **Bootstrap 加载**: `D:\moltbot\src\agents\bootstrap-files.ts`
- **工具处理器**: `D:\moltbot\src\agents\pi-embedded-subscribe.handlers.tools.ts`
- **Gateway 客户端**: `D:\moltbot\src\gateway\client.ts`
- **会话管理**: `D:\moltbot\src\gateway\session-manager.ts`
