"""
CLI Adapter for FastReAct Nano

Provides command-line interface for the Nano kernel.
Install with: pip install fastreact-nano[cli]
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

try:
    import typer
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.syntax import Syntax

    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False

from fastreact import Agent, Config

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
║   Kernel: 2,847 lines | Tools: 4 | Skills: Markdown        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold blue")


@app.command()
def run(
    query: str = typer.Argument(..., help="要执行的任务或问题"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM模型"),
    skill: Optional[str] = typer.Option(None, "--skill", "-s", help="使用的Skill"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细信息"),
):
    """
    运行FastReAct Agent

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
    config = Config.from_env()
    if model:
        config.llm.model = model

    # Initialize agent
    if verbose:
        console.print(f"[info]模型: {config.llm.model}")
        console.print(f"[info]最大迭代: {config.react.max_iterations}")

    agent = Agent(config=config)

    # Run query
    try:
        skills = [skill] if skill else None

        console.print(f"\n[bold]Query:[/bold] {query}\n")

        response = asyncio.run(agent.run(query, skills=skills))

        # Display response
        console.print(Panel(response, title="[bold green]Response[/bold green]"))

    except KeyboardInterrupt:
        console.print("\n[yellow]中断[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"\n[red]错误: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def interactive():
    """
    启动交互式模式

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

            response = asyncio.run(agent.run(query))

            console.print(Panel(response, title="[bold green]Response[/bold green]"))
            console.print()

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
