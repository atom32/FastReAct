"""
多智能体系统演示

演示智能体路由、智能体通信和协作功能。
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastreact import FastReAct
from fastreact.tools import create_calculator_tool
from fastreact.agents import (
    AgentRouter,
    create_agent_from_fastreact,
    SessionsListTool,
    ConsultAgentTool
)


async def demo_multi_agent():
    """演示多智能体系统"""
    print("=" * 60)
    print("FastReAct Multi-Agent System Demo")
    print("=" * 60)

    # 创建 FastReAct 实例
    print("\n[1/7] Creating FastReAct instance...")
    fastreact = FastReAct(
        api_key="test-key",
        model="gpt-4",
        tools=[create_calculator_tool()],
        max_iterations=2,
    )
    print("OK - FastReAct instance created")

    # 创建智能体路由器
    print("\n[2/7] Creating agent router...")
    router = AgentRouter()

    # 创建并注册智能体
    print("\n[3/7] Creating specialized agents...")

    researcher = create_agent_from_fastreact(
        name="researcher",
        role="研究专家",
        description="擅长信息搜索、数据收集和分析",
        fastreact=fastreact
    )
    router.register_agent(researcher)
    print("  - Research agent registered")

    coder = create_agent_from_fastreact(
        name="coder",
        role="编程专家",
        description="擅长编程、代码审查和调试",
        fastreact=fastreact
    )
    router.register_agent(coder)
    print("  - Code agent registered")

    creator = create_agent_from_fastreact(
        name="creator",
        role="创意专家",
        description="擅长文案创作和内容设计",
        fastreact=fastreact
    )
    router.register_agent(creator)
    print("  - Creative agent registered")

    general_agent = create_agent_from_fastreact(
        name="general",
        role="通用助手",
        description="处理各类任务的通用智能体",
        fastreact=fastreact
    )
    router.register_agent(general_agent)
    print("  - General agent registered")

    # 查看所有智能体
    print("\n[4/7] Listing all agents...")
    agents = router.list_agents()
    print(f"Total agents: {len(agents)}")
    for agent_info in agents:
        print(f"  - {agent_info['name']}: {agent_info['role']}")

    # 测试自动路由
    print("\n[5/7] Testing automatic routing...")
    test_tasks = [
        "帮我写一个排序算法",
        "分析一下2024年的AI发展趋势",
        "创建一个产品宣传文案",
        "今天天气怎么样"
    ]

    for task in test_tasks:
        agent = router.route(task)
        print(f"  Task: {task[:30]}")
        print(f"  -> Routed to: {agent.name} ({agent.role})")

    # 测试会话绑定
    print("\n[6/7] Testing session binding...")
    session_id = "test_session_123"

    # 绑定会话到代码智能体
    router.bind_session_agent(session_id, "coder")
    bound_agent = router.get_session_agent(session_id)
    print(f"  Session {session_id} bound to: {bound_agent}")

    # 后续请求会自动路由到绑定的智能体
    follow_up_task = "这个函数有个bug"
    agent = router.route(follow_up_task, session_id=session_id)
    print(f"  Follow-up task routed to: {agent.name} (because of binding)")

    # 解绑会话
    router.unbind_session(session_id)
    print(f"  Session unbound")

    # 测试统计
    print("\n[7/7] Getting router stats...")
    stats = router.get_stats()
    print(f"  Total agents: {stats['total_agents']}")
    print(f"  Default agent: {stats['default_agent']}")
    print(f"  Available agents: {', '.join(stats['agents'])}")

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)

    print("\nKey Features Demonstrated:")
    print("  [v] Agent creation from FastReAct")
    print("  [v] Agent registration")
    print("  [v] Automatic task routing")
    print("  [v] Session-agent binding")
    print("  [v] Router statistics")

    print("\nNext Steps:")
    print("  - Implement agent-to-agent communication tools")
    print("  - Integrate with Gateway")
    print("  - Add comprehensive tests")

    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(demo_multi_agent())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
