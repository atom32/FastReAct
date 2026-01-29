# FastReAct 生产化改进路线图

> **目标**: 从"学习试用"升级为"生产可用"的 Agent 系统
> **时间**: 2026-01-29 制定
> **版本**: v0.3.0-v1.0.0

---

## 📊 当前状态评估

### ✅ 已完成（v0.2.x）

**核心能力**：
- ✅ ReAct 引擎（清晰、高效）
- ✅ 多智能体系统（4个专用 Agent）
- ✅ 持久化存储（SQLite）
- ✅ 多通道集成（Telegram, Slack, WeChat）
- ✅ Docker 沙箱（安全执行）
- ✅ Gateway 基础（WebSocket, 认证）

**质量指标**：
- 测试通过率：100%（284个测试）
- 代码覆盖率：~60%
- 文档完整度：80%
- 异步支持：100%

### ⚠️ 生产可用性差距

| 维度 | 当前状态 | 生产级要求 | 差距 |
|------|----------|-----------|------|
| **稳定性** | 基本可用 | 错误恢复、重试、降级 | ⭐⭐⭐ |
| **可观测性** | 基础日志 | 结构化日志、指标、追踪 | ⭐⭐⭐⭐ |
| **性能** | 单机运行 | 并发控制、缓存、优化 | ⭐⭐⭐ |
| **易用性** | 需要编程 | CLI、配置文件、一键部署 | ⭐⭐⭐⭐ |
| **可扩展性** | 继承扩展 | 插件系统、Hook 机制 | ⭐⭐⭐ |
| **安全性** | 基础认证 | 权限控制、审计、加密 | ⭐⭐⭐⭐ |
| **运维** | 手动启动 | 健康检查、监控、告警 | ⭐⭐⭐⭐⭐ |

---

## 🎯 生产化策略

### 核心原则

1. **保持简洁** - 不破坏 ReAct 的清晰性
2. **渐进增强** - 分阶段实施，不重写
3. **可选扩展** - 高级功能可插拔
4. **向后兼容** - 不破坏现有 API

### 参考 moltbot 的经验

**值得借鉴**：
- ✅ Bootstrap 文件系统（灵活配置）
- ✅ 分层事件流（更好的可观测性）
- ✅ Lane-based 并发（会话隔离）
- ✅ 自动上下文压缩（长对话优化）
- ✅ 设备认证（安全增强）

**不需要**：
- ❌ 复杂的 p-mono 运行时（保持 ReAct）
- ❌ Node.js 微服务（保持 Python 单体）
- ❌ 过度抽象（保持简单）

---

## 📅 三阶段改进计划

### 🚀 Phase 1: 生产基础（2-3周）

**目标**: 让系统稳定可靠，易于部署和监控

#### 1.1 Bootstrap 文件系统 ⭐⭐⭐⭐⭐

**优先级**: P0 - 立即可实施，高价值

**功能**：
```python
# ~/.fastreact/workspace/
├── AGENTS.md       # Agent 操作指令
├── SOUL.md         # 人格和边界
├── TOOLS.md        # 工具使用指南
├── WORKSPACE.md    # 工作区配置
└── config.json     # 技术配置
```

**实现**：
```python
# src/fastreact/bootstrap/loader.py
class BootstrapLoader:
    def __init__(self, workspace: str = None):
        self.workspace = workspace or "~/.fastreact"
        self.files = self._load_bootstrap_files()

    def _load_bootstrap_files(self) -> Dict[str, str]:
        """加载 Bootstrap 文件"""
        return {
            "agents": self._read_file("AGENTS.md"),
            "soul": self._read_file("SOUL.md"),
            "tools": self._read_file("TOOLS.md"),
        }

    def build_system_prompt(self, base_prompt: str) -> str:
        """构建系统提示（注入 Bootstrap）"""
        sections = []
        for name, content in self.files.items():
            if content:
                sections.append(f"=== {name.upper()} ===\n{content}")
        return base_prompt + "\n\n" + "\n\n".join(sections)

    def _read_file(self, filename: str) -> str:
        """读取文件"""
        path = os.path.join(self.workspace, filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
```

