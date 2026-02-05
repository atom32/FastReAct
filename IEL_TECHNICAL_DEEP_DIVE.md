# FastReAct IEL 技术深度解析

## 日期: 2025-02-06
**版本**: v1.1.0 (Sprint 3完成后)

---

## 1. 实际的执行模式（基于代码）

### 1.1 模式路由逻辑

**文件**: `src/fastreact/cli/unified_repl.py:1208-1223`

```python
# 自动模式选择
if self.state.execution_mode == "auto":
    evaluator = self._get_or_create_evaluator()
    evaluation = await evaluator.evaluate(query)
    mode = evaluation["suggested_mode"]  # "react" | "graph_agent" | "iel"
else:
    mode = self.state.execution_mode

# 执行路由
if mode == "react":
    return await self._run_react(query)
elif mode == "graph_agent":
    # Sprint 3: 检查是否启用非阻塞模式
    if PROMPT_TOOLKIT_AVAILABLE and os.environ.get("FASTREACT_STEPPABLE", "").lower() in ["1", "true", "yes"]:
        return await self._run_graph_agent_non_blocking(query)  # 渐进式IEL
    else:
        return await self._run_graph_agent(query)  # 阻塞模式
elif mode == "iel":
    return await self._run_iel(query)  # 占位符，实际回退到阻塞模式
```

### 1.2 三种模式的实际实现

| 模式名 | 复杂度范围 | 实际调用 | 状态 |
|--------|-----------|---------|------|
| **REACT** | 0.0 - 0.33 | `_run_react()` | ✅ 完整实现 |
| **GraphAgent (阻塞)** | 0.34 - 0.66 | `_run_graph_agent()` | ✅ 完整实现 |
| **GraphAgent (非阻塞)** | 0.34 - 0.66 + 环境变量 | `_run_graph_agent_non_blocking()` | ✅ Sprint 3实现 |
| **IEL** | 0.67 - 1.0 | `_run_iel()` → `_run_graph_agent()` | ⚠️ 占位符，回退到阻塞模式 |

---

## 2. 非阻塞IEL：渐进式交互执行

### 2.1 核心概念

**定义**: 非阻塞IEL（Interactive Execution Loop）是一种"默认自动执行，用户可随时干预"的执行模式。

**关键特性**:
- ✅ 输入框始终可用（非阻塞）
- ✅ 执行过程中实时显示进度（StepEvent）
- ✅ 用户可随时输入 `stop` 中断执行
- ✅ 在层级边界检查用户输入（不是每步）
- ❌ 不需要每步都确认（那不是理想的IEL）

### 2.2 为什么不实现"每步确认"式IEL？

**保守IEL的问题**（每步都问用户）:
```
[Step 1] 执行ls_repo - 列出文件
确认? [Y/n]: Y
[Step 2] 执行bash - 过滤.py文件
确认? [Y/n]: Y
[Step 3] 执行bash - 统计行数
确认? [Y/n]: Y
[Step 4] 执行bash - 查找asyncio导入
确认? [Y/n]: Y
[Step 5] 执行write_file - 生成报告
确认? [Y/n]: Y
```

**问题**:
1. 用户体验极差（5次确认）
2. 违背了"自动化工具"的初衷
3. 如果都需要确认，不如手动执行
4. 对于5步任务尚可忍受，20步任务呢？

**渐进式IEL的优势**（Sprint 3实现）:
```
[START] Executing level 1/4 (1 nodes)
[OK] Node step_1: completed
[START] Executing level 2/4 (1 nodes)
[OK] Node step_2: completed
[START] Executing level 3/4 (2 nodes)
[OK] Node step_3: completed
[OK] Node step_4: completed
[START] Executing level 4/4 (1 nodes)
stop  ← 用户发现有问题，随时中断
[OK] Node step_5: completed  (当前层级执行完)

[执行统计] 总节点: 5, 完成: 5, 失败: 0, 耗时: 1.54s
```

**优势**:
1. 默认自动执行（高效）
2. 实时显示进度（透明）
3. 发现问题可随时中断（可控）
4. 输入框始终可用（不阻塞）

**结论**: 不实现"每步确认"式IEL是正确的产品决策。

---

## 3. 关键技术点详解

### 3.1 异步生成器（Async Generator）

**文件**: `src/fastreact/graph/runtime.py:216-277`

