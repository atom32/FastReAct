# FastReAct v2.0 方案：企业级 + 极速

## 执行摘要

**目标**：打造一个 **Fast（<5000 行核心）** 但具备 **企业级特性** 的 ReAct Agent 框架

**核心原则**：
1. **极简核心** - 核心引擎 <2000 行
2. **文件驱动** - 配置、Prompt、技能全文件化
3. **渐进增强** - 企业特性作为可选插件
4. **生产就绪** - 可观测性、可靠性、可扩展性

---

## 一、现状分析

### 1.1 问题诊断

| 问题 | 现状 | 影响 |
|------|------|------|
| **太慢** | 50,792 行代码 | 难以理解、难以维护、迭代慢 |
| **过度设计** | 3 种模式 (ReAct/Graph/IEL) | 复杂度爆炸，80% 功能只用 20% |
| **硬编码** | Prompt、配置在代码中 | 用户无法定制，扩展困难 |
| **厚抽象** | LLMDriver、EventManager... | 学习曲线陡峭 |
| **文件臃肿** | engine.py 3043 行 | 难以定位问题 |

### 1.2 成功案例学习

#### **nanobot** - 极简主义的胜利
- ✅ 7,095 行实现完整功能
- ✅ 文件驱动（Bootstrap、技能）
- ✅ 单一职责，模块清晰
- ❌ 缺少企业级特性（监控、追踪）

#### **Claude Code** - ReAct 的实践证明
- ✅ ReAct 模式足够强大
- ✅ 工具调用简洁高效
- ✅ 流式输出用户体验好
- ❌ 闭源，无法学习细节

#### **Moltbot** - 企业级的平衡
- ✅ 功能与规模的平衡
- ✅ 可观测性设计
- ❌ 仍有优化空间

---

## 二、v2.0 核心架构

### 2.1 设计哲学

```
极简核心 + 文件驱动 + 可选插件 = FastReAct v2.0
```

**三大支柱**：

1. **极简核心 (Core)**
   - 单一 ReAct 引擎
   - <2000 行代码
   - 清晰的职责边界

2. **文件驱动 (FileSystem)**
   - Prompt → Markdown 文件
   - 配置 → YAML 文件
   - 技能 → SKILL.md 文件
   - 记忆 → Markdown + JSON

3. **插件系统 (Plugins)**
   - 企业特性作为可选插件
   - 按需加载
   - 标准化接口

### 2.2 目录结构

```
fastreact/
├── core/                      # 核心引擎 (~2000 行)
│   ├── __init__.py
│   ├── engine.py              # ReAct 引擎 (~500 行)
│   ├── context.py             # 上下文构建 (~300 行)
│   ├── memory.py              # 记忆系统 (~200 行)
│   ├── tools.py               # 工具注册表 (~200 行)
│   └── session.py             # 会话管理 (~200 行)
│
├── plugins/                   # 可选插件
│   ├── observability/         # 可观测性插件
│   │   ├── tracker.py         # 追踪系统
│   │   ├── metrics.py         # 指标收集
│   │   └── logger.py          # 结构化日志
│   │
│   ├── storage/               # 存储插件
│   │   ├── vector.py          # 向量存储
│   │   ├── checkpoint.py      # 检查点
│   │   └── sqlite.py          # SQLite 持久化
│   │
│   └── channels/              # 渠道插件
│       ├── web.py             # Web 渠道
│       ├── cli.py             # CLI 渠道
│       └── api.py             # API 渠道
│
├── tools/                     # 工具实现 (~1500 行)
│   ├── filesystem.py          # 文件操作
│   ├── shell.py               # Shell 执行
│   ├── web.py                 # Web 工具
│   └── base.py                # 工具基类
│
├── providers/                 # LLM 提供商 (~800 行)
│   ├── base.py                # 提供商接口
│   ├── openai.py              # OpenAI 兼容
│   ├── anthropic.py           # Anthropic
│   └── registry.py            # 提供商注册表
│
├── cli/                       # 命令行界面 (~500 行)
│   ├── repl.py                # 交互式 REPL
│   └── commands.py            # CLI 命令
│
└── templates/                 # 模板文件
    ├── AGENTS.md              # Agent 角色模板
    ├── TOOLS.md               # 工具指南模板
    ├── MEMORY.md              # 记忆模板
    └── config.yaml            # 配置模板
```

