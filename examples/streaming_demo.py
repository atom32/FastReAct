"""
FastReAct 实时控制功能演示

展示如何使用流式回调系统来实时监控和控制 Agent 的执行过程。
"""

import asyncio
import os
from fastreact import FastReAct
from fastreact.core.callbacks import (
    StreamingCallbacks,
    ConsoleCallbacks,
    CallbackRecorder,
    Phase,
    StepEvent
)
from fastreact.tools import CalculatorTool, SearchTool


async def demo_01_console_output():
    """示例 1: 使用默认的控制台回调（最简单）"""
    print("\n" + "=" * 70)
    print("示例 1: 默认控制台输出")
    print("=" * 70)

    # 创建 Agent
    agent = FastReAct(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        tools=[CalculatorTool(), SearchTool()],
        model="qwen-max"
    )

    # 使用默认的 ConsoleCallbacks
    result = await agent.run_async_streaming(
        "帮我计算 25 * 18，然后搜索今天的天气情况"
    )

    print(f"\n最终答案: {result['answer']}")


async def demo_02_custom_callbacks():
    """示例 2: 自定义回调函数"""
    print("\n" + "=" * 70)
    print("示例 2: 自定义回调")
    print("=" * 70)

    agent = FastReAct(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        tools=[CalculatorTool()],
        model="qwen-max"
    )

    # 定义自定义回调
    async def my_thought_handler(thought: str):
        print(f"💭 Agent 正在思考: {thought}")

    async def my_action_handler(action: dict):
        tool_name = action.get("tool_name", "unknown")
        params = action.get("parameters", {})
        print(f"🔧 准备调用工具: {tool_name}")
        if params:
            print(f"   参数: {params}")

    async def my_observation_handler(observation: str):
        # 截断过长的输出
        obs_short = observation[:150] + "..." if len(observation) > 150 else observation
        print(f"📊 工具返回: {obs_short}")

    async def my_delta_handler(delta: str):
        # 实时显示答案生成过程
        print(delta, end="", flush=True)

    # 创建自定义回调
    callbacks = StreamingCallbacks(
        on_thought=my_thought_handler,
        on_action=my_action_handler,
        on_observation=my_observation_handler,
        on_answer_delta=my_delta_handler
    )

    result = await agent.run_async_streaming(
        "计算 (123 + 456) * 789",
        callbacks=callbacks
    )

    print(f"\n\n最终答案: {result['answer']}")


async def demo_03_event_recording():
    """示例 3: 记录所有事件用于分析"""
    print("\n" + "=" * 70)
    print("示例 3: 事件记录和分析")
    print("=" * 70)

    agent = FastReAct(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        tools=[CalculatorTool()],
        model="qwen-max"
    )

    # 使用回调记录器
    recorder = CallbackRecorder()

    result = await agent.run_async_streaming(
        "计算 100 * 200 + 50",
        callbacks=recorder
    )

    print("\n执行完成！事件分析：")
    print(f"- 总事件数: {len(recorder.get_events())}")
    print(f"- 执行时长: {recorder.get_summary()['duration']:.2f}s")
    print(f"- 各阶段统计: {recorder.get_summary()['phases']}")

    print("\n详细时间线:")
    print(recorder.get_timeline())


async def demo_04_combined_callbacks():
    """示例 4: 组合多个回调（同时输出到控制台和记录）"""
    print("\n" + "=" * 70)
    print("示例 4: 组合回调（控制台 + 记录）")
    print("=" * 70)

    agent = FastReAct(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        tools=[CalculatorTool()],
        model="qwen-max"
    )

    # 创建记录器
    recorder = CallbackRecorder()

    # 创建一个同时支持控制台输出和记录的回调
    class CombinedCallbacks(ConsoleCallbacks):
        def __init__(self, recorder: CallbackRecorder):
            super().__init__(
                show_thoughts=True,
                show_actions=True,
                show_observations=True,
                show_timing=True
            )
            self.recorder = recorder

        async def emit(self, event: StepEvent):
            # 先记录事件
            await self.recorder.emit(event)
            # 然后调用父类的 emit 进行控制台输出
            await super().emit(event)

    callbacks = CombinedCallbacks(recorder)

    result = await agent.run_async_streaming(
        "计算 99 * 99",
        callbacks=callbacks
    )

    print("\n执行完成！")
    print(f"控制台已显示详细过程，同时记录了 {len(recorder.get_events())} 个事件")


async def demo_05_filtered_output():
    """示例 5: 过滤输出（只显示部分信息）"""
    print("\n" + "=" * 70)
    print("示例 5: 过滤输出（只显示工具调用，不显示思考）")
    print("=" * 70)

    agent = FastReAct(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        tools=[CalculatorTool()],
        model="qwen-max"
    )

    # 创建只显示工具调用的回调
    callbacks = ConsoleCallbacks(
        show_thoughts=False,      # 不显示思考
        show_actions=True,        # 显示工具调用
        show_observations=False,  # 不显示观察结果
        show_timing=True          # 显示时间
    )

    result = await agent.run_async_streaming(
        "计算 888 * 666",
        callbacks=callbacks
    )

    print(f"\n最终答案: {result['answer']}")


async def demo_06_web_ui_style():
    """示例 6: 模拟 Web UI 的 JSON 输出"""
    print("\n" + "=" * 70)
    print("示例 6: 模拟 Web UI 的 JSON 事件流")
    print("=" * 70)

    agent = FastReAct(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        tools=[CalculatorTool()],
        model="qwen-max"
    )

    # 模拟 WebSocket 事件推送
    async def web_ui_style(event: StepEvent):
        """模拟 Web UI 的 JSON 事件推送"""
        event_dict = event.to_dict()
        print(f"[WS Event] {event_dict['phase'].upper()}: {event_dict['content'][:100]}")

    callbacks = StreamingCallbacks(
        on_thought=lambda s: web_ui_style(StepEvent(phase=Phase.THINK, content=s)),
        on_action=lambda a: web_ui_style(StepEvent(phase=Phase.ACTION, content=str(a))),
        on_observation=lambda o: web_ui_style(StepEvent(phase=Phase.OBSERVATION, content=str(o)))
    )

    result = await agent.run_async_streaming(
        "计算 234 * 567",
        callbacks=callbacks
    )


async def main():
    """运行所有示例"""
    print("\n" + "=" * 70)
    print("FastReAct 实时控制功能演示")
    print("=" * 70)

    # 检查 API Key
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("\n⚠️  警告: 请设置 DASHSCOPE_API_KEY 环境变量")
        print("   export DASHSCOPE_API_KEY=your-api-key")
        return

    try:
        # 运行示例（可以选择运行哪些）
        await demo_01_console_output()
        await demo_02_custom_callbacks()
        await demo_03_event_recording()
        await demo_04_combined_callbacks()
        await demo_05_filtered_output()
        await demo_06_web_ui_style()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