**收益**：
- 用户可自定义 Agent 人格
- 无需修改代码即可调整行为
- 类似 Moltbot 的灵活性

**验收**：
- [ ] Bootstrap 文件加载正常
- [ ] 系统提示正确注入
- [ ] 文件热重载（可选）

---

#### 1.2 分层事件流系统 ⭐⭐⭐⭐⭐

**优先级**: P0 - 改进可观测性

**功能**：
```python
# 事件类型
class LifecycleEvent:
    phase: str  # "start" | "end" | "error"

class AssistantEvent:
    delta: str  # 文本增量

class ToolEvent:
    phase: str  # "start" | "result" | "error"
    name: str
    tool_call_id: str
    args: dict = None
    result: Any = None

# 使用示例
async def run_async(self, query, event_callback=None):
    await event_callback(LifecycleEvent(phase="start"))

    for step in self._run_loop(query):
        if step.type == "thought":
            await event_callback(AssistantEvent(delta=step.text))

        if step.type == "action":
            await event_callback(ToolEvent(
                phase="start",
                name=step.tool_name,
                args=step.params
            ))

    await event_callback(LifecycleEvent(phase="end"))
```

**收益**：
- 实时进度反馈
- 结构化日志
- 便于调试和监控

**验收**：
- [ ] 三种事件正确触发
- [ ] 回调机制正常
- [ ] WebSocket Gateway 事件推送

---

#### 1.3 CLI 工具 ⭐⭐⭐⭐

**优先级**: P0 - 提升易用性

**功能**：
```bash
# 安装后可直接使用
fastreact --help

# 启动 Gateway 服务器
fastreact gateway start --port 8765

# 交互式对话
fastreact chat --model gpt-4

# 运行单个查询
fastreact run "帮我搜索最新 AI 新闻"

# 查看 Agent 状态
fastreact status

# 初始化工作区
fastreact init --workspace ./my-agent
```

**实现**：
```python
# src/fastreact/cli/main.py
import click

@click.group()
def cli():
    """FastReAct - 生产级 ReAct Agent 框架"""
    pass

@cli.command()
@click.option('--port', default=8765, help='Gateway 端口')
@click.option('--host', default='0.0.0.0', help='监听地址')
def start_gateway(port, host):
    """启动 Gateway 服务器"""
    from fastreact.gateway.server import GatewayServer
    server = GatewayServer(host=host, port=port)
    server.run()

@cli.command()
@click.argument('query')
@click.option('--model', default='gpt-4', help='LLM 模型')
def run(query, model):
    """运行单个查询"""
    from fastreact import FastReAct
    agent = FastReAct(model=model)
    result = asyncio.run(agent.run_async(query))
    print(result['answer'])

@cli.command()
def init():
    """初始化工作区"""
    from fastreact.bootstrap import init_workspace
    init_workspace()
    click.echo("✓ 工作区初始化完成")
```

**收益**：
- 无需编程即可使用
- 降低使用门槛
- 更好的用户体验

**验收**：
- [ ] 所有 CLI 命令正常
- [ ] 帮助文档完整
- [ ] 错误提示友好

---

#### 1.4 配置管理增强 ⭐⭐⭐

**优先级**: P1

**功能**：
```python
# config.json 支持多环境
{
  "profile": "production",
  "profiles": {
    "development": {
      "llm": {"api_key": "...", "model": "gpt-4"},
      "log_level": "DEBUG"
    },
    "production": {
      "llm": {"api_key": "...", "model": "gpt-4-turbo"},
      "log_level": "INFO",
      "enable_metrics": true
    }
  }
}

# 环境变量覆盖
export FASTREACT_PROFILE=production
export FASTREACT_LLM_API_KEY=sk-...
```

**验收**：
- [ ] 多环境配置支持
- [ ] 环境变量覆盖
- [ ] 配置验证

---

#### 1.5 错误处理和重试 ⭐⭐⭐⭐

**优先级**: P0

