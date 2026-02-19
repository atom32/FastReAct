#!/usr/bin/env python3
"""
诊断 Gateway 问题
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact import Agent
from fastreact.core.config import Config


async def diagnose():
    print("=" * 60)
    print("FastReAct Agent 诊断")
    print("=" * 60)

    # 1. 加载配置
    print("\n[1] 加载配置...")
    try:
        config = Config.load()
        print(f"✓ 配置加载成功")
        print(f"  - Model: {config.llm.model}")
        print(f"  - API Base: {config.llm.api_base}")
        print(f"  - API Key: {config.llm.api_key[:10]}...{config.llm.api_key[-4:] if config.llm.api_key else 'None'}")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

    # 2. 检查 API key
    print("\n[2] 检查 API Key...")
    if not config.llm.api_key or config.llm.api_key in ["sk-xxx", "sk-test", "", "None"]:
        print(f"❌ API Key 无效: {config.llm.api_key}")
        print(f"\n请设置真实的 API Key:")
        print(f"  export FASTRACT_API_KEY=sk-your-real-api-key")
        print(f"  或编辑 ~/.fastreact/config.json")
        return False
    else:
        print(f"✓ API Key 已配置")

    # 3. 创建 Agent
    print("\n[3] 创建 Agent...")
    try:
        agent = Agent(config=config, multitenant=False)
        print(f"✓ Agent 创建成功")
    except Exception as e:
        print(f"❌ Agent 创建失败: {e}")
        return False

    # 4. 检查 SKILL
    print("\n[4] 检查 SKILL...")
    skill_names = agent._skills.list_available()
    print(f"✓ 可用 SKILL: {len(skill_names)} 个")
    for skill in skill_names:
        print(f"  - {skill}")

    # 5. 加载 MCP
    print("\n[5] 加载 MCP 服务器...")
    try:
        await agent._load_mcp_servers()
        print(f"✓ MCP 服务器加载成功")
        if agent._mcp_manager:
            servers = agent._mcp_manager.list_servers()
            print(f"  - MCP 服务器: {servers}")
    except Exception as e:
        print(f"⚠️  MCP 加载失败: {e}")
        print(f"  （这可能不影响基本功能）")

    # 6. 测试简单查询
    print("\n[6] 测试简单查询...")
    print("  发送: '你好'")

    try:
        event_count = 0
        has_think = False
        has_tool_call = False

        async for event in agent.run_event_stream("你好"):
            event_count += 1
            if event.type == "THINK":
                has_think = True
            elif event.type == "TOOL_CALL":
                has_tool_call = True

            if event_count > 10:  # 限制输出
                print(f"  ... (收到 {event_count} 个事件)")
                break

        print(f"✓ 收到 {event_count} 个事件")
        print(f"  - 有 THINK 事件: {'是' if has_think else '否'}")
        print(f"  - 有 TOOL_CALL 事件: {'是' if has_tool_call else '否'}")

        if event_count == 2 and not has_think:
            print(f"\n❌ 只收到 session_start 和 session_end")
            print(f"   可能原因:")
            print(f"   1. LLM API 调用失败（检查 API Key）")
            print(f"   2. 网络连接问题")
            print(f"   3. LLM API 返回错误")
            return False

    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✓ 诊断完成 - Agent 正常工作")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(diagnose())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  诊断中断")
        sys.exit(1)
