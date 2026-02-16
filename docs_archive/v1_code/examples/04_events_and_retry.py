"""
事件流和重试机制示例

展示如何使用 FastReAct 的事件流系统和错误重试机制。

功能：
1. 实时事件流 - 监听 Agent 执行的每个步骤
2. 智能重试 - 自动处理临时性网络错误
3. 性能统计 - 跟踪工具调用和重试次数
"""

import asyncio
from fastreact import FastReAct
from fastreact.core.tool import Tool
from fastreact.observability.events import (
    LifecycleEvent,
    AssistantEvent,
    ToolEvent,
)


# ============================================================================
# 示例 1: 基础事件流监听
# ============================================================================

async def example_1_basic_event_stream():
    """示例 1: 监听 Agent 执行事件"""

    print("\n" + "=" * 60)
    print("示例 1: 基础事件流监听")
    print("=" * 60)

    # 定义事件回调
    async def event_callback(event):
        if event.type == "lifecycle":
            print(f"[生命周期] {event.phase.upper()}")
        elif event.type == "assistant":
            print(f"[助手] {event.delta[:50]}...")
        elif event.type == "tool":
            if event.phase == "start":
                print(f"[工具] 开始执行: {event.tool_name}")
            elif event.phase == "result":
                print(f"[工具] 完成: {event.tool_name} ({event.duration_ms:.2f}ms)")
            elif event.phase == "error":
                print(f"[工具] 错误: {event.tool_name} - {event.error}")

    # 创建 Agent（启用事件流）
    agent = FastReAct(
        api_key="your-api-key",
        model="gpt-3.5-turbo",
        enable_event_stream=True,
        event_callback=event_callback,
    )

    # 运行查询
    result = await agent.run_async("What is 25 * 36?")

    print(f"\n最终答案: {result['answer']}")
    print(f"统计: {result['stats']}")


# ============================================================================
# 示例 2: 带重试的容错工具执行
# ============================================================================

async def example_2_retry_mechanism():
    """示例 2: 演示重试机制处理临时错误"""

    print("\n" + "=" * 60)
    print("示例 2: 重试机制")
    print("=" * 60)

    # 创建一个会失败几次然后成功的工具
    call_count = 0

    async def flaky_api(**kwargs):
        """模拟不稳定的 API"""
        nonlocal call_count
        call_count += 1

        if call_count <= 2:
            print(f"  [尝试 {call_count}] 失败: ConnectionError")
            raise ConnectionError(f"网络错误 (尝试 {call_count})")

        print(f"  [尝试 {call_count}] 成功!")
        return "数据获取成功"

    # 注册工具
    from fastreact.core.tool import Tool

    flaky_tool = Tool(
        name="flaky_api",
        description="不稳定的 API（前两次失败，第三次成功）",
        parameters={"type": "object", "properties": {}}
    )
    flaky_tool.execute_async = flaky_api

    # 创建 Agent（启用重试）
    agent = FastReAct(
        api_key="your-api-key",
        model="gpt-3.5-turbo",
        enable_event_stream=False,
        enable_tool_retry=True,  # 启用智能重试
        max_tool_retries=3,      # 最多重试 3 次
    )

    agent.register_tool(flaky_tool)

    # 使用重试执行器
    from fastreact.utils.resilience import RetryExecutor, RetryPolicy

    executor = RetryExecutor(RetryPolicy(max_attempts=3))

    print("执行不稳定的工具...")
    result = await executor.execute(flaky_api)

    print(f"\n结果: {result}")
    print(f"统计: {executor.get_stats()}")


# ============================================================================
# 示例 3: 事件流 + 重试 + 统计
# ============================================================================

