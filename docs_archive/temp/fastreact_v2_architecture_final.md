# FastReAct v2.0 最终架构设计

## 执行摘要

基于对 nanobot 的深入研究和代码审查，我们确定了 FastReAct v2.0 的最终架构方案。

**核心决策**：保留 nanobot 70% 的优秀设计 + 增强 30% 的企业特性

**目标**：
- 代码量：<6500 行（v1.0 的 13%）
- Token 成本：降低 70%+
- 启动时间：<1 秒
- 首响延迟：<1 秒
- 多渠道：6+ 种渠道支持
- Skills 系统：完整实现

---

## 一、架构总览

### 1.1 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    Channels Layer                        │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │ CLI  │  │ Web  │  │ API  │  │  IM  │  │Email │      │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘      │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  MessageBus (Bridge)                     │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ StandardMessage  │  │ ReasoningResult  │            │
│  └──────────────────┘  └──────────────────┘            │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                     Core Layer                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
│  │ ReAct Loop │  │  Context   │  │  Skills    │        │
│  │  (~400)    │  │  (~250)    │  │  (~250)    │        │
│  └────────────┘  └────────────┘  └────────────┘        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                    Support Layer                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │
│  │ Tools   │  │Provider │  │ Session │  │ Memory  │   │
│  │ (~1000) │  │ (~300)  │  │ (~200)  │  │ (~150)  │   │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 1.2 代码分布

| 层级 | 模块 | 代码量 | 来源 |
|------|------|--------|------|
| **Channels** | 渠道实现 | ~1800 | nanobot 改造 |
| **Bridge** | MessageBus | ~400 | 新增 |
| **Core** | ReAct 循环 | ~400 | nanobot 复用 |
| **Core** | 上下文构建 | ~250 | nanobot 复用 |
| **Core** | Skills 系统 | ~250 | nanobot 复用 |
| **Support** | 工具系统 | ~1000 | nanobot 复用 |
| **Support** | Provider | ~300 | nanobot 简化 |
| **Support** | 会话管理 | ~200 | nanobot 复用 |
| **Support** | 记忆系统 | ~150 | nanobot 复用 |
| **Support** | 插件系统 | ~900 | 新增 |
| **总计** | | **~6150** | |

---

## 二、核心组件设计

### 2.1 ReAct Loop（基于 nanobot）

**复用 nanobot 的 377 行实现**：

```python
# src/fastreact/core/loop.py
class ReActCore:
    async def reason(self, query: str, context: dict) -> ReasoningResult:
        """Pure ReAct reasoning, channel-agnostic"""
        messages = self._build_context(context)

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            # 调用 LLM
            response = await self.provider.chat(
                messages=messages,
                tools=self.tools.get_definitions(),
                model=self.model
            )

            # 处理工具调用
            if response.has_tool_calls:
                for tool_call in response.tool_calls:
                    result = await self.tools.execute(
                        tool_call.name,
                        tool_call.arguments
                    )
                    messages = self._add_tool_result(
                        messages,
                        tool_call.id,
                        result
                    )
            else:
                # 无工具调用，结束
                return ReasoningResult(answer=response.content)

        return ReasoningResult(answer="Max iterations reached")
```

**关键点**：
- ✅ 纯推理逻辑，零渠道依赖
- ✅ 异步执行
- ✅ 最大迭代保护（20 次）
- ✅ 流式输出支持

### 2.2 Context 构建（基于 nanobot）

**4 层渐进式加载**：

```python
# src/fastreact/core/context.py
class ContextBuilder:
    def build_system_prompt(self) -> str:
        parts = []

        # Layer 1: 核心身份（~200 tokens）
        parts.append(self._get_identity())

        # Layer 2: Bootstrap 文件（~1000 tokens）
        parts.append(self._load_bootstrap_files())

        # Layer 3: Always 技能（~3000 tokens）
        always_skills = self.skills.get_always_skills()
        parts.append(self.load_skills_for_context(always_skills))

        # Layer 4: Available 技能（~500 tokens）
        skills_summary = self.skills.build_skills_summary()
        parts.append(skills_summary)

        # 总计: ~4700 tokens（比 v1.0 节省 72%）
        return "\n\n---\n\n".join(parts)
```

**Bootstrap 文件**：
```
~/.fastreact/
├── AGENTS.md       # Agent 角色和行为
├── TOOLS.md        # 工具使用指南
├── CONSTRAINTS.md  # 约束条件
└── IDENTITY.md     # 身份信息
```

### 2.3 Skills 系统（基于 nanobot）

**三级加载**：

