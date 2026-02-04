"""
示例1: FastReAct基础使用

演示如何创建一个简单的ReACT Agent并运行
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastreact import FastReAct
from fastreact.tools import create_calculator_tool


async def main():
    """主函数"""
    print("=" * 60)
    print("FastReAct 基础示例")
    print("=" * 60)

    # 1. 创建ReACT引擎
    react = FastReAct(
        api_key="your-api-key",  # 替换为你的API密钥
        base_url="https://api.openai.com/v1",
        model="gpt-4",
        tools=[create_calculator_tool()],
        enable_cache=True,  # 启用缓存
        max_iterations=5,
    )

    # 2. 运行查询
    query = "帮我计算 (15 + 25) * 2 - 10"

    print(f"\n[NOTE] 查询: {query}\n")
    print("-" * 60)

    # 定义步骤回调（显示每一步）
    def on_step(step):
        if step.get("is_final"):
            print(f"\n[OK] 最终答案: {step['answer']}")
        else:
            print(f"\n🔄 步骤 {step['iteration'] + 1}")
            if "tool_calls" in step:
                for tc in step["tool_calls"]:
                    print(f"   [CONFIG] 调用工具: {tc['name']}")
                    print(f"   📋 参数: {tc['parameters']}")
            if "observation" in step:
                print(f"   👀 观察: {step['observation'][:100]}...")

    # 运行
    result = await react.run_async(
        query=query,
        step_callback=on_step,
    )

    # 3. 显示统计信息
    print("\n" + "=" * 60)
    print("[STATS] 性能统计")
    print("=" * 60)
    stats = result["stats"]
    print(f"总调用次数: {stats['total_calls']}")
    print(f"总耗时: {stats['total_time']:.2f}秒")
    print(f"工具调用次数: {stats['tool_calls']}")
    print(f"缓存命中: {stats['cache_hits']}")
    print(f"缓存未命中: {stats['cache_misses']}")
    if stats['cache_hits'] + stats['cache_misses'] > 0:
        print(f"缓存命中率: {stats.get('cache_hit_rate', 0) * 100:.1f}%")

    # 关闭连接
    await react.close()


if __name__ == "__main__":
    # 检查API密钥
    if "your-api-key" in open(__file__).read():
        print("[WARNING] 请先设置你的OpenAI API密钥！")
        print("编辑此文件，将 'your-api-key' 替换为你的实际API密钥")
    else:
        asyncio.run(main())
