# REPL Enhancement Plan - 自动模式选择

## 问题：当前架构的不足

### 1. GraphAgent 已实现但未集成
- **有**：`GraphAgent` 可以让 LLM 自动规划 ToolGraph
- **缺**：REPL 没有使用，用户无法受益

### 2. 没有自动模式选择
- **现状**：所有查询都走 ReAct 模式
- **问题**：复杂任务无法发挥 ToolGraph 的优势

### 3. IEL 功能被埋没
- **有**：完整的 IEL 执行循环、重规划、快照回滚
- **缺**：REPL 无法使用这些功能

---

## 解决方案：三层模式架构

### Layer 1: ReAct 模式（默认，快速响应）

```python
# 适用：简单查询
# 触发：默认模式
# 特点：自动循环，轻量级

agent = FastReAct(api_key="...")
result = await agent.run_async("2+2=?")
```

### Layer 2: GraphAgent 模式（LLM 自动规划）

```python
# 适用：中等复杂度任务
# 触发：命令 /graph 或关键词检测
# 特点：LLM 规划，DAG 执行

from fastreact.graph import GraphAgent

agent = GraphAgent(llm_client=client, tools=tools)
result = await agent.run("分析最近的 AI 新闻并生成报告")
```

### Layer 3: IEL 模式（高级，交互式）

```python
# 适用：复杂工作流，需要重规划
# 触发：命令 /iel 或手动构建
# 特点：动态重规划，用户中断，快照回滚

from fastreact.graph import IELLoop, IELExecutionContext

loop = IELLoop(executor, replanner)
result = await loop.run(context)
```

---

## 实现计划

### Phase 1: REPL 集成 GraphAgent

**目标**：让 REPL 能够使用 GraphAgent

#### 1.1 添加模式切换命令

```python
# repl.py

class REPLState:
    def __init__(self):
        # 新增：执行模式
        self.execution_mode = "react"  # react | graph_agent | iel

        # 新增：GraphAgent 实例
        self.graph_agent = None

class InteractiveREPL:
    async def cmd_mode(self, args: str) -> bool:
        """切换执行模式"""
        mode = args.strip().lower()

        if mode == "react":
            self.state.execution_mode = "react"
            self.print_success("Switched to ReAct mode (default)")

        elif mode == "graph":
            self.state.execution_mode = "graph_agent"
            # 初始化 GraphAgent
            self.state.graph_agent = self._create_graph_agent()
            self.print_success("Switched to GraphAgent mode (LLM planning)")

        elif mode == "iel":
            self.state.execution_mode = "iel"
            self.print_success("Switched to IEL mode (interactive)")

        else:
            self.print_error(f"Unknown mode: {mode}")
            self.print_output("Available modes: react, graph, iel")
```

#### 1.2 修改 cmd_run 支持多模式

```python
async def cmd_run(self, query: str) -> bool:
    """执行查询（根据模式选择）"""

    mode = self.state.execution_mode

    if mode == "react":
        # 原有逻辑
        return await self._run_react(query)

    elif mode == "graph_agent":
        # 新增：GraphAgent 模式
        return await self._run_graph_agent(query)

    elif mode == "iel":
        # 新增：IEL 模式
        return await self._run_iel(query)
```

#### 1.3 实现 _run_graph_agent

```python
async def _run_graph_agent(self, query: str) -> bool:
    """使用 GraphAgent 执行"""

    agent = self.state.get_or_create_agent()

    # 创建 GraphAgent
    from fastreact.graph import GraphAgent, AgentConfig

    graph_agent = GraphAgent(
        llm_client=agent._get_client(),
        tools=agent.tools,
        config=AgentConfig(
            execution_strategy="level_based",
            max_parallel=3,
        ),
    )

    # 执行
    if console:
        with Status("[bold cyan]Graph Agent 正在规划并执行...[/bold cyan]", console=console):
            result = await graph_agent.run(query)
    else:
        result = await graph_agent.run(query)

    # 显示结果
    self._display_graph_agent_result(result)

    return True

def _display_graph_agent_result(self, result: dict):
    """显示 GraphAgent 结果"""

    # 显示计划
    if console:
        console.print(Panel(
            f"目标: {result['plan']['goal']}\n"
            f"步骤数: {len(result['plan']['steps'])}",
            title="[Graph Plan]",
            border_style="blue"
        ))

    # 显示执行报告
    report = result['report']
    stats = f"""
    总节点: {report['total_nodes']}
    完成: {report['completed_nodes']}
    失败: {report['failed_nodes']}
    耗时: {report['execution_time']:.2f}s
    """

    if console:
        console.print(Panel(stats, title="[Execution Stats]", border_style="green"))

    # 显示最终响应
    if console:
        console.print(Panel(
            result['response'],
            title="Answer",
            border_style="green"
        ))
```

---

### Phase 2: 自动模式选择（智能）

**目标**：根据任务复杂度自动选择模式

#### 2.1 复杂度评估器