```python
# src/fastreact/core/skills.py
class SkillsLoader:
    def list_skills(self):
        """列出所有技能（workspace > builtin）"""
        for skill_dir in self.workspace_skills.iterdir():
            yield self._load_skill_meta(skill_dir)

        for skill_dir in self.builtin_skills.iterdir():
            yield self._load_skill_meta(skill_dir)

    def build_skills_summary(self) -> str:
        """构建 XML 摘要（~500 tokens）"""
        lines = ["<skills>"]
        for skill in self.list_skills():
            available = self._check_requirements(skill)
            lines.append(f"""  <skill available="{str(available).lower()}">
    <name>{skill.name}</name>
    <description>{skill.description}</description>
    <location>{skill.path}</location>
    <requires>{skill.missing_requirements}</requires>
  </skill>""")
        return "\n".join(lines)
```

**SKILL.md 格式**：
```yaml
---
name: web_search
description: "Search the web using Brave Search API"
dependencies: []
always_load: false
---

# Web Search

## Usage

Search the web:
```bash
search_brave "Python 3.12 features"
```
```

### 2.4 MessageBus（新增）

**解耦核心和渠道**：

```python
# src/fastreact/bridge/messagebus.py
class MessageBus:
    """Bridge between ReAct core and channels"""

    async def process(self, message: StandardMessage) -> ReasoningResult:
        """Process a message through the core"""
        context = {
            "user_id": message.user_id,
            "channel_type": message.channel_type,
            "attachments": message.attachments,
            "metadata": message.metadata,
        }

        result = await self.core.reason(
            query=message.content,
            context=context
        )

        return result
```

**标准消息格式**：
```python
@dataclass
class StandardMessage:
    session_id: str
    content: str
    user_id: str | None = None
    channel_type: str | None = None
    attachments: list[Attachment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ReasoningResult:
    answer: str
    tool_calls: list[dict] = field(default_factory=list)
    tokens_used: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 2.5 渠道接口（新增）

**统一渠道接口**：

```python
# src/fastreact/channels/base.py
class Channel(ABC):
    @abstractmethod
    async def start(self) -> None: pass

    @abstractmethod
    async def stop(self) -> None: pass

    @abstractmethod
    async def send(self, result: ReasoningResult, recipient: str) -> None: pass

    @abstractmethod
    async def receive(self) -> StandardMessage: pass
```

**CLI 渠道示例**：
```python
# src/fastreact/channels/cli.py
class CLIChannel(Channel):
    async def start(self) -> None:
        while True:
            message = await self.receive()
            result = await self.bus.process(message)
            await self.send(result, message.session_id)

    async def receive(self) -> StandardMessage:
        user_input = await self._get_input()
        return StandardMessage(
            session_id="cli-session",
            content=user_input,
            channel_type="cli"
        )

    async def send(self, result: ReasoningResult, recipient: str) -> None:
        print(f"\n[Assistant] {result.answer}\n")
```

---

## 三、工具系统设计

### 3.1 Tool 基类（复用 nanobot）

**103 行极简设计**：

```python
# src/fastreact/tools/base.py
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def description(self) -> str: pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]: pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str: pass

    def validate_params(self, params: dict) -> list[str]:
        """JSON Schema 验证"""
        ...
```

### 3.2 ToolRegistry（复用 nanobot）

**74 行动态注册**：

```python
# src/fastreact/tools/registry.py
class ToolRegistry:
    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get_definitions(self) -> list[dict[str, Any]]:
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(self, name: str, params: dict) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"

        errors = tool.validate_params(params)
        if errors:
            return f"Error: Invalid parameters: " + "; ".join(errors)

        return await tool.execute(**params)
```

### 3.3 Shell 工具（复用 nanobot）

**8 种安全防护**：

```python
# src/fastreact/tools/shell.py
class ExecTool(Tool):
    def __init__(self):
        self.deny_patterns = [
            r"\brm\s+-[rf]{1,2}\b",          # rm -r, rm -rf
            r"\bdel\s+/[fq]\b",              # del /f, del /q
            r"\brmdir\s+/s\b",               # rmdir /s
            r"\b(format|mkfs|diskpart)\b",   # 磁盘操作
            r"\bdd\s+if=",                   # dd
            r">\s*/dev/sd",                  # 写入磁盘
            r"\b(shutdown|reboot)\b",        # 系统关机
            r":\(\)\s*\{.*\};\s*:",          # Fork 炸弹
        ]

    def _guard_command(self, command: str) -> str | None:
        for pattern in self.deny_patterns:
            if re.search(pattern, command.lower()):
                return "Error: Command blocked (dangerous pattern)"
        return None
