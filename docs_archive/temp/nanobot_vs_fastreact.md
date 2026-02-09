# nanobot vs FastReAct 深度对比分析

## 代码规模对比

| 项目 | 总行数 | 最大文件 | 核心文件数 | Python 文件数 |
|------|--------|----------|------------|--------------|
| **nanobot** | 7,095 | 851 (cli/commands.py) | ~20 | 50 |
| **FastReAct** | 50,792 | 3,043 (core/engine.py) | ~40 | 100+ |

**规模差异**: FastReAct 是 nanobot 的 **7.2倍**（代码行数）

---

## 架构设计对比

### nanobot: 极简主义

```
nanobot/
├── agent/          # 核心代理逻辑 (377行 loop.py)
│   ├── loop.py     # 主处理循环
│   ├── context.py  # Prompt 构建
│   ├── memory.py   # 记忆系统
│   ├── skills.py   # 技能加载
│   └── tools/      # 工具实现
├── providers/      # LLM 提供商抽象
├── channels/       # 聊天渠道集成
├── bus/            # 消息总线
└── config/         # 配置管理
```

**设计哲学**:
- **单一职责**: 每个模块只做一件事
- **依赖注入**: 通过构造函数传递依赖
- **文件驱动**: 配置、技能、记忆都通过文件系统
- **渐进增强**: 技能按需加载

### FastReAct: 企业级架构

```
FastReAct/
├── core/           # 核心引擎 (3043行 engine.py)
│   ├── engine.py   # ReAct 执行引擎
│   ├── pumps.py    # IEL 数据流
│   └── streaming.py # 流式处理
├── graph/          # GraphAgent (2500+行)
│   ├── runtime.py  # DAG 执行
│   ├── replanner.py # 动态重规划
│   ├── checkpoint.py # 检查点机制
│   └── history.py  # 历史管理
├── cli/            # 命令行界面 (2964行 unified_repl.py)
│   ├── unified_repl.py # 统一 REPL
│   └── repl.py     # 交互式 shell
├── memory/         # 记忆系统 (2000+行)
│   ├── embeddings.py # 向量嵌入
│   └── sqlite_vec.py  # 向量数据库
├── tools/          # 工具系统 (4000+行)
│   ├── mcp_client_manager.py # MCP 客户端
│   ├── deep_research.py     # 深度研究
│   └── fn_registry.py       # 函数注册表
├── llm/            # LLM 抽象层
├── channels/       # 聊天渠道 (2000+行)
└── gateway/        # API 网关 (665行)
```

**设计哲学**:
- **多模式支持**: ReAct + GraphAgent + IEL
- **企业级功能**: 检查点、重规划、向量存储
- **抽象层丰富**: LLMDriver、EventManager、ContextMonitor
- **可观测性**: 详细的日志、指标、事件系统

---

## 核心差异分析

### 1. Prompt 构建

**nanobot** (context.py, 235行):
```python
def build_system_prompt(self) -> str:
    parts = []

    # 1. 核心身份
    parts.append(self._get_identity())

    # 2. Bootstrap 文件 (AGENTS.md, SOUL.md, USER.md, TOOLS.md, IDENTITY.md)
    bootstrap = self._load_bootstrap_files()
    if bootstrap:
        parts.append(bootstrap)

    # 3. 记忆上下文
    memory = self.memory.get_memory_context()
    if memory:
        parts.append(f"# Memory\n\n{memory}")

    # 4. 技能 - 渐进式加载
    always_skills = self.skills.get_always_skills()
    if always_skills:
        always_content = self.skills.load_skills_for_context(always_skills)
        if always_content:
            parts.append(f"# Active Skills\n\n{always_content}")

    # 5. 可用技能 - 只显示摘要
    skills_summary = self.skills.build_skills_summary()
    if skills_summary:
        parts.append(f"""# Skills

The following skills extend your capabilities. To use a skill, read its SKILL.md file using the read_file tool.
Skills with available="false" need dependencies installed first - you can try installing them with apt/brew.

{skills_summary}""")

    return "\n\n---\n\n".join(parts)
```

**特点**:
- ✅ **文件驱动**: 所有配置通过 Markdown 文件
- ✅ **分层加载**: Active skills 完整加载，Available skills 只显示摘要
- ✅ **可扩展**: 用户可通过添加 SKILL.md 文件扩展能力
- ✅ **简洁**: 235 行实现完整的上下文构建

