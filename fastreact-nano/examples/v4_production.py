#!/usr/bin/env python3
"""
FastReAct Nano - v4: Production-Ready Features
展示完整功能：Skills + MCP + 事件流 + 错误处理
"""

import asyncio
from fastreact import Agent

async def main():
    """
    完整功能演示
    """
    print("=" * 70)
    print("FastReAct Nano v4: Production-Ready Demo")
    print("=" * 70)
    print()
    print("功能特性:")
    print("  ✅ 事件驱动实时响应")
    print("  ✅ Skills 智能选择")
    print("  ✅ MCP 工具集成")
    print("  ✅ 多轮对话记忆")
    print("  ✅ 安全策略保护")
    print("  ✅ 无限循环防护")
    print()

    # 创建 Agent
    agent = Agent()

    # 查询 1：使用 Skills
    query1 = "使用 GitHub 集成功能查看 atom32/FastReAct 仓库的最近提交"
    print(f"[查询 1] {query1}")
    print()

    async for event in agent.run_event_stream(query1):
        if event.type == "think":
            print(f"  [思考] {event.content[:80]}...")
        elif event.type == "tool_call":
            print(f"  [工具] 调用 {event.tool_name}")
        elif event.type == "tool_result":
            print(f"  [结果] 收到结果 ({len(event.content)} 字符)")
        elif event.type == "session_end":
            print(f"\n[完成] 回答:\n{event.content}\n")
            break

    # 查询 2：验证多轮对话记忆
    print("-" * 70)
    query2 = "我刚才问了什么？"
    print(f"[查询 2] {query2}")

    response2 = await agent.ask(query2)
    print(f"[回答] {response2}")
    print()

    print("[完成] 所有功能正常运行")

if __name__ == "__main__":
    asyncio.run(main())
