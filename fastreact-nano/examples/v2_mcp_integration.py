#!/usr/bin/env python3
"""
FastReAct Nano - v2: MCP Server Integration
展示如何使用 MCP 工具扩展功能
"""

import asyncio
from fastreact import Agent

async def main():
    """
    展示 MCP 工具使用
    """
    # 创建 Agent（会自动加载 MCP 服务器）
    agent = Agent()

    print("=" * 60)
    print("FastReAct Nano v2: MCP Integration Demo")
    print("=" * 60)
    print()

    # 查询需要使用 GraphRAG MCP 工具
    query = "什么是 GraphRAG？它有什么优势？"
    print(f"用户查询: {query}\n")

    print("已加载的 MCP 服务器:")
    print("  - graphrag: 知识图谱查询工具")
    print("  - filesystem: 文件操作工具")
    print("  - fetch: HTTP 请求工具")
    print()

    # 运行查询
    response = await agent.ask(query)

    print(f"\n回答:\n{response}")

if __name__ == "__main__":
    asyncio.run(main())
