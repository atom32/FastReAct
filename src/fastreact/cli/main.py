"""
FastReAct CLI - 命令行工具

提供便捷的命令行界面，让用户无需编程即可使用 FastReAct。

核心命令：
- init: 初始化工作区
- chat: 交互式对话
- run: 单次执行
- gateway: 启动 Gateway 服务器

使用示例：
    fastreact init
    fastreact chat
    fastreact run "What's the weather in Beijing?"
    fastreact gateway start --port 8765
"""

import sys
import asyncio
import os
from pathlib import Path
from typing import Optional

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import click

# 尝试导入 FastReAct
try:
    from fastreact import FastReAct
    from fastreact.bootstrap import init_workspace
except ImportError:
    click.echo("Error: FastReAct not installed. Run: pip install fastreact", err=True)
    sys.exit(1)


@click.group()
@click.version_option(version="1.0.0", prog_name="fastreact")
def cli():
    """
    FastReAct - 生产级 ReAct Agent 框架

    一个轻量级但功能完整的 ReAct 框架，支持工具调用、流式响应、多智能体协作。
    """
    pass


@cli.command()
@click.option(
    '--workspace',
    default=None,
    help='工作区路径（默认 ~/.fastreact）'
)
@click.option(
    '--overwrite',
    is_flag=True,
    default=False,
    help='覆盖已存在的文件'
)
def init(workspace: Optional[str], overwrite: bool):
    """
    初始化工作区

    创建 Bootstrap 配置文件，让你无需编程即可自定义 Agent 行为。

    示例:
        fastreact init
        fastreact init --workspace ./my-workspace
        fastreact init --overwrite
    """
    try:
        click.echo("[*] Initializing FastReAct workspace...")
        manager = init_workspace(workspace=workspace, overwrite=overwrite)

        click.echo(f"[OK] Workspace created: {manager.workspace}")
        click.echo()
        click.echo("Created files:")
        for filename in manager.list_files():
            click.echo(f"  - {filename}")

        click.echo()
        click.echo("Next steps:")
        click.echo(f"  1. Edit configuration: vim {manager.workspace}/SOUL.md")
        click.echo("  2. Start chatting: fastreact chat")
        click.echo("  3. Or run a query: fastreact run \"your question\"")

    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('query', required=False)