**FastReAct** (engine.py, prompt_builder.py, ~500行):
```python
def _build_system_prompt(self, tools: List[Tool], config: Dict) -> str:
    # 1. 基础身份
    parts = [self._get_base_identity()]

    # 2. 工具描述
    if tools:
        tool_descriptions = self._build_tool_descriptions(tools)
        parts.append(f"## Available Tools\n\n{tool_descriptions}")

    # 3. 复杂度评估提示 (如果启用)
    if config.get("complexity_evaluation"):
        parts.append(self._get_complexity_guidance())

    # 4. 输出格式要求
    parts.append(self._get_output_format_requirements())

    # 5. 约束和规则
    if config.get("constraints"):
        parts.append(f"## Constraints\n\n{config['constraints']}")

    # 6. 上下文窗口信息
    if config.get("context_window"):
        parts.append(f"## Context Window\n\n{config['context_window']} tokens")

    return "\n\n".join(parts)
```

**特点**:
- ⚠️ **硬编码**: 大部分逻辑在代码中
- ⚠️ **复杂**: 500+ 行实现，包含多种模式支持
- ✅ **灵活**: 支持动态配置
- ❌ **不易扩展**: 添加新功能需要修改代码

### 2. 主处理循环

**nanobot** (loop.py, 377行):
```python
async def _process_message(self, msg: InboundMessage) -> OutboundMessage:
    # 1. 获取/创建会话
    session = self.sessions.get_or_create(msg.session_key)

    # 2. 构建上下文
    messages = self.context.build_messages(
        history=session.get_history(),
        current_message=msg.content,
        media=msg.media,
        channel=msg.channel,
        chat_id=msg.chat_id,
    )

    # 3. Agent 循环
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
                result = await self.tools.execute(tool_call.name, tool_call.arguments)
                messages = self.context.add_tool_result(messages, tool_call.id, tool_call.name, result)

            # 添加 assistant 消息
            messages = self.context.add_assistant_message(
                messages,
                content=response.content,
                tool_calls=[tc.to_dict() for tc in response.tool_calls],
                reasoning_content=response.reasoning_content
            )
        else:
            final_content = response.content
            break

    # 4. 保存会话并返回
    session.save()
    return OutboundMessage(...)
```

**特点**:
- ✅ **极简**: 50 行核心逻辑
- ✅ **清晰**: 单一循环，易于理解
- ✅ **可靠**: 最大迭代次数保护
- ❌ **功能单一**: 只支持 ReAct 模式

**FastReAct** (engine.py, 3043行):
```python
async def run_async(
    self,
    query: str,
    session_context: Dict[str, Any],
    stream_callback: Optional[Callable] = None,
    step_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    # 1. 复杂度评估 (可选)
    if self.config.get("complexity_evaluation"):
        complexity = await self._evaluate_complexity(query)
        # 根据复杂度选择模式...

    # 2. ReAct 循环
    for iteration in range(self.max_iterations):
        # Phase 1: 思考
        thought = await self._generate_thought(query, context)

        # Phase 2: 行动计划
        action_plan = await self._plan_actions(thought, tools)

        # Phase 3: 工具执行
        results = await self._execute_tools(action_plan)

        # Phase 4: 观察整合
        observations = self._integrate_observations(results)

        # Phase 5: 后工具检查 (Double Check Mechanism)
        if self.config.get("reactive_loop", {}).get("enabled"):
            await self._check_and_correct(query, observations)

        # Phase 6: 判断是否完成
        if self._should_stop(observations):
            break

    # 3. 流式回调
    if stream_callback:
        await stream_callback(final_response)

    # 4. 事件发送
    await self._emit_event(TaskCompletionEvent(...))

    # 5. 上下文监控
    self.context_monitor.track_token_usage(...)

    # 6. 返回结果
    return {
        "response": final_response,
        "steps": steps,
        "metrics": metrics,
        "trace_id": trace_id,
    }
```

**特点**:
- ✅ **功能丰富**: 思考-计划-执行-观察-检查完整流程
- ✅ **可观测**: 详细的事件、指标、追踪
- ✅ **高级特性**: Double Check 机制、复杂度评估
- ❌ **复杂**: 3000+ 行，难以理解和维护

### 3. 工具实现

