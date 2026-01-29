"""
Tavily 搜索演示 - 直接传入 API Key
"""

import asyncio
from fastreact import FastReAct
from fastreact.tools import TavilySearchTool

# 在这里填写你的 Tavily API Key
TAVILY_API_KEY = "your-tavily-api-key-here"  # 替换为你的 API Key


async def main():
    if TAVILY_API_KEY == "your-tavily-api-key-here":
        print("[ERROR] 请先在代码中填写你的 Tavily API Key")
        print("\n获取 API Key:")
        print("  1. 访问: https://tavily.com/")
        print("  2. 注册账号")
        print("  3. 在 Dashboard 获取 API Key")
        print("  4. 将 API Key 填写到代码中的 TAVILY_API_KEY 变量")
        return

    # 创建 Tavily 搜索工具
    search_tool = TavilySearchTool(api_key=TAVILY_API_KEY)

    # 创建 Agent
    agent = FastReAct(
        api_key="your-fastreact-api-key",  # 你的 FastReAct API Key
        model="deepseek-ai/DeepSeek-V3",
        tools=[search_tool],
        max_iterations=5
    )

    print("=" * 70)
    print("Tavily 搜索演示")
    print("=" * 70)

    questions = [
        "搜索最新的 AI 新闻",
        "查找 Python 3.12 的新特性",
        "搜索 FastReAct 框架相关信息"
    ]

    for question in questions:
        print(f"\n问题: {question}")
        print("-" * 70)
        try:
            response = await agent.run_async(question)
            print(f"回答: {response}\n")
        except Exception as e:
            print(f"[ERROR] {e}\n")

    await agent.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[BYE] Goodbye!")