async def example_3_combined():
    """示例 3: 结合事件流、重试和性能统计"""

    print("\n" + "=" * 60)
    print("示例 3: 完整功能演示")
    print("=" * 60)

    events_log = []

    async def event_callback(event):
        """记录所有事件"""
        events_log.append({
            'type': event.type,
            'phase': getattr(event, 'phase', None),
            'tool_name': getattr(event, 'tool_name', None),
            'timestamp': event.timestamp,
        })

        # 实时输出
        if event.type == "lifecycle":
            print(f"✓ {event.phase.upper()}")
        elif event.type == "tool":
            if event.phase == "start":
                print(f"  → 工具: {event.tool_name}")
            elif event.phase == "result":
                print(f"  ✓ 完成 ({event.duration_ms:.2f}ms)")

    # 创建一个简单的计算器工具
    async def calculator(expression: str) -> str:
        try:
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"错误: {e}"

    calc_tool = Tool(
        name="calculator",
        description="数学计算器",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '2+2' 或 '5*10'"
                }
            },
            "required": ["expression"]
        }
    )
    calc_tool.execute_async = calculator

    # 创建 Agent（启用所有功能）
    agent = FastReAct(
        api_key="your-api-key",
        model="gpt-3.5-turbo",
        enable_event_stream=True,
        event_callback=event_callback,
        enable_tool_retry=True,
        max_tool_retries=2,
        enable_cache=True,
    )

    agent.register_tool(calc_tool)

    # 运行查询
    result = await agent.run_async(
        "Calculate (123 + 456) * 2"
    )

    # 输出统计
    print("\n" + "-" * 60)
    print("统计信息:")
    print(f"  总工具调用: {result['stats']['tool_calls']}")
    print(f"  缓存命中: {result['stats']['cache_hits']}")
    print(f"  工具重试: {result['stats']['tool_retries']}")
    print(f"  总执行时间: {result['stats']['total_time']:.2f}s")
    print(f"  事件数量: {len(events_log)}")

    # 事件流分析
    lifecycle_events = [e for e in events_log if e['type'] == 'lifecycle']
    tool_events = [e for e in events_log if e['type'] == 'tool']

    print(f"\n事件流分析:")
    print(f"  生命周期事件: {len(lifecycle_events)}")
    print(f"  工具事件: {len(tool_events)}")


# ============================================================================
# 示例 4: 自定义重试策略
# ============================================================================

async def example_4_custom_retry_policy():
    """示例 4: 自定义重试策略"""

    print("\n" + "=" * 60)
    print("示例 4: 自定义重试策略")
    print("=" * 60)

    from fastreact.utils.resilience import RetryPolicy, RetryExecutor

    # 自定义重试策略
    custom_policy = RetryPolicy(
        max_attempts=5,           # 最多尝试 5 次
        base_delay=0.5,           # 基础延迟 0.5 秒
        max_delay=30.0,           # 最大延迟 30 秒
        exponential_base=2.0,     # 指数退避基数 2
        jitter=True,              # 启用随机抖动
        retriable_errors=(        # 只对这些错误重试
            ConnectionError,
            TimeoutError,
            OSError,
        )
    )

    executor = RetryExecutor(custom_policy)

    # 测试重试延迟
    print("\n重试延迟计算:")
    for i in range(5):
        delay = custom_policy.calculate_delay(i)
        print(f"  尝试 {i}: 延迟 {delay:.2f}s")

    # 模拟失败后重试
    attempt = 0

    async def failing_function():
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise ConnectionError(f"失败 (尝试 {attempt})")
        return f"成功 (尝试 {attempt})"

    print("\n执行带重试的函数:")
    result = await executor.execute(failing_function)

    print(f"\n结果: {result}")
    print(f"统计: {executor.get_stats()}")


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """运行所有示例"""

    print("\n" + "=" * 60)
    print("FastReAct 事件流和重试机制示例")
    print("=" * 60)

    # 注意：这些示例需要真实的 API Key 才能运行
    # 请将 "your-api-key" 替换为实际的 API Key

    print("\n注意：请将 'your-api-key' 替换为实际的 API Key")
    print("跳过实际执行，仅展示代码结构。\n")

    # 如果有 API Key，可以取消注释以下代码运行示例：

    # await example_1_basic_event_stream()
    # await example_2_retry_mechanism()
    # await example_3_combined()
    # await example_4_custom_retry_policy()

    print("\n所有示例完成！")


if __name__ == "__main__":
    asyncio.run(main())