@click.option(
    '--model',
    default=None,
    help='LLM 模型（覆盖配置文件）'
)
@click.option(
    '--workspace',
    default=None,
    help='工作区路径'
)
@click.option(
    '--enable-bootstrap',
    is_flag=True,
    default=True,
    help='启用 Bootstrap 配置（默认启用）'
)
@click.option(
    '--show-thoughts',
    is_flag=True,
    default=False,
    help='显示推理过程'
)
@click.option(
    '--stream',
    is_flag=True,
    default=False,
    help='启用流式响应（实时输出思考过程和工具调用）'
)
def run(query: Optional[str], model: Optional[str], workspace: Optional[str],
        enable_bootstrap: bool, show_thoughts: bool, stream: bool):
    """
    运行单个查询

    执行一次性的 Agent 查询，获取工具验证的答案。

    示例:
        fastreact run "What's the weather in Beijing?"
        fastreact run "Calculate 15 * 25 + 10" --show-thoughts
        fastreact run "Write a FastAPI endpoint" --model gpt-4
    """
    if not query:
        click.echo("Error: Please provide a query", err=True)
        click.echo("Example: fastreact run \"What's the weather?\"", err=True)
        sys.exit(1)

    try:
        from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model

        # 加载配置
        config = load_config()

        # 获取 API Key（自动从配置文件或环境变量获取）
        try:
            api_key = get_api_key(config)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            click.echo("Please set FASTREACT_API_KEY environment variable or configure it in config.json", err=True)
            sys.exit(1)

        # 模型和 Base URL
        model = model or get_model(config)
        base_url = get_base_url(config)

        click.echo(f"[Agent] FastReAct ({model})")
        click.echo(f"Query: {query}")
        click.echo()

        # 创建 Agent
        agent = FastReAct(
            api_key=api_key,
            base_url=base_url,
            model=model,
            enable_bootstrap=enable_bootstrap,
            workspace=workspace
        )

        # 流式响应处理
        if stream:
            click.echo("[Streaming] Streaming response enabled...")
            click.echo()

            asyncio.run(_run_streaming_output(agent, query))
            return

        # 步骤回调
        def step_callback(step):
            if show_thoughts:
                if step.get('thought'):
                    click.echo(f"[Thought] {step['thought']}", dim=True)
                if step.get('action'):
                    click.echo(f"[Tool] {step['action']['tool_name']}({step['action'].get('params', {})})", dim=True)

        # 运行
        result = asyncio.run(agent.run_async(
            query=query,
            step_callback=step_callback if show_thoughts else None
        ))

        click.echo()
        click.echo("[Answer] Answer:")
        click.echo(result['answer'])
        click.echo()
        click.echo(f"[Stats] Stats: {result['stats']}")

    except Exception as e:
        click.echo(f"[ERROR] Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option(
    '--model',
    default=None,
    help='LLM 模型'
)
@click.option(
    '--workspace',
    default=None,
    help='工作区路径'
)
def chat(model: Optional[str], workspace: Optional[str]):
    """
    交互式对话

    启动交互式对话会话，连续与 Agent 对话。

    示例:
        fastreact chat
        fastreact chat --model gpt-4
    """
    try:
        from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model

        # 加载配置
        config = load_config()

        # 获取 API Key（自动从配置文件或环境变量获取）
        try:
            api_key = get_api_key(config)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            click.echo("Please set FASTREACT_API_KEY environment variable or configure it in config.json", err=True)
            sys.exit(1)

        # 模型和 Base URL
        model = model or get_model(config)
        base_url = get_base_url(config)

        click.echo(f"[Agent] FastReAct Chat ({model})")
        click.echo("Type 'quit' or 'exit' to end the conversation")
        click.echo()

        # 创建 Agent
        agent = FastReAct(
            api_key=api_key,
            base_url=base_url,
            model=model,
            enable_bootstrap=True,
            workspace=workspace
        )

        # 对话循环
        while True:
            try:
                query = click.prompt("You", type=str)

                if query.lower() in ['quit', 'exit', 'q']:
                    click.echo("[Bye] Goodbye!")
                    break

                if not query.strip():
                    continue

                click.echo()

                # 步骤回调
                def step_callback(step):
                    if step.get('thought'):
                        click.echo(f"[Thought] {step['thought']}", dim=True)
                    if step.get('action'):
                        tool_name = step['action']['tool_name']
                        params = step['action'].get('params', {})
                        click.echo(f"[Tool] {tool_name}({params})", dim=True)

                # 运行
                result = asyncio.run(agent.run_async(
                    query=query,
                    step_callback=step_callback
                ))

                click.echo()
                click.echo("[Answer] Agent:")
                click.echo(result['answer'])
                click.echo()
                click.echo(f"[Stats] {result['stats']['tool_calls']} tools, {result['stats']['iterations']} iterations")
                click.echo()

            except KeyboardInterrupt:
                click.echo("\n[Bye] Goodbye!")
                break
            except Exception as e:
                click.echo(f"[ERROR] Error: {e}", err=True)

    except Exception as e:
        click.echo(f"[ERROR] {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('action', type=click.Choice(['start', 'stop']))
@click.option(
    '--port',
    default=8765,
    type=int,
    help='Gateway 端口（默认 8765）'
)
@click.option(
    '--host',
    default='0.0.0.0',
    help='监听地址（默认 0.0.0.0）'
)
def gateway(action: str, port: int, host: str):
    """
    Gateway 服务器管理

    启动或停止 WebSocket Gateway 服务器。

    示例:
        fastreact gateway start
        fastreact gateway start --port 9000
        fastreact gateway start --host localhost --port 8765
    """
    if action == 'start':
        try:
            from fastreact.gateway.server import GatewayServer

            click.echo(f"[*] Starting FastReAct Gateway on {host}:{port}")
            click.echo()

            server = GatewayServer(host=host, port=port)
            server.run()

        except ImportError:
            click.echo("[ERROR] Gateway module not installed.", err=True)
            click.echo("Install: pip install fastreact[gateway]", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"[ERROR] Error: {e}", err=True)
            sys.exit(1)

    elif action == 'stop':
        click.echo("[WARNING]  Gateway stop not implemented yet", err=True)
        click.echo("Use Ctrl+C to stop the server", err=True)


@cli.command()
def version():
    """显示版本信息"""
    click.echo("FastReAct v1.0.0")
    click.echo()
    click.echo("Features:")
    click.echo("  [+] ReAct loop with transparent reasoning")
    click.echo("  [+] Tool calling and verification")
    click.echo("  [+] Bootstrap configuration system")
    click.echo("  [+] Multi-agent support")
    click.echo("  [+] WebSocket Gateway")
    click.echo()
    click.echo("Documentation: https://github.com/atom32/FastReAct")


async def _run_streaming_output(agent, query: str):
    """
    流式输出处理器（用于 --stream 模式）

    实时输出 <thinking>、工具调用和答案。
    """
    from fastreact.core.streaming import StreamChunkType

    try:
        async for chunk in agent.run_streaming(query=query, enable_thinking=True):
            if chunk.type == StreamChunkType.METADATA:
                if chunk.content == "start":
                    click.echo("[Start] Processing your query...", fg="green")
                elif chunk.content == "complete":
                    stats = chunk.metadata or {}
                    click.echo(f"[Complete] Done! (iterations: {stats.get('tool_calls', 0)}, cache_hits: {stats.get('cache_hits', 0)})", fg="green")

            elif chunk.type == StreamChunkType.THINKING:
                # 显示思考过程（灰色）
                click.echo(f"[Thinking] {chunk.content[:100]}...", dim=True)

            elif chunk.type == StreamChunkType.TOOL_CALL:
                # 显示工具调用（黄色）
                tool_info = f"{chunk.tool_name}({chunk.tool_params or ''})"
                click.echo(f"[Tool] {tool_info}", fg="yellow")

            elif chunk.type == StreamChunkType.TOOL_RESULT:
                # 显示工具结果（蓝色）
                result_preview = chunk.content[:100]
                click.echo(f"[Result] {chunk.tool_name}: {result_preview}...", fg="blue")

            elif chunk.type == StreamChunkType.ANSWER:
                # 显示答案（白色）
                click.echo(f"[Answer] {chunk.content}")

            elif chunk.type == StreamChunkType.ERROR:
                # 显示错误（红色）
                click.echo(f"[Error] {chunk.content}", fg="red")

    except KeyboardInterrupt:
        click.echo("\n[Interrupted] Stopping...", fg="yellow")
    except Exception as e:
        click.echo(f"[Error] Streaming failed: {e}", fg="red")


def main():
    """CLI 入口点"""
    cli()


if __name__ == '__main__':
    main()
