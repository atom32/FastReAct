#!/usr/bin/env python3
"""
FastReAct Nano - v1: Event-Driven Architecture
展示事件流协议和实时响应
"""

import asyncio
from fastreact import Agent

async def main():
    """
    展示事件流：THINK, TOOL_CALL, TOOL_RESULT, SESSION_END
    """
    # 创建 Agent
    agent = Agent()

    print("=" * 60)
    print("FastReAct Nano v1: Event Stream Demo")
    print("=" * 60)
    print()

    # 运行查询并监听事件
    query = "列出当前目录的文件"
    print(f"用户查询: {query}\n")

    async for event in agent.run_event_stream(query):
        if event.type == "session_start":
            print(f"[事件] 会话开始: {event.session_id[:8]}...")

        elif event.type == "think":
            print(f"[思考] {event.content[:60]}...")

        elif event.type == "tool_call":
            print(f"[工具] 调用: {event.tool_name}")

        elif event.type == "tool_result":
            result_preview = event.content[:100].replace('\n', ' ')
            print(f"[结果] {result_preview}...")

        elif event.type == "session_end":
            print(f"\n[完成] 最终答案:\n{event.content}")
            print()

if __name__ == "__main__":
    asyncio.run(main())
