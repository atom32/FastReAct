"""
示例2: 异步并发工具调用

演示如何并发执行多个工具以提升性能
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastreact import FastReAct
from fastreact.tools import CalculatorTool, SearchTool, WeatherTool


async def main():
    """主函数"""
    print("=" * 60)
    print("FastReAct 异步并发示例")
    print("=" * 60)

    # 1. 创建ReACT引擎（多个工具）
    react = FastReAct(
        api_key="your-api-key",
        base_url="https://api.openai.com/v1",
        model="gpt-4",
        tools=[CalculatorTool(), SearchTool(), WeatherTool()],
        max_concurrent_tools=3,  # 最多3个工具并发执行
        enable_cache=True,
    )

    # 2. 复杂查询（需要调用多个工具）
    query = """
    我需要：
    1. 北京今天的天气
    2. 计算 100 * 25 的结果
    3. 搜索Python最新版本信息
    """

    print(f"\n📝 查询: {query}\n")
    print("-" * 60)

    # 记录开始时间
    start_time = asyncio.get_event_loop().time()

    # 定义步骤回调
    def on_step(step):
        if step.get("is_final"):
            print(f"\n✅ 完成！")
        else:
            if "tool_calls" in step:
                print(f"\n🔧 并发调用 {len(step['tool_calls'])} 个工具:")
                for tc in step["tool_calls"]:
                    print(f"   - {tc['name']}")

    # 运行
    result = await react.run_async(
        query=query,
        step_callback=on_step,
    )

    # 计算耗时
    elapsed = asyncio.get_event_loop().time() - start_time

    # 3. 显示结果
    print("\n" + "=" * 60)
    print("📊 性能对比")
    print("=" * 60)
    print(f"实际耗时: {elapsed:.2f}秒")

    # 如果工具串行执行，耗时会是多少
    serial_time = result["stats"]["tool_calls"] * 0.1  # 假设每个工具100ms
    print(f"串行执行预估: {serial_time:.2f}秒")
    print(f"性能提升: {serial_time / elapsed:.2f}x")

    await react.close()


if __name__ == "__main__":
    asyncio.run(main())