```python
class ComplexityEvaluator:
    """评估任务复杂度"""

    async def evaluate(self, query: str) -> dict:
        """
        评估查询复杂度

        Returns:
            {
                "complexity": "simple" | "medium" | "complex",
                "confidence": 0.0-1.0,
                "reasons": [...],
                "suggested_mode": "react" | "graph_agent" | "iel"
            }
        """
        factors = []

        # 因子 1：查询长度
        if len(query) > 200:
            factors.append(("long_query", 0.3))

        # 因子 2：关键词检测
        multi_step_keywords = [
            "然后", "之后", "接着", "再", "最后",
            "分析", "生成", "比较", "总结"
        ]
        if any(kw in query for kw in multi_step_keywords):
            factors.append(("multi_step", 0.4))

        # 因子 3：工具数量估算
        tool_count = len(re.findall(r'(计算|搜索|分析|生成|保存|发送)', query))
        if tool_count >= 3:
            factors.append(("many_tools", 0.5))

        # 因子 4：条件/循环关键词
        conditional_keywords = ["如果", "否则", "当", "直到", "循环"]
        if any(kw in query for kw in conditional_keywords):
            factors.append(("conditional", 0.6))

        # 计算总分
        score = sum(score for _, score in factors)

        # 判定复杂度
        if score < 0.4:
            complexity = "simple"
            suggested_mode = "react"
        elif score < 0.8:
            complexity = "medium"
            suggested_mode = "graph_agent"
        else:
            complexity = "complex"
            suggested_mode = "iel"

        return {
            "complexity": complexity,
            "confidence": min(score + 0.3, 1.0),
            "reasons": [reason for reason, _ in factors],
            "suggested_mode": suggested_mode,
        }
```

#### 2.2 REPL 集成自动选择

```python
class InteractiveREPL:
    def __init__(self):
        # 新增：自动模式选择
        self.auto_mode = True  # 默认启用
        self.complexity_evaluator = ComplexityEvaluator()

    async def cmd_auto_mode(self, args: str) -> bool:
        """切换自动模式选择"""
        if args == "on":
            self.auto_mode = True
            self.print_success("Auto mode selection: ON")
        elif args == "off":
            self.auto_mode = False
            self.print_success("Auto mode selection: OFF")
        else:
            status = "ON" if self.auto_mode else "OFF"
            self.print_output(f"Auto mode selection: {status}")

    async def cmd_run(self, query: str) -> bool:
        """执行查询（自动模式选择）"""

        if self.auto_mode:
            # 评估复杂度
            evaluation = await self.complexity_evaluator.evaluate(query)

            # 显示评估结果
            self.print_output(
                f"[Complexity: {evaluation['complexity'].upper()}] "
                f"Mode: {evaluation['suggested_mode']}"
            )

            # 自动选择模式
            self.state.execution_mode = evaluation['suggested_mode']

        # 根据选择的模式执行
        return await self._execute_by_mode(query)
```

---

### Phase 3: IEL 模式集成

**目标**：让 REPL 能够使用 IEL 的交互式功能

#### 3.1 IEL 命令支持

```python
class InteractiveREPL:
    async def cmd_iel(self, args: str) -> bool:
        """IEL 模式命令"""

        subcommand = args.split()[0] if args else ""

        if subcommand == "status":
            # 显示 IEL 状态
            self._show_iel_status()

        elif subcommand == "interrupt":
            # 发送中断信号
            message = args[len("interrupt"):].strip()
            await self._send_iel_interrupt(message)

        elif subcommand == "snapshot":
            # 创建快照
            snapshot_id = await self._create_iel_snapshot()
            self.print_success(f"Snapshot created: {snapshot_id}")

        elif subcommand == "rollback":
            # 回滚到快照
            snapshot_id = args.split()[1] if len(args.split()) > 1 else None
            await self._rollback_iel_snapshot(snapshot_id)

        else:
            self.print_output("IEL commands: status, interrupt, snapshot, rollback")
```

---

## 优化建议

### ToolRuntime 优化

1. **并行执行优化**
   - 当前：固定的 `max_parallel=3`
   - 优化：动态调整并行度（根据任务类型）

2. **缓存优化**
   - 当前：无缓存
   - 优化：节点结果缓存（避免重复执行）

3. **流式输出**
   - 当前：批量返回结果
   - 优化：实时输出每个节点的进度

### IEL 优化

1. **智能重规划**
   - 当前：每次失败都重规划
   - 优化：根据失败类型决定是否重规划

2. **增量快照**
   - 当前：每次快照保存整个状态
   - 优化：增量快照（节省内存）

3. **并行中断处理**
   - 当前：串行处理用户中断
   - 优化：异步中断队列

---

## 优先级

### P0（立即）
- [ ] REPL 集成 GraphAgent
- [ ] 添加 `/mode` 命令切换模式
- [ ] 实现基本的 GraphAgent 执行

### P1（短期）
- [ ] 实现复杂度评估器
- [ ] 添加自动模式选择
- [ ] IEL 基本命令支持

### P2（中期）
- [ ] ToolRuntime 性能优化
- [ ] IEL 智能重规划
- [ ] 流式输出支持

---

## 测试计划

### 单元测试
- [ ] ComplexityEvaluator 测试
- [ ] 模式切换逻辑测试

### 集成测试
- [ ] REPL 多模式执行测试
- [ ] GraphAgent 集成测试
- [ ] IEL 交互测试

### 性能测试
- [ ] 模式切换开销
- [ ] 自动选择准确性
- [ ] 并行执行性能

---

**最后更新**: 2025-02-05
**状态**: 规划中，待实现
