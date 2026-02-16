#!/usr/bin/env python3
"""追踪第一次 LLM 响应"""
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

    query = "读取 config.json 并总结"
    print(f"Query: {query}\n")

    async for event in agent.run_event_stream(query):
        if event.type == EventType.THINK:
            print(f"[THINK] Length: {len(event.content)}, Content: '{event.content}'")
        elif event.type == EventType.STEP_END:
            content = event.content
            print(f"[STEP_END] Length: {len(content) if content else 0}, Content: '{content}'")
        elif event.type == EventType.TOOL_RESULT:
            print(f"[TOOL_RESULT] Length: {len(event.content)}")

if __name__ == "__main__":
    asyncio.run(main())
