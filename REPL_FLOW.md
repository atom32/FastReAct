# FastReAct REPL 详细流程说明

## 日期: 2025-02-06
**版本**: v1.1.0 (Sprint 3完成后)

---

## 1. 总体架构

```
用户输入 Query
       ↓
┌─────────────────────────────────────┐
│   ComplexityEvaluator (复杂度评估)   │
│   - 分析步骤数量                     │
│   - 分析依赖关系                     │
│   - 分析工具调用数量                 │
│   - 分析不确定性                     │
└──────────────┬──────────────────────┘
               ↓
         计算复杂度分数 (0.0 - 1.0)
               ↓
    ┌──────────┴──────────┐
    │                     │
 0.0-0.33              0.34-0.66      0.67-1.0
    │                     │             │
    ↓                     ↓             ↓
REACT模式           GraphAgent模式     IEL模式
(简单快速)          (计划驱动)        (安全执行)
```

---

## 2. 模式详解

### 2.1 REACT 模式 (复杂度 0.0 - 0.33)

**特点**: 无计划，直接执行，适合简单任务

**流程**:
```
Query → REACT Agent
  ↓
Loop:
  1. LLM 推理 (Think)
  2. 选择工具 (Action)
  3. 执行工具 (Observe)
  4. 更新上下文
  5. 重复直到完成
```

**适用场景**:
- 简单问答 ("hello?")
- 单一工具调用
- 快速查询

**文件位置**: `src/fastreact/cli/unified_repl.py:_run_react()`

---

### 2.2 GraphAgent 模式 (复杂度 0.34 - 0.66)

**特点**: 先计划再执行，适合中等复杂度任务

**核心组件**:
- **Planning**: LLM生成执行计划
- **Graph**: DAG图表示依赖关系
- **Runtime**: 按层级执行节点

**有两种执行方式**:

#### A. 阻塞模式 (默认，或 `FASTREACT_STEPPABLE=0`)

```
Query → GraphAgent
  ↓
1. 生成计划
2. 显示计划
3. 用户确认
4. [BLACK BOX] 执行所有步骤
5. 显示结果
```

**文件位置**: `src/fastreact/cli/unified_repl.py:_run_graph_agent()`

#### B. 非阻塞模式 (Sprint 3, `FASTREACT_STEPPABLE=1`)

```
Query → GraphAgent (Non-blocking)
  ↓
1. 生成计划
2. 显示计划
3. 用户确认
  ↓
[双轨并发执行]
  ├─ Agent轨道: 执行 → yield事件 → 显示 → 检查队列 → 继续
  └─ 用户轨道:   异步输入 → 放入队列
  ↓
用户可随时输入 "stop" 中断
```

**文件位置**: `src/fastreact/cli/unified_repl.py:_run_graph_agent_non_blocking()`

---

### 2.3 IEL 模式 (复杂度 0.67 - 1.0)

**状态**: ⚠️ **未实现，当前为占位符**

**代码行为**:
```python
async def _run_iel(self, query: str) -> bool:
    """IEL 模式执行"""
    self.print_output("[yellow]IEL 模式正在开发中，暂时使用 GraphAgent 模式[/yellow]")
    # 回退到 GraphAgent
    return await self._run_graph_agent(query)
```

**设计理念（未实现）**:
- 每步执行前都需要用户确认 (Y/n)
- 适合关键操作（文件删除、系统修改）
- 需要人工监督的场景

**为什么不实现？**

"每步确认"式 IEL 有以下问题：
1. 用户体验极差（5步任务需要5次确认）
2. 违背了"自动化工具"的初衷
3. 如果都需要确认，不如手动执行

**更好的方案**: 使用 **GraphAgent 非阻塞模式**（见下一节）
- 默认自动执行（高效）
- 实时显示进度（透明）
- 发现问题可随时中断（可控）

**文件位置**: `src/fastreact/cli/unified_repl.py:_run_iel()`

---

## 3. GraphAgent 非阻塞模式 = 渐进式 IEL（Sprint 3核心）

**核心理念**: 默认自动执行，用户可随时干预

