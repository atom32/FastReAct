"""
FastReAct + Tavily 搜索演示

演示如何使用 Tavily 搜索工具进行实时网络搜索。
"""

import asyncio
import os
import json
from fastreact import FastReAct
# Note: TavilySearchTool still uses class-based API
from fastreact.tools import TavilySearchTool


async def main():
    print("=" * 60)
    print("FastReAct + Tavily Search Demo")
    print("=" * 60)

    # 读取配置
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        # 读取 LLM 配置
        default_provider = config.get("default_provider", "siliconflow")
        provider_config = config["llm"]["providers"].get(default_provider, {})
        llm_api_key = provider_config.get("api_key")
        llm_model = provider_config.get("model", "deepseek-ai/DeepSeek-V3")

        # 读取 Tavily 配置（如果在 config.json 中）
        tavily_api_key = config.get("tavily_api_key") or os.getenv("TAVILY_API_KEY")

    except Exception as e:
        print(f"\n[ERROR] Config load failed: {e}")
        return

    if not llm_api_key:
        print("\n[ERROR] LLM API Key not found")
        return

    # 创建 Tavily 搜索工具
    print("\n[*] Initializing Tavily Search Tool...")
    search_tool = TavilySearchTool(api_key=tavily_api_key)

    # 创建 FastReAct Agent
    print(f"[*] Initializing FastReAct Agent (model: {llm_model})...")
    agent = FastReAct(
        api_key=llm_api_key,
        model=llm_model,
        tools=[search_tool],  # 添加搜索工具
        max_iterations=5,
        verbose=False
    )

    print("[OK] Ready!\n")
    print("Commands:")
    print("  - Ask any question (AI will search the web)")
    print("  - Type 'quit' or 'exit' to exit")
    print("  - Type 'reset' to reset conversation")
    print("-" * 60)

    session_id = "tavily_search_session"

    # 示例查询
    examples = [
        "最新的 AI 新闻是什么？",
        "Python asyncio 怎么用？",
        "2024年有哪些科技突破？",
        "如何使用 LangChain？"
    ]

    print("\nExample queries you can try:")
    for i, example in enumerate(examples, 1):
        print(f"  {i}. {example}")

    while True:
        try:
            # 获取用户输入
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            # 检查退出命令
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n[BYE] Goodbye!")
                break

            # 检查重置命令
            if user_input.lower() == 'reset':
                print("\n[RESET] Conversation reset")
                session_id = f"tavily_search_{asyncio.get_event_loop().time()}"
                continue

            # 运行 Agent
            print("\nAI: ", end="", flush=True)
            response = await agent.run(
                query=user_input,
                session_id=session_id
            )
            print(response)

        except KeyboardInterrupt:
            print("\n\n[BYE] Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("Please try again or type 'quit' to exit")

    # 清理
    await agent.close()
    await search_tool.close()


async def test_search():
    """测试搜索功能"""
    print("=" * 60)
    print("Tavily Search Test")
    print("=" * 60)

    # 从环境变量或配置读取 API Key
    tavily_api_key = os.getenv("TAVILY_API_KEY")

    if not tavily_api_key:
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                tavily_api_key = config.get("tavily_api_key")
        except:
            pass

    if not tavily_api_key:
        print("\n[WARN] TAVILY_API_KEY not set, using fallback search")
        print("Get your API key at: https://tavily.com/")

    # 创建搜索工具
    search = TavilySearchTool(api_key=tavily_api_key)

    # 测试搜索
    test_queries = [
        "Python asyncio tutorial",
        "latest AI news 2024",
        "LangChain 快速入门"
    ]

    for query in test_queries:
        print(f"\n[*] Searching: {query}")
        print("-" * 60)

        try:
            result = await search.execute_async(query, max_results=3)
            print(result)
        except Exception as e:
            print(f"[ERROR] {e}")

        print()

    await search.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 运行测试
        asyncio.run(test_search())
    else:
        # 运行交互式对话
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n\n[BYE] Goodbye!")