**功能**：
```python
# src/fastreact/utils/resilience.py
class RetryPolicy:
    max_attempts: int = 3
    backoff_base: float = 1.0
    max_backoff: float = 10.0
    retriable_errors: List[Type[Exception]] = [
        ConnectionError,
        TimeoutError,
        APIError
    ]

async def retry_with_backoff(
    func: Callable,
    policy: RetryPolicy
):
    """带退避的重试"""
    for attempt in range(policy.max_attempts):
        try:
            return await func()
        except Exception as e:
            if attempt < policy.max_attempts - 1:
                backoff = min(
                    policy.backoff_base * (2 ** attempt),
                    policy.max_backoff
                )
                await asyncio.sleep(backoff)
            else:
                raise
```

**验收**：
- [ ] LLM 调用自动重试
- [ ] 工具调用重试
- [ ] 退避策略合理

---

### Phase 1 总结

**交付物**：
- Bootstrap 文件系统
- 分层事件流
- CLI 工具
- 配置管理增强
- 错误重试机制

**时间**：2-3周
**难度**：⭐⭐⭐
**收益**：⭐⭐⭐⭐⭐

**里程碑**：v0.3.0 发布 - 生产基础版

---

### 🔧 Phase 2: 可观测性和性能（2-3周）

**目标**: 让系统可监控、可调试、高性能

#### 2.1 结构化日志系统 ⭐⭐⭐⭐

**功能**：
```python
# 日志级别
DEBUG, INFO, WARNING, ERROR, CRITICAL

# 结构化输出
{
  "timestamp": "2026-01-29T10:30:00Z",
  "level": "INFO",
  "run_id": "run_abc123",
  "event": "tool_call",
  "data": {
    "tool": "search",
    "duration": 1.23,
    "success": true
  }
}

# 日志文件
logs/
  {run_id}/
    agent.log.jsonl    # 结构化日志
    console.log        # 人读日志
    metrics.json       # 性能指标
```

**实现**：
```python
# src/fastreact/observability/logger.py
class StructuredLogger:
    def __init__(self, run_id: str, log_dir: str = "logs"):
        self.run_id = run_id
        self.log_file = f"{log_dir}/{run_id}/agent.log.jsonl"

    def log(self, level: str, event: str, data: dict):
        """记录结构化日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "run_id": self.run_id,
            "event": event,
            "data": data
        }
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
```

**验收**：
- [ ] 所有操作都有日志
- [ ] 日志格式统一
- [ ] 支持日志查询

---

#### 2.2 性能指标收集 ⭐⭐⭐⭐

**功能**：
```python
# 收集的指标
{
  "llm_calls": 10,
  "llm_tokens": 5000,
  "llm_latency": 15.3,  # 秒
  "tool_calls": 8,
  "tool_latency": 2.1,
  "total_time": 20.5,
  "memory_usage": "256MB"
}

# 导出到 Prometheus
from prometheus_client import Counter, Histogram

llm_calls_total = Counter('fastreact_llm_calls_total', 'Total LLM calls')
llm_latency = Histogram('fastreact_llm_latency_seconds', 'LLM latency')
```

**验收**：
- [ ] 关键指标收集
- [ ] Prometheus 导出
- [ ] Grafana 仪表盘（可选）

---

#### 2.3 分布式追踪 ⭐⭐⭐

**功能**：
```python
# 使用 OpenTelemetry
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("agent_run"):
    with tracer.start_as_current_span("llm_call"):
        response = await llm.chat()
    with tracer.start_as_current_span("tool_call"):
        result = await tool.execute()
```

**验收**：
- [ ] 追踪链路完整
- [ ] Jaeger 集成
- [ ] 性能分析

---

#### 2.4 Lane-based 并发控制 ⭐⭐⭐

**参考 moltbot 的实现**

**功能**：
```python
# 会话级串行，全局并发
class SessionLane:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._queue = asyncio.Queue()
        self._running = False

    async def run(self, coro):
        """在会话车道中运行"""
        future = asyncio.Future()
        await self._queue.put((coro, future))

        if not self._running:
            self._running = True
            while not self._queue.empty():
                coro, future = await self._queue.get()
                try:
                    result = await coro
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
            self._running = False

        return await future

# 使用
lane = agent.get_lane(session_id)
result = await lane.run(agent.run_async(query))
```

**收益**：
- 会话隔离（防止竞态）
- 更好的并发性能
- 状态一致性

**验收**：
- [ ] 会话正确串行
- [ ] 不同会话并发
- [ ] 无状态竞态

