#!/usr/bin/env python3
"""追踪第二次 LLM 响应"""
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

    think_count = 0
    async for event in agent.run_event_stream(query):
        if event.type == EventType.THINK:
            think_count += 1
            content = event.content.strip()
            print(f"[THINK #{think_count}] Length: {len(content)}, Content: '{content}'")
        elif event.type == EventType.TOOL_RESULT:
            print(f"\n[TOOL_RESULT] End of first iteration\n")

if __name__ == "__main__":
    asyncio.run(main())
