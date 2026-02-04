"""
GraphRAG ReAct查询示例

演示如何使用FastReAct + GraphRAG工具进行知识图谱查询和推理

特性：
1. 真正的ReAct循环（Thought → Action → Observation）
2. GraphRAG工具集成（5个工具）
3. 流式输出支持
4. 并发工具执行
5. 智能缓存
"""

import asyncio
import os
from typing import Dict, Any

from fastreact.core.engine import FastReAct
from fastreact.tools import export_tools_to_fastreact


def print_step(step: Dict[str, Any]) -> None:
    """
    打印ReAct步骤

    Args:
        step: 步骤信息字典
    """
    iteration = step.get("iteration", 0)
    thought = step.get("thought", "")
    is_final = step.get("is_final", False)

    print(f"\n{'='*70}")
    print(f"🔄 Iteration {iteration + 1}")
    print(f"{'='*70}")

    # Thought
    print(f"\n💭 Thought:")
    print(f"   {thought}")

    # 检查是否是最终答案
    if is_final:
        answer = step.get("answer", "")
        print(f"\n[TARGET] Final Answer:")
        print(f"   {answer}")
        return

    # Tool calls
    tool_calls = step.get("tool_calls", [])
    if tool_calls:
        print(f"\n[CONFIG] Action:")
        for call in tool_calls:
            name = call.get("name", "")
            params = call.get("parameters", {})
            print(f"   [{name}]")
            for key, value in params.items():
                print(f"     {key}: {value}")

    # Observation
    observation = step.get("observation", "")
    if observation:
        print(f"\n👀 Observation:")
        # 缩进显示observation
        for line in observation.split("\n"):
            print(f"   {line}")


async def demo_simple_query():
    """示例1：简单GraphRAG查询"""
    print("\n" + "[START]" * 35)
    print("示例1: 简单GraphRAG查询")
    print("[START]" * 35)

    # 使用上下文管理器自动管理资源
    async with FastReAct(
        api_key=os.getenv("OPENAI_API_KEY", "sk-test"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("OPENAI_MODEL", "gpt-4"),
        max_iterations=5,
        enable_cache=True,
        enable_streaming=False,
    ) as agent:
        # 注册GraphRAG工具
        from fastreact.tools.mcp_adapter import get_global_registry

        for tool in export_tools_to_fastreact():
            agent.register_tool(tool)

        # 查询
        query = "查询Alice的兴趣爱好"

        print(f"\n[QUESTION] 用户查询: {query}")

        # 执行ReAct循环
        result = await agent.run_async(
            query=query,
            step_callback=print_step,
        )

        # 打印结果
        print(f"\n\n{'='*70}")
        print("[STATS] 执行统计")
        print(f"{'='*70}")
        stats = result.get("stats", {})
        print(f"  总调用次数: {stats.get('total_calls', 0)}")
        print(f"  工具调用: {stats.get('tool_calls', 0)}")
        print(f"  缓存命中: {stats.get('cache_hits', 0)}")
        print(f"  缓存未命中: {stats.get('cache_misses', 0)}")
        print(f"  缓存命中率: {stats.get('cache_hit_rate', 0):.2%}")
        print(f"  平均执行时间: {stats.get('avg_time_per_call', 0):.2f}秒")

        # 注意：不需要手动调用 agent.close()，上下文管理器会自动处理


async def demo_complex_reasoning():
    """示例2：复杂多跳推理"""
    print("\n\n" + "[START]" * 35)
    print("示例2: 复杂多跳推理")
    print("[START]" * 35)

    # 使用上下文管理器
    async with FastReAct(
        api_key=os.getenv("OPENAI_API_KEY", "sk-test"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("OPENAI_MODEL", "gpt-4"),
        max_iterations=10,
        enable_cache=True,
        enable_streaming=False,
    ) as agent:
        # 注册工具
        for tool in export_tools_to_fastreact():
            agent.register_tool(tool)

        # 复杂查询
        query = "Alice和Bob有什么共同兴趣？他们如何认识彼此的？"

        print(f"\n[QUESTION] 用户查询: {query}")

        # 执行ReAct循环
        result = await agent.run_async(
            query=query,
            step_callback=print_step,
        )

        print(f"\n\n[OK] 最终答案: {result.get('answer', '未能完成')}")


async def demo_multi_entity_analysis():
    """示例3：多实体关系分析"""
    print("\n\n" + "[START]" * 35)
    print("示例3: 多实体关系分析")
    print("[START]" * 35)

    # 使用上下文管理器
    async with FastReAct(
        api_key=os.getenv("OPENAI_API_KEY", "sk-test"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("OPENAI_MODEL", "gpt-4"),
        max_iterations=8,
        enable_cache=True,
        enable_streaming=False,
    ) as agent:
        # 注册工具
        for tool in export_tools_to_fastreact():
            agent.register_tool(tool)

        # 多实体查询
        query = "分析Alice、Bob和Charlie三人之间的关系网络，找出谁是连接中心"

        print(f"\n[QUESTION] 用户查询: {query}")

        # 执行ReAct循环
        result = await agent.run_async(
            query=query,
            step_callback=print_step,
        )

        print(f"\n\n[OK] 最终答案: {result.get('answer', '未能完成')}")


async def demo_with_streaming():
    """示例4：流式输出"""
    print("\n\n" + "[START]" * 35)
    print("示例4: 流式输出")
    print("[START]" * 35)

    # 使用上下文管理器
    async with FastReAct(
        api_key=os.getenv("OPENAI_API_KEY", "sk-test"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("OPENAI_MODEL", "gpt-4"),
        max_iterations=5,
        enable_cache=True,
        enable_streaming=True,  # 启用流式输出
    ) as agent:
        # 注册工具
        for tool in export_tools_to_fastreact():
            agent.register_tool(tool)

        query = "简单查询：Python是什么？"

        print(f"\n[QUESTION] 用户查询: {query}")

        # 流式回调
        def stream_callback(text: str):
            """实时输出LLM生成的内容"""
            print(text, end="", flush=True)

        # 执行ReAct循环（流式）
        result = await agent.run_async(
            query=query,
            stream_callback=stream_callback,
            step_callback=print_step,
        )

        print(f"\n\n[OK] 完成")


async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("FastReAct + GraphRAG 查询示例")
    print("=" * 70)

    # 检查环境变量
    if not os.getenv("OPENAI_API_KEY"):
        print("\n[WARNING]  警告: 未设置OPENAI_API_KEY环境变量")
        print("   请设置: export OPENAI_API_KEY='your-api-key'")
        print("   使用模拟模式运行...")

    # 检查GraphRAG配置
    hippo_url = os.getenv("HIPPO_RAG_URL", "http://localhost:8080")
    print(f"\n📡 GraphRAG服务: {hippo_url}")

    # 运行示例
    try:
        await demo_simple_query()
        # await demo_complex_reasoning()
        # await demo_multi_entity_analysis()
        # await demo_with_streaming()

    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断")
    except Exception as e:
        print(f"\n\n[ERROR] 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
