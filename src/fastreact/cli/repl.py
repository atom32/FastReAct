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
        self.last_query = None  # 上一次查询
        self.session_start = datetime.now()
        self.agent = None  # 持久的 Agent 实例
        self.conversation_history: List[Dict[str, str]] = []  # 对话历史

        # 快捷命令（alias）
        self.aliases: Dict[str, str] = {
            'h': 'help',
            'q': 'quit',
            'v': 'vars',
            'hist': 'history',
            'conv': 'conversation',
            'st': 'status',
            'cls': 'clear',
            'res': 'reset',
        }

        # 查询模板
        self.templates: Dict[str, str] = {
            'summarize': '请总结以下内容：{}',
            'explain': '请详细解释：{}',
            'code': '请编写代码实现：{}',
            'debug': '请帮我调试以下代码：{}',
            'optimize': '请优化以下代码：{}',
            'translate': '请翻译成中文：{}',
        }

        # 配置
        self.config = {
            'streaming': False,  # 流式输出
            'show_thoughts': False,  # 显示思考过程
            'compact_mode': False,  # 紧凑模式
            'auto_save': True,  # 自动保存会话
        }

    def get_or_create_agent(self) -> 'FastReAct':
        """获取或创建 Agent 实例"""
        if self.agent is None:
            from fastreact import FastReAct
            from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model

            config = load_config()
            api_key = get_api_key(config)
            model = get_model(config)
            base_url = get_base_url(config)

            self.agent = FastReAct(
                api_key=api_key,
                base_url=base_url,
                model=model,
                enable_bootstrap=True,
                config=config,  # 传递完整配置，用于工具初始化
                # 启用工具分组（包括 deep_research）
                enable_groups=['file_ops', 'web', 'math', 'ai', 'code', 'system'],
            )

        return self.agent

    def add_conversation(self, role: str, content: str):
        """添加对话记录"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

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
            "conversation_turns": len(self.conversation_history),
            "agent_created": self.agent is not None,
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
            'conversation': self.cmd_conversation,
            'clear': self.cmd_clear,
            'status': self.cmd_status,
            'debug': self.cmd_debug,
            'eval': self.cmd_eval,
            'python': self.cmd_python,
            'reset': self.cmd_reset,
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
        turns = len(self.state.conversation_history) // 2

        # 显示模型信息（如果已初始化）
        model_info = ""
        if self.state.agent:
            model = getattr(self.state.agent, 'model', None)
            if model:
                model_info = f"| {model.split('/')[-1][:15]} "

        return f"[{mins:02d}:{secs:02d}|T:{turns}{model_info}]>> "

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

        # 快捷命令处理
        if command.startswith('/'):
            return await self._handle_quick_command(command)

        # 解析命令和参数
        parts = command.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # 检查是否是 alias
        if cmd in self.state.aliases:
            expanded = self.state.aliases[cmd]
            if args:
                command = f"{expanded} {args}"
            else:
                command = expanded
            parts = command.split(None, 1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

        # 特殊处理：直接执行查询（run 的简写）
        if cmd not in self.commands:
            # 检查是否是模板调用
            if cmd in self.state.templates and args:
                template = self.state.templates[cmd]
                query = template.format(args)
                return await self.cmd_run(query)
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

    async def _handle_quick_command(self, command: str) -> bool:
        """处理快捷命令"""
        cmd = command[1:].strip().lower()

        # /r - 重复上一次查询
        if cmd == 'r':
            if self.state.last_query:
                self.print_output(f"Repeating: {self.state.last_query}")
                return await self.cmd_run(self.state.last_query)
            else:
                self.print_error("No previous query")
                return True

        # /! - 编辑并执行上一次查询（简化版：直接显示并提示重新输入）
        elif cmd == '!':
            if self.state.last_query:
                self.print_output(f"Last query: {self.state.last_query}")
                self.print_output("Use 'history' to see all queries")
            else:
                self.print_error("No previous query")
            return True

        # /s - 切换流式输出
        elif cmd == 's':
            self.state.config['streaming'] = not self.state.config['streaming']
            status = "enabled" if self.state.config['streaming'] else "disabled"
            self.print_success(f"Streaming {status}")
            return True

        # /t - 切换显示思考过程
        elif cmd == 't':
            self.state.config['show_thoughts'] = not self.state.config['show_thoughts']
            status = "enabled" if self.state.config['show_thoughts'] else "disabled"
            self.print_success(f"Show thoughts {status}")
            return True

        # /c - 切换紧凑模式
        elif cmd == 'c':
            self.state.config['compact_mode'] = not self.state.config['compact_mode']
            status = "enabled" if self.state.config['compact_mode'] else "disabled"
            self.print_success(f"Compact mode {status}")
            return True

        # /save - 保存会话
        elif cmd.startswith('save '):
            filename = cmd[5:].strip()
            return await self.cmd_save(filename)

        # /load - 加载会话
        elif cmd.startswith('load '):
            filename = cmd[5:].strip()
            return await self.cmd_load_session(filename)

        else:
            self.print_error(f"Unknown quick command: /{cmd}")
            self.print_output("Quick commands: /r, /!, /s, /t, /c, /save <file>, /load <file>")
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

            # 基础命令
            console.print("[bold yellow]Basic Commands:[/bold yellow]")
            basic = [
                ("run <query>", "Execute a query (keeps context)"),
                ("chat", "Interactive chat mode"),
                ("help", "Show this help"),
                ("exit/quit", "Exit the shell"),
            ]
            for cmd, desc in basic:
                console.print(f"  {cmd:<30} {desc}")
            console.print()

            # 快捷命令
            console.print("[bold yellow]Quick Commands:[/bold yellow]")
            quick = [
                ("/r", "Repeat last query"),
                ("/!", "Show/edit last query"),
                ("/s", "Toggle streaming output"),
                ("/t", "Toggle show thoughts"),
                ("/c", "Toggle compact mode"),
                ("/save <file>", "Save session"),
                ("/load <file>", "Load session"),
            ]
            for cmd, desc in quick:
                console.print(f"  {cmd:<30} {desc}")
            console.print()

            # Graph 和模板
            console.print("[bold yellow]Graph & Templates:[/bold yellow]")
            graph = [
                ("graph <sub>", "Tool Graph commands"),
                ("load <file>", "Load a graph definition"),
                ("summarize <text>", "Summarize template"),
                ("explain <topic>", "Explain template"),
                ("code <task>", "Code template"),
            ]
            for cmd, desc in graph:
                console.print(f"  {cmd:<30} {desc}")
            console.print()

            # 状态和工具
            console.print("[bold yellow]Status & Tools:[/bold yellow]")
            status = [
                ("vars", "List all variables"),
                ("history [n]", "Show command history"),
                ("conversation [n]", "Show conversation history"),
                ("status", "Show session status"),
                ("clear", "Clear screen"),
                ("reset", "Reset agent and conversation"),
                ("eval <expr>", "Evaluate Python expression"),
                ("python", "Start Python REPL"),
            ]
            for cmd, desc in status:
                console.print(f"  {cmd:<30} {desc}")
            console.print()

            # 别名
            console.print("[bold yellow]Aliases:[/bold yellow]")
            for alias, full in self.state.aliases.items():
                console.print(f"  {alias:<10} -> {full}")
            console.print()

        else:
            print("\nAvailable Commands:")
            basic = [
                ("run <query>", "Execute a query"),
                ("chat", "Interactive chat mode"),
                ("help", "Show help"),
                ("exit/quit", "Exit"),
            ]
            for cmd, desc in basic:
                print(f"  {cmd:<30} {desc}")
            print("\nQuick commands: /r, /!, /s, /t, /c, /save, /load")
            print("\nType 'help' in Rich mode for full help")
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
            # 保存上一次查询
            self.state.last_query = query

            # 获取或创建持久 Agent 实例
            agent = self.state.get_or_create_agent()

            if console:
                console.print()
                console.print(f"[dim]Query: {query}[/dim]")
                console.print()

            # 记录用户输入
            self.state.add_conversation("user", query)

            # 构建会话上下文（传递对话历史）
            session_context = {
                "history": [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in self.state.conversation_history
                ],
                "session_id": "repl-session",
            }

            # 步骤回调 - 显示工具执行过程
            def step_callback(step):
                """显示推理和工具执行过程"""
                if step.get('thought'):
                    # 显示思考过程
                    thought = step['thought']
                    if console and not self.state.config['compact_mode']:
                        console.print(Panel(
                            thought[:300],  # 限制长度
                            title="[Thought]",
                            border_style="blue"
                        ))
                    else:
                        console.print(f"[blue][Thought] {thought[:100]}...[/blue]")

                if step.get('action'):
                    # 显示工具调用
                    action = step['action']
                    tool_name = action.get('tool_name', 'unknown')
                    params = action.get('params', {})

                    # 格式化参数
                    if params:
                        params_str = ", ".join([f"{k}={v}" for k, v in list(params.items())[:5]])
                        action_str = f"{tool_name}({params_str})"
                    else:
                        action_str = tool_name

                    if console:
                        console.print(Panel(
                            action_str,
                            title="[Action]",
                            border_style="yellow"
                        ))

                if step.get('observation'):
                    # 显示工具结果
                    obs = step['observation']
                    # 限制长度
                    if len(obs) > 500:
                        obs = obs[:500] + "..."

                    if console:
                        console.print(Panel(
                            obs,
                            title="[Observation]",
                            border_style="cyan"
                        ))

            # 进度回调 - 显示长时间运行的工具的进度
            def progress_callback(message: str):
                """显示工具执行进度"""
                if console:
                    # 使用 dim 颜色显示进度，不使用 Panel 以节省空间
                    # 用户可以设置环境变量 FASTREACT_SHOW_PROGRESS=1 来显示详细进度
                    import os
                    show_progress = os.getenv("FASTREACT_SHOW_PROGRESS", "1") == "1"
                    if show_progress:
                        console.print(f"[dim cyan]  {message}[/dim cyan]")
                else:
                    print(f"  {message}")

            # 设置进度回调到 agent（在两种模式下都设置）
            agent.set_progress_callback(progress_callback)

            # 流式输出模式
            if self.state.config['streaming']:
                from fastreact import StreamChunkType
                async for chunk in agent.run_streaming(query=query, enable_thinking=True, session_context=session_context):
                    if chunk.type == StreamChunkType.THINKING and self.state.config['show_thoughts']:
                        console.print(f"[dim blue][Thinking] {chunk.content[:100]}...[/dim blue]")
                    elif chunk.type == StreamChunkType.TOOL_CALL:
                        console.print(f"[yellow][Tool] {chunk.tool_name}[/yellow]")
                    elif chunk.type == StreamChunkType.ANSWER:
                        # 显示完整答案
                        if not self.state.config['compact_mode']:
                            console.print(Panel(
                                chunk.content,
                                title="Answer",
                                border_style="green"
                            ))
                        else:
                            console.print(f"[green]{chunk.content}[/green]")
                # 流式结束后获取最终结果
                result = {'answer': '(streaming complete)'}
            else:
                # 标准执行模式（传递会话上下文，使用步骤回调）
                result = await agent.run_async(
                    query=query,
                    session_context=session_context,
                    step_callback=step_callback
                )

                self.state.last_result = result

                # 紧凑模式或面板模式
                if self.state.config['compact_mode']:
                    console.print(f"[green]{result['answer']}[/green]")
                else:
                    console.print(Panel(
                        result['answer'],
                        title="Answer",
                        border_style="green"
                    ))

            # 记录助手回复
            self.state.add_conversation("assistant", result.get('answer', ''))

            if not self.state.config['compact_mode']:
                console.print(f"[dim]Conversation turns: {len(self.state.conversation_history)//2}[/dim]\n")

            # 自动保存会话
            if self.state.config['auto_save']:
                await self._auto_save_session()

            return True

        except Exception as e:
            self.print_error(str(e))
            import traceback
            traceback.print_exc()
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

            # 显示最近的对话（如果有）
            if self.state.conversation_history:
                console.print("\n[bold]Recent Conversation:[/bold]")
                for msg in self.state.conversation_history[-6:]:
                    role = msg['role'].title()
                    content = msg['content'][:100]
                    if len(msg['content']) > 100:
                        content += "..."
                    console.print(f"  [{role}]: {content}")
        else:
            self.print_output("\nSession Status:")
            for key, value in stats.items():
                print(f"  {key}: {value}")

        return True

    def cmd_conversation(self, args: str) -> bool:
        """显示对话历史"""
        if not self.state.conversation_history:
            self.print_output("No conversation yet")
            return True

        limit = int(args) if args.isdigit() else 20
        recent = self.state.conversation_history[-limit:]

        if console:
            from rich.table import Table
            table = Table(show_header=True)
            table.add_column("Role")
            table.add_column("Message")

            for msg in recent:
                role = msg['role'].upper()
                content = msg['content'][:200]
                table.add_row(role, content)

            console.print(table)
        else:
            self.print_output(f"\nLast {len(recent)} messages:")
            for msg in recent:
                role = msg['role'].upper()
                content = msg['content'][:100]
                print(f"  [{role}]: {content}")

        return True

    def cmd_reset(self, args: str) -> bool:
        """重置会话"""
        # 重置 Agent
        self.state.agent = None
        # 清空对话历史
        self.state.conversation_history.clear()
        # 清空变量
        self.state.variables.clear()

        self.print_success("Session reset - agent and conversation cleared")
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

    async def cmd_save(self, args: str) -> bool:
        """保存会话"""
        import json
        from pathlib import Path

        filename = args.strip() or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path(filename)

        if not filename.endswith('.json'):
            filepath = Path(f"{filename}.json")

        session_data = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "conversation": self.state.conversation_history,
            "variables": {k: str(v) for k, v in self.state.variables.items()},
            "stats": self.state.get_stats(),
            "config": self.state.config,
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            self.print_success(f"Session saved to: {filepath}")
        except Exception as e:
            self.print_error(f"Failed to save: {e}")

        return True

    async def cmd_load_session(self, args: str) -> bool:
        """加载会话"""
        import json
        from pathlib import Path

        filename = args.strip()
        if not filename:
            self.print_error("Usage: /load <filename>")
            return True

        filepath = Path(filename)
        if not filepath.exists():
            self.print_error(f"File not found: {filepath}")
            return True

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # 恢复对话历史
            self.state.conversation_history = session_data.get("conversation", [])

            # 恢复变量
            self.state.variables = session_data.get("variables", {})

            # 恢复配置
            self.state.config.update(session_data.get("config", {}))

            self.print_success(f"Session loaded from: {filepath}")
            self.print_output(f"  - {len(self.state.conversation_history)} messages")
            self.print_output(f"  - {len(self.state.variables)} variables")
            self.print_output(f"  - Saved: {session_data.get('timestamp', 'unknown')}")

            # 重建 Agent（如果有对话历史）
            if self.state.conversation_history and not self.state.agent:
                self.state.get_or_create_agent()

        except Exception as e:
            self.print_error(f"Failed to load: {e}")

        return True

    async def _auto_save_session(self):
        """自动保存会话（最新）"""
        try:
            from pathlib import Path
            save_dir = Path.home() / '.fastreact' / 'sessions'
            save_dir.mkdir(parents=True, exist_ok=True)

            filename = f"autosave_{datetime.now().strftime('%Y%m%d')}.json"
            filepath = save_dir / filename

            session_data = {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "conversation": self.state.conversation_history,
                "variables": {k: str(v) for k, v in self.state.variables.items()},
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # 静默失败，不影响主流程

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