**nanobot** (base.py + filesystem.py, ~300行):
```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def description(self) -> str: pass

    @property
    @abstractmethod
    def parameters(self) -> dict: pass

    @abstractmethod
    async def execute(self, **kwargs) -> str: pass

class ReadFileTool(Tool):
    def __init__(self, allowed_dir: Path | None = None):
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file at the given path."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The file path to read"}
            },
            "required": ["path"]
        }

    async def execute(self, path: str, **kwargs) -> str:
        try:
            file_path = _resolve_path(path, self._allowed_dir)
            if not file_path.exists():
                return f"Error: File not found: {path}"
            content = file_path.read_text(encoding="utf-8")
            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"
```

**特点**:
- ✅ **极简**: 基类 103 行，工具 50 行
- ✅ **直接**: 无中间层，直接实现
- ✅ **异步**: 原生 async/await
- ❌ **功能有限**: 无进度回调、无详细验证

**FastReAct** (tool.py + shell_tool.py, ~1500行):
```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def description(self) -> str: pass

    @property
    @abstractmethod
    def parameters(self) -> dict: pass

    @abstractmethod
    async def execute_async(self, **kwargs) -> ToolResult: pass

    # 额外功能
    @abstractmethod
    def validate_params(self, params: dict) -> List[str]: pass

    @property
    def schema(self) -> dict: ...

class StatefulShellTool(Tool):
    def __init__(self, timeout: int = 30, shell: Optional[str] = None, ...):
        # 单例模式
        if cls._global_shell is None:
            cls._global_shell = self
        # 复杂初始化...

    async def execute_async(
        self,
        command: str,
        timeout: Optional[int] = None,
        new_session: bool = False,
    ) -> ToolResult:
        # 1. 启动持久化 Shell 进程
        self._start_shell()

        # 2. 写入命令到 stdin
        self._process.stdin.write(cmd_with_newline.encode('utf-8'))

        # 3. 读取输出（带超时和输出队列）
        output_lines = []
        start_time = time.time()
        last_output_time = start_time

        while time.time() - start_time < timeout:
            if time.time() - last_output_time > output_timeout:
                break
            # 读取逻辑...

        # 4. 检测 cd 命令并更新 cwd
        if command.strip().startswith("cd "):
            new_cwd = self._get_actual_cwd()
            if new_cwd != old_cwd:
                self._current_cwd = new_cwd
                # 触发回调（通知 RepoMap 更新）
                if self._on_cwd_change:
                    self._on_cwd_change(new_cwd)

        # 5. 添加状态信息
        return f"""[DIR] {cwd_display}
$ {command}

{output}
"""
```

**特点**:
- ✅ **功能丰富**: 持久化会话、CWD 追踪、回调机制
- ✅ **健壮**: 超时控制、输出截断、错误处理
- ✅ **可观测**: 详细的执行状态
- ❌ **复杂**: 1500 行实现一个 shell 工具

---

## 为什么 FastReAct 这么大？

### 1. 多模式支持

| 模式 | 代码量 | 功能 |
|------|--------|------|
| ReAct | ~3000行 | 思考-行动-观察循环 |
| GraphAgent | ~2500行 | DAG 执行、重规划 |
| IEL | ~2000行 | 非阻塞 I/O 数据流 |

**nanobot 只有 ReAct 模式**

### 2. 企业级功能

| 功能 | 代码量 | nanobot 是否有 |
|------|--------|---------------|
| 检查点/恢复 | ~600行 | ❌ |
| 向量存储/检索 | ~2000行 | ❌ (只有文件记忆) |
| 事件系统 | ~500行 | ❌ |
| 复杂度评估 | ~400行 | ❌ |
| 流式处理 | ~800行 | ✅ (但更简单) |
| 多 LLM Provider | ~1000行 | ✅ (但更简单) |
| MCP 客户端 | ~1100行 | ❌ |
| 多渠道支持 | ~2000行 | ✅ |

### 3. 抽象层

| 抽象层 | 代码量 | 作用 |
|--------|--------|------|
| LLMDriver | ~600行 | 统一 LLM 接口 |
| EventManager | ~300行 | 事件系统 |
| ContextMonitor | ~400行 | Token 监控 |
| ToolResult | ~200行 | 统一结果格式 |
| SessionManager | ~400行 | 会话管理 |

**nanobot 的抽象层更薄**，直接使用具体实现

### 4. 文档和注释

FastReAct 包含大量:
- 详细的 docstring
- 类型注解
- 示例代码
- 设计文档

nanobot 的代码更紧凑，注释较少

---

## 哪个更先进？

### nanobot 的优势

1. **极简主义**
   - 代码少 = 易于理解、修改、扩展
   - 快速迭代