```

---

## 四、Provider 简化设计

### 4.1 简化版 Registry（基于 nanobot）

**从 11+ 简化到 6 个核心提供商**：

```python
# src/fastreact/providers/registry.py
PROVIDERS: tuple[ProviderSpec, ...] = (
    # 网关
    ProviderSpec(name="openrouter", keywords=("openrouter",), ...),

    # 标准
    ProviderSpec(name="anthropic", keywords=("anthropic", "claude"), ...),
    ProviderSpec(name="openai", keywords=("openai", "gpt"), ...),
    ProviderSpec(name="deepseek", keywords=("deepseek",), ...),

    # 本地
    ProviderSpec(name="ollama", keywords=("ollama",), is_local=True),
    ProviderSpec(name="vllm", keywords=("vllm",), is_local=True),
)
```

**减少原因**：
- ✅ 覆盖 99% 使用场景
- ✅ 降低维护成本
- ✅ 减少代码复杂度

### 4.2 智能匹配（复用 nanobot）

```python
def find_by_model(model: str) -> ProviderSpec | None:
    model_lower = model.lower()
    for spec in PROVIDERS:
        if spec.is_local:
            continue
        if any(kw in model_lower for kw in spec.keywords):
            return spec
    return None
```

---

## 五、插件系统设计（新增）

### 5.1 插件接口

```python
# src/fastreact/plugins/base.py
class Plugin(ABC):
    @abstractmethod
    async def on_init(self, app) -> None: pass

    @abstractmethod
    async def on_message(self, message: StandardMessage) -> StandardMessage: pass

    @abstractmethod
    async def on_result(self, result: ReasoningResult) -> ReasoningResult: pass

    @abstractmethod
    async def on_shutdown(self, app) -> None: pass
```

### 5.2 插件管理器

```python
# src/fastreact/plugins/manager.py
class PluginManager:
    def __init__(self):
        self.plugins: list[Plugin] = []

    def register(self, plugin: Plugin) -> None:
        self.plugins.append(plugin)

    async def hook_message(self, message: StandardMessage) -> StandardMessage:
        for plugin in self.plugins:
            message = await plugin.on_message(message)
        return message

    async def hook_result(self, result: ReasoningResult) -> ReasoningResult:
        for plugin in self.plugins:
            result = await plugin.on_result(result)
        return result
```

### 5.3 可观测性插件

```python
# src/fastreact/plugins/observability.py
class ObservabilityPlugin(Plugin):
    async def on_init(self, app) -> None:
        self.metrics = MetricsCollector()

    async def on_message(self, message: StandardMessage) -> StandardMessage:
        self.metrics.track_message(message)
        return message

    async def on_result(self, result: ReasoningResult) -> ReasoningResult:
        self.metrics.track_result(result)
        return result
