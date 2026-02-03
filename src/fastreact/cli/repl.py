"""
Interactive REPL - 交互式命令行界面

提供类似 Claude Code 的交互式 REPL 会话：
- 持续的命令行会话
- 命令历史和自动补全
- 多步工作流
- 状态持久化
- 彩色输出
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
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.patch_stdout import patch_stdout
    PROMPT_TOOLKIT_AVAILABLE = True
except (ImportError, Exception) as e:
    # ImportError: module not installed
    # Exception: Windows terminal compatibility issues
    PROMPT_TOOLKIT_AVAILABLE = False
    PromptSession = None

# Rich UI (fallback if prompt_toolkit not available)
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    console = Console()
except ImportError:
    console = None


class REPLState:
    """REPL 会话状态"""

    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self.current_graph = None
        self.workspace = Path.cwd()
        self.last_result = None
        self.session_start = datetime.now()

    def set_var(self, name: str, value: Any):
        """设置变量"""
        self.variables[name] = value

    def get_var(self, name: str, default=None):
        """获取变量"""
        return self.variables.get(name, default)

    def add_history(self, command: str, result: Any):
        """添加历史记录"""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "result": str(result)[:200],  # 限制长度
        })

    def get_stats(self) -> Dict[str, Any]:
        """获取会话统计"""
        return {
            "session_duration": (datetime.now() - self.session_start).total_seconds(),
            "commands_executed": len(self.history),
            "variables": len(self.variables),
            "workspace": str(self.workspace),
        }


class InteractiveREPL:
    """交互式 REPL"""

    def __init__(self, use_prompt_toolkit: bool = None):
        """
        初始化 REPL

        Args:
            use_prompt_toolkit: 是否使用 prompt_toolkit (None=自动检测)
        """
        self.state = REPLState()
        self.running = True

        # 自动检测是否使用 prompt_toolkit
        if use_prompt_toolkit is None:
            # 在 Windows 上禁用 prompt_toolkit 以避免兼容性问题
            self.use_prompt_toolkit = False  # 强制使用基础模式
        else:
            self.use_prompt_toolkit = use_prompt_toolkit and PROMPT_TOOLKIT_AVAILABLE

        # 定义命令
        self.commands = {
            'help': self.cmd_help,
            'exit': self.cmd_exit,
            'quit': self.cmd_exit,
            'run': self.cmd_run,
            'chat': self.cmd_chat,
            'graph': self.cmd_graph,
            'load': self.cmd_load,
            'vars': self.cmd_vars,
            'history': self.cmd_history,
            'clear': self.cmd_clear,
            'status': self.cmd_status,
            'debug': self.cmd_debug,
            'eval': self.cmd_eval,
            'python': self.cmd_python,
        }

        # 仅在使用 prompt_toolkit 时初始化
        if self.use_prompt_toolkit:
            self.completer = WordCompleter(list(self.commands.keys()), ignore_case=True)
            self.style = Style.from_dict({
                'prompt': 'ansicyan bold',
                'command': 'ansiyellow',
                'output': 'white',
                'error': 'ansired bold',
                'info': 'ansiblue',
                'success': 'ansigreen',
            })
            self.key_bindings = KeyBindings()

            @self.key_bindings.add('c-d')
            def _(event):
                """Ctrl+D 退出"""
                event.app.exit()

            @self.key_bindings.add('c-c')
            def _(event):
                """Ctrl+C 清空当前输入"""
                event.app.current_buffer.text = ''

    def get_prompt(self) -> str:
        """获取提示符"""
        duration = int((datetime.now() - self.state.session_start).total_seconds())
        mins = duration // 60
        secs = duration % 60
        return f"[{mins:02d}:{secs:02d}] >> "

    def print_welcome(self):
        """打印欢迎信息"""
        # 检测是否在交互式终端
        is_interactive = sys.stdin.isatty()

        if console and is_interactive:
            console.print()
            console.print(Panel(
                "FastReAct Interactive Shell\n\n"
                "Type 'help' for available commands\n"
                "Type 'exit' or 'quit' to exit\n"
                "Type Ctrl+D to exit",
                title="FastReAct",
                border_style="cyan"
            ))
            console.print()
        else:
            print()
            print("=" * 60)
            print("FastReAct Interactive Shell")
            print("=" * 60)
            print("Type 'help' for available commands")
            print("Type 'exit' or 'quit' to exit")
            print()

    def print_output(self, text: str, style: str = "") -> None:
        """打印输出"""
        if console:
            if style:
                console.print(f"[{style}]{text}[/{style}]")
            else:
                console.print(text)
        else:
            print(text)

    def print_error(self, text: str) -> None:
        """打印错误"""
        if console:
            console.print(f"[red bold]Error:[/red bold] {text}")
        else:
            print(f"Error: {text}", file=sys.stderr)

    def print_success(self, text: str) -> None:
        """打印成功信息"""
        if console:
            console.print(f"[green bold]Success:[/green bold] {text}")
        else:
            print(f"Success: {text}")

    async def execute_command(self, command: str) -> bool:
        """执行命令"""
        command = command.strip()
        if not command:
            return True

        # 解析命令和参数
        parts = command.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # 特殊处理：直接执行查询（run 的简写）
        if cmd not in self.commands:
            # 当作查询执行
            return await self.cmd_run(command)

        # 执行命令
        handler = self.commands[cmd]
        try:
            result = await handler(args) if asyncio.iscoroutinefunction(handler) else handler(args)
            self.state.add_history(command, result)
            return result if isinstance(result, bool) else True
        except Exception as e:
            self.print_error(str(e))
            import traceback
            traceback.print_exc()
            return True

    # ========================================================================
    # 命令处理器
    # ========================================================================

    def cmd_help(self, args: str) -> bool:
        """显示帮助"""
        if console:
            console.print()
            console.print("Available Commands:", style="bold cyan")
            console.print()

            commands = [
                ("run <query>", "Execute a query"),
                ("chat", "Interactive chat mode"),
                ("graph <subcommand>", "Tool Graph commands (init, run, list, validate)"),
                ("load <file>", "Load a graph definition"),
                ("vars", "List all variables"),
                ("history", "Show command history"),
                ("clear", "Clear screen"),
                ("status", "Show session status"),
                ("debug <command>", "Debug commands"),
                ("eval <expr>", "Evaluate Python expression"),
                ("python", "Start Python REPL"),
                ("help", "Show this help"),
                ("exit/quit", "Exit the shell"),
            ]

            for cmd, desc in commands:
                console.print(f"  {cmd:<30} {desc}", style="yellow")
            console.print()
        else:
            print("\nAvailable Commands:")
            for cmd, desc in [
                ("run <query>", "Execute a query"),
                ("chat", "Interactive chat mode"),
                ("graph <subcommand>", "Tool Graph commands"),
                ("load <file>", "Load a graph definition"),
                ("vars", "List all variables"),
                ("history", "Show command history"),
                ("clear", "Clear screen"),
                ("status", "Show session status"),
                ("exit/quit", "Exit the shell"),
            ]:
                print(f"  {cmd:<30} {desc}")
            print()

        return True

    def cmd_exit(self, args: str) -> bool:
        """退出"""
        if console:
            console.print("\nGoodbye!\n", style="bold cyan")
        else:
            print("\nGoodbye!\n")
        return False

    async def cmd_run(self, query: str) -> bool:
        """执行查询"""
        if not query:
            self.print_error("Please provide a query")
            return True

        try:
            from fastreact import FastReAct
            from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model

            config = load_config()
            api_key = get_api_key(config)
            model = get_model(config)
            base_url = get_base_url(config)

            if console:
                console.print()
                console.print(f"[dim]Executing with {model}...[/dim]")
                console.print()

            agent = FastReAct(
                api_key=api_key,
                base_url=base_url,
                model=model,
                enable_bootstrap=True,
            )

            result = await agent.run_async(query=query)

            self.state.last_result = result

            if console:
                console.print(Panel(
                    result['answer'],
                    title="Answer",
                    border_style="green"
                ))
                console.print(f"Stats: {result['stats']}\n", style="dim")
            else:
                print(f"\nAnswer: {result['answer']}")
                print(f"Stats: {result['stats']}\n")

            return True

        except Exception as e:
            self.print_error(str(e))
            return True

    async def cmd_chat(self, args: str) -> bool:
        """进入聊天模式"""
        self.print_output("Entering chat mode (type 'quit' to exit)...")

        while True:
            try:
                if PROMPT_TOOLKIT_AVAILABLE:
                    session = PromptSession("You >> ")
                    query = await session.prompt_async()
                else:
                    query = input("You >> ")

                if query.lower() in ['quit', 'exit', 'q']:
                    break

                if not query.strip():
                    continue

                await self.cmd_run(query)

            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                continue

        return True

    def cmd_graph(self, args: str) -> bool:
        """图命令"""
        if not args:
            self.print_output("Usage: graph <init|run|list|validate> [args]")
            return True

        parts = args.split(None, 1)
        subcommand = parts[0]
        subargs = parts[1] if len(parts) > 1 else ""

        if subcommand == "init":
            self.graph_init(subargs)
        elif subcommand == "run":
            # 异步执行
            asyncio.create_task(self.graph_run(subargs))
        elif subcommand == "list":
            self.graph_list()
        elif subcommand == "validate":
            self.graph_validate(subargs)
        else:
            self.print_error(f"Unknown graph subcommand: {subcommand}")

        return True

    def graph_init(self, args: str) -> None:
        """创建图模板"""
        import json
        from pathlib import Path

        name = args.strip() or "workflow"
        template = {
            "name": name,
            "description": f"Tool Graph: {name}",
            "nodes": [
                {"id": "node1", "type": "tool", "tool": "tool_name", "inputs": {}},
                {"id": "node2", "type": "tool", "tool": "tool_name", "inputs": {}}
            ],
            "edges": [{"from": "node1", "to": "node2"}]
        }

        filepath = Path(f"{name}.json")
        with open(filepath, 'w') as f:
            json.dump(template, f, indent=2)

        self.print_success(f"Created template: {filepath}")

    async def graph_run(self, args: str) -> None:
        """运行图"""
        import json
        from pathlib import Path

        filepath = args.strip() or "workflow.json"

        if not Path(filepath).exists():
            self.print_error(f"File not found: {filepath}")
            return

        with open(filepath) as f:
            graph_def = json.load(f)

        self.print_output(f"Running graph: {graph_def.get('name', 'unnamed')}")
        # TODO: 实际执行图
        self.print_output("(Graph execution not yet implemented in REPL)")

    def graph_list(self) -> None:
        """列出图文件"""
        from pathlib import Path

        graphs = []
        for ext in ['*.json', '*.yaml', '*.yml']:
            graphs.extend(Path.cwd().glob(ext))

        if not graphs:
            self.print_output("No graph files found")
            return

        self.print_output(f"Found {len(graphs)} graph file(s):\n")
        for f in graphs:
            self.print_output(f"  • {f.name}")

    def graph_validate(self, args: str) -> None:
        """验证图"""
        import json
        from pathlib import Path

        filepath = args.strip()
        if not filepath:
            self.print_error("Usage: graph validate <file>")
            return

        if not Path(filepath).exists():
            self.print_error(f"File not found: {filepath}")
            return

        try:
            with open(filepath) as f:
                graph_def = json.load(f)

            errors = []
            if 'nodes' not in graph_def:
                errors.append("Missing 'nodes'")
            if 'edges' not in graph_def:
                errors.append("Missing 'edges'")

            if errors:
                self.print_error("Validation failed:\n  - " + "\n  - ".join(errors))
            else:
                self.print_success(f"Validation passed ({len(graph_def['nodes'])} nodes, {len(graph_def['edges'])} edges)")

        except Exception as e:
            self.print_error(f"Failed to load: {e}")

    def cmd_load(self, args: str) -> bool:
        """加载图"""
        import json
        from pathlib import Path

        filepath = args.strip()
        if not filepath:
            self.print_error("Usage: load <file>")
            return True

        if not Path(filepath).exists():
            self.print_error(f"File not found: {filepath}")
            return True

        try:
            with open(filepath) as f:
                self.state.current_graph = json.load(f)

            self.print_success(f"Loaded graph: {self.state.current_graph.get('name', 'unnamed')}")
        except Exception as e:
            self.print_error(f"Failed to load: {e}")

        return True

    def cmd_vars(self, args: str) -> bool:
        """列出变量"""
        if not self.state.variables:
            self.print_output("No variables defined")
        else:
            if console:
                from rich.table import Table
                table = Table(show_header=True)
                table.add_column("Variable")
                table.add_column("Value")

                for name, value in self.state.variables.items():
                    table.add_row(name, str(value)[:50])

                console.print(table)
            else:
                self.print_output("\nVariables:")
                for name, value in self.state.variables.items():
                    print(f"  {name} = {value}")

        return True

    def cmd_history(self, args: str) -> bool:
        """显示历史"""
        limit = int(args) if args.isdigit() else 10

        recent = self.state.history[-limit:]

        if not recent:
            self.print_output("No history yet")
        else:
            if console:
                from rich.table import Table
                table = Table(show_header=True)
                table.add_column("Time")
                table.add_column("Command")
                table.add_column("Result")

                for entry in recent:
                    table.add_row(
                        entry['timestamp'][-8:],
                        entry['command'][:40],
                        entry['result'][:30]
                    )

                console.print(table)
            else:
                self.print_output(f"\nLast {len(recent)} commands:")
                for entry in recent:
                    print(f"  [{entry['timestamp'][-8:]}] {entry['command'][:50]}")

        return True

    def cmd_clear(self, args: str) -> bool:
        """清屏"""
        if console:
            console.clear()
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
        return True

    def cmd_status(self, args: str) -> bool:
        """显示状态"""
        stats = self.state.get_stats()

        if console:
            from rich.table import Table
            table = Table(title="Session Status", show_header=False)
            table.add_column("Metric")
            table.add_column("Value")

            for key, value in stats.items():
                table.add_row(key.replace('_', ' ').title(), str(value))

            console.print(table)
        else:
            self.print_output("\nSession Status:")
            for key, value in stats.items():
                print(f"  {key}: {value}")

        return True

    def cmd_debug(self, args: str) -> bool:
        """调试命令"""
        self.print_output("Debug commands: (not yet implemented)")
        return True

    def cmd_eval(self, args: str) -> bool:
        """计算 Python 表达式"""
        try:
            # 在变量的上下文中执行
            result = eval(args, {}, self.state.variables)
            self.print_output(f"= {result}")
            return True
        except Exception as e:
            self.print_error(str(e))
            return True

    def cmd_python(self, args: str) -> bool:
        """启动 Python REPL"""
        self.print_output("Starting Python REPL (exit() to return)...")
        import code
        code.interact(local=dict(self.state.variables))
        return True

    # ========================================================================
    # 主循环
    # ========================================================================

    async def run_async(self):
        """运行 REPL（异步）"""
        self.print_welcome()

        if self.use_prompt_toolkit:
            await self._run_with_prompt_toolkit()
        else:
            await self._run_basic()

    async def _run_with_prompt_toolkit(self):
        """使用 prompt_toolkit 运行"""
        session = PromptSession(
            completer=self.completer,
            style=self.style,
            key_bindings=self.key_bindings,
            history=FileHistory('.fastreact_history'),
            auto_suggest=AutoSuggestFromHistory(),
        )

        while self.running:
            try:
                with patch_stdout():
                    command = await session.prompt_async(
                        HTML('<style fg="ansicyan bold">>>></style> '),
                        style=self.style
                    )

                if command.strip():
                    self.running = await self.execute_command(command)

            except EOFError:
                break
            except KeyboardInterrupt:
                continue

    async def _run_basic(self):
        """基础输入模式"""
        # 检测是否在交互式终端
        is_interactive = sys.stdin.isatty()

        if not is_interactive:
            # 非交互模式：从 stdin 逐行读取命令
            for line in sys.stdin:
                command = line.strip()
                if command:
                    self.running = await self.execute_command(command)
                    if not self.running:
                        break
            return

        # 交互模式
        while self.running:
            try:
                command = input(self.get_prompt())

                if command.strip():
                    self.running = await self.execute_command(command)

            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                continue


def run_repl():
    """启动 REPL"""
    repl = InteractiveREPL()
    asyncio.run(repl.run_async())


# ============================================================================
# 入口点
# ============================================================================

if __name__ == '__main__':
    run_repl()
