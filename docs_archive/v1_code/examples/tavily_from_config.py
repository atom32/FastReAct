"""
从 config.json 读取 Tavily API Key 的演示
"""

import asyncio
import json
from fastreact import FastReAct
# Note: TavilySearchTool still uses class-based API
from fastreact.tools import TavilySearchTool


def get_tavily_api_key():
    """从 config.json 读取 Tavily API Key"""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        tavily_key = config.get("tools", {}).get("tavily", {}).get("api_key")

        if not tavily_key:
            print("[ERROR] Tavily API Key 未配置")
            print("\n请在 config.json 的 tools.tavily.api_key 中填入你的 API Key")
            print("获取 API Key: https://tavily.com/")
            return None

        return tavily_key
    except Exception as e:
        print(f"[ERROR] 读取配置文件失败: {e}")
        return None


async def main():
    # 读取 Tavily API Key
    tavily_api_key = get_tavily_api_key()
    if not tavily_api_key:
        return

    print(f"[OK] Tavily API Key 已加载")

    # 读取 LLM 配置
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        default_provider = config.get("default_provider", "siliconflow")
        provider_config = config["llm"]["providers"].get(default_provider, {})

        llm_api_key = provider_config.get("api_key")
        llm_base_url = provider_config.get("base_url", "https://api.siliconflow.cn/v1")
        llm_model = provider_config.get("model", "deepseek-ai/DeepSeek-V3")

    except Exception as e:
        print(f"[ERROR] 读取 LLM 配置失败: {e}")
        return

    # 创建 Tavily 搜索工具
    search_tool = TavilySearchTool(api_key=tavily_api_key)

    # 创建 Agent
    agent = FastReAct(
        api_key=llm_api_key,
        base_url=llm_base_url,
        model=llm_model,
        tools=[search_tool],
        max_iterations=5
    )

    print("=" * 70)
    print("Tavily 搜索演示（从 config.json 读取 API Key）")
    print("=" * 70)

    questions = [
        "搜索最新的 Python 新闻",
        "查找 FastReAct 框架相关信息",
    ]

    for question in questions:
        print(f"\n问题: {question}")
        print("-" * 70)
        try:
            result = await agent.run_async(question)
            answer = result['answer'] if isinstance(result, dict) else result
            print(f"回答: {answer}\n")
        except Exception as e:
            print(f"[ERROR] {e}\n")

    await agent.close()

    print("\n" + "=" * 70)
    print("演示完成！")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[BYE] Goodbye!")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
