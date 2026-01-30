# -*- coding: utf-8 -*-
"""
调试版本：显示ReACT循环的完整过程
"""

import asyncio
import sys
import os
import io

# 设置UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastreact import FastReAct
from fastreact.tools import CalculatorTool
from fastreact.utils.config import get_config


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


async def main():
    """主函数"""

    print_section("🔍 FastReAct 调试模式")

    # 加载配置
    config = get_config()
    llm_config = config.get_llm_config()

    print(f"\n🔧 配置:")
    print(f"  模型: {llm_config.get('model')}")
    print(f"  API: {llm_config.get('base_url')}")

    # 创建ReACT引擎
    async with FastReAct(
        api_key=llm_config.get("api_key", ""),
        base_url=llm_config.get("base_url"),
        model=llm_config.get("model"),
        tools=[CalculatorTool()],
        max_iterations=5,
        enable_cache=False,  # 关闭缓存以便观察
    ) as react:

        query = "帮我计算 (25 + 35) * 2 - 40"
        print(f"\n📝 查询: {query}")

        # 详细回调
        def debug_callback(step):
            print("\n" + "-" * 70)
            print(f"📍 迭代 #{step['iteration'] + 1}")

            # Thought
            if 'thought' in step:
                print(f"\n💭 LLM响应:")
                print(f"   {step['thought']}")

            # Tool Calls
            if 'tool_calls' in step:
                if step['tool_calls']:
                    print(f"\n🔧 解析到的工具调用:")
                    for tc in step['tool_calls']:
                        print(f"   - {tc['name']}")
                        print(f"     参数: {tc['parameters']}")
                else:
                    print(f"\n⚠️  没有工具调用")

            # Observation
            if 'observation' in step:
                print(f"\n👀 工具执行结果:")
                print(f"   {step['observation']}")

            # Final Answer
            if step.get('is_final'):
                print(f"\n🎯 最终答案:")
                print(f"   {step['answer']}")

        # 运行
        try:
            result = await react.run_async(
                query=query,
                step_callback=debug_callback
            )

            print_section("📊 执行统计")
            stats = result['stats']
            print(f"  总迭代: {stats['total_calls']}")
            print(f"  工具调用: {stats['tool_calls']}")
            print(f"  总耗时: {stats['total_time']:.2f}秒")
            print(f"  缓存命中: {stats['cache_hits']}")
            print(f"  缓存未命中: {stats['cache_misses']}")

            print(f"\n✅ 最终答案: {result['answer']}")

        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
