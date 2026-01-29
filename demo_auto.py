"""
FastReAct 自动演示程序

自动运行并展示 FastReAct 的核心功能
"""

import asyncio
import json
import os

from fastreact import FastReAct
from fastreact.tools import (
    CalculatorTool,
    GetCurrentTimeTool,
    GetDateInfoTool,
)


def load_config():
    """加载配置文件"""
    config_path = "config.json"

    if not os.path.exists(config_path):
        print(f"[ERROR] 配置文件不存在: {config_path}")
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


async def run_demo():
    """运行自动演示"""
    print("=" * 70)
    print("FastReAct 自动演示")
    print("=" * 70)

    # 加载配置
    config = load_config()
    if not config:
        return

    print(f"\n[配置信息]")
    print(f"  API: {config['base_url']}")
    print(f"  Model: {config['model']}")

    # 创建 Agent
    print(f"\n[初始化 Agent]")
    print(f"  工具: CalculatorTool, GetCurrentTimeTool, GetDateInfoTool")

    agent = FastReAct(
        api_key=config["api_key"],
        base_url=config["base_url"],
        model=config["model"],
        tools=[
            CalculatorTool(),
            GetCurrentTimeTool(),
            GetDateInfoTool()
        ],
        max_iterations=5
    )

    # 演示问题列表
    demos = [
        {
            "name": "计算器演示",
            "question": "计算 123 + 456 等于多少？",
        },
        {
            "name": "时间查询演示",
            "question": "现在北京时间几点？请用 ISO 格式输出",
        },
        {
            "name": "日期信息演示",
            "question": "今天是几号？是星期几？",
        },
        {
            "name": "复杂计算演示",
            "question": "先计算 15 + 25，然后把结果乘以 2",
        },
    ]

    # 运行演示
    for i, demo in enumerate(demos, 1):
        print(f"\n{'=' * 70}")
        print(f"[演示 {i}/{len(demos)}] {demo['name']}")
        print(f"{'=' * 70}")
        print(f"\n问题: {demo['question']}")
        print(f"\nAI 思考中...\n")

        try:
            result = await agent.run_async(demo['question'])
            answer = result['answer'] if isinstance(result, dict) else result
            print(f"[回答]")
            print(f"{answer}")
        except Exception as e:
            print(f"[错误] {e}")
            import traceback
            traceback.print_exc()

    # 关闭
    await agent.close()

    print(f"\n{'=' * 70}")
    print("[演示完成]")
    print(f"{'=' * 70}")
    print("\nFastReAct 核心功能:")
    print("  ✓ ReAct 工具自动调用")
    print("  ✓ 多工具协同工作")
    print("  ✓ AI 推理和决策")
    print("  ✓ 会话记忆管理")
    print("\n更多信息请查看:")
    print("  - README.md")
    print("  - docs/ 目录")
    print("  - examples/ 目录")


if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\n[BYE] Goodbye!")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
