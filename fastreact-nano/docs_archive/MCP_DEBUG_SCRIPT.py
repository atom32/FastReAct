#!/usr/bin/env python3
"""调试 MCP 加载问题"""

import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastreact import Agent, Config

async def main():
    print("=" * 60)
    print("调试 MCP 加载")
    print("=" * 60)

    # Load config
    config = Config.from_env()

    # Create agent with multitenant enabled
    print("\n[1] 创建 Agent (multitenant=True)...")
    agent = Agent(config=config, multitenant=True)

    # Check initial state
    print(f"\n[2] 初始状态:")
    print(f"  _mcp_manager: {agent._mcp_manager}")
    print(f"  _tools: {type(agent._tools)}")

    # List initial tools
    print(f"\n[3] 初始工具列表:")
    tools = agent._tools.list()
    print(f"  总数: {len(tools)}")
    for tool in tools:
        print(f"  - {tool['name']}")

    # Trigger MCP loading
    print(f"\n[4] 加载 MCP 服务器...")
    await agent._load_mcp_servers()

    # Check after loading
    print(f"\n[5] 加载后状态:")
    print(f"  _mcp_manager: {type(agent._mcp_manager)}")

    # List tools after MCP load
    print(f"\n[6] 加载后工具列表:")
    tools = agent._tools.list()
    print(f"  总数: {len(tools)}")

    builtin_count = 0
    mcp_count = 0
    for tool in tools:
        if ":" in tool['name']:
            mcp_count += 1
            print(f"  [MCP] {tool['name']}: {tool.get('description', 'No desc')[:50]}")
        else:
            builtin_count += 1

    print(f"\n  系统工具: {builtin_count}")
    print(f"  MCP 工具: {mcp_count}")

    # Test Core access to tools
    print(f"\n[7] Core 工具访问:")
    print(f"  Core._tools: {type(agent._core._tools)}")
    core_tools = agent._core._tools.list()
    print(f"  Core 可见工具数: {len(core_tools)}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
