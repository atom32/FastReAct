#!/usr/bin/env python3
"""
完整的调试输出
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
    print("完整调试 - 读取 config.json")
    print("=" * 60)
    print()

    config = Config.load()
    agent = Agent(config=config)

    query = "读取 config.json 并用一句话总结"
    print(f"Query: {query}\n")

    iteration = 0
    async for event in agent.run_event_stream(query):
        iteration += 1
        event_type = event.type.value

        print(f"[{iteration:02d}] {event_type.upper():15} | ", end="")

        if event_type == "session_start":
            print(f"Query: {event.content[:50]}...")

        elif event_type == "think":
            content = event.content.strip()
            if content:
                print(f"{content[:100]}")
            else:
                print("(empty thinking)")

        elif event_type == "tool_call":
            print(f"{event.tool_name}({event.tool_args})")

        elif event_type == "tool_result":
            preview = event.content[:100].replace('\n', ' ')
            print(f"{preview}...")

        elif event_type == "step_end":
            has_calls = event.metadata.get("has_tool_calls", False)
            print(f"has_tool_calls={has_calls}, content={event.content[:50] if event.content else '(empty)'}")

        elif event_type == "session_end":
            answer = event.content.strip() if event.content else ""
            print(f"Answer: {answer if answer else '(empty answer)'}")
            print()
            print("=" * 60)
            if answer:
                print("[SUCCESS] LLM 生成了最终答案")
            else:
                print("[PROBLEM] LLM 没有生成最终答案")
            print("=" * 60)

        elif event_type == "error":
            print(f"ERROR: {event.content}")

if __name__ == "__main__":
    asyncio.run(main())
