"""
Rich UI - 增强 CLI 交互体验

提供类似 Claude Code 的 Rich 界面组件：
- Panels: 面板显示
- Progress: 进度条
- Tables: 表格
- Syntax: 语法高亮
- Markdown: Markdown 渲染
- Spinners: 加载动画
"""

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text
from rich.tree import Tree
from rich.columns import Columns
from rich.align import Align
from rich import box
from typing import Optional, List, Dict, Any, Union
import time


# 创建全局 console 实例
console = Console()


# ============================================================================
# 面板组件
# ============================================================================

def info_panel(title: str, content: str, border_style: str = "blue") -> None:
    """显示信息面板"""
    console.print(Panel(content, title=title, border_style=border_style))


def success_panel(title: str, content: str) -> None:
    """显示成功面板"""
    console.print(Panel(content, title=title, border_style="green"))


def warning_panel(title: str, content: str) -> None:
    """显示警告面板"""
    console.print(Panel(content, title=title, border_style="yellow"))


def error_panel(title: str, content: str) -> None:
    """显示错误面板"""
    console.print(Panel(content, title=title, border_style="red"))


def code_panel(code: str, language: str = "python", title: Optional[str] = None) -> None:
    """显示代码面板"""
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    if title:
        console.print(Panel(syntax, title=title, border_style="cyan"))
    else:
        console.print(syntax)


def markdown_panel(content: str, title: Optional[str] = None) -> None:
    """显示 Markdown 面板"""
    md = Markdown(content)
    if title:
        console.print(Panel(md, title=title))
    else:
        console.print(md)


# ============================================================================
# 进度条组件
# ============================================================================

class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, description: str = "Processing"):
        self.description = description
        self.progress = None
        self.task_id = None

    def __enter__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        )
        self.task_id = self.progress.add_task(self.description, total=100)
        self.progress.__enter__()
        return self

    def __exit__(self, *args):
        self.progress.__exit__(*args)

    def update(self, advance: int, description: Optional[str] = None):
        """更新进度"""
        if self.progress and self.task_id is not None:
            kwargs = {"advance": advance}
            if description:
                kwargs["description"] = description
            self.progress.update(self.task_id, **kwargs)


def with_progress(description: str, total: int = 100):
    """进度条上下文管理器"""
    return ProgressTracker(description)


# ============================================================================
# 表格组件
# ============================================================================

def show_table(
    title: str,
    columns: List[str],
    rows: List[List[str]],
    title_style: str = "bold cyan"
) -> None:
    """显示表格"""
    table = Table(title=title, title_style=title_style, box=box.ROUNDED)
    for col in columns:
        table.add_column(col, style="dim")

    for row in rows:
        table.add_row(*row)

    console.print(table)


def show_dict_table(title: str, data: List[Dict[str, Any]]) -> None:
    """从字典列表显示表格"""
    if not data:
        console.print(f"[yellow]No data for {title}[/yellow]")
        return

    # 获取所有列
    columns = list(data[0].keys())

    # 创建表格
    table = Table(title=title, title_style="bold cyan", box=box.ROUNDED)
    for col in columns:
        table.add_column(col.replace("_", " ").title(), style="dim")

    # 添加行
    for item in data:
        row = [str(item.get(col, "")) for col in columns]
        table.add_row(*row)

    console.print(table)


# ============================================================================
# 树形组件
# ============================================================================

def show_tree(title: str, data: Dict[str, Any]) -> None:
    """显示树形结构"""
    tree = Tree(f"[bold cyan]{title}[/bold cyan]")

    def add_node(parent, key, value):
        if isinstance(value, dict):
            branch = parent.add(f"[bold]{key}[/bold]")
            for k, v in value.items():
                add_node(branch, k, v)
        elif isinstance(value, list):
            branch = parent.add(f"[bold]{key}[/bold]")
            for i, item in enumerate(value):
                add_node(branch, f"[{i}]", item)
        else:
            parent.add(f"[dim]{key}:[/dim] {value}")

    for key, value in data.items():
        add_node(tree, key, value)

    console.print(tree)


# ============================================================================
# Live 组件（实时更新）
# ============================================================================

class LiveDisplay:
    """实时显示组件"""

    def __init__(self, refresh_per_second: int = 4):
        self.live = Live(console=console, refresh_per_second=refresh_per_second)
        self.content = Text()

    def __enter__(self):
        self.live.__enter__()
        return self

    def __exit__(self, *args):
        self.live.__exit__(*args)

    def update(self, text: str, style: Optional[str] = None) -> None:
        """更新显示内容"""
        if style:
            self.content = Text(text, style=style)
        else:
            self.content = Text(text)
        self.live.update(self.content)

    def update_panel(self, content: str, title: str = "") -> None:
        """更新面板内容"""
        self.live.update(Panel(content, title=title))


# ============================================================================
# 状态指示器
# ============================================================================

def print_status(status: str, message: str, icon: bool = True) -> None:
    """打印状态信息"""
    # Use ASCII-safe icons for Windows
    icons = {
        "running": "[*]",
        "done": "[OK]",
        "error": "[ERROR]",
        "warning": "[WARNING]",
        "info": "[INFO]",
        "success": "[SUCCESS]",
    }

    colors = {
        "running": "yellow",
        "done": "green",
        "error": "red",
        "warning": "yellow",
        "info": "blue",
        "success": "green",
    }

    color = colors.get(status.lower(), "white")
    icon_str = icons.get(status.lower(), "") if icon else ""
    status_text = f"[{color}]{icon_str}[/{color}]"

    console.print(f"{status_text} {message}")


