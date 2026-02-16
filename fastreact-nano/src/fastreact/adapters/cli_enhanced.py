"""
FastReAct Nano - Enhanced CLI Adapter

Features:
- Multi-turn conversation with context
- Command history (up/down arrows)
- Special commands: /history, /clear, /export
- Better event visualization
"""

import asyncio
import sys
import uuid
from pathlib import Path
from typing import Optional, List

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.live import Live
    from rich import box

    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False

from fastreact import Agent, Config, EventType

console = Console()


class ConversationHistory:
    """Store conversation history"""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.messages: List[dict] = []
        self.events: List[dict] = []

    def add_message(self, role: str, content: str):
        """Add a message to history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": asyncio.get_event_loop().time(),
        })

        # Trim if too long
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

    def add_event(self, event_type: str, content: str, metadata: dict = None):
        """Add an event to history"""
        self.events.append({
            "type": event_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": asyncio.get_event_loop().time(),
        })

    def get_history(self) -> List[dict]:
        """Get message history for LLM"""
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]

    def clear(self):
        """Clear history"""
        self.messages = []
        self.events = []


async def interactive_mode():
    """Enhanced interactive mode with context and history"""

    print_banner()

    # Initialize
    config = Config.load()
    agent = Agent(config=config)
    history = ConversationHistory()
    session_id = str(uuid.uuid4())

    console.print("\n[dim]提示: 输入 /help 查看可用命令[/dim]\n")

    while True:
        try:
            # Get user input
            query = console.input("[bold blue]>>>[/bold blue] ").strip()

            if not query:
                continue

            # Handle special commands
            if query.startswith("/"):
                await handle_command(query, history, agent, session_id)
                continue

            if query.lower() in ("quit", "exit", "q"):
                console.print("\n[yellow]再见！[/yellow]")
                break

            # Run agent with history
            console.print("")

            final_answer = None
            event_summary = {}

            async for event in agent.run_event_stream(
                query,
                session_id=session_id,
                history=history.get_history(),
            ):
                # Track events for summary
                event_summary[event.type.value] = event_summary.get(event.type.value, 0) + 1

                # Render events
                if event.type == EventType.SESSION_START:
                    pass  # Already printed

                elif event.type == EventType.THINK:
                    # Show thinking (collapsed)
                    pass

                elif event.type == EventType.TOOL_CALL:
                    console.print(f"[yellow]→ {event.tool_name}[/yellow] [dim]{str(event.tool_args)[:60]}...[/dim]")

                elif event.type == EventType.TOOL_RESULT:
                    lines = event.content.split("\n")
                    if len(lines) > 5:
                        preview = "\n".join(lines[:5]) + f"\n[dim]... ({len(lines)} lines total)[/dim]"
                    else:
                        preview = event.content[:300]
                    console.print(f"[dim]{preview}[/dim]\n")

                elif event.type == EventType.ERROR:
                    console.print(f"[bold red]ERROR: {event.content}[/bold red]")

                elif event.type == EventType.SESSION_END:
                    final_answer = event.content

            # Add to history
            history.add_message("user", query)
            if final_answer:
                history.add_message("assistant", final_answer)

            # Show final answer
            if final_answer:
                console.print(Panel(
                    final_answer,
                    title="[bold green]回答[/bold green]",
                    border_style="green",
                    padding=(1, 1),
                ))

            # Show event summary
            console.print(f"[dim]事件: {', '.join(f'{k}:{v}' for k, v in event_summary.items())}[/dim]\n")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]使用 /quit 或 quit 来退出[/yellow]")
        except Exception as e:
            console.print(f"\n[bold red]错误: {e}[/bold red]")


async def handle_command(command: str, history: ConversationHistory, agent: Agent, session_id: str):
    """Handle special commands"""

    parts = command.split()
    cmd = parts[0].lower()

    if cmd == "/help":
        show_help()

    elif cmd == "/history":
        show_history(history)

    elif cmd == "/clear":
        history.clear()
        console.print("[green]历史记录已清除[/green]")

    elif cmd == "/export":
        export_history(history, parts[1] if len(parts) > 1 else None)

    elif cmd == "/stats":
        show_stats(history, agent, session_id)

    else:
        console.print(f"[red]未知命令: {cmd}[/red]")
        console.print("使用 /help 查看可用命令")


def show_help():
    """Show help message"""
    help_text = """
可用命令:

  /help      - 显示此帮助信息
  /history   - 显示对话历史
  /clear     - 清除对话历史
  /export    - 导出对话历史到文件
  /stats     - 显示统计信息
  /quit      - 退出程序
"""
    console.print(Panel(help_text, title="[bold]帮助[/bold]", border_style="blue"))


def show_history(history: ConversationHistory):
    """Show conversation history"""

    if not history.messages:
        console.print("[dim]暂无对话历史[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("序号", style="dim", width=6)
    table.add_column("角色", style="cyan", width=12)
    table.add_column("内容", style="white")

    for i, msg in enumerate(history.messages, 1):
        role = "用户" if msg["role"] == "user" else "助手"
        content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
        table.add_row(str(i), role, content)

    console.print("\n[bold]对话历史:[/bold]\n")
    console.print(table)


def export_history(history: ConversationHistory, filename: Optional[str] = None):
    """Export conversation history to file"""

    if not history.messages:
        console.print("[dim]暂无对话历史可导出[/dim]")
        return

    if filename is None:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conversation_{timestamp}.md"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# FastReAct Nano 对话记录\n\n")
            f.write(f"导出时间: {timestamp}\n\n")
            f.write("---\n\n")

            for msg in history.messages:
                role = "用户" if msg["role"] == "user" else "助手"
                f.write(f"## {role}\n\n")
                f.write(f"{msg['content']}\n\n")
                f.write("---\n\n")

        console.print(f"[green]对话历史已导出到: {filename}[/green]")
    except Exception as e:
        console.print(f"[red]导出失败: {e}[/red]")


def show_stats(history: ConversationHistory, agent: Agent, session_id: str):
    """Show statistics"""

    console.print("\n[bold]统计信息:[/bold]\n")
    console.print(f"  对话轮数: {len([m for m in history.messages if m['role'] == 'user'])}")
    console.print(f"  总消息数: {len(history.messages)}")
    console.print(f"  总事件数: {len(history.events)}")
    console.print(f"  Session ID: {session_id}")
    console.print("")


def print_banner():
    """Print welcome banner"""
    banner = r"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        FastReAct Nano v2.1 - 增强交互模式                     ║
║                                                               ║
║   ✓ 多轮对话  ✓ 历史记录  ✓ 导出功能                         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold blue")


if __name__ == "__main__":
    if not TYPER_AVAILABLE:
        print("[ERROR] 请安装 CLI 依赖: pip install fastreact-nano[cli]")
        sys.exit(1)

    asyncio.run(interactive_mode())
