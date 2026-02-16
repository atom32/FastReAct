#!/usr/bin/env python3
"""详细调试脚本"""
import sys
import asyncio
from pathlib import Path

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))
sys.path = [p for p in sys.path if not ('FastReAct/src' in p and 'fastreact-nano' not in p)]

from fastreact import Agent, Config, EventType

async def main():
    config = Config.load()
    agent = Agent(config=config)

    query = "读取 config.json 并总结内容"
    print(f"Query: {query}\n")
    print("=" * 60)

    outer_iteration = 0
    async for event in agent.run_event_stream(query):
        event_type = event.type.value

        if event_type == "session_start":
            print(f"[SESSION_START] {event.content}")

        elif event_type == "think":
            content = event.content.strip()
            if content:
                print(f"[THINK] {content}")

        elif event_type == "step_end":
            outer_iteration += 1
            has_calls = event.metadata.get("has_tool_calls", False)
            print(f"[STEP_END] Iteration {outer_iteration} | has_tool_calls={has_calls}")

        elif event_type == "tool_call":
            print(f"[TOOL_CALL] {event.tool_name}({event.tool_args})")

        elif event_type == "tool_result":
            print(f"[TOOL_RESULT] {len(event.content)} chars")

        elif event_type == "session_end":
            print(f"\n[SESSION_END]")
            print(f"Final Answer: '{event.content}'")
            print(f"Outer iterations: {outer_iteration}")

if __name__ == "__main__":
    asyncio.run(main())
