#!/usr/bin/env python3
"""
FastReAct Nano - 调试版 CLI（显示所有事件）
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
    print("FastReAct Nano - 调试模式")
    print("=" * 60)
    print()

    # 加载配置
    print("[1] 加载配置...")
    try:
        config = Config.load()
        print(f"  Model: {config.llm.model}")
        print(f"  API Base: {config.llm.api_base}")
        print(f"  API Key: {config.llm.api_key[:20]}...{config.llm.api_key[-10:] if config.llm.api_key else 'None'}")
    except Exception as e:
        print(f"  [ERROR] {e}")
        return

    print()
    print("[2] 创建 Agent...")
    try:
        agent = Agent(config=config)
        print(f"  [OK] Agent created")
        print(f"  Tools: {agent._tools.list_all()}")
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    print("[3] 运行测试查询...")
    query = "你好，请简短介绍一下你自己"
    print(f"  Query: {query}")
    print()

    try:
        event_count = 0
        async for event in agent.run_event_stream(query):
            event_count += 1
            print(f"  [Event {event_count}] {event.type.value}: {event.content[:100] if event.content else '(no content)'}")

            if event.type == EventType.ERROR:
                print(f"    [ERROR DETAILS] {event.content}")

        print()
        print(f"[DONE] Total events: {event_count}")

    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
