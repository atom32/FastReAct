#!/usr/bin/env python3
"""
调试 LLM 响应
"""
import sys
import asyncio
from pathlib import Path

# 添加项目 src 目录到路径
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# 清除可能冲突的旧路径
sys.path = [
    p for p in sys.path
    if not ('FastReAct/src' in p and 'fastreact-nano' not in p)
]

from fastreact import Agent, Config, EventType

async def main():
    print("=" * 60)
    print("调试 LLM 响应")
    print("=" * 60)
    print()

    config = Config.load()
    agent = Agent(config=config)

    query = "读取 config.json 并总结内容"
    print(f"Query: {query}\n")

    async for event in agent.run_event_stream(query):
        event_type = event.type.value

        if event_type == "think":
            print(f"[THINK] {event.content}")

        elif event_type == "tool_call":
            print(f"[TOOL_CALL] {event.tool_name}: {event.tool_args}")

        elif event_type == "tool_result":
            lines = event.content.split('\n')
            preview = '\n'.join(lines[:5]) + f"\n... ({len(lines)} lines)"
            print(f"[TOOL_RESULT] {preview}")

        elif event_type == "session_end":
            print(f"\n[SESSION_END]")
            print(f"Final Answer: {event.content}")
            print(f"Final Answer Length: {len(event.content) if event.content else 0}")

if __name__ == "__main__":
    asyncio.run(main())