```python
async def execute_steppable(
    self,
    graph: ToolGraph,
    initial_inputs: Optional[Dict[str, Any]] = None,
    intervention_queue: Optional["asyncio.Queue"] = None,
):
    """
    可步进执行 - 支持干预的异步生成器

    Args:
        graph: 工具图（DAG结构）
        initial_inputs: 初始输入
        intervention_queue: 用户干预指令队列

    Yields:
        StepEvent: 每步执行事件
    """
    # 验证图
    is_valid, errors = graph.validate()
    if not is_valid:
        yield StepEvent(type="ERROR", ...)
        return

    # 选择执行策略
    if self.config.strategy == ExecutionStrategy.LEVEL_BASED:
        executor = self._execute_level_based_steppable
    # ... 其他策略

    # 执行并yield事件（关键！）
    async for event in executor(graph, intervention_queue):
        yield event
```

**为什么用异步生成器？**

| 方案 | 优点 | 缺点 |
|------|------|------|
| **回调函数** | 简单 | 回调地狱，代码难读 |
| **协程并发** | 灵活 | 需要手动管理状态 |
| **异步生成器** ✅ | Pythonic，易读，天然支持流式处理 | 需要理解 `yield` |

**对比示例**:

```python
# 方案1: 回调函数（不推荐）
def execute_with_callback(graph, on_step):
    results = []
    for step in execute_steps(graph):
        results.append(step)
        on_step(step)  # 回调
    return results

# 方案2: 异步生成器（推荐）
async def execute_steppable(graph):
    for step in execute_steps(graph):
        yield StepEvent(...)  # 简洁清晰
```

### 3.2 双轨并发架构

**文件**: `src/fastreact/cli/unified_repl.py:1083-1116`

```python
# Track 1: Agent执行任务（消费者生成器）
async def agent_task():
    """Agent轨道：执行并yield事件"""
    async for event in runtime.execute_steppable(graph, intervention_queue):
        if not is_running:
            break  # 用户停止了执行
        self._render_step_event(event)  # 渲染到屏幕

# Track 2: 用户输入任务（生产者指令）
async def user_input_task():
    """用户轨道：异步输入，始终活跃"""
    prompt_session = PromptSession("FastReAct[interrupt] >> ")
    while is_running:
        with patch_stdout():  # 关键！防止日志打断输入
            user_input = await prompt_session.prompt_async("")
        await intervention_queue.put(user_input)  # 放入队列

# 创建任务列表
tasks = [
    asyncio.create_task(agent_task(), name="agent"),
    asyncio.create_task(user_input_task(), name="input"),
]

# 并发执行，等待任意一个完成
done, pending = await asyncio.wait(
    tasks,
    return_when=asyncio.FIRST_COMPLETED
)
```

**为什么用 `asyncio.wait(FIRST_COMPLETED)`？**

**问题**: 如果用 `asyncio.gather()` 会怎样？

```python
# ❌ 错误：使用 gather
await asyncio.gather(agent_task(), user_input_task())
# 问题：两个任务都必须完成才返回，无法实现"用户中断"
```

```python
# ✅ 正确：使用 wait + FIRST_COMPLETED
done, pending = await asyncio.wait(
    tasks,
    return_when=asyncio.FIRST_COMPLETED
)
# 任意一个任务完成就返回：
# - Agent执行完成 → 正常结束
# - 用户输入"stop" → 中断执行
```

**终止流程**:
```
1. 用户输入 "stop"
2. user_input_task 将 "stop" 放入 intervention_queue
3. agent_task 从队列取出 "stop"
4. agent_task 设置 is_running = False
5. agent_task 退出循环
6. agent_task 完成 → FIRST_COMPLETED 触发
7. 取消 user_input_task（如果还在等待输入）
```

### 3.3 干预队列（Intervention Queue）

**文件**: `src/fastreact/graph/runtime.py:289-304`

```python
async def _execute_level_based_steppable(self, graph, intervention_queue):
    levels = self._compute_node_levels(graph)
    max_level = max(levels.values()) if levels else 0

    for level in range(max_level + 1):
        # 关键：每层开始前检查队列
        if intervention_queue and not intervention_queue.empty():
            intervention = await intervention_queue.get()
            yield StepEvent(
                type="INTERVENTION",
                message=f"User intervention: {intervention}"
            )

            # 根据干预决定是否继续
            if intervention.lower() in ["stop", "abort", "exit"]:
                logger.info("[STEPPABLE] Execution stopped by user")
                break  # 停止执行

        # ... 执行当前层级
```

**为什么用 `asyncio.Queue`？**

| 方案 | 优点 | 缺点 |
|------|------|------|
| **共享变量** | 简单 | 需要锁（Lock），容易死锁 |
| **回调函数** | 直接调用 | 用户输入线程如何回调？ |
| **asyncio.Queue** ✅ | 线程安全，异步原生，无需锁 | 需要理解队列概念 |

