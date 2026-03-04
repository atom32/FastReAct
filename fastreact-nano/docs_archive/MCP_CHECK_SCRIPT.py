#!/usr/bin/env python3
"""检查 Agent 是否加载了 MCP 服务器"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastreact import Agent, Config
import json

print("=" * 60)
print("检查 MCP 和 Skills 加载状态")
print("=" * 60)

# Load config
config = Config.from_env()

# Create agent
print("\n[INFO] 创建 Agent...")
agent = Agent(config=config)

# Check MCP manager
print("\n=== MCP 服务器状态 ===")
if hasattr(agent, '_mcp_manager'):
    mcp_manager = agent._mcp_manager
    print(f"MCP Manager 类型: {type(mcp_manager)}")

    # Check loaded servers
    if hasattr(mcp_manager, '_servers'):
        print(f"已加载的服务器: {list(mcp_manager._servers.keys())}")

    # List available tools
    try:
        tools = mcp_manager.list_tools()
        print(f"\n可用的 MCP 工具数量: {len(tools)}")
        print("\nMCP 工具列表:")
        for tool in tools[:20]:  # 只显示前20个
            print(f"  - {tool.name}: {tool.description[:60]}...")
    except Exception as e:
        print(f"获取工具列表失败: {e}")
else:
    print("❌ Agent 没有 _mcp_manager 属性")

# Check skills
print("\n=== Skills 状态 ===")
if hasattr(agent, '_skill_manager'):
    skill_manager = agent._skill_manager
    print(f"Skill Manager 类型: {type(skill_manager)}")

    try:
        skills = skill_manager.list_skills()
        print(f"已加载的 Skills 数量: {len(skills)}")
        print("\nSkills 列表:")
        for skill_name, skill_info in skills.items():
            print(f"  - {skill_name}: {skill_info.get('description', 'No description')}")
    except Exception as e:
        print(f"获取 Skills 列表失败: {e}")
else:
    print("❌ Agent 没有 _skill_manager 属性")

print("\n=== 工具列表 ===")
all_tools = agent.list_tools()
print(f"总工具数量: {len(all_tools)}")
print("\n核心工具:")
for tool in all_tools[:5]:
    print(f"  - {tool['name']}: {tool.get('description', 'No desc')}")

print("\nMCP 工具:")
mcp_tools = [t for t in all_tools if ':' in t['name']]
for tool in mcp_tools[:10]:
    print(f"  - {tool['name']}: {tool.get('description', 'No desc')}")

print("\n" + "=" * 60)
