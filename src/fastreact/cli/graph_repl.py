"""
GraphAgent REPL - 智能任务规划 REPL

集成 GraphAgent 和 IEL，提供"先思考，再动手"的执行模式：

1. 大脑升级：GraphAgent 自动规划任务
2. 防弹背心：IEL 快照和自动回滚
3. 实时反馈：流式进度和工具状态面板

使用：
    python -m fastreact.cli.graph_repl
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Windows UTF-8 设置
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    console = Console()
except ImportError:
    console = None
    print("[Warning] Rich not installed, falling back to basic output")

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.key_binding import KeyBindings
except ImportError:
    PromptSession = None

# ============================================================================
# Complexity Evaluator - 任务复杂度评估
# ============================================================================

class ComplexityEvaluator:
    """评估任务复杂度，决定使用哪种执行模式"""

    async def evaluate(self, query: str) -> Dict[str, Any]:
        """
        评估查询复杂度

        Returns:
            {
                "complexity": "simple" | "medium" | "complex",
                "score": 0.0-1.0,
                "reasons": [...],
                "suggested_mode": "react" | "graph_agent" | "iel"
            }
        """
        import re

        factors = []
        score = 0.0

        # 因子 1：查询长度
        if len(query) > 200:
            factors.append("长查询")
            score += 0.2

        # 因子 2：多步骤关键词
        multi_step_keywords = [
            "然后", "之后", "接着", "再", "最后",
            "首先", "其次", "最后",
            "分析", "生成", "比较", "总结", "重构"
        ]
        found_keywords = [kw for kw in multi_step_keywords if kw in query]
        if found_keywords:
            factors.append(f"多步骤关键词: {', '.join(found_keywords)}")
            score += 0.3 * len(found_keywords)

        # 因子 3：工具数量估算
        tool_keywords = {
            "搜索": "search", "查找": "search",
            "计算": "calculator", "分析": "analyze",
            "编辑": "edit", "修改": "edit",
            "创建": "create", "生成": "generate",
            "测试": "test", "运行": "run",
            "保存": "save", "写入": "write",
        }
        found_tools = set()
        for keyword, tool_type in tool_keywords.items():
            if keyword in query:
                found_tools.add(tool_type)

        if len(found_tools) >= 3:
            factors.append(f"多个工具: {', '.join(found_tools)}")
            score += 0.4

        # 因子 4：条件/循环关键词
        conditional_keywords = ["如果", "否则", "当", "直到", "循环", "每个", "对于"]
        if any(kw in query for kw in conditional_keywords):
            factors.append("包含条件或循环逻辑")
            score += 0.3

        # 因子 5：文件操作关键词
        file_keywords = ["文件", "项目", "代码", "重构", "修改所有", "批量"]
        if any(kw in query for kw in file_keywords):
            factors.append("涉及文件操作")
            score += 0.2

        # 因子 6：数字/参数关键词
        if re.search(r'\d+.*个|批量|所有', query):
            factors.append("批量操作")
            score += 0.2

        # 归一化分数
        score = min(score, 1.0)

        # 判定复杂度
        if score < 0.4:
            complexity = "simple"
            suggested_mode = "react"
        elif score < 0.7:
            complexity = "medium"
            suggested_mode = "graph_agent"
        else:
            complexity = "complex"
            suggested_mode = "iel"

        return {
            "complexity": complexity,
            "score": score,
            "reasons": factors,
            "suggested_mode": suggested_mode,
        }

# ============================================================================
# GraphAgent REPL State
# ============================================================================

class GraphAgentREPLState:
    """GraphAgent REPL 会话状态"""

    def __init__(self):
        # 执行模式
        self.execution_mode = "auto"  # auto | react | graph_agent | iel

        # Agent 实例
        self.react_agent = None
        self.graph_agent = None
        self.iel_loop = None

        # 对话历史
        self.conversation_history: List[Dict[str, str]] = []

        # 配置
        self.config = {
            "auto_confirm_plan": True,  # 自动确认计划
            "show_plan_details": True,  # 显示计划详情
            "enable_streaming": True,   # 启用流式输出
            "auto_snapshot": True,      # 自动快照
            "git_integration": True,    # Git 集成
        }

        # 统计
        self.stats = {
            "total_queries": 0,
            "react_queries": 0,
            "graph_agent_queries": 0,
            "iel_queries": 0,
            "plan_rejections": 0,
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()

# ============================================================================
# GraphAgent REPL
# ============================================================================

class GraphAgentREPL:
    """
    GraphAgent REPL - 智能任务规划 REPL

    特点：
    1. 自动评估任务复杂度
    2. GraphAgent 自动生成执行计划
    3. 用户确认后再执行
    4. IEL 快照和自动回滚
    5. 实时进度反馈
    """

    def __init__(self, session_to_load: Optional[Path] = None):
        """初始化 REPL"""
        self.state = GraphAgentREPLState()
        self.running = True
        self.session_to_load = session_to_load

        # 评估器
        self.complexity_evaluator = ComplexityEvaluator()

        # Rich Console
        self.console = console

        # 命令
        self.commands = {
            'help': self.cmd_help,
            'exit': self.cmd_exit,
            'quit': self.cmd_exit,
            'run': self.cmd_run,
            'mode': self.cmd_mode,
            'stats': self.cmd_stats,
            'clear': self.cmd_clear,
            'history': self.cmd_history,
        }

    # ========================================================================
    # 主循环
    # ========================================================================

    async def run_async(self):
        """运行 REPL"""
        self.print_welcome()

        # 加载会话
        if self.session_to_load:
            await self._load_session(self.session_to_load)

        # 主循环
        while self.running:
            try:
                # 读取命令
                command = input(self.get_prompt())

                if not command.strip():
                    continue

                # 执行命令
                await self.execute_command(command)

            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                continue

    def get_prompt(self) -> str:
        """获取提示符"""
        mode_display = {
            "auto": "[AUTO]",
            "react": "[REACT]",
            "graph_agent": "[GRAPH]",
            "iel": "[IEL]",
        }

        mode_tag = mode_display.get(self.state.execution_mode, "[UNKNOWN]")

        query_count = self.state.stats["total_queries"]

        return f"FastReAct{mode_tag} Q{query_count} >> "

    def print_welcome(self):
        """打印欢迎信息"""
        if self.console:
            self.console.print()
            self.console.print(Panel(
                """**FastReAct GraphAgent REPL**