2. **文件驱动**
   - 用户可通过 Markdown 文件定制行为
   - 无需修改代码

3. **渐进增强**
   - 技能按需加载
   - 避免上下文膨胀

4. **专注核心**
   - 只实现必要功能
   - 避免 "过度工程"

5. **适合个人使用**
   - 轻量级部署
   - 易于定制

### FastReAct 的优势

1. **企业级功能**
   - 检查点/恢复
   - 向量存储
   - 事件系统

2. **多模式支持**
   - ReAct (推理)
   - GraphAgent (规划)
   - IEL (并发)

3. **可观测性**
   - 详细日志
   - 指标收集
   - 事件追踪

4. **生产就绪**
   - 错误处理
   - 超时控制
   - 资源管理

5. **适合团队协作**
   - 标准化接口
   - 文档完善
   - 可扩展架构

---

## 学到了什么？

### 1. 简化 FastReAct 的可能方向

#### 选项 A: 创建 "Lite" 版本
```
FastReAct-Lite/
├── core/
│   ├── engine.py (简化版, ~500行)
│   └── context.py (~200行)
├── tools/ (只保留核心工具, ~1000行)
└── cli/ (简化 REPL, ~500行)
```

**总代码量**: ~2500 行（nanobot 的 1/3）

#### 选项 B: 抽取核心模块
保留核心功能，将高级功能作为可选插件:
- 基础 ReAct 引擎 (必需)
- GraphAgent (可选插件)
- IEL (可选插件)
- 向量存储 (可选插件)

#### 选项 C: 采用 nanobot 的文件驱动模式
将 Prompt、配置、技能都改为文件驱动:
```
~/.fastreact/
├── AGENTS.md       # Agent 角色定义
├── TOOLS.md        # 工具使用指南
├── MEMORY.md       # 长期记忆
├── skills/         # 技能目录
│   └── weather/SKILL.md
└── config.yaml     # 配置文件
```

### 2. 值得借鉴的设计

#### 技能系统 (nanobot)
```yaml
---
name: weather
description: Get weather information
dependencies: ["curl"]
always_load: false
---

# Weather Skill

Use the following command to get weather:
curl "wttr.in/{location}?format=3"
```

**优势**:
- 用户可自定义技能
- 依赖检查
- 按需加载

#### 单例 Shell (nanobot)
```python
class StatefulShellTool(Tool):
    _global_shell = None

    def __new__(cls, *args, **kwargs):
        if cls._global_shell is None:
            cls._global_shell = super().__new__(cls)
        return cls._global_shell
```

**优势**:
- 全局唯一 Shell 会话
- 状态保持

#### Bootstrap 文件 (nanobot)
```
~/.nanobot/
├── AGENTS.md   # 定义 Agent 行为
├── SOUL.md     # 个性特征
├── USER.md     # 用户偏好
└── TOOLS.md    # 工具使用指南
```

**优势**:
- 用户可定制
- 版本控制友好

### 3. FastReAct 应该保留的

1. **多模式支持**
   - GraphAgent 的规划能力
   - IEL 的并发处理

2. **可观测性**
   - 事件系统
   - 指标收集

3. **类型安全**
   - 完整的类型注解
   - Pydantic 验证

4. **错误处理**
   - 详细的错误信息
   - 优雅降级

---

## 结论

### nanobot: 极简主义的胜利

**适合场景**:
- 个人助手
- 快速原型
- 学习 Agent 开发
- 轻量级部署

**代码哲学**: "Less is More"

### FastReAct: 企业级的权衡

**适合场景**:
- 生产环境
- 团队协作
- 复杂任务
- 需要可观测性

**代码哲学**: "Correctness over Simplicity"

### 最终建议

**对于 FastReAct**:
1. **创建 Lite 版本** - 专注核心功能，代码量 <5000 行
2. **采用文件驱动** - 将配置、Prompt、技能改为文件
3. **插件化架构** - 高级功能作为可选插件
4. **学习极简主义** - nanobot 证明 7000 行足够实现完整功能

**对于学习**:
- nanobot 是学习 Agent 开发的最佳范例
- FastReAct 是学习企业级架构的最佳范例
- 两者结合 = 理解 "何时简单，何时复杂"

---

**统计数据**:
- nanobot: 7,095 行 (1 个作者，6 个月)
- FastReAct: 50,792 行 (1 个作者，3 个月)

**教训**: 代码量 ≠ 功能量，有时反而相反
