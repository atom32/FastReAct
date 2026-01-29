"""
FastReAct 完整演示程序

展示 FastReAct 的核心功能：
1. ReAct 工具调用
2. 多种工具使用
3. AI 推理过程
"""

import asyncio
import json
import os
import sys
from typing import Optional

from fastreact import FastReAct
from fastreact.tools import (
    CalculatorTool,
    GetCurrentTimeTool,
    GetDateInfoTool,
    HTTPTool,
)


def load_config():
    """加载配置文件"""
    config_path = "config.json"

    if not os.path.exists(config_path):
        print(f"[ERROR] 配置文件不存在: {config_path}")
        print("\n请创建配置文件，格式如下:")
        print(json.dumps({
            "api_key": "your-api-key",
            "base_url": "https://api.siliconflow.cn/v1",
            "model": "deepseek-ai/DeepSeek-V3"
        }, indent=2))
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 支持多种配置格式
    if "api_key" in config:
        return {
            "api_key": config["api_key"],
            "base_url": config.get("base_url", "https://api.siliconflow.cn/v1"),
            "model": config.get("model", "deepseek-ai/DeepSeek-V3")
        }
    elif "llm" in config and "providers" in config["llm"]:
        default_provider = config.get("default_provider", "siliconflow")
        provider_config = config["llm"]["providers"].get(default_provider, {})
        return {
            "api_key": provider_config.get("api_key"),
            "base_url": provider_config.get("base_url", "https://api.siliconflow.cn/v1"),
            "model": provider_config.get("model", "deepseek-ai/DeepSeek-V3")
        }
    else:
        print("[ERROR] 无法识别的配置文件格式")
        return None


async def demo_calculator():
    """演示 1: 计算器工具"""
    print("\n" + "=" * 70)
    print("[演示 1] 计算器工具")
    print("=" * 70)

    config = load_config()
    if not config:
        return

    agent = FastReAct(
        api_key=config["api_key"],
        base_url=config["base_url"],
        model=config["model"],
        tools=[CalculatorTool()],
        max_iterations=5
    )

    questions = [
        "计算 123 + 456",
        "计算 (15 + 25) * 2",
        "2 的 10 次方是多少？"
    ]

    for question in questions:
        print(f"\n问题: {question}")
        print("-" * 70)
        try:
            result = await agent.run_async(question)
            answer = result['answer'] if isinstance(result, dict) else result
            print(f"回答: {answer}")
        except Exception as e:
            print(f"[ERROR] {e}")

    await agent.close()


async def demo_datetime():
    """演示 2: 日期时间工具"""
    print("\n" + "=" * 70)
    print("[演示 2] 日期时间工具")
    print("=" * 70)

    config = load_config()
    if not config:
        return

    agent = FastReAct(
        api_key=config["api_key"],
        base_url=config["base_url"],
        model=config["model"],
        tools=[GetCurrentTimeTool(), GetDateInfoTool()],
        max_iterations=5
    )

    questions = [
        "现在北京时间几点？",
        "今天是什么日子？给我详细信息",
        "2024年2月29日是星期几？"
    ]

    for question in questions:
        print(f"\n问题: {question}")
        print("-" * 70)
        try:
            result = await agent.run_async(question)
            answer = result['answer'] if isinstance(result, dict) else result
            print(f"回答: {answer}")
        except Exception as e:
            print(f"[ERROR] {e}")

    await agent.close()


async def demo_http_request():
    """演示 3: HTTP 请求工具"""
    print("\n" + "=" * 70)
    print("[演示 3] HTTP 请求工具")
    print("=" * 70)

    config = load_config()
    if not config:
        return

    agent = FastReAct(
        api_key=config["api_key"],
        base_url=config["base_url"],
        model=config["model"],
        tools=[HTTPTool()],
        max_iterations=5
    )

    questions = [
        "帮我访问 https://httpbin.org/get 并告诉我返回的内容",
    ]

    for question in questions:
        print(f"\n问题: {question}")
        print("-" * 70)
        try:
            response = await agent.run_async(question)
            print(f"回答: {response[:500]}...")
        except Exception as e:
            print(f"[ERROR] {e}")

    await agent.close()