```

---

## 六、目录结构（最终版）

```
fastreact/
├── src/fastreact/
│   ├── __init__.py
│   │
│   ├── core/                      # 核心引擎（~1100 行）
│   │   ├── __init__.py
│   │   ├── loop.py                # ReAct 循环（~400）
│   │   ├── context.py             # 上下文构建（~250）
│   │   ├── skills.py              # Skills 系统（~250）
│   │   └── session.py             # 会话管理（~200）
│   │
│   ├── bridge/                    # 桥接层（~400 行）
│   │   ├── __init__.py
│   │   ├── messagebus.py          # 消息总线（~150）
│   │   ├── message.py             # 标准消息（~100）
│   │   └── session.py             # 会话管理（~150）
│   │
│   ├── channels/                  # 渠道（~1800 行）
│   │   ├── __init__.py
│   │   ├── base.py                # 渠道基类（~150）
│   │   ├── cli.py                 # CLI 渠道（~400）
│   │   ├── web.py                 # Web 渠道（~500）
│   │   ├── telegram.py            # IM 渠道（~500）
│   │   └── discord.py             # IM 渠道（~400）
│   │
│   ├── tools/                     # 工具（~1000 行）
│   │   ├── __init__.py
│   │   ├── base.py                # 工具基类（~100）
│   │   ├── registry.py            # 工具注册（~100）
│   │   ├── shell.py               # Shell 工具（~150）
│   │   ├── filesystem.py          # 文件操作（~200）
│   │   └── web.py                 # Web 工具（~150）
│   │
│   ├── providers/                 # LLM 提供商（~300 行）
│   │   ├── __init__.py
│   │   ├── registry.py            # 提供商注册（~200）
│   │   └── litellm_provider.py    # LiteLLM（~100）
│   │
│   └── plugins/                   # 插件（~900 行）
│       ├── __init__.py
│       ├── base.py                # 插件基类（~100）
│       ├── manager.py             # 插件管理（~150）
│       ├── observability/         # 可观测性（~400）
│       └── storage/               # 存储插件（~250）
│
├── templates/                     # 模板文件
│   ├── AGENTS.md
│   ├── TOOLS.md
│   ├── CONSTRAINTS.md
│   └── skills/                    # Skills 模板
│       ├── web_search/
│       │   └── SKILL.md
│       └── github/
│           └── SKILL.md
│
├── tests/                         # 测试
│   ├── test_core/
│   ├── test_bridge/
│   ├── test_channels/
│   └── test_tools/
│
├── examples/                      # 示例
│   ├── demo_cli.py
│   └── demo_skills.py
│
├── pyproject.toml
├── README.md
└── INSTALLATION.md
```

---

## 七、关键设计决策

### 7.1 为什么基于 nanobot？

| 因素 | nanobot | 从头写 |
|------|---------|--------|
| **时间** | 6 周 | 12 周 |
| **风险** | 低（已验证） | 高（未知问题）|
| **代码质量** | 高（已测试） | 中（需迭代）|
| **功能完整** | 高（开箱即用） | 中（逐步添加）|
| **学习价值** | 中 | 高 |

**决策**：基于 nanobot 改造（节省 50% 时间）

### 7.2 为什么添加 MessageBus？

**问题**：nanobot 的核心直接处理渠道消息，耦合度高

**解决**：MessageBus 作为中间层，解耦核心和渠道

**好处**：
- ✅ 核心专注推理
- ✅ 渠道专注交互
- ✅ 易于扩展新渠道
- ✅ 易于测试

### 7.3 为什么简化 Provider？

**nanobot**：11+ 提供商

**FastReAct v2.0**：6 个核心提供商

**原因**：
- ✅ 覆盖 99% 使用场景
- ✅ 降低维护成本
- ✅ 减少代码复杂度

### 7.4 为什么保留 Skills 系统？

**核心价值**：
- ✅ Token 节省 72%
- ✅ 文件驱动（用户可定制）
- ✅ Agent 可读写
- ✅ 未来标准

**复用策略**：完整采用 nanobot 的 Skills 系统

---

## 八、实施计划

### 阶段 1：核心复用（1 周）
- [ ] 复制 Tool、ToolRegistry、Shell、Filesystem
- [ ] 调整导入路径
- [ ] 验证核心功能

### 阶段 2：Provider 简化（3 天）
- [ ] 创建简化版 Registry（6 个提供商）
- [ ] 验证模型匹配
- [ ] 测试 LLM 调用

### 阶段 3：Skills 集成（1 周）
- [ ] 复制 SkillsLoader
- [ ] 创建 FastReAct 技能
- [ ] 测试渐进式加载

### 阶段 4：MessageBus（1 周）
- [ ] 实现标准消息格式
- [ ] 实现 MessageBus
- [ ] 测试解耦架构

### 阶段 5：渠道实现（1 周）
- [ ] 实现渠道基类
- [ ] 实现 CLI 渠道
- [ ] 实现 Web 渠道

### 阶段 6：插件系统（1 周）
- [ ] 实现插件接口
- [ ] 实现插件管理器
- [ ] 实现可观测性插件

### 阶段 7：测试和文档（1 周）
- [ ] 集成测试
- [ ] 性能测试
- [ ] 文档编写

**总计**：5-6 周

---

## 九、成功标准

### 9.1 功能完整性
- ✅ 保留所有 FastReAct v1.0 功能
- ✅ 添加 Skills 系统
- ✅ 添加 MessageBus
- ✅ 支持多渠道

### 9.2 性能目标
- ✅ Token 成本降低 70%
- ✅ 启动时间 <1 秒
- ✅ 首响延迟 <1 秒
- ✅ 代码量 <7000 行

### 9.3 质量目标
- ✅ 所有测试通过
- ✅ 文档完整
- ✅ 跨平台兼容
- ✅ 生产就绪

---

## 十、下一步行动

**立即开始**：

1. **Fork nanobot** - 已完成（D:/FastReAct/fastreact-v2）
2. **代码审查** - 已完成（核心文件分析）
3. **创建 POC** - 下一步（MessageBus 概念验证）
4. **开始迁移** - 阶段 1（核心复用）

**本周目标**：
- [ ] 完成 Tool、ToolRegistry 复用
- [ ] 完成 Shell、Filesystem 复用
- [ ] 验证核心功能
- [ ] 创建 MessageBus POC

---

**FastReAct v2.0 = nanobot 的简洁 + 企业级特性**

准备好了开始实现吗？