### 3.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    UnifiedAgentREPL                         │
│                                                             │
│  Query: "扫描.py文件，统计行数，找出asyncio导入，生成报告"    │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 1. ComplexityEvaluator.evaluate()                  │    │
│  │    → Score: 0.65 → GraphAgent mode                 │    │
│  └────────────────────────────────────────────────────┘    │
│                  ↓                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 2. Check FASTREACT_STEPPABLE env var               │    │
│  │    → Enabled → Non-blocking mode                   │    │
│  └────────────────────────────────────────────────────┘    │
│                  ↓                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 3. GraphAgent._generate_plan(query)                │    │
│  │    → 5 steps: ls_repo, bash, bash, bash, write     │    │
│  └────────────────────────────────────────────────────┘    │
│                  ↓                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 4. Display plan + User confirmation                │    │
│  │    User: Y                                         │    │
│  └────────────────────────────────────────────────────┘    │
│                  ↓                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 5. Convert plan → ToolGraph                         │    │
│  │    → 5 nodes, 4 levels (DAG)                       │    │
│  └────────────────────────────────────────────────────┘    │
│                  ↓                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │         DUAL-TRACK EXECUTION (并发)                 │    │
│  │                                                     │    │
│  │  ┌─────────────────┐    ┌──────────────────┐       │    │
│  │  │ Agent Task      │    │ User Input Task  │       │    │
│  │  │ (消费者生成器)   │    │ (生产者)         │       │    │
│  │  │                 │    │                  │       │    │
│  │  │ async for event │    │ while is_running:│       │    │
│  │  │   in runtime.   │    │   text = await   │       │    │
│  │  │   execute_      │    │   session.       │       │    │
│  │  │   steppable():  │    │   prompt_async() │       │    │
│  │  │                 │    │   await queue.   │       │    │
│  │  │   render(event) │    │   put(text)      │       │    │
│  │  │                 │    │                  │       │    │
│  │  └─────────────────┘    └──────────────────┘       │    │
│  │         ↓                        ↓                  │    │
│  │    StepEvent            User commands             │    │
│  │    (START/COMPLETE)       ("stop", "help")         │    │
│  │         ↓                        ↓                  │    │
│  │    Display to           Intervention Queue         │    │
│  │    screen                (asyncio.Queue)           │    │
│  │                            ↓                        │    │
│  │                    Agent checks queue              │    │
│  │                    between levels                  │    │
│  └────────────────────────────────────────────────────┘    │
│                  ↓                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 6. Execution complete or stopped                    │    │
│  │    → Show statistics                               │    │
│  │    → Show final result                             │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 详细步骤

**步骤 1: 复杂度评估**
```python
evaluation = await evaluator.evaluate(query)
# {
#   "score": 0.65,
#   "reasoning": "...",
#   "suggested_mode": "graph_agent"
# }
```

**步骤 2: 选择执行模式**
```python
if os.environ.get("FASTREACT_STEPPABLE"):
    return await self._run_graph_agent_non_blocking(query)
else:
    return await self._run_graph_agent(query)
```

**步骤 3: 生成执行计划**
```python
agent = await self._get_or_create_graph_agent()
plan = await agent._generate_plan(query)
# [
#   {"id": "step_1", "tool": "ls_repo", "description": "...", "dependencies": []},
#   {"id": "step_2", "tool": "bash", "description": "...", "dependencies": ["step_1"]},
#   ...
# ]
```

**步骤 4: 用户确认**
```python
if not self._confirm_plan():
    return True  # Cancelled
```

**步骤 5: 转换为执行图**
```python
graph = agent._plan_to_graph(plan)
# ToolGraph with 5 nodes in 4 levels (DAG structure)
```

**步骤 6: 双轨执行**
```python
# Track 1: Agent execution (producer of events)
async def agent_task():
    async for event in runtime.execute_steppable(graph, intervention_queue):
        self._render_step_event(event)  # Display progress

# Track 2: User input (consumer of commands)
async def user_input_task():
    while is_running:
        user_input = await prompt_session.prompt_async("")
        await intervention_queue.put(user_input)

# True parallel execution
await asyncio.wait([agent_task(), user_input_task()], return_when=FIRST_COMPLETED)
```

**步骤 7: 事件渲染**
```python
def _render_step_event(event: StepEvent):
    if event.type == "STEP_START":
        print(f"[START] {event.message}")
    elif event.type == "STEP_COMPLETE":
        print(f"[OK] {event.message}")
```

---

## 4. StepEvent 事件系统

### 4.1 事件类型

```python
@dataclass
class StepEvent:
    type: str           # "STEP_START", "STEP_COMPLETE", "INTERVENTION", "ERROR"
    node_id: str        # "step_1", "step_2", ...
    tool_name: str      # "ls_repo", "bash", "write_file", ...
    level: int          # 当前层级 (1, 2, 3, 4)
    total_levels: int   # 总层数
    status: str         # "completed", "failed"
    result: Dict        # 工具执行结果
    message: str        # 人类可读消息
```

### 4.2 事件流示例

