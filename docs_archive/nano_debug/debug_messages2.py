#!/usr/bin/env python3
"""检查第二次 LLM 调用时的 messages"""
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

    iteration = 0
    async for event in agent.run_event_stream(query):
        if event.type == EventType.TOOL_RESULT:
            print(f"\n[After tool execution]")
            print(f"Messages count: {len(agent._core._react.core.messages)}")
            print(f"Last 3 messages:")
            for i, msg in enumerate(agent._core._react.core.messages[-3:]):
                print(f"  {i+1}. role={msg.get('role')}, content_len={len(msg.get('content', ''))}")

if __name__ == "__main__":
    asyncio.run(main())