async def demo_multi_tool():
    """演示 4: 多工具协同"""
    print("\n" + "=" * 70)
    print("[演示 4] 多工具协同")
    print("=" * 70)

    config = load_config()
    if not config:
        return

    agent = FastReAct(
        api_key=config["api_key"],
        base_url=config["base_url"],
        model=config["model"],
        tools=[
            CalculatorTool(),
            GetCurrentTimeTool(),
            GetDateInfoTool(),
            HTTPTool()
        ],
        max_iterations=5
    )

    questions = [
        "现在几点了？然后再帮我算一下 100 除以 3 等于多少",
        "今天是几号？请帮我查询一下今天的日期信息",
    ]

    for question in questions:
        print(f"\n问题: {question}")
        print("-" * 70)
        try:
            result = await agent.run_async(question)
            answer = result['answer'] if isinstance(result, dict) else result
            print(f"回答: {answer}")
        except Exception as e:
            print(f"[ERROR] {e}")

    await agent.close()


async def demo_interactive():
    """演示 5: 交互式对话"""
    print("\n" + "=" * 70)
    print("[演示 5] 交互式对话模式")
    print("=" * 70)

    config = load_config()
    if not config:
        return

    agent = FastReAct(
        api_key=config["api_key"],
        base_url=config["base_url"],
        model=config["model"],
        tools=[
            CalculatorTool(),
            GetCurrentTimeTool(),
            GetDateInfoTool(),
            HTTPTool()
        ],
        max_iterations=5
    )

    print("\n可用工具:")
    print("  - 计算器: 可以进行数学计算")
    print("  - 时间查询: 可以查询当前时间和日期信息")
    print("  - HTTP 请求: 可以访问网页 API")
    print("\n示例问题:")
    print("  - '123 + 456 等于多少？'")
    print("  - '现在北京时间几点？'")
    print("  - '今天是几号？'")
    print("  - '访问 https://httpbin.org/get'")
    print("\n输入 'quit' 或 'exit' 退出\n")

    session_id = "demo_session"

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n[BYE] Goodbye!")
                break

            print("\nAI: ", end="", flush=True)
            result = await agent.run_async(user_input)
            answer = result['answer'] if isinstance(result, dict) else result
            print(answer)

        except KeyboardInterrupt:
            print("\n\n[BYE] Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("请重试或输入 'quit' 退出")

    await agent.close()


async def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║         FastReAct 完整演示程序                            ║
╚══════════════════════════════════════════════════════════╝

本演示程序展示 FastReAct 的核心功能：
    1. ReAct 工具自动调用
    2. 多种工具使用
    3. AI 推理过程
    4. 多工具协同工作
    5. 交互式对话

请选择演示模式：
    1 - 计算器演示
    2 - 日期时间演示
    3 - HTTP 请求演示
    4 - 多工具协同演示
    5 - 交互式对话
    0 - 退出
    """)

    # 检查配置
    config = load_config()
    if not config:
        return

    print(f"[OK] 配置加载成功")
    print(f"    API: {config['base_url']}")
    print(f"    Model: {config['model']}")
    print()

    while True:
        try:
            choice = input("请选择 (0-5): ").strip()

            if not choice:
                continue

            if choice == '0':
                print("\n[BYE] Goodbye!")
                break
            elif choice == '1':
                await demo_calculator()
            elif choice == '2':
                await demo_datetime()
            elif choice == '3':
                await demo_http_request()
            elif choice == '4':
                await demo_multi_tool()
            elif choice == '5':
                await demo_interactive()
            else:
                print("[ERROR] 无效选择，请输入 0-5")

            print("\n" + "=" * 70)
            input("按回车继续...")
            print("\n" + "=" * 70)

        except KeyboardInterrupt:
            print("\n\n[BYE] Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[BYE] Goodbye!")