**代码分布**：
- 核心：2000 行
- 工具：1500 行
- 提供商：800 行
- CLI：500 行
- **总计：~5000 行**（v1.0 的 10%）

---

## 三、核心设计

### 3.1 极简 ReAct 引擎

**设计目标**：
- 单一职责：只做 ReAct 循环
- <500 行代码
- 清晰的接口

**实现要点**：

```python
class ReActEngine:
    """
    极简 ReAct 引擎

    职责：
    1. 运行 ReAct 循环
    2. 调用 LLM
    3. 执行工具
    4. 管理会话
    """

    def __init__(
        self,
        provider: LLMProvider,
        tools: ToolRegistry,
        workspace: Path,
        config: EngineConfig,
    ):
        self.provider = provider
        self.tools = tools
        self.workspace = workspace
        self.config = config

        # 可选插件
        self.plugins = []
        if config.get("enable_observability"):
            self.plugins.append(ObservabilityPlugin())
        if config.get("enable_checkpoint"):
            self.plugins.append(CheckpointPlugin())

    async def run(
        self,
        query: str,
        session_id: str | None = None,
    ) -> ReActResult:
        """运行 ReAct 循环"""

        # 1. 获取/创建会话
        session = self._get_session(session_id)

        # 2. 构建上下文
        context = self._build_context(session)

        # 3. ReAct 循环（核心逻辑）
        for iteration in range(self.config.max_iterations):

            # Phase 1: 思考
            thought = await self._think(query, context)

            # Phase 2: 行动
            actions = self._parse_actions(thought)

            # Phase 3: 观察
            observations = await self._execute_actions(actions)

            # Phase 4: 判断
            if self._should_stop(observations):
                break

            # 更新上下文
            context = self._update_context(context, observations)

        # 4. 返回结果
        return ReActResult(
            answer=context["last_message"],
            steps=context["history"],
            metrics=self._collect_metrics(),
        )

    async def _think(self, query: str, context: dict) -> str:
        """思考阶段：调用 LLM"""
        messages = self._build_messages(query, context)

        response = await self.provider.chat(
            messages=messages,
            tools=self.tools.get_schemas(),
        )

        return response

    def _parse_actions(self, thought: str) -> list[Action]:
        """解析工具调用"""
        # 从 LLM 响应中提取工具调用
        ...

    async def _execute_actions(self, actions: list[Action]) -> list[Observation]:
        """执行工具调用"""
        observations = []
        for action in actions:
            result = await self.tools.execute(action.name, action.args)
            observations.append(Observation(action.name, result))
        return observations
```

**关键设计决策**：

1. **无复杂度评估** - 直接进入 ReAct，节省 400 行
2. **无模式选择** - 只支持 ReAct，节省 2000 行
3. **无 Double Check** - 简化流程，节省 500 行
4. **插件化** - 企业特性通过插件添加，不污染核心

### 3.2 文件驱动架构

**核心理念**：所有可定制内容都通过文件管理

#### **文件结构**

```
~/.fastreact/
├── config.yaml               # 全局配置
├── agents/                   # Agent 定义
│   ├── default/
│   │   ├── AGENTS.md         # Agent 角色
│   │   ├── TOOLS.md          # 工具指南
│   │   └── CONSTRAINTS.md    # 约束条件
│   └── coder/                # 自定义 Agent
│       └── AGENTS.md
├── skills/                   # 技能库
│   ├── web_search/
│   │   └── SKILL.md
│   ├── code_analysis/
│   │   └── SKILL.md
│   └── data_processing/
│       └── SKILL.md
├── memory/                   # 记忆系统
│   ├── MEMORY.md             # 长期记忆
│   └── 2025-02-09.md         # 每日笔记
└── sessions/                 # 会话存储
    └── {session_id}.jsonl    # 会话历史
```