**队列的数据流**:
```
user_input_task (生产者)
    ↓
    await intervention_queue.put("stop")
    ↓
┌──────────────────────────┐
│  asyncio.Queue           │
│  - 线程安全               │
│  - 异步原生               │
│  - FIFO                   │
└──────────────────────────┘
    ↓
    intervention = await intervention_queue.get()
    ↓
_execute_level_based_steppable (消费者)
```

### 3.4 patch_stdout：防止输出打断输入

**文件**: `src/fastreact/cli/unified_repl.py:1054-1056`

```python
async def user_input_task():
    prompt_session = PromptSession("FastReAct[interrupt] >> ")
    while is_running:
        with patch_stdout():  # 关键！
            user_input = await prompt_session.prompt_async("")
        await intervention_queue.put(user_input)
```

**问题**: 如果不用 `patch_stdout()` 会怎样？

```
FastReAct[interrupt] >> _
[START] Executing level 3/4 (2 nodes)  ← 输出打断输入！
[OK] Node step_3: completed
```

用户的输入被日志打断，体验极差。

**`patch_stdout()` 的原理**:

```
正常情况（无 patch_stdout）:
┌─────────────────────────────────┐
│ [START] Executing level 3...    │  ← 直接输出到终端
│ FastReAct[interrupt] >> inp     │  ← 输入光标被移动
└─────────────────────────────────┘

使用 patch_stdout:
┌─────────────────────────────────┐
│ FastReAct[interrupt] >> inp     │  ← 输入区域受保护
│ [START] Executing level 3...    │  ← 输出到备用缓冲区
└─────────────────────────────────┘
     ↓ 刷新完成后合并显示
```

**原理**: `patch_stdout()` 将标准输出重定向到临时缓冲区，输入完成后一次性刷新，确保输入行不被打断。

### 3.5 StepEvent 数据结构

**文件**: `src/fastreact/graph/runtime.py:23-31`

```python
@dataclass
class StepEvent:
    """
    步进执行事件

    Attributes:
        type: 事件类型 ("STEP_START", "STEP_COMPLETE", "INTERVENTION", "ERROR")
        node_id: 节点ID
        tool_name: 工具名称
        level: 当前层级
        total_levels: 总层级数
        status: 执行状态 ("completed", "failed")
        result: 执行结果字典
        message: 人类可读消息
    """
    type: str
    node_id: str
    tool_name: str
    level: int = 0
    total_levels: int = 0
    status: str = ""
    result: Optional[Dict[str, Any]] = None
    message: str = ""
```

**事件流示例**:

```python
# Level 1 开始
StepEvent(
    type="STEP_START",
    node_id="level_0",
    tool_name="ls_repo",
    level=0,
    total_levels=4,
    message="Executing level 1/4 (1 nodes)"
)

# Level 1 完成
StepEvent(
    type="STEP_COMPLETE",
    node_id="step_1",
    tool_name="ls_repo",
    level=0,
    total_levels=4,
    status="completed",
    result={"files": ["a.py", "b.py"]},
    message="Node step_1: completed"
)

# 用户干预
StepEvent(
    type="INTERVENTION",
    node_id="level_2",
    tool_name="intervention",
    level=2,
    total_levels=4,
    message="User intervention: stop"
)
```

### 3.6 层级执行策略（LEVEL_BASED）

**文件**: `src/fastreact/graph/runtime.py:278-344`

**DAG 层级计算**:

```python
# 示例：5个节点的依赖关系
# step_1 → step_2 → step_5
#         ↘ step_3 ↗
#         ↘ step_4 ↗

# 层级计算结果:
# Level 0: [step_1]     ← 无依赖
# Level 1: [step_2]     ← 依赖 step_1
# Level 2: [step_3, step_4]  ← 依赖 step_2（并行！）
# Level 3: [step_5]     ← 依赖 step_3, step_4
```

**并行执行同一层级**:

```python
# 获取当前层级的所有节点
level_nodes = [
    node for node in graph.nodes.values()
    if levels.get(node.id, 0) == level
]

# 并行执行（关键！）
level_results = await self._execute_parallel(level_nodes, graph)
```

**`_execute_parallel` 的实现**:

