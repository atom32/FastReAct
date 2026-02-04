"""
FastReAct V2 流式响应演示

展示如何使用 V2 的流式响应功能来实时监控 Agent 的执行过程。
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastreact import FastReAct, StreamChunkType
from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model


# UTF-8 encoding for Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'


async def demo_01_basic_streaming():
    """示例 1: 基础流式输出"""
    print("\n" + "=" * 70)
    print("示例 1: 基础流式输出")
    print("=" * 70 + "\n")

    # 加载配置
    config = load_config()
    api_key = get_api_key(config)
    base_url = get_base_url(config)
    model = get_model(config)

    # 创建 Agent
    agent = FastReAct(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    query = "2 + 2 = ?"
    print(f"Query: {query}\n")

    # 流式执行
    async for chunk in agent.run_streaming(query):
        if chunk.type == StreamChunkType.THINKING:
            print(f"[Thinking] {chunk.content[:100]}...")
        elif chunk.type == StreamChunkType.TOOL_CALL:
            print(f"[Tool] {chunk.tool_name}({chunk.tool_params})")
        elif chunk.type == StreamChunkType.TOOL_RESULT:
            print(f"[Result] {chunk.content[:100]}...")
        elif chunk.type == StreamChunkType.ANSWER:
            print(f"[Answer] {chunk.content}")

    await agent.close()


async def demo_02_filter_thinking():
    """示例 2: 只显示思考过程"""
    print("\n" + "=" * 70)
    print("示例 2: 只显示思考过程")
    print("=" * 70 + "\n")

    config = load_config()
    api_key = get_api_key(config)
    base_url = get_base_url(config)
    model = get_model(config)

    agent = FastReAct(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    query = "解释什么是快速排序算法"
    print(f"Query: {query}\n")

    # 只显示思考过程
    async for chunk in agent.run_streaming(query, enable_thinking=True):
        if chunk.type == StreamChunkType.THINKING:
            print(f"{chunk.content}")

    await agent.close()


async def demo_03_collect_results():
    """示例 3: 收集流式结果"""
    print("\n" + "=" * 70)
    print("示例 3: 收集流式结果")
    print("=" * 70 + "\n")

    from fastreact.core.streaming import AsyncIteratorWrapper

    config = load_config()
    api_key = get_api_key(config)
    base_url = get_base_url(config)
    model = get_model(config)

    agent = FastReAct(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    query = "计算 15 * 25 + 10"
    print(f"Query: {query}\n")

    # 收集所有数据块
    wrapper = AsyncIteratorWrapper(agent.run_streaming(query))
    chunks = await wrapper.to_list()

    # 分析结果
    print(f"总共收到 {len(chunks)} 个数据块\n")

    type_counts = {}
    for chunk in chunks:
        type_counts[chunk.type.value] = type_counts.get(chunk.type.value, 0) + 1

    print("数据块类型分布:")
    for chunk_type, count in sorted(type_counts.items()):
        print(f"  - {chunk_type}: {count}")

    # 显示最终答案
    for chunk in chunks:
        if chunk.type == StreamChunkType.ANSWER:
            print(f"\n最终答案: {chunk.content}")

    await agent.close()


async def demo_04_custom_processor():
    """示例 4: 自定义流式处理器"""
    print("\n" + "=" * 70)
    print("示例 4: 自定义流式处理器")
    print("=" * 70 + "\n")

    config = load_config()
    api_key = get_api_key(config)
    base_url = get_base_url(config)
    model = get_model(config)

    agent = FastReAct(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    query = "计算斐波那契数列的第 10 项"
    print(f"Query: {query}\n")

    # 自定义处理器
    thinking_buffer = []
    tool_calls = []

    async for chunk in agent.run_streaming(query):
        if chunk.type == StreamChunkType.THINKING:
            thinking_buffer.append(chunk.content)
        elif chunk.type == StreamChunkType.TOOL_CALL:
            tool_calls.append({
                "name": chunk.tool_name,
                "params": chunk.tool_params
            })
        elif chunk.type == StreamChunkType.ANSWER:
            print(f"最终答案: {chunk.content}")
            print(f"\n统计:")
            print(f"  - 思考步骤: {len(thinking_buffer)}")
            print(f"  - 工具调用: {len(tool_calls)}")

    await agent.close()


async def demo_05_file_writing_streaming():
    """示例 5: 流式文件写入"""
    print("\n" + "=" * 70)
    print("示例 5: 流式文件写入")
    print("=" * 70 + "\n")

    config = load_config()
    api_key = get_api_key(config)
    base_url = get_base_url(config)
    model = get_model(config)

    agent = FastReAct(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    query = "创建一个 Python 文件 hello.py，打印 'Hello World'"
    print(f"Query: {query}\n")

    async for chunk in agent.run_streaming(query):
        if chunk.type == StreamChunkType.TOOL_CALL:
            if chunk.tool_name == "write_file":
                print(f"[Creating] {chunk.tool_params.get('path', 'file')}")
        elif chunk.type == StreamChunkType.TOOL_RESULT:
            if "written" in chunk.content:
                print(f"[Success] {chunk.content}")
        elif chunk.type == StreamChunkType.ANSWER:
            print(f"\n[Answer] {chunk.content}")

    await agent.close()


async def demo_06_sse_format():
    """示例 6: SSE 格式输出"""
    print("\n" + "=" * 70)
    print("示例 6: SSE 格式输出（模拟 Server-Sent Events）")
    print("=" * 70 + "\n")

    config = load_config()
    api_key = get_api_key(config)
    base_url = get_base_url(config)
    model = get_model(config)

    agent = FastReAct(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    query = "什么是 Python？"
    print(f"Query: {query}\n")

    # 输出 SSE 格式
    async for chunk in agent.run_streaming(query):
        sse_data = chunk.to_sse()
        print(sse_data.strip())

    await agent.close()


async def main():
    """运行所有示例"""
    print("\n" + "=" * 70)
    print("FastReAct V2 流式响应演示")
    print("=" * 70)

    # 检查配置
    try:
        config = load_config()
        api_key = get_api_key(config)
        if not api_key:
            print("\n[WARNING]  警告: 请配置 API Key")
            print("   方式 1: 设置 FASTREACT_API_KEY 环境变量")
            print("   方式 2: 在 ~/.fastreact/config.json 中配置")
            return

        model = get_model(config)
        print(f"\n✓ 配置已加载")
        print(f"  Model: {model}")
        print(f"  Base URL: {get_base_url(config)}")
    except Exception as e:
        print(f"\n[ERROR] 配置加载失败: {e}")
        return

    try:
        # 运行示例
        await demo_01_basic_streaming()
        await demo_02_filter_thinking()
        await demo_03_collect_results()
        await demo_04_custom_processor()
        await demo_05_file_writing_streaming()
        await demo_06_sse_format()

        print("\n" + "=" * 70)
        print("所有示例运行完成！")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