智能任务规划 REPL：
• 自动评估任务复杂度
• GraphAgent 自动生成执行计划
• 用户确认后再执行
• IEL 快照和自动回滚

输入 `/help` 查看命令""",
                title="Welcome",
                border_style="cyan"
            ))
            self.console.print()
        else:
            print()
            print("=" * 60)
            print("FastReAct GraphAgent REPL")
            print("=" * 60)
            print("智能任务规划 REPL：自动规划 + 用户确认 + 安全执行")
            print("输入 `/help` 查看命令")
            print()

    async def execute_command(self, command: str) -> bool:
        """执行命令"""
        command = command.strip()

        if not command:
            return True

        # 快捷命令
        if command.startswith('/'):
            return await self._handle_quick_command(command)

        # 解析命令
        parts = command.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # 执行命令
        if cmd in self.commands:
            handler = self.commands[cmd]
            result = await handler(args) if asyncio.iscoroutinefunction(handler) else handler(args)
            return result if isinstance(result, bool) else True
        else:
            # 当作查询执行
            return await self.cmd_run(command)

    async def _handle_quick_command(self, command: str) -> bool:
        """处理快捷命令"""
        cmd = command[1:].strip().lower()

        if cmd == "react":
            self.state.execution_mode = "react"
            self.print_success("切换到 ReAct 模式")
        elif cmd == "graph":
            self.state.execution_mode = "graph_agent"
            self.print_success("切换到 GraphAgent 模式")
        elif cmd == "iel":
            self.state.execution_mode = "iel"
            self.print_success("切换到 IEL 模式")
        elif cmd == "auto":
            self.state.execution_mode = "auto"
            self.print_success("切换到自动模式")
        else:
            self.print_error(f"未知命令: /{cmd}")
            return await self.cmd_help("")

        return True

    # ========================================================================
    # 命令处理器
    # ========================================================================

    def cmd_help(self, args: str) -> bool:
        """显示帮助"""
        if self.console:
            self.console.print()
            self.console.print("[bold cyan]可用命令：[/bold cyan]")
            self.console.print()

            self.console.print("[bold yellow]基础命令：[/bold yellow]")
            basics = [
                ("run <query>", "执行查询（自动模式选择）"),
                ("mode <name>", "切换模式 (auto/react/graph/iel)"),
                ("stats", "显示统计信息"),
                ("history", "显示查询历史"),
                ("help", "显示帮助"),
                ("exit/quit", "退出"),
            ]
            for cmd, desc in basics:
                self.console.print(f"  {cmd:<30} {desc}")

            self.console.print()
            self.console.print("[bold yellow]快捷命令：[/bold yellow]")
            shortcuts = [
                ("/react", "切换到 ReAct 模式"),
                ("/graph", "切换到 GraphAgent 模式"),
                ("/iel", "切换到 IEL 模式"),
                ("/auto", "切换到自动模式"),
            ]
            for cmd, desc in shortcuts:
                self.console.print(f"  {cmd:<30} {desc}")

            self.console.print()
        else:
            print("\n可用命令：")
            print("  run <query> - 执行查询")
            print("  mode <name> - 切换模式")
            print("  stats - 统计信息")
            print("  history - 历史记录")
            print("  help - 帮助")
            print("  exit/quit - 退出")

        return True

    def cmd_exit(self, args: str) -> bool:
        """退出"""
        if self.console:
            self.console.print("\n[bold cyan]Goodbye![/bold cyan]\n")
        else:
            print("\nGoodbye!\n")
        return False

    async def cmd_mode(self, args: str) -> bool:
        """切换模式"""
        mode = args.strip().lower()

        valid_modes = ["auto", "react", "graph_agent", "iel"]

        if mode not in valid_modes:
            self.print_error(f"无效模式: {mode}")
            self.print_output(f"可用模式: {', '.join(valid_modes)}")
            return True

        self.state.execution_mode = mode
        self.print_success(f"切换到 {mode.upper()} 模式")

        return True

    async def cmd_stats(self, args: str) -> bool:
        """显示统计"""
        stats = self.state.get_stats()

        if self.console:
            table = Table(title="Session Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Total Queries", str(stats["total_queries"]))
            table.add_row("ReAct Queries", str(stats["react_queries"]))
            table.add_row("GraphAgent Queries", str(stats["graph_agent_queries"]))
            table.add_row("IEL Queries", str(stats["iel_queries"]))
            table.add_row("Plan Rejections", str(stats["plan_rejections"]))

            self.console.print(table)
        else:
            print("\nSession Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")

        return True

    async def cmd_history(self, args: str) -> bool:
        """显示历史"""
        limit = int(args) if args.isdigit() else 10

        recent = self.state.conversation_history[-limit:]

        if not recent:
            self.print_output("No history yet")
        else:
            if self.console:
                table = Table(title=f"Last {len(recent)} Messages")
                table.add_column("Role")
                table.add_column("Message")

                for msg in recent:
                    content = msg["content"][:100]
                    table.add_row(msg["role"].upper(), content)

                self.console.print(table)
            else:
                print(f"\nLast {len(recent)} messages:")
                for msg in recent:
                    print(f"  [{msg['role'].upper()}]: {msg['content'][:100]}")

        return True

    def cmd_clear(self, args: str) -> bool:
        """清屏"""
        if self.console:
            self.console.clear()
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
        return True

    # ========================================================================
    # 核心命令：RUN
    # ========================================================================

    async def cmd_run(self, query: str) -> bool:
        """执行查询（智能模式选择）"""
        try:
            # 保存查询
            self.state.conversation_history.append({"role": "user", "content": query})
            self.state.stats["total_queries"] += 1

            # 自动模式选择
            if self.state.execution_mode == "auto":
                evaluation = await self.complexity_evaluator.evaluate(query)

                self._show_complexity_evaluation(evaluation)

                # 选择模式
                mode = evaluation["suggested_mode"]
            else:
                mode = self.state.execution_mode

            # 执行
            if mode == "react":
                return await self._run_react(query)
            elif mode == "graph_agent":
                return await self._run_graph_agent(query)
            elif mode == "iel":
                return await self._run_iel(query)
            else:
                self.print_error(f"未知模式: {mode}")
                return True

        except Exception as e:
            self.print_error(str(e))
            import traceback
            traceback.print_exc()
            return True

    def _show_complexity_evaluation(self, evaluation: Dict[str, Any]):
        """显示复杂度评估"""
        if not self.console:
            return

        complexity = evaluation["complexity"].upper()
        score = evaluation["score"]
        reasons = evaluation["reasons"]
        mode = evaluation["suggested_mode"].upper()

        # 颜色
        colors = {
            "SIMPLE": "green",
            "MEDIUM": "yellow",
            "COMPLEX": "red",
        }

        color = colors.get(complexity, "white")

        self.console.print()
        self.console.print(f"[{color}]任务复杂度: {complexity}[/] (score: {score:.2f})")
        self.console.print(f"[cyan]推荐模式: {mode}[/]")

        if reasons:
            self.console.print(f"  原因: {', '.join(reasons)}")

        self.console.print()

    # ========================================================================
    # ReAct 模式
    # ========================================================================

    async def _run_react(self, query: str) -> bool:
        """ReAct 模式执行"""
        self.state.stats["react_queries"] += 1

        if self.console:
            self.console.print(f"[yellow][REACT 模式][/yellow]")
            self.console.print()

        # 创建 FastReAct agent
        agent = self._get_or_create_react_agent()

        # 执行
        result = await agent.run_async(query)

        # 显示结果
        if self.console:
            self.console.print(Panel(
                result.get("answer", ""),
                title="[REACT] Result",
                border_style="green"
            ))
        else:
            print(f"\nAnswer: {result.get('answer', '')}")

        # 保存到历史
        self.state.conversation_history.append({
            "role": "assistant",
            "content": result.get("answer", "")
        })

        return True

    def _get_or_create_react_agent(self):
        """获取或创建 ReAct Agent"""
        if self.state.react_agent is None:
            from fastreact import FastReAct
            from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model

            config = load_config()
            api_key = get_api_key(config)
            base_url = get_base_url(config)
            model = get_model(config)

            self.state.react_agent = FastReAct(
                api_key=api_key,
                base_url=base_url,
                model=model,
                enable_bootstrap=True,
                config=config,
            )

        return self.state.react_agent

    # ========================================================================
    # GraphAgent 模式
    # ========================================================================

    async def _run_graph_agent(self, query: str) -> bool:
        """GraphAgent 模式执行"""
        self.state.stats["graph_agent_queries"] += 1

        if self.console:
            self.console.print(f"[cyan][GRAPHAGENT 模式][/cyan]")
            self.console.print()

        # 创建 GraphAgent
        agent = self._get_or_create_graph_agent()

        # 步骤 1：生成计划
        if self.console:
            self.console.print("[bold blue]Step 1: 生成执行计划...[/bold blue]")

        plan = await agent._generate_plan(query)

        # 显示计划
        self._display_plan(plan)

        # 确认
        if self.state.config["auto_confirm_plan"]:
            if not self._confirm_plan():
                self.state.stats["plan_rejections"] += 1
                self.print_output("[yellow]计划已取消[/yellow]")
                return True

        # 步骤 2：执行计划
        if self.console:
            self.console.print()
            self.console.print("[bold blue]Step 2: 执行计划...[/bold blue]")

        with self._create_progress() as progress:
            task = progress.add_task("[cyan]执行中...", total=None)

            try:
                result = await agent.run(query)

                progress.update(task, completed=True)

                # 显示结果
                self._display_graph_agent_result(result)

                # 保存到历史
                self.state.conversation_history.append({
                    "role": "assistant",
                    "content": result.get("response", "")
                })

            except Exception as e:
                self.print_error(f"执行失败: {e}")
                raise

        return True

    def _get_or_create_graph_agent(self):
        """获取或创建 GraphAgent"""
        if self.state.graph_agent is None:
            from fastreact.graph import GraphAgent, AgentConfig

            react_agent = self._get_or_create_react_agent()

            self.state.graph_agent = GraphAgent(
                llm_client=react_agent._get_client(),
                tools=react_agent.tools,
                config=AgentConfig(
                    execution_strategy="level_based",
                    max_parallel=3,
                    enable_visualization=True,
                ),
            )

        return self.state.graph_agent

    def _display_plan(self, plan):
        """显示执行计划"""
        if not self.console:
            print(f"\nPlan: {plan.goal}")
            print(f"Steps: {len(plan.steps)}")
            for step in plan.steps:
                print(f"  - {step.step_id}: {step.tool_name} - {step.description}")
            return

        self.console.print()
        self.console.print(Panel(
            f"[bold]目标:[/] {plan.goal}\n"
            f"[bold]步骤数:[/] {len(plan.steps)}",
            title="[bold blue]执行计划[/bold blue]",
            border_style="blue"
        ))

        # 步骤表格
        table = Table(show_header=True, show_lines=True)
        table.add_column("ID", style="cyan")
        table.add_column("Tool", style="yellow")
        table.add_column("Description")
        table.add_column("Dependencies", style="dim")

        for step in plan.steps:
            deps = ", ".join(step.dependencies) if step.dependencies else "-"
            table.add_row(
                step.step_id,
                step.tool_name,
                step.description,
                deps
            )

        self.console.print(table)

    def _confirm_plan(self) -> bool:
        """确认计划"""
        try:
            response = input("\n是否执行该计划？ [Y/n]: ").strip().lower()

            if response in ['n', 'no', '否']:
                return False

            return True

        except (EOFError, KeyboardInterrupt):
            return False

    def _display_graph_agent_result(self, result: dict):
        """显示 GraphAgent 结果"""
        if not self.console:
            print(f"\nResult: {result.get('response', '')}")
            return

        self.console.print()

        # 执行报告
        report = result.get("report", {})

        stats = f"""[bold]总节点:[/] {report.get('total_nodes', 0)}