```python
async def _execute_parallel(self, nodes: List[ToolNode], graph: ToolGraph):
    """并行执行多个节点"""
    tasks = [node.execute(inputs, context) for node in nodes]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    result_dict = {}
    for node, result in zip(nodes, results):
        if isinstance(result, Exception):
            result_dict[node.id] = NodeResult(
                node_id=node.id,
                status=NodeStatus.FAILED,
                error=str(result)
            )
        else:
            result_dict[node.id] = result

    return result_dict
```

**为什么层级并行很重要？**

```
串行执行（不推荐）:
Level 2 (2 nodes): step_3 (2s) + step_4 (3s) = 5s

并行执行（推荐）:
Level 2 (2 nodes): max(step_3 (2s), step_4 (3s)) = 3s  ← 节省 2s！
```

---

## 4. 环境变量控制

### 4.1 可用的环境变量

**文件**: `src/fastreact/cli/unified_repl.py`

```python
# 启用非阻塞IEL模式
FASTREACT_STEPPABLE=1

# 强制文本模式（避免ANSI乱码）
FASTREACT_TEXT_MODE=1

# 强制执行模式
FASTREACT_MODE=auto|react|graph_agent|iel
```

### 4.2 使用示例

**Windows PowerShell**:
```powershell
# 启用非阻塞模式
$env:FASTREACT_STEPPABLE="1"
python -m fastreact.cli.unified_repl

# 启用文本模式
$env:FASTREACT_TEXT_MODE="1"
python -m fastreact.cli.unified_repl

# 组合使用
$env:FASTREACT_STEPPABLE="1"
$env:FASTREACT_TEXT_MODE="1"
python -m fastreact.cli.unified_repl
```

**Linux/Mac**:
```bash
# 启用非阻塞模式
export FASTREACT_STEPPABLE=1
python -m fastreact.cli.unified_repl

# 启用文本模式
export FASTREACT_TEXT_MODE=1
python -m fastreact.cli.unified_repl

# 组合使用
export FASTREACT_STEPPABLE=1
export FASTREACT_TEXT_MODE=1
python -m fastreact.cli.unified_repl
```

---

## 5. 终端兼容性处理

### 5.1 ANSI 检测

**文件**: `src/fastreact/cli/unified_repl.py:61-85`

```python
def _supports_ansi():
    """检测终端是否支持ANSI颜色码"""
    # Windows Terminal
    if os.environ.get("WT_SESSION"): return True
    # VS Code
    if os.environ.get("TERM_PROGRAM"): return True
    # PowerShell 7+
    if "pwsh" in os.environ.get("PSModulePath", ""): return True
    # Windows 10 build 14931+
    if sys.platform == "win32":
        try:
            import platform
            version = platform.version()
            if int(version.split(".")[-1]) >= 14931:
                return True
        except:
            pass
    return False
```

### 5.2 文本模式回退

**文件**: `src/fastreact/cli/unified_repl.py:571-574`

```python
# 强制文本模式标志（用于不支持ANSI的终端）
self.force_text_mode = os.environ.get("FASTREACT_TEXT_MODE", "").lower() in ("1", "true", "yes")
```

**事件渲染回退**:

```python
def _render_step_event(self, event: StepEvent):
    # 检查是否强制使用文本模式
    if self.force_text_mode or not self.console:
        # 文本模式
        if event.type == "STEP_START":
            print(f"[START] {event.message}")
        elif event.type == "STEP_COMPLETE":
            print(f"[OK] {event.message}")
        return

    # Rich UI 模式
    try:
        if event.type == "STEP_START":
            self.console.print(Text("➤ ", style="bold blue") + Text(event.message))
        # ...
    except Exception:
        # 回退到文本模式
        print(f"[START] {event.message}")
```

---

## 6. MCP 工具异步加载

### 6.1 问题：GraphAgent 缺少 MCP 工具

**原因**:
- REACT Agent 在第一次查询时加载 MCP 工具
- GraphAgent 创建时复用 REACT Agent 的工具列表
- 但如果 REACT Agent 还没加载 MCP 工具，GraphAgent 就没有它们

### 6.2 解决方案：强制加载

**文件**: `src/fastreact/cli/unified_repl.py:1433-1467`

```python
async def _get_or_create_graph_agent(self):
    """获取或创建 GraphAgent（Sprint 3.5: 异步方法）"""
    react_agent = self._get_or_create_react_agent()

    # Sprint 3.5 Hotfix: 强制加载MCP工具
    if hasattr(react_agent, '_mcp_enabled') and react_agent._mcp_enabled:
        if not react_agent._mcp_loaded:
            await react_agent._load_mcp_tools()  # 关键！异步加载

    self.state.graph_agent = GraphAgent(
        tools=react_agent.tools,  # 现在包含 MCP 工具
        llm_driver=self._get_or_create_llm_driver(),
        ...
    )
    return self.state.graph_agent
```