#### **Bootstrap 文件示例**

**AGENTS.md**:
```markdown
# FastReAct Agent

You are FastReAct, an intelligent AI assistant.

## Core Capabilities

- Read, write, and edit files
- Execute shell commands
- Search the web and fetch pages
- Analyze code and data
- Write and test code

## Behavior Guidelines

1. **Be Helpful**: Always aim to solve the user's problem
2. **Be Accurate**: Verify information before presenting it
3. **Be Concise**: Get to the point quickly
4. **Be Transparent**: Explain your reasoning

## Tool Usage

- Use `read_file` to examine files before editing
- Use `shell` for commands (not `bash` tool)
- Always explain what you're doing before using tools
```

**SKILL.md 示例**:

```yaml
---
name: web_search
description: Search the web using Brave Search API
version: 1.0
dependencies: []
always_load: true
---

# Web Search Skill

Search the web for information using Brave Search API.

## Usage

```python
# The agent will automatically use this tool when you ask to search
# Example queries:
- "Search for the latest Python 3.12 features"
- "Find information about Rust vs Go performance"
```

## Notes

- Returns top 10 results
- Includes snippets and URLs
- Requires BRAVE_API_KEY environment variable
```

#### **Context Builder 实现**

```python
class ContextBuilder:
    """文件驱动的上下文构建器"""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory = MemoryStore(workspace)
        self.skills = SkillLoader(workspace)

    def build_system_prompt(self, agent_name: str = "default") -> str:
        """构建系统 Prompt"""
        parts = []

        # 1. 核心 Agent 定义
        agent_file = self.workspace / "agents" / agent_name / "AGENTS.md"
        if agent_file.exists():
            parts.append(agent_file.read_text())

        # 2. 技能加载
        always_skills = self.skills.get_always_skills()
        if always_skills:
            skills_content = self.skills.load_skills(always_skills)
            parts.append(f"## Available Skills\n\n{skills_content}")

        # 3. 记忆上下文
        memory = self.memory.get_context()
        if memory:
            parts.append(f"## Memory\n\n{memory}")

        # 4. 当前会话信息
        parts.append(self._get_runtime_info())

        return "\n\n---\n\n".join(parts)
```

### 3.3 插件系统

**设计目标**：
- 企业特性作为可选插件
- 标准化接口
- 按需加载

**插件接口**：

```python
class EnginePlugin(ABC):
    """引擎插件基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass

    @abstractmethod
    async def on_before_run(self, context: RunContext) -> None:
        """运行前钩子"""
        pass

    @abstractmethod
    async def on_after_run(self, result: ReActResult) -> None:
        """运行后钩子"""
        pass

    @abstractmethod
    async def on_tool_call(self, tool: str, args: dict) -> None:
        """工具调用钩子"""
        pass
```

**示例插件**：

```python
class ObservabilityPlugin(EnginePlugin):
    """可观测性插件"""

    def __init__(self):
        self.tracer = Tracer()
        self.metrics = MetricsCollector()

    @property
    def name(self) -> str:
        return "observability"

    async def on_before_run(self, context: RunContext) -> None:
        """开始追踪"""
        self.tracer.start_span("react_run")
        self.metrics.start_timer("total_time")

    async def on_after_run(self, result: ReActResult) -> None:
        """结束追踪"""
        self.metrics.end_timer("total_time")
        self.tracer.end_span()

        # 发送到监控系统
        await self._emit_metrics(result)

    async def on_tool_call(self, tool: str, args: dict) -> None:
        """追踪工具调用"""
        self.tracer.add_event("tool_call", {
            "tool": tool,
            "args": args,
        })
        self.metrics.increment_counter(f"tool.{tool}")
```

---

## 四、迁移路径

### 4.1 阶段 1：核心重构（2 周）

**目标**：提取极简核心

**任务**：
1. ✅ 提取 ReAct 核心逻辑（~500 行）
2. ✅ 简化 Context Builder（~300 行）
3. ✅ 移除 GraphAgent 和 IEL 代码
4. ✅ 移除复杂度评估
5. ✅ 移除 Double Check 机制