---

#### 2.5 缓存优化 ⭐⭐⭐

**功能**：
```python
# 多级缓存
class CacheManager:
    def __init__(self):
        self.l1_cache = {}  # 内存缓存
        self.l2_cache = None  # Redis（可选）

    async def get(self, key: str):
        # L1: 内存
        if key in self.l1_cache:
            return self.l1_cache[key]

        # L2: Redis
        if self.l2_cache:
            value = await self.l2_cache.get(key)
            if value:
                self.l1_cache[key] = value
                return value

        return None

    async def set(self, key: str, value: any, ttl: int = 3600):
        self.l1_cache[key] = value
        if self.l2_cache:
            await self.l2_cache.set(key, value, ex=ttl)
```

**验收**：
- [ ] LRU 缓存正常
- [ ] Redis 缓存（可选）
- [ ] 缓存命中率 > 30%

---

### Phase 2 总结

**交付物**：
- 结构化日志
- 性能指标
- 分布式追踪
- Lane 并发
- 缓存优化

**时间**：2-3周
**难度**：⭐⭐⭐⭐
**收益**：⭐⭐⭐⭐

**里程碑**：v0.4.0 发布 - 可观测性增强版

---

### 🚀 Phase 3: 高级特性（3-4周）

**目标**: 让系统更智能、更强大

#### 3.1 任务规划器（Planner）⭐⭐⭐⭐

**已有规划**，参考 `implementation_roadmap.md`

**简化实现**：
```python
class TaskPlanner:
    async def plan(self, goal: str) -> Plan:
        """生成执行计划"""
        # 1. 分析任务
        analysis = await self._analyze(goal)

        # 2. 分解子任务
        subtasks = await self._decompose(goal, analysis)

        # 3. 生成执行顺序
        plan = Plan(goal=goal, subtasks=subtasks)
        return plan

    async def execute(self, plan: Plan) -> Dict:
        """执行计划"""
        results = []
        for subtask in plan.subtasks:
            result = await self.agent.run_async(subtask.description)
            results.append(result)

        return self._synthesize(results)
```

**验收**：
- [ ] 自动任务分解
- [ ] 并行执行
- [ ] 计划调整

---

#### 3.2 长期记忆系统 ⭐⭐⭐⭐

**已有规划**，简化实现：

```python
# 使用 ChromaDB（轻量级）
from fastreact.memory import MemoryManager

memory = MemoryManager()

# 存储记忆
await memory.memorize(
    content="用户偏好使用 Python",
    memory_type="episodic",
    metadata={"user": "alice"}
)

# 检索记忆
memories = await memory.remember(
    query="用户喜欢什么编程语言？",
    limit=5
)
```

**验收**：
- [ ] 向量存储
- [ ] 语义检索
- [ ] 记忆更新

---

#### 3.3 自动上下文压缩 ⭐⭐⭐

**参考 moltbot**

**功能**：
```python
class ContextCompressor:
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens

    async def compress(self, messages: List) -> List:
        """压缩上下文"""
        current_tokens = self._count_tokens(messages)

        if current_tokens > self.max_tokens * 0.9:
            # 触发压缩
            return await self._do_compress(messages)

        return messages

    async def _do_compress(self, messages: List) -> List:
        """执行压缩"""
        # 保留最近 N 条消息
        recent = messages[-10:]

        # 早期消息总结
        summary = await self._summarize(messages[:-10])

        # 组合
        return [
            {"role": "system", "content": f"历史对话总结: {summary}"}
        ] + recent
```

**验收**：
- [ ] 自动检测超限
- [ ] 智能压缩
- [ ] 保持连贯性

---

#### 3.4 插件系统 ⭐⭐⭐

**功能**：
```python
# 插件定义
# plugins/custom_tool.py
from fastreact.plugins import Plugin

class CustomToolPlugin(Plugin):
    name = "custom_tool"

    def register_tools(self):
        return [MyCustomTool()]

    def on_init(self, agent):
        """插件初始化"""
        pass

    def on_before_run(self, query):
        """运行前钩子"""
        pass

    def on_after_run(self, result):
        """运行后钩子"""
        pass

# 插件加载
agent = FastReAct(
    plugins=["custom_tool", "memory", "analytics"]
)
```