### 6.3 工具数量对比

```
内置工具: 13 个
- ls_repo, read_file, write_file, bash, grep_file, ...

MCP 工具: 28 个
- GitHub: 26 个工具（issues, PRs, repo management）
- Apollo: 2 个工具（moonphase, astronaut）

总计: 41 个工具
```

---

## 7. 执行流程完整示例

### 7.1 用户输入

```
FastReAct[AUTO] Q0 >> 扫描.py文件，统计行数，找出asyncio导入，生成报告
```

### 7.2 复杂度评估

```python
# ComplexityEvaluator.evaluate()
evaluation = {
    "score": 0.65,
    "complexity": "MEDIUM",
    "suggested_mode": "graph_agent",
    "estimated_steps": 5,
    "estimated_tools": 3,
}
```

### 7.3 模式选择

```python
mode = "graph_agent"
# 检查环境变量
FASTREACT_STEPPABLE="1"  # 启用
→ 调用 _run_graph_agent_non_blocking()
```

### 7.4 计划生成

```python
# GraphAgent._generate_plan()
plan = [
    {"id": "step_1", "tool": "ls_repo", "dependencies": []},
    {"id": "step_2", "tool": "bash", "dependencies": ["step_1"]},
    {"id": "step_3", "tool": "bash", "dependencies": ["step_2"]},
    {"id": "step_4", "tool": "bash", "dependencies": ["step_2"]},
    {"id": "step_5", "tool": "write_file", "dependencies": ["step_2", "step_3", "step_4"]},
]
```

### 7.5 转换为DAG

```python
# GraphAgent._plan_to_graph()
graph = ToolGraph(name="execution_graph")
graph.add_node(ToolNode(...))  # 添加5个节点
graph.add_edge("step_1", "step_2")  # 添加依赖边
# ...

# 层级计算
levels = {
    "step_1": 0,
    "step_2": 1,
    "step_3": 2,
    "step_4": 2,
    "step_5": 3,
}
```

### 7.6 双轨执行

```
时间轴:
t=0s:  [START] Level 1/4 (1 nodes)
t=1s:  [OK] step_1 completed
t=1s:  [START] Level 2/4 (1 nodes)
t=2s:  [OK] step_2 completed
t=2s:  [START] Level 3/4 (2 nodes)  ← step_3 和 step_4 并行
t=4s:  [OK] step_3 completed
t=5s:  [OK] step_4 completed
t=5s:  [START] Level 4/4 (1 nodes)
t=5.5s: 用户输入 "stop"  ← 在 Level 4 执行期间
t=6s:  [OK] step_5 completed  ← 当前层级执行完
t=6s:  检查队列 → 发现 "stop"
t=6s:  停止执行（本来也没有 Level 5 了）
```

### 7.7 最终输出

```
[执行统计] 总节点: 5, 完成: 5, 失败: 0, 耗时: 6.0s

[最终答案]
[OK] File written: analysis_report.md (185781 bytes)
```

---

## 8. 总结

### 8.1 FastReAct IEL 的本质

**FastReAct 的 IEL = 渐进式交互执行**

```
保守IEL（未实现）:
  每步确认 → 效率低 → 用户体验差

渐进式IEL（Sprint 3）:
  默认自动执行 + 可随时中断 → 高效 + 可控
```

### 8.2 核心技术栈

| 技术 | 用途 | 文件 |
|------|------|------|
| **Async Generator** | 事件流 | `runtime.py:execute_steppable()` |
| **asyncio.Queue** | 干预队列 | `runtime.py:intervention_queue` |
| **asyncio.wait(FIRST_COMPLETED)** | 双轨并发 | `unified_repl.py:1100-1103` |
| **prompt_toolkit** | 非阻塞输入 | `unified_repl.py:PromptSession` |
| **patch_stdout** | 输出不打断输入 | `unified_repl.py:1055` |

### 8.3 关键设计决策

| 决策 | 原因 |
|------|------|
| 不实现"每步确认"IEL | 用户体验差，违背自动化初衷 |
| 在层级边界检查队列 | 平衡响应速度和执行效率 |
| 使用异步生成器 | Pythonic，易读，支持流式处理 |
| 双轨并发 + FIRST_COMPLETED | 用户或Agent都能终止执行 |
| 文本模式回退 | 兼容不支持ANSI的终端 |

---

*文档版本: 1.0*
*最后更新: 2025-02-06*
*状态: Sprint 3 Complete*