```
[START] Executing level 1/4 (1 nodes)
[OK] Node step_1: completed
[START] Executing level 2/4 (1 nodes)
[OK] Node step_2: completed
[START] Executing level 3/4 (2 nodes)
[OK] Node step_3: completed
[OK] Node step_4: completed
[START] Executing level 4/4 (1 nodes)
[OK] Node step_5: completed

[执行统计] 总节点: 5, 完成: 5, 失败: 0, 耗时: 1.54s
```

---

## 5. 执行策略

### 5.1 LEVEL_BASED (默认)

**原理**: 按层级执行，同层节点并行

```
Level 1:  [step_1]
Level 2:        [step_2]
Level 3:             [step_3] [step_4]  ← 并行
Level 4:                      [step_5]
```

**优点**:
- 最大化并行度
- 清晰的执行顺序
- 易于理解进度

**文件位置**: `src/fastreact/graph/runtime.py:_execute_level_based_steppable()`

### 5.2 TOPOLOGICAL

**原理**: 按拓扑序执行，严格按依赖

**适用场景**: 需要严格顺序控制

### 5.3 MAX_PARALLEL

**原理**: 尽可能并行执行所有可用节点

**适用场景**: 任务之间无依赖关系

---

## 6. 干预机制

### 6.1 干预队列

```python
intervention_queue = asyncio.Queue()
```

**工作原理**:
1. 用户输入 "stop"
2. 放入队列: `await intervention_queue.put("stop")`
3. Agent在层级之间检查队列
4. 如果检测到 "stop"，停止执行

### 6.2 干预时机

```
Level 1 开始
  ↓
检查队列 (empty)
  ↓
执行 Level 1 节点
  ↓
Level 1 完成
  ↓
检查队列 (empty)
  ↓
Level 2 开始
  ↓
检查队列 (has "stop") ← 在这里检测到用户输入
  ↓
停止执行
```

**注意**: 当前实现只在层级之间检查，不在节点执行过程中检查。这意味着：
- 如果用户在Level 3执行期间输入"stop"，会在Level 3完成后停止
- Level 4不会开始

### 6.3 支持的命令

- `stop` - 停止执行
- 未来可扩展: `pause`, `modify`, `insert_step`

---

## 7. MCP 工具加载 (Sprint 3.5)

### 7.1 异步加载

```python
async def _get_or_create_graph_agent(self):
    react_agent = self._get_or_create_react_agent()

    # 强制加载MCP工具
    if hasattr(react_agent, '_mcp_enabled') and react_agent._mcp_enabled:
        if not react_agent._mcp_loaded:
            await react_agent._load_mcp_tools()

    self.state.graph_agent = GraphAgent(
        tools=react_agent.tools,  # 现在包含 MCP 工具
        ...
    )
```

### 7.2 工具列表

**内置工具** (13个):
- `ls_repo`, `read_file`, `write_file`, `bash`, `grep_file`, ...

**MCP工具** (28个):
- GitHub: 26个工具 (issues, PRs, repo management)
- Apollo: 2个工具 (moonphase, astronaut)

---

## 8. 终端兼容性

### 8.1 ANSI 检测

```python
def _supports_ansi():
    # Windows Terminal
    if os.environ.get("WT_SESSION"): return True
    # VS Code
    if os.environ.get("TERM_PROGRAM"): return True
    # PowerShell 7+
    if "pwsh" in os.environ.get("PSModulePath", ""): return True
    # Windows 10 build 14931+
    if sys.platform == "win32":
        if int(platform.version().split(".")[-1]) >= 14931:
            return True
    return False
```

### 8.2 文本模式

**问题**: PowerShell 5.x 不支持ANSI颜色码

**解决**: 强制文本模式
```powershell
$env:FASTREACT_TEXT_MODE="1"
python -m fastreact.cli.unified_repl
```

**效果**:
```
# 有颜色 (Rich)
✔ Node step_1: completed

# 无颜色 (文本模式)
[OK] Node step_1: completed
```

---

## 9. 使用示例

### 9.1 简单任务 (REACT模式)

```
FastReAct[AUTO] Q0 >> hello?
[INFO] Complexity score: 0.05 (SIMPLE)
→ REACT mode

[REACT] Thinking...
[REACT] Hello! How can I help you today?
```

### 9.2 中等复杂度 (GraphAgent模式)

```
FastReAct[AUTO] Q0 >> 写fib_demo.py并运行它
[INFO] Complexity score: 0.45 (MEDIUM)
→ GraphAgent mode

[PLAN]
step_1: write_file - Create fib_demo.py
step_2: bash - Run fib_demo.py

Confirm? [Y/n]: Y

[START] Executing level 1/2 (1 nodes)
[OK] Node step_1: completed
[START] Executing level 2/2 (1 nodes)
[OK] Node step_2: completed

[Result]
0, 1, 1, 2, 3, 5, 8, 13, 21, 34
```

