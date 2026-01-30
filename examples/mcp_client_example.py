"""
MCP Client 使用示例

演示如何使用 FastReAct 连接外部 MCP Servers 并使用它们的工具。
"""

import asyncio
import os
from pathlib import Path

from fastreact import FastReAct
from fastreact.tools import MCPClientManager


async def example_1_basic_filesystem():
    """示例 1: 基础文件系统操作"""
    print("=" * 60)
    print("示例 1: 基础文件系统操作")
    print("=" * 60)

    # 创建 MCP Manager
    mcp_manager = MCPClientManager()

    # 添加 filesystem 服务器（使用 examples 目录）
    examples_dir = Path(__file__).parent.absolute()
    mcp_manager.add_server("filesystem", {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            str(examples_dir)
        ]
    })

    try:
        # 连接服务器
        print("\n1. 连接到 MCP 服务器...")
        await mcp_manager.connect_all()

        # 获取工具
        print("2. 获取可用工具...")
        tools = await mcp_manager.get_all_tools()

        print(f"\n3. 成功加载 {len(tools)} 个工具:")
        for tool in tools[:5]:  # 只显示前 5 个
            print(f"   - {tool.name}: {tool.description[:60]}...")

        # 创建 FastReAct 引擎
        print("\n4. 创建 FastReAct 引擎...")
        engine = FastReAct(
            api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
            tools=tools,
            model="gpt-4o-mini",
        )

        # 执行任务
        print("\n5. 执行任务: 列出 examples 目录的文件")
        print("-" * 60)

        response = await engine.run(
            "请列出当前目录下的所有 Python 文件，"
            "并统计每个文件的行数"
        )

        print("\n6. 响应:")
        print(response)

    finally:
        # 清理连接
        print("\n7. 清理连接...")
        await mcp_manager.disconnect_all()


async def example_2_config_file():
    """示例 2: 从配置文件加载"""
    print("\n" + "=" * 60)
    print("示例 2: 从配置文件加载")
    print("=" * 60)

    # 检查配置文件
    config_path = Path(__file__).parent / "mcp_servers.json"

    if not config_path.exists():
        print(f"\n配置文件不存在: {config_path}")
        print("请先创建 mcp_servers.json 配置文件")
        return

    try:
        # 从配置文件加载
        print(f"\n1. 从配置文件加载: {config_path}")
        mcp_manager = MCPClientManager(str(config_path))

        print("2. 配置的服务器:")
        for server_name in mcp_manager.list_servers():
            print(f"   - {server_name}")

        print("\n3. 连接所有服务器...")
        results = await mcp_manager.connect_all()

        print("4. 连接结果:")
        for server_name, success in results.items():
            status = "✓ 成功" if success else "✗ 失败"
            print(f"   {server_name}: {status}")

        # 获取所有工具
        print("\n5. 获取所有可用工具...")
        tools = await mcp_manager.get_all_tools()
        print(f"   总共: {len(tools)} 个工具")

        # 按服务器分组显示
        from collections import defaultdict
        tools_by_server = defaultdict(list)

        for tool in tools:
            # 提取服务器名称（从工具包装器中）
            if hasattr(tool, '_connection'):
                server_name = tool._connection.name
            else:
                server_name = "unknown"
            tools_by_server[server_name].append(tool)

        print("\n6. 按服务器分组的工具:")
        for server_name, server_tools in tools_by_server.items():
            print(f"\n   [{server_name}] ({len(server_tools)} tools)")
            for tool in server_tools[:3]:  # 只显示前 3 个
                print(f"      - {tool.name}")

    finally:
        await mcp_manager.disconnect_all()


async def example_3_mixed_tools():
    """示例 3: 混合使用 MCP 和原生工具"""
    print("\n" + "=" * 60)
    print("示例 3: 混合使用 MCP 和原生工具")
    print("=" * 60)

    from fastreact.tools import create_calculator_tool

    try:
        # 创建 MCP Manager
        mcp_manager = MCPClientManager()

        # 添加 filesystem 服务器
        examples_dir = Path(__file__).parent.absolute()
        mcp_manager.add_server("filesystem", {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                str(examples_dir)
            ]
        })

        await mcp_manager.connect_all()

        # MCP 工具
        mcp_tools = await mcp_manager.get_all_tools()

        # 原生工具 (using functional approach)
        native_tools = [create_calculator_tool()]

        # 合并
        all_tools = native_tools + mcp_tools

        print(f"\n工具总数: {len(all_tools)}")
        print(f"  - 原生工具: {len(native_tools)}")
        print(f"  - MCP 工具: {len(mcp_tools)}")

        # 创建引擎
        engine = FastReAct(
            api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
            tools=all_tools,
            model="gpt-4o-mini",
        )

        print("\n执行任务...")
        print("-" * 60)

        response = await engine.run(
            "请读取当前目录的文件，"
            "然后计算一些数学表达式，"
            "最后将结果保存到新文件中"
        )

        print("\n响应:")
        print(response)

    finally:
        await mcp_manager.disconnect_all()


async def example_4_error_handling():
    """示例 4: 错误处理"""
    print("\n" + "=" * 60)
    print("示例 4: 错误处理")
    print("=" * 60)

    mcp_manager = MCPClientManager()

    # 添加一个不存在的服务器（会失败）
    mcp_manager.add_server("invalid-server", {
        "command": "invalid-command-that-does-not-exist",
        "args": []
    })

    # 添加一个有效的服务器
    examples_dir = Path(__file__).parent.absolute()
    mcp_manager.add_server("filesystem", {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            str(examples_dir)
        ]
    })

    try:
        print("\n1. 尝试连接所有服务器（包括无效的）...")
        results = await mcp_manager.connect_all()

        print("\n2. 连接结果:")
        success_count = 0
        for server_name, success in results.items():
            status = "✓ 成功" if success else "✗ 失败"
            print(f"   {server_name}: {status}")
            if success:
                success_count += 1

        print(f"\n3. 成功连接 {success_count}/{len(results)} 个服务器")

        # 即使部分失败，仍然可以使用成功的服务器
        if success_count > 0:
            print("\n4. 获取可用工具（跳过失败的服务器）...")
            tools = await mcp_manager.get_all_tools()
            print(f"   成功加载 {len(tools)} 个工具")

    finally:
        await mcp_manager.disconnect_all()


async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("FastReAct MCP Client 使用示例")
    print("=" * 60)

    examples = [
        ("基础文件系统操作", example_1_basic_filesystem),
        ("从配置文件加载", example_2_config_file),
        ("混合工具使用", example_3_mixed_tools),
        ("错误处理", example_4_error_handling),
    ]

    print("\n可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\n请选择要运行的示例 (1-4, 或 'all' 运行所有):")
    choice = input("> ").strip().lower()

    async def run_example(func):
        try:
            await func()
        except Exception as e:
            print(f"\n错误: {e}")
            import traceback
            traceback.print_exc()

    if choice == "all":
        for name, func in examples:
            try:
                await func()
            except Exception as e:
                print(f"\n示例 '{name}' 执行失败: {e}")
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        _, func = examples[int(choice) - 1]
        await run_example(func)
    else:
        print("无效的选择")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