**验收**：
- [ ] 插件加载
- [ ] Hook 机制
- [ ] 插件示例

---

### Phase 3 总结

**交付物**：
- 任务规划器
- 长期记忆
- 上下文压缩
- 插件系统

**时间**：3-4周
**难度**：⭐⭐⭐⭐
**收益**：⭐⭐⭐⭐⭐

**里程碑**：v1.0.0 发布 - 功能完整版

---

## 📦 部署和运维

### Docker 部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8765

CMD ["fastreact", "gateway", "start", "--port", "8765"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  fastreact:
    build: .
    ports:
      - "8765:8765"
    environment:
      - FASTREACT_PROFILE=production
    volumes:
      - ./config:/app/config
      - ./data:/app/data
      - ./logs:/app/logs
```

### 健康检查

```python
# src/fastreact/health.py
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "uptime": uptime()
    }
```

### 监控告警

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'fastreact'
    static_configs:
      - targets: ['localhost:8765']
```

---

## 🎯 优先级总结

### 立即开始（P0）

1. **Bootstrap 文件系统** - 灵活配置
2. **分层事件流** - 可观测性基础
3. **CLI 工具** - 易用性
4. **错误重试** - 稳定性

### 近期实施（P1）

5. **配置管理增强**
6. **结构化日志**
7. **性能指标**
8. **Lane 并发**

### 中期考虑（P2）

9. **任务规划器**
10. **长期记忆**
11. **上下文压缩**
12. **插件系统**

### 长期优化（P3）

13. **分布式追踪**
14. **多级缓存**
15. **Dashboard**
16. **自动扩缩容**

---

## 📊 版本规划

| 版本 | 时间 | 核心特性 | 定位 |
|------|------|----------|------|
| **v0.3.0** | 2-3周 | Bootstrap, 事件流, CLI, 重试 | 生产基础 |
| **v0.4.0** | 2-3周 | 日志, 指标, 追踪, 并发 | 可观测性 |
| **v0.5.0** | 2-3周 | 规划器, 记忆, 压缩 | 智能化 |
| **v1.0.0** | 1周 | 插件, 文档, 测试 | 功能完整 |

---

## 🎨 架构愿景

```
FastReAct v1.0.0 架构

┌─────────────────────────────────────────────┐
│              CLI / API / Gateway             │
├─────────────────────────────────────────────┤
│           Bootstrap 配置系统                  │
├─────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Planner  │  │ Memory   │  │ Orchestr. │  │
│  └──────────┘  └──────────┘  └──────────┘  │
├─────────────────────────────────────────────┤
│              ReAct 核心引擎                   │
│  - 事件流                                   │
│  - Lane 并发                                │
│  - 自动重试                                 │
├─────────────────────────────────────────────┤
│           工具系统 + 沙箱                    │
├─────────────────────────────────────────────┤
│  可观测性：日志 | 指标 | 追踪                │
└─────────────────────────────────────────────┘
```

---

## 💡 成功标准

### v0.3.0（生产基础）

- [ ] 无需编程即可使用（CLI）
- [ ] 配置文件管理一切
- [ ] 系统稳定运行 24h+
- [ ] 错误自动恢复

### v0.4.0（可观测性）

- [ ] 所有操作可追踪
- [ ] 性能指标可视化
- [ ] 日志统一格式
- [ ] 问题快速定位

### v1.0.0（功能完整）

- [ ] 任务自动规划
- [ ] 长期记忆工作
- [ ] 插件易于扩展
- [ ] 文档完整清晰

---

## 🚀 开始实施

### 第一步：Bootstrap 文件系统

**为什么先做这个？**
1. **高价值** - 大幅提升灵活性
2. **低成本** - 实现简单
3. **无风险** - 不破坏现有功能
4. **立即可用** - 用户马上受益

**实施步骤**：
1. 创建 `src/fastreact/bootstrap/` 模块
2. 实现 `BootstrapLoader` 类
3. 集成到 `FastReAct.__init__()`
4. 编写测试
5. 更新文档

**预计时间**：3-5天

---

**准备好了吗？让我们开始！**
