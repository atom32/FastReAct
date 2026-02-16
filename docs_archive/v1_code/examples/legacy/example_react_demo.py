# -*- coding: utf-8 -*-
"""
使用配置文件的ReACT测试

使用 SiliconFlow (DeepSeek) API 运行真实的ReACT循环
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

    print_section("[START] FastReAct 真实测试 (使用配置文件)")

    # 加载配置
    print("\n📁 加载配置文件...")
    config = get_config()

    # 列出可用的提供商
    config.list_providers()

    # 获取LLM配置
    llm_config = config.get_llm_config()
    react_config = config.get_react_config()

    print(f"\n[CONFIG] 使用配置:")
    print(f"  模型: {llm_config.get('model', 'N/A')}")
    print(f"  API: {llm_config.get('base_url', 'N/A')}")
    print(f"  最大迭代: {react_config.get('max_iterations', 10)}")
    print(f"  缓存: {'启用' if react_config.get('enable_cache') else '禁用'}")

    # 创建ReACT引擎
    print("\n[PACKAGE] 初始化ReACT引擎...")

    async with FastReAct(
        api_key=llm_config.get("api_key", ""),
        base_url=llm_config.get("base_url", "https://api.openai.com/v1"),
        model=llm_config.get("model", "gpt-4"),
        tools=[CalculatorTool()],
        max_iterations=react_config.get("max_iterations", 10),
        enable_cache=react_config.get("enable_cache", True),
        cache_size=react_config.get("cache_size", 1000),
        temperature=llm_config.get("temperature", 0.7),
    ) as react:

        # 测试查询
        queries = [
            "帮我计算 (25 + 35) * 2 - 40",
            "计算 123 * 45 + 678",
            "如果我有100元，买了3个15元的东西，还剩多少钱？"
        ]

        for idx, query in enumerate(queries, 1):
            print_section(f"[NOTE] 测试 #{idx}: {query}")

            # 定义回调函数
            def debug_callback(step):
                if not step.get('is_final'):
                    iteration = step['iteration'] + 1
                    print(f"\n  🔄 步骤 {iteration}")

                    if 'thought' in step:
                        thought = step['thought'][:100]
                        print(f"  💭 {thought}...")

                    if 'tool_calls' in step and step['tool_calls']:
                        for tc in step['tool_calls']:
                            print(f"  [CONFIG] 调用: {tc['name']}({tc['parameters']})")

                    if 'observation' in step:
                        obs = step['observation'][:80]
                        print(f"  👀 结果: {obs}...")

            try:
                # 运行ReACT循环
                result = await react.run_async(
                    query=query,
                    step_callback=debug_callback
                )

                # 显示结果
                stats = result['stats']
                print(f"\n  [OK] 答案: {result['answer'][:100]}")
                print(f"  [STATS] 迭代: {stats['total_calls']}次 | 工具: {stats['tool_calls']}次 | 耗时: {stats['total_time']:.2f}秒")

            except Exception as e:
                print(f"\n  [ERROR] 错误: {e}")

            if idx < len(queries):
                print("\n⏳ 准备下一个测试...")
                await asyncio.sleep(1)

        # 最终统计
        print_section("[STATS] 测试总结")
        print(" [OK] 所有测试完成！")
        print("\n[INFO] 提示:")
        print("  - 你可以修改 config.json 来切换不同的LLM提供商")
        print("  - 支持 OpenAI、SiliconFlow、Ollama 等")
        print("  - 也可以添加自定义的API端点")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[WARNING]  测试被中断")
    except Exception as e:
        print(f"\n\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