### 9.3 复杂任务 (非阻塞模式)

```
FastReAct[AUTO] Q0 >> 扫描.py文件，统计行数，找出asyncio导入，生成报告
[INFO] Complexity score: 0.65 (MEDIUM)
→ GraphAgent mode (Non-blocking IEL)

[PLAN]
step_1: ls_repo - List all files
step_2: bash - Filter .py files
step_3: bash - Count lines
step_4: bash - Find asyncio imports
step_5: write_file - Generate report

Confirm? [Y/n]: Y

[INFO] 执行中... (Type 'stop' to interrupt)

[START] Executing level 1/4 (1 nodes)
[OK] Node step_1: completed
[START] Executing level 2/4 (1 nodes)
[OK] Node step_2: completed
[START] Executing level 3/4 (2 nodes)
[OK] Node step_3: completed
[OK] Node step_4: completed
[START] Executing level 4/4 (1 nodes)
[OK] Node step_5: completed

[执行统计] 总节点: 5, 完成: 5, 失败: 0, 耗时: 1.54s
```

---

## 10. 文件索引

| 文件 | 功能 |
|------|------|
| `src/fastreact/cli/unified_repl.py` | REPL主入口，模式路由 |
| `src/fastreact/graph/runtime.py` | ToolRuntime, execute_steppable() |
| `src/fastreact/graph/node.py` | ToolNode, 节点执行 |
| `src/fastreact/agents/graph_agent.py` | GraphAgent, 计划生成 |
| `src/fastreact/context/monitor.py` | ContextMonitor, token跟踪 |
| `src/fastreact/core/complexity.py` | ComplexityEvaluator, 复杂度评估 |

---

## 11. 总结

### 实际实现的执行模式

基于代码实际分析，FastReAct 当前真正实现的模式有：

| 模式 | 复杂度 | 状态 | 特点 |
|------|--------|------|------|
| **REACT** | 0.0-0.33 | ✅ 完整实现 | 无计划，快速执行 |
| **GraphAgent (阻塞)** | 0.34-0.66 | ✅ 完整实现 | 计划驱动，一次性执行 |
| **GraphAgent (非阻塞)** | 0.34-0.66 + 环境变量 | ✅ Sprint 3实现 | **渐进式IEL**，可随时中断 |
| **IEL (保守式)** | 0.67-1.0 | ⚠️ 占位符 | 回退到GraphAgent |

### IEL 的实际实现

**重要理解**: FastReAct 中的 "IEL" 实际上有两种含义：

1. **保守式 IEL**（代码中占位，未实现）
   - 每步都询问用户确认
   - 体验差，不实用
   - **正确决策：不实现**

2. **渐进式 IEL**（Sprint 3实现，`FASTREACT_STEPPABLE=1`）
   - 默认自动执行
   - 实时显示进度
   - 用户可随时中断
   - **这才是理想的 IEL！**

### FastReAct REPL的核心价值

1. **智能路由**: 根据任务复杂度自动选择最合适的执行模式
2. **透明性**: 用户可以看到每一步的执行过程（StepEvent）
3. **可控性**: 用户可以随时中断执行（干预队列）
4. **灵活性**: 支持阻塞/非阻塞、彩色/文本多种模式（环境变量控制）
5. **安全性**: 复杂任务需要用户确认计划后才执行

### 从"自动化脚本"到"交互式AI助手"的转变

```
BEFORE (Sprint 3前):
User → Plan → Confirm → [BLACK BOX] → Result

AFTER (Sprint 3后 - 渐进式IEL):
User → Plan → Confirm → [Step 1] → [Step 2] → [Step 3] → ...
                      ↑           ↑          ↑
                   实时进度显示，用户可随时中断
```

### 关键技术点总结

| 技术 | 作用 | 文件位置 |
|------|------|----------|
| **异步生成器** | 事件流（StepEvent） | `runtime.py:execute_steppable()` |
| **asyncio.Queue** | 干预队列 | `runtime.py:intervention_queue` |
| **asyncio.wait(FIRST_COMPLETED)** | 双轨并发 | `unified_repl.py:1100` |
| **prompt_toolkit** | 非阻塞输入 | `unified_repl.py:1050` |
| **patch_stdout** | 防止输出打断输入 | `unified_repl.py:1055` |
| **层级执行策略** | DAG并行优化 | `runtime.py:_execute_level_based_steppable()` |

详细技术解析: [IEL_TECHNICAL_DEEP_DIVE.md](IEL_TECHNICAL_DEEP_DIVE.md)

---

*文档版本: 1.1*
*最后更新: 2025-02-06*
*状态: Sprint 3 Complete*
