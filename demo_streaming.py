# -*- coding: utf-8 -*-
"""
FastReAct 实时控制功能完整演示

展示：
1. 默认控制台输出
2. 自定义回调
3. 事件记录
"""
import asyncio
import sys
import io

# 设置 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from fastreact import FastReAct
from fastreact.tools import CalculatorTool, SearchTool
from fastreact.core.callbacks import (
    StreamingCallbacks,
    ConsoleCallbacks,
    CallbackRecorder
)
from fastreact.utils.config import get_config


async def demo_console_output():
    """演示 1: 使用默认控制台回调"""
    print("\n" + "=" * 70)
    print("DEMO 1: Console Output (Default)")
    print("=" * 70)
    print()

    # 加载配置
    config = get_config()
    llm_config = config.get_llm_config()

    # 创建 Agent
    agent = FastReAct(
        api_key=llm_config.get('api_key'),
        base_url=llm_config.get('base_url'),
        model=llm_config.get('model'),
        tools=[CalculatorTool()],
        enable_cache=True
    )

    # 使用默认回调（会自动显示思考过程）
    result = await agent.run_async_streaming(
        "计算 99 × 99 等于多少？"
    )

    print(f"\n[RESULT] {result['answer']}")


async def demo_custom_callbacks():
    """演示 2: 自定义回调函数"""
    print("\n" + "=" * 70)
    print("DEMO 2: Custom Callbacks")
    print("=" * 70)
    print()

    config = get_config()
    llm_config = config.get_llm_config()

    agent = FastReAct(
        api_key=llm_config.get('api_key'),
        base_url=llm_config.get('base_url'),
        model=llm_config.get('model'),
        tools=[CalculatorTool()],
        enable_cache=True
    )

    # 自定义回调
    thought_count = 0

    async def count_thoughts(thought):
        nonlocal thought_count
        thought_count += 1
        print(f"[THOUGHT #{thought_count}] {thought[:80]}...")

    async def show_action(action):
        tool = action.get('tool_name', 'unknown')
        print(f"[ACTION] Calling tool: {tool}")

    async def show_observation(obs):
        print(f"[OBSERVATION] {obs[:100]}...")

    callbacks = StreamingCallbacks(
        on_thought=count_thoughts,
        on_action=show_action,
        on_observation=show_observation
    )

    result = await agent.run_async_streaming(
        "先计算 50 × 50，然后计算 60 × 60",
        callbacks=callbacks
    )

    print(f"\n[RESULT] Total thoughts: {thought_count}")
    print(f"[RESULT] Answer: {result['answer']}")


async def demo_event_recording():
    """演示 3: 事件记录和分析"""
    print("\n" + "=" * 70)
    print("DEMO 3: Event Recording")
    print("=" * 70)
    print()

    config = get_config()
    llm_config = config.get_llm_config()

    agent = FastReAct(
        api_key=llm_config.get('api_key'),
        base_url=llm_config.get('base_url'),
        model=llm_config.get('model'),
        tools=[CalculatorTool()],
        enable_cache=True
    )

    # 使用记录器
    recorder = CallbackRecorder()

    result = await agent.run_async_streaming(
        "计算 123 + 456",
        callbacks=recorder
    )

    print(f"Answer: {result['answer']}")
    print()
    print("[STATISTICS]")
    summary = recorder.get_summary()
    print(f"  Total events: {summary['total_events']}")
    print(f"  Duration: {summary['duration']:.2f}s")
    print(f"  Phase breakdown: {summary['phases']}")

    print()
    print("[TIMELINE]")
    print(recorder.get_timeline())


async def main():
    """运行所有演示"""
    print("\n" + "=" * 70)
    print("FastReAct - Real-time Control Feature Demo")
    print("=" * 70)

    try:
        # 运行演示
        await demo_console_output()
        await demo_custom_callbacks()
        await demo_event_recording()

        print("\n" + "=" * 70)
        print("All demos completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
