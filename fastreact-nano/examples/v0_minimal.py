#!/usr/bin/env python3
"""
FastReAct Nano - v0: Minimal Core Concept
展示 180 行 Brain-Body 分离架构的核心概念
"""

import asyncio
from fastreact import ask

async def main():
    """
    最简示例：展示核心架构
    """
    # 运行查询（使用便利函数）
    response = await ask("什么是 FastReAct Nano？用一句话回答")

    print(f"回答: {response}")

if __name__ == "__main__":
    asyncio.run(main())
