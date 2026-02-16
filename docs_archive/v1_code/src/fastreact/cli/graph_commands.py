"""
Tool Graph CLI Commands - 工具图命令行接口

提供创建、执行、调试工具图的命令行工具。
"""

import sys
import json
import asyncio
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

import click

# Rich UI components
try:
    from .rich_ui import (
        console, print_header, print_status, print_list,
        GraphExecutor, info_panel, success_panel,
        error_panel, show_dict_table
    )
except ImportError:
    # Fallback to basic output
    console = None
    def print_status(*args, **kwargs):
        pass
    def print_header(*args, **kwargs):
        pass
    def print_list(*args, **kwargs):
        pass


def load_graph_definition(file_path: str) -> Dict[str, Any]:
    """
    加载图定义文件

    支持 JSON 和 YAML 格式。
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Graph file not found: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        if path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif path.suffix == '.json':
            return json.load(f)
        else:
            # Try JSON first, then YAML
            content = f.read()
            f.seek(0)
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return yaml.safe_load(content)


async def execute_graph_async(
    graph_def: Dict[str, Any],
    inputs: Dict[str, Any],
    debug: bool = False,
    breakpoints: Optional[list] = None
):
    """异步执行图"""
    from fastreact.graph import (
        create_graph,
        create_tool_node,
        execute_graph,
        create_debugger,
        debug_graph,
    )

    # 创建图
    graph = create_graph(graph_def.get('name', 'unnamed'))

    # 创建节点
    nodes = {}
    for node_def in graph_def.get('nodes', []):
        # 这里简化处理，实际需要从工具注册表获取工具函数
        # 暂时跳过节点创建
        pass

    # 连接节点
    for edge in graph_def.get('edges', []):
        graph.connect(edge['from'], edge['to'])

    # 执行
    if debug:
        debugger = create_debugger()
        if breakpoints:
            for bp in breakpoints:
                debugger.add_breakpoint(bp)
        return await debug_graph(graph, inputs, breakpoints)
    else:
        return await execute_graph(graph, inputs)


@click.group()
def graph():
    """Tool Graph 工具图命令"""
    pass


@graph.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option(
    '--inputs',
    '-i',
    help='输入参数 (JSON 格式)',
    default='{}'
)
@click.option(
    '--debug',
    '-d',
    is_flag=True,
    help='启用调试模式'
)
@click.option(
    '--breakpoint',
    '-b',
    multiple=True,
    help='添加断点（可多次指定）'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    help='保存输出到文件'
)
def run(file_path: str, inputs: str, debug: bool, breakpoint: tuple, output: Optional[str]):
    """
    执行工具图

    示例:
        fastreact graph run workflow.json
        fastreact graph run workflow.json -i '{"query": "test"}'
        fastreact graph run workflow.json --debug -b node1 -b node2
    """
    try:
        # 加载图定义
        if console:
            print_status("running", f"Loading graph from {file_path}...")
        else:
            click.echo(f"[*] Loading graph from {file_path}...")

        graph_def = load_graph_definition(file_path)

        node_count = len(graph_def.get('nodes', []))
        edge_count = len(graph_def.get('edges', []))

        if console:
            console.print(f"[green]✓[/green] Graph: [bold cyan]{graph_def.get('name', 'unnamed')}[/bold cyan]")
            console.print(f"  Nodes: {node_count}, Edges: {edge_count}")
            console.print()
        else:
            click.echo(f"[OK] Graph: {graph_def.get('name', 'unnamed')}")
            click.echo(f"    Nodes: {node_count}")
            click.echo(f"    Edges: {edge_count}")
            click.echo()

        # 解析输入
        try:
            inputs_data = json.loads(inputs) if inputs else {}
        except json.JSONDecodeError as e:
            if console:
                error_panel("Invalid Inputs", str(e))
            else:
                click.echo(f"[ERROR] Invalid JSON inputs: {e}", err=True)
            sys.exit(1)

        # 执行图
        if console:
            executor = GraphExecutor()
            executor.start(graph_def.get('name', 'unnamed'), node_count)
        else:
            click.echo("[*] Executing graph...")

        result = asyncio.run(execute_graph_async(
            graph_def,
            inputs_data,
            debug=debug,
            breakpoints=list(breakpoint) if breakpoint else None
        ))

        # 显示结果
        if console:
            executor.finish(result)
        else:
            click.echo()
            click.echo("[Result] Execution Result:")
            if isinstance(result, dict):
                click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                click.echo(str(result))

        # 保存到文件
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                if isinstance(result, dict):
                    json.dump(result, f, indent=2, ensure_ascii=False)
                else:
                    f.write(str(result))
            if console:
                print_status("done", f"Saved to: {output}")
            else:
                click.echo()
                click.echo(f"[OK] Saved to: {output}")

    except Exception as e:
        if console:
            error_panel("Execution Error", str(e))
        else:
            click.echo(f"[ERROR] {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@graph.command()
@click.argument('file_path', type=click.Path(exists=True))
def validate(file_path: str):
    """
    验证图定义

    检查图定义文件的语法和结构是否正确。

    示例:
        fastreact graph validate workflow.json
    """
    try:
        if console:
            print_status("running", f"Validating {file_path}...")
        else:
            click.echo(f"[*] Validating {file_path}...")

        graph_def = load_graph_definition(file_path)

        # 基本验证
        errors = []

        if 'name' not in graph_def:
            errors.append("Missing 'name' field")

        if 'nodes' not in graph_def:
            errors.append("Missing 'nodes' field")
        elif not isinstance(graph_def['nodes'], list):
            errors.append("'nodes' must be a list")

        if 'edges' not in graph_def:
            errors.append("Missing 'edges' field")
        elif not isinstance(graph_def['edges'], list):
            errors.append("'edges' must be a list")

        # 验证节点
        node_ids = set()
        for i, node in enumerate(graph_def.get('nodes', [])):
            if 'id' not in node:
                errors.append(f"Node {i}: Missing 'id'")
            else:
                node_ids.add(node['id'])

        # 验证边
        edge_ids = set()
        for i, edge in enumerate(graph_def.get('edges', [])):
            if 'from' not in edge or 'to' not in edge:
                errors.append(f"Edge {i}: Missing 'from' or 'to'")
            else:
                from_node = edge['from']
                to_node = edge['to']
                if from_node not in node_ids:
                    errors.append(f"Edge {i}: Unknown node '{from_node}' in 'from'")
                if to_node not in node_ids:
                    errors.append(f"Edge {i}: Unknown node '{to_node}' in 'to'")
                edge_ids.add((from_node, to_node))

        # 显示结果
        if errors:
            if console:
                error_panel("Validation Failed", "\n".join([f"• {e}" for e in errors]))
            else:
                click.echo("[FAIL] Validation failed:", err=True)
                for error in errors:
                    click.echo(f"  - {error}", err=True)
            sys.exit(1)
        else:
            if console:
                success_panel(
                    "Validation Passed",
                    f"✓ All checks passed\n\nNodes: {len(node_ids)}\nEdges: {len(edge_ids)}"
                )
            else:
                click.echo("[OK] Validation passed!")
                click.echo(f"  - {len(node_ids)} nodes")
                click.echo(f"  - {len(edge_ids)} edges")

    except Exception as e:
        if console:
            error_panel("Validation Error", str(e))
        else:
            click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)


@graph.command()
@click.argument('name')
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    default='workflow.json',
    help='输出文件路径'
)
def init(name: str, output: str):
    """
    创建图定义模板

    创建一个新的图定义文件模板。

    示例:
        fastreact graph init my_workflow
        fastreact graph init my_workflow -o workflows/my.json
    """
    template = {
        "name": name,
        "description": f"Tool Graph: {name}",
        "nodes": [
            {
                "id": "node1",
                "type": "tool",
                "tool": "tool_name",
                "inputs": {}
            },
            {
                "id": "node2",
                "type": "tool",
                "tool": "tool_name",
                "inputs": {}
            }
        ],
        "edges": [
            {
                "from": "node1",
                "to": "node2"
            }
        ]
    }

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    if console:
        success_panel(
            "Template Created",
            f"File: {output}\n\nNext steps:\n"
            f"1. Edit: [cyan]vim {output}[/cyan]\n"
            f"2. Validate: [cyan]fastreact graph validate {output}[/cyan]\n"
            f"3. Run: [cyan]fastreact graph run {output}[/cyan]"
        )
    else:
        click.echo(f"[OK] Created template: {output}")
        click.echo()
        click.echo("Next steps:")
        click.echo(f"  1. Edit the template: vim {output}")
        click.echo(f"  2. Validate: fastreact graph validate {output}")
        click.echo(f"  3. Run: fastreact graph run {output}")


@graph.command()
def list():
    """列出可用的工具图"""
    # 查找当前目录下的图定义文件
    current_dir = Path.cwd()

    graph_files = []
    for ext in ['*.json', '*.yaml', '*.yml']:
        graph_files.extend(current_dir.glob(ext))

    if not graph_files:
        if console:
            info_panel(
                "No Graph Files Found",
                "Create one with: [cyan]fastreact graph init my_workflow[/cyan]"
            )
        else:
            click.echo("[INFO] No graph files found in current directory")
            click.echo()
            click.echo("Create one with:")
            click.echo("  fastreact graph init my_workflow")
        return

    # 收集图信息
    graphs_info = []
    for f in graph_files:
        try:
            graph_def = load_graph_definition(str(f))
            graphs_info.append({
                "file": f.name,
                "name": graph_def.get('name', 'unnamed'),
                "nodes": len(graph_def.get('nodes', [])),
                "edges": len(graph_def.get('edges', [])),
            })
        except Exception as e:
            graphs_info.append({
                "file": f.name,
                "name": "Error",
                "nodes": 0,
                "edges": 0,
                "error": str(e),
            })

    # 显示
    if console:
        show_dict_table("Tool Graphs", graphs_info)
    else:
        click.echo(f"Found {len(graph_files)} graph file(s):")
        click.echo()
        for info in graphs_info:
            click.echo(f"  {info['file']}")
            click.echo(f"    Name: {info['name']}")
            click.echo(f"    Nodes: {info['nodes']}")
            click.echo()


@graph.command()
@click.argument('file_path', type=click.Path(exists=True))
def export(file_path: str):
    """
    导出图定义

    将图定义导出为可读的格式。

    示例:
        fastreact graph export workflow.json
    """
    try:
        graph_def = load_graph_definition(file_path)

        click.echo(f"# Graph: {graph_def.get('name', 'unnamed')}")
        click.echo(f"# Description: {graph_def.get('description', 'N/A')}")
        click.echo()

        # 显示节点
        nodes = graph_def.get('nodes', [])
        if nodes:
            click.echo("## Nodes:")
            for node in nodes:
                click.echo(f"  - {node['id']}: {node.get('tool', 'N/A')}")

        # 显示边
        edges = graph_def.get('edges', [])
        if edges:
            click.echo()
            click.echo("## Edges:")
            for edge in edges:
                click.echo(f"  - {edge['from']} -> {edge['to']}")

        # 显示完整 JSON
        click.echo()
        click.echo("## Full Definition (JSON):")
        click.echo(json.dumps(graph_def, indent=2, ensure_ascii=False))

    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)


def register_graph_commands(cli_group):
    """注册图命令到 CLI 组"""
    cli_group.add_command(graph)
