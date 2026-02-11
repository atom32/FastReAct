"""
CLI Adapter for FastReAct Nano

Provides command-line interface for the Nano kernel.
Install with: pip install fastreact-nano[cli]

This is a CONSUMER of the AgentEvent stream.
All UI rendering is driven by AgentEvent protocol.
"""

import asyncio
import sys
import uuid
from pathlib import Path
from typing import Optional

try:
    import typer
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.live import Live
    from rich.spinner import Spinner

    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False

from fastreact import Agent, Config, EventType

app = typer.Typer(
    name="fastreact",
    help="FastReAct Nano - 轻量级AI Agent",
    add_completion=False,
)

console = Console()


def print_banner():
    """Print welcome banner"""
    banner = r"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║        FastReAct Nano v2.0 - 轻量级 AI Agent               ║
║                                                               ║
║   Kernel: ~3000 lines | Tools: 4 | Event-Driven            ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold blue")


async def run_event_stream(agent: Agent, query: str, skills: Optional[list[str]] = None):
    """
    Run agent with event stream visualization

    This function subscribes to AgentEvent stream and renders each event
    using Rich UI components.

    Event → UI Mapping:
    - SESSION_START → Show session ID
    - THINK → Stream thinking content (cyan)
    - TOOL_CALL → Show tool call (yellow)
    - TOOL_RESULT → Show result preview (dim)
    - ERROR → Show error (red)
    - SESSION_END → Show completion (green)
    """
    session_id = str(uuid.uuid4())

    # Print query
    console.print(f"\n[bold blue]Query:[/bold blue] {query}")
    console.print(f"[dim]Session: {session_id}[/dim]\n")

    # Event counters
    event_counts = {}
    final_answer = None

    try:
        async for event in agent.run_event_stream(query, skills=skills, session_id=session_id):
            # Count events
            event_counts[event.type] = event_counts.get(event.type, 0) + 1

            # Render based on event type
            if event.type == EventType.SESSION_START:
                # Already printed above
                pass

            elif event.type == EventType.THINK:
                # Stream thinking content (no newline)
                console.print(f"[cyan]{event.content}[/]", end="")

            elif event.type == EventType.TOOL_CALL:
                # Show tool call with newline
                args_preview = str(event.tool_args)[:80] if event.tool_args else ""
                console.print(f"\n[yellow]→ {event.tool_name}[/yellow]")
                if args_preview:
                    console.print(f"[dim]   {args_preview}...[/dim]")

            elif event.type == EventType.TOOL_RESULT:
                # Show result preview (folded)
                lines = event.content.split("\n")
                if len(lines) > 3:
                    preview = "\n".join(lines[:3]) + f"\n... ({len(lines)} lines total)"
                else:
                    preview = event.content[:200]
                console.print(f"[dim]{preview}[/dim]")

            elif event.type == EventType.ERROR:
                console.print(f"\n[bold red]ERROR: {event.content}[/bold red]")

            elif event.type == EventType.SESSION_END:
                final_answer = event.content
                console.print(f"\n[bold green][DONE] Complete[/bold green]")

    except KeyboardInterrupt:
        console.print(f"\n[yellow] interrupted[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]ERROR: {e}[/bold red]")

    # Show final answer in panel
    if final_answer:
        console.print("\n")
        console.print(Panel(final_answer, title="[bold green]Answer[/bold green]", border_style="green"))

    # Show event summary if verbose
    if event_counts:
        console.print(f"\n[dim]Events: {', '.join(f'{k.value}:{v}' for k, v in event_counts.items())}[/dim]")


@app.command()
def run(
    query: str = typer.Argument(..., help="要执行的任务或问题"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM模型"),
    skill: Optional[str] = typer.Option(None, "--skill", "-s", help="使用的Skill"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
):
    """
    运行FastReAct Agent (事件流模式)

    示例:
        fastreact "分析这个代码库"
        fastreact "创建git分支" --skill git_workflow
        fastreact "读取README.md" -m gpt-4o
    """
    if not TYPER_AVAILABLE:
        console.print("[error]请先安装CLI依赖: pip install fastreact-nano[cli]")
        raise typer.Exit(1)

    print_banner()

    # Build config
    config = Config.load()  # Load from config file
    if model:
        config.llm.model = model

    # Initialize agent
    if verbose:
        console.print(f"[info]模型: {config.llm.model}")
        console.print(f"[info]最大迭代: {config.react.max_iterations}")

    agent = Agent(config=config)

    # Run with event stream
    skills = [skill] if skill else None
    asyncio.run(run_event_stream(agent, query, skills))


@app.command()
def interactive():
    """
    启动交互式模式 (事件流模式)

    示例:
        fastreact interactive
    """
    if not TYPER_AVAILABLE:
        console.print("[error]请先安装CLI依赖: pip install fastreact-nano[cli]")
        raise typer.Exit(1)

    print_banner()

    console.print("[info]启动交互模式 (输入 'quit' 退出)\n")

    agent = Agent()

    while True:
        try:
            query = console.input("[bold blue]>>> [/bold blue]")

            if not query.strip():
                continue

            if query.lower() in ["quit", "exit", "q"]:
                console.print("[yellow]再见![/yellow]")
                break

            # Run with event stream
            asyncio.run(run_event_stream(agent, query))

        except KeyboardInterrupt:
            console.print("\n[yellow]中断[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]错误: {e}[/red]\n")


@app.command()
def skills():
    """列出可用的Skills"""
    if not TYPER_AVAILABLE:
        console.print("[error]请先安装CLI依赖: pip install fastreact-nano[cli]")
        raise typer.Exit(1)

    from fastreact import SkillLoader

    loader = SkillLoader()
    available = loader.list_skills()

    console.print("\n[bold]可用的Skills:[/bold]\n")

    for skill_name in available:
        skill = loader.load_skill(skill_name)
        if skill:
            console.print(f"  • [cyan]{skill.name}[/cyan]: {skill.description}")

    console.print()


@app.command()
def tools():
    """列出可用的Tools"""
    if not TYPER_AVAILABLE:
        console.print("[error]请先安装CLI依赖: pip install fastreact-nano[cli]")
        raise typer.Exit(1)

    from fastreact import ReadFileTool, WriteFileTool, ExecTool, EditFileTool

    console.print("\n[bold]可用的Tools:[/bold]\n")
    console.print("  • [cyan]read_file[/cyan]: 读取文件内容")
    console.print("  • [cyan]write_file[/cyan]: 写入文件")
    console.print("  • [cyan]exec[/cyan]: 执行Shell命令")
    console.print("  • [cyan]edit_file[/cyan]: 编辑文件（文本替换）")
    console.print()


@app.command()
def version():
    """显示版本信息"""
    if not TYPER_AVAILABLE:
        console.print("[error]请先安装CLI依赖: pip install fastreact-nano[cli]")
        raise typer.Exit(1)

    from fastreact import __version__

    console.print(f"\nFastReAct Nano v{__version__}")
    console.print("内核 + 适配器架构\n")


def main():
    """Main entry point"""
    if not TYPER_AVAILABLE:
        print("错误: 请先安装CLI依赖")
        print("  pip install fastreact-nano[cli]")
        sys.exit(1)

    app()


if __name__ == "__main__":
    main()