**输出**：
- `core/engine.py` (~500 行)
- `core/context.py` (~300 行)
- 核心单元测试

**验收**：
- 代码行数 < 2000 行
- 通过现有 ReAct 测试用例

### 4.2 阶段 2：文件驱动（1 周）

**目标**：采用文件驱动架构

**任务**：
1. ✅ 设计 Bootstrap 文件格式
2. ✅ 实现 Skill Loader
3. ✅ 实现 Memory Store（文件系统）
4. ✅ 迁移现有 Prompt 到文件
5. ✅ 更新文档

**输出**：
- `core/skills.py`
- `core/memory.py`
- Bootstrap 文件模板
- 迁移指南

**验收**：
- 用户可通过文件定制 Agent
- 所有测试通过

### 4.3 阶段 3：插件系统（2 周）

**目标**：实现插件架构

**任务**：
1. ✅ 设计插件接口
2. ✅ 实现插件加载器
3. ✅ 迁移可观测性到插件
4. ✅ 迁移检查点到插件
5. ✅ 迁移存储到插件

**输出**：
- `plugins/` 目录
- 插件开发文档
- 示例插件

**验收**：
- 核心引擎无插件依赖
- 插件可独立开发测试

### 4.4 阶段 4：清理和优化（1 周）

**目标**：代码清理和性能优化

**任务**：
1. ✅ 移除死代码
2. ✅ 统一代码风格
3. ✅ 性能优化
4. ✅ 文档更新
5. ✅ 示例更新

**输出**：
- 清晰的代码库
- 完整的文档
- 迁移指南

**验收**：
- 代码行数 < 5000 行
- 所有测试通过
- 文档完整

### 4.5 阶段 5：测试和发布（1 周）

**目标**：全面测试和发布

**任务**：
1. ✅ 集成测试
2. ✅ 性能测试
3. ✅ 用户测试
4. ✅ 发布准备
5. ✅ 发布 v2.0

**输出**：
- FastReAct v2.0
- 发布说明
- 迁移工具

**验收**：
- 所有测试通过
- 性能满足要求
- 文档完整

---

## 五、企业特性保留

### 5.1 必须保留的特性

| 特性 | 实现方式 | 代码量 |
|------|---------|--------|
| **会话管理** | 核心 | 200 行 |
| **错误处理** | 核心 | 100 行 |
| **超时控制** | 核心 | 50 行 |
| **工具验证** | 核心 | 150 行 |
| **流式输出** | 核心 | 200 行 |
| **可观测性** | 插件 | 500 行 |
| **检查点** | 插件 | 400 行 |
| **向量存储** | 插件 | 600 行 |
| **结构化日志** | 插件 | 300 行 |

**总计**：核心 ~1000 行 + 插件 ~1800 行

### 5.2 可选特性

| 特性 | 移除原因 | 替代方案 |
|------|---------|---------|
| **GraphAgent** | 复杂度高，使用率低 | 外部工具 |
| **IEL** | 复杂度高，使用率低 | 异步工具 |
| **复杂度评估** | ReAct 足够好 | 用户手动选择 |
| **Double Check** | 增加延迟 | 用户验证 |

### 5.3 新增特性

| 特性 | 价值 | 代码量 |
|------|------|--------|
| **技能系统** | 用户可扩展 | 300 行 |
| **文件驱动** | 易于定制 | 200 行 |
| **插件系统** | 企业可扩展 | 400 行 |
| **热重载** | 开发体验 | 100 行 |

---

## 六、性能优化

### 6.1 目标

| 指标 | v1.0 | v2.0 目标 | 提升 |
|------|------|----------|------|
| **启动时间** | ~3s | <1s | 3x |
| **首响延迟** | ~2s | <1s | 2x |
| **内存占用** | ~200MB | <100MB | 2x |
| **代码行数** | 50,792 | <5,000 | 10x |

### 6.2 优化策略

1. **懒加载**
   - 技能按需加载
   - 插件按需加载
   - 工具按需注册

