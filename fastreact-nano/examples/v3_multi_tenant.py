#!/usr/bin/env python3
"""
FastReAct Nano - v3: Multi-Tenant Session Management
展示多租户会话隔离和内存管理
"""

import asyncio
from fastreact import Agent

async def main():
    """
    展示多租户场景：不同用户拥有独立的会话
    """
    print("=" * 60)
    print("FastReAct Nano v3: Multi-Tenant Demo")
    print("=" * 60)
    print()

    # 创建两个模拟用户
    users = {
        "alice": "用户A - 前端开发者",
        "bob": "用户B - 后端开发者"
    }

    # 模拟多用户并发使用
    async def user_session(user_id: str, user_desc: str):
        """模拟用户会话"""
        agent = Agent()

        print(f"[{user_id}] 开始会话: {user_desc}")

        # 查询 1
        query1 = f"我叫{user_id}，请记住我的名字"
        response1 = await agent.ask(query1)
        print(f"[{user_id}] 记住了: {response1[:50]}...")

        # 查询 2（验证记忆）
        query2 = "我叫什么名字？"
        response2 = await agent.ask(query2)
        print(f"[{user_id}] 回忆验证: {response2[:50]}...")
        print()

    # 并发运行两个用户会话
    await asyncio.gather(
        user_session("alice", users["alice"]),
        user_session("bob", users["bob"])
    )

    print("[完成] 两个用户会话独立运行，互不干扰")

if __name__ == "__main__":
    asyncio.run(main())