# ============================================================================
# Agent 执行显示组件
# ============================================================================

class AgentExecutor:
    """Agent 执行器 - 显示执行过程"""

    def __init__(self):
        self.steps = []
        self.current_step = None

    def start(self, query: str) -> None:
        """开始执行"""
        console.print()
        console.print(Panel(
            f"[bold cyan]Query:[/bold cyan] {query}",
            title=">> FastReAct",
            border_style="cyan"
        ))
        console.print()

    def add_thought(self, thought: str) -> None:
        """添加思考过程"""
        console.print(Panel(
            Text(thought, style="dim"),
            title="[Thought]",
            border_style="blue"
        ))

    def add_action(self, tool_name: str, params: Dict[str, Any]) -> None:
        """添加工具调用"""
        params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        console.print(f"[yellow] > Tool:[/yellow] [bold]{tool_name}[/bold]({params_str})")

    def add_observation(self, result: str) -> None:
        """添加观察结果"""
        # 截断长结果
        if len(result) > 200:
            result = result[:200] + "..."
        console.print(f"[blue] > Result:[/blue] {result}")

    def finish(self, answer: str, stats: Dict[str, Any]) -> None:
        """完成执行"""
        console.print()
        console.print(Panel(
            Text(answer, style="white"),
            title="[Answer]",
            border_style="green"
        ))
        console.print()

        # 显示统计
        stats_table = Table(show_header=False, box=box.SIMPLE)
        stats_table.add_column("Metric", style="dim")
        stats_table.add_column("Value")

        for key, value in stats.items():
            stats_table.add_row(
                Text(key.replace("_", " ").title() + ":"),
                str(value)
            )

        console.print(stats_table)


# ============================================================================
# Tool Graph 执行显示组件
# ============================================================================

class GraphExecutor:
    """图执行器 - 显示图执行过程"""

    def __init__(self):
        self.console = Console()

    def start(self, graph_name: str, node_count: int) -> None:
        """开始执行"""
        self.console.print()
        self.console.print(Panel(
            f"[bold]Graph:[/bold] {graph_name}\n[dim]Nodes:[/dim] {node_count}",
            title=">> Tool Graph Execution",
            border_style="cyan"
        ))
        self.console.print()

    def node_start(self, node_id: str, inputs: Dict[str, Any]) -> None:
        """节点开始"""
        self.console.print(f"[yellow] >[/yellow] [bold cyan]{node_id}[/bold cyan]", end=" ")
        if inputs:
            inputs_str = ", ".join([f"{k}={v}" for k, v in list(inputs.items())[:3]])
            self.console.print(f"[dim]({inputs_str})[/dim]", end="")
        self.console.print()

    def node_complete(self, node_id: str, outputs: Dict[str, Any]) -> None:
        """节点完成"""
        output_keys = list(outputs.keys())[:3]
        outputs_str = ", ".join(output_keys)
        if len(outputs) > 3:
            outputs_str += f" +{len(outputs)-3} more"
        self.console.print(f"[green] [OK][/green] [dim]{node_id} → {outputs_str}[/dim]")

    def node_error(self, node_id: str, error: str) -> None:
        """节点错误"""
        self.console.print(f"[red] [ERROR][/red] [bold red]{node_id}[/bold red]: {error}")

    def finish(self, report: Any) -> None:
        """完成执行"""
        self.console.print()
        status = "[OK] Success" if report.success else "[ERROR] Failed"
        status_color = "green" if report.success else "red"

        summary = (
            f"[{status_color}]{status}[/{status_color}]\n"
            f"[dim]Completed:[/dim] {report.completed_nodes}/{report.total_nodes}\n"
            f"[dim]Time:[/dim] {report.execution_time:.2f}s"
        )

        self.console.print(Panel(
            summary,
            title=">> Execution Summary",
            border_style=status_color
        ))


# ============================================================================
# 快捷函数
# ============================================================================

def print_header(text: str) -> None:
    """打印标题"""
    console.print()
    console.print(Panel(
        f"[bold cyan]{text}[/bold cyan]",
        border_style="cyan"
    ))


def print_subheader(text: str) -> None:
    """打印子标题"""
    console.print(f"\n[bold white]▸ {text}[/bold white]\n")


def print_key_value(key: str, value: Any, key_style: str = "cyan") -> None:
    """打印键值对"""
    console.print(f"[{key_style}]{key}:[/{key_style}] {value}")


def print_list(items: List[str], title: Optional[str] = None) -> None:
    """打印列表"""
    if title:
        console.print(f"\n[bold]{title}[/bold]")
    for item in items:
        console.print(f"  • {item}")


def print_separator(char: str = "─") -> None:
    """打印分隔线"""
    console.print(char * console.width)


def clear() -> None:
    """清屏"""
    console.clear()


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "console",
    # Panels
    "info_panel",
    "success_panel",
    "warning_panel",
    "error_panel",
    "code_panel",
    "markdown_panel",
    # Progress
    "ProgressTracker",
    "with_progress",
    # Tables
    "show_table",
    "show_dict_table",
    # Tree
    "show_tree",
    # Live
    "LiveDisplay",
    # Status
    "print_status",
    # Executors
    "AgentExecutor",
    "GraphExecutor",
    # Shortcuts
    "print_header",
    "print_subheader",
    "print_key_value",
    "print_list",
    "print_separator",
    "clear",
]