2. **缓存**
   - Bootstrap 文件缓存
   - 技能解析缓存
   - LLM 响应缓存

3. **异步优化**
   - 并发工具执行
   - 异步文件 I/O
   - 流式 LLM 调用

4. **代码精简**
   - 移除未使用功能
   - 简化抽象层
   - 统一接口

---

## 七、兼容性

### 7.1 向后兼容

**配置兼容**：
```yaml
# v1.0 配置
llm:
  model: "claude-opus-4-5"
  api_key: "sk-..."

# v2.0 配置（兼容）
provider:
  name: "anthropic"
  model: "claude-opus-4-5"
  api_key: "sk-..."
```

**API 兼容**：
```python
# v1.0 API
from fastreact import FastReAct
agent = FastReAct(config)
result = await agent.run(query)

# v2.0 API（兼容）
from fastreact import ReActEngine
engine = ReActEngine(config)
result = await engine.run(query)
```

### 7.2 迁移工具

```bash
# 自动迁移工具
fastreact-migrate --from v1.0 --to v2.0

# 功能：
# 1. 配置文件转换
# 2. Prompt 迁移到文件
# 3. 自定义工具迁移
# 4. 插件生成
```

---

## 八、风险评估

### 8.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **功能缺失** | 高 | 插件系统覆盖 |
| **性能下降** | 中 | 性能测试、优化 |
| **兼容性问题** | 中 | 迁移工具、测试 |
| **稳定性问题** | 高 | 全面测试、灰度发布 |

### 8.2 项目风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **时间不足** | 中 | 分阶段发布 |
| **资源不足** | 低 | 社区贡献 |
| **用户流失** | 低 | 向后兼容 |
| **社区不满** | 中 | 早期沟通、Beta 测试 |

---

## 九、成功指标

### 9.1 技术指标

- ✅ 代码行数 < 5,000
- ✅ 启动时间 < 1s
- ✅ 首响延迟 < 1s
- ✅ 内存占用 < 100MB
- ✅ 测试覆盖率 > 80%

### 9.2 用户指标

- ✅ 迁移成功率 > 90%
- ✅ 用户满意度 > 4.0/5.0
- ✅ 活跃用户增长 > 20%
- ✅ 问题报告减少 > 50%

### 9.3 社区指标

- ✅ 贡献者增长 > 30%
- ✅ 技能数量 > 20
- ✅ 插件数量 > 10
- ✅ 文档完整度 > 90%

---

## 十、总结

### 10.1 核心价值

**FastReAct v2.0 = 极简核心 + 文件驱动 + 企业插件**

1. **极简核心**：2000 行实现完整 ReAct
2. **文件驱动**：用户可通过 Markdown 定制
3. **插件系统**：企业特性按需添加
4. **生产就绪**：可观测、可靠、可扩展

### 10.2 与竞品对比

| 特性 | nanobot | Claude Code | Moltbot | FastReAct v1 | FastReAct v2 |
|------|---------|-------------|---------|--------------|---------------|
| **代码行数** | 7,095 | 未知 | 未知 | 50,792 | **<5,000** |
| **企业特性** | ❌ | ✅ | ✅ | ✅ | **✅** |
| **文件驱动** | ✅ | ❌ | ❌ | ❌ | **✅** |
| **插件系统** | ❌ | ❌ | ❌ | ❌ | **✅** |
| **可定制** | ✅ | ❌ | ❌ | ⚠️ | **✅** |
| **多模式** | ❌ | ❌ | ❌ | ✅ | **❌** |

### 10.3 最终建议

**立即开始**：
1. 创建 `v2` 分支
2. 开始核心重构
3. 保持 v1 维护
4. 社区 Preview 测试

**6 周发布计划**：
- Week 1-2: 核心重构
- Week 3: 文件驱动
- Week 4-5: 插件系统
- Week 6: 测试和发布

**成功关键**：
- ✅ 极简核心
- ✅ 文件驱动
- ✅ 插件系统
- ✅ 向后兼容
- ✅ 社区参与

---

**让我们一起打造 FastReAct v2.0！** 🚀