[bold]完成:[/] {report.get('completed_nodes', 0)}
[bold]失败:[/] {report.get('failed_nodes', 0)}
[bold]耗时:[/] {report.get('execution_time', 0):.2f}s"""

        self.console.print(Panel(
            stats,
            title="[green]执行统计[/green]",
            border_style="green"
        ))

        # 最终响应
        self.console.print()
        self.console.print(Panel(
            result.get("response", ""),
            title="[bold green]最终答案[/bold green]",
            border_style="green"
        ))

        # 可视化（如果有）
        if result.get("visualization"):
            self.console.print()
            self.console.print(Panel(
                result["visualization"],
                title="[dim]Graph Visualization[/dim]",
                border_style="dim",
            ))

    def _create_progress(self):
        """创建进度条"""
        if self.console:
            from rich.progress import (
                Progress,
                SpinnerColumn,
                TextColumn,
                BarColumn,
                TimeRemainingColumn,
            )

            return Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeRemainingColumn(),
                console=self.console,
            )
        else:
            # 简单的上下文管理器
            class DummyProgress:
                def __enter__(self): return self
                def __exit__(self, *args): pass

                def add_task(self, description, total=None):
                    return None

                def update(self, task, **kwargs):
                    pass

            return DummyProgress()

    # ========================================================================
    # IEL 模式
    # ========================================================================

    async def _run_iel(self, query: str) -> bool:
        """IEL 模式执行"""
        self.state.stats["iel_queries"] += 1

        if self.console:
            self.console.print(f"[magenta][IEL 模式][/magenta]")
            self.console.print()

        self.print_output("[yellow]IEL 模式正在开发中，暂时使用 GraphAgent 模式[/yellow]")

        # 回退到 GraphAgent
        return await self._run_graph_agent(query)

    # ========================================================================
    # 会话管理
    # ========================================================================

    async def _load_session(self, session_file: Path):
        """加载会话"""
        import json

        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            self.state.conversation_history = session_data.get("conversation", [])
            self.state.stats.update(session_data.get("stats", {}))

            self.print_success(f"会话已加载: {session_file.name}")

        except Exception as e:
            self.print_error(f"加载会话失败: {e}")

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def print_success(self, message: str):
        """打印成功信息"""
        if self.console:
            self.console.print(f"[green bold][SUCCESS][/green bold] {message}")
        else:
            print(f"[SUCCESS] {message}")

    def print_error(self, message: str):
        """打印错误信息"""
        if self.console:
            self.console.print(f"[red bold][ERROR][/red bold] {message}")
        else:
            print(f"[ERROR] {message}", file=sys.stderr)

    def print_output(self, message: str):
        """打印输出"""
        if self.console:
            self.console.print(message)
        else:
            print(message)


# ============================================================================
# 入口点
# ============================================================================

def run_graph_repl():
    """启动 GraphAgent REPL"""
    repl = GraphAgentREPL()

    try:
        asyncio.run(repl.run_async())
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")


if __name__ == '__main__':
    run_graph_repl()
