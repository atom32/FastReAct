"""
测试多智能体系统
"""

import pytest
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastreact import FastReAct
from fastreact.tools import CalculatorTool
from fastreact.agents import (
    AgentRouter,
    create_agent_from_fastreact,
    ResearchAgent,
    CodeAgent,
    GeneralAgent
)


@pytest.fixture
def fastreact():
    """创建 FastReAct 实例"""
    return FastReAct(
        api_key="test-key",
        model="gpt-4",
        tools=[CalculatorTool()],
        max_iterations=2,
    )


@pytest.fixture
def router(fastreact):
    """创建路由器并注册智能体"""
    router = AgentRouter()

    # 注册智能体
    researcher = create_agent_from_fastreact(
        name="researcher",
        role="研究专家",
        description="擅长研究",
        fastreact=fastreact
    )
    router.register_agent(researcher)

    coder = create_agent_from_fastreact(
        name="coder",
        role="编程专家",
        description="擅长编程",
        fastreact=fastreact
    )
    router.register_agent(coder)

    general = create_agent_from_fastreact(
        name="general",
        role="通用助手",
        description="通用",
        fastreact=fastreact
    )
    router.register_agent(general)

    return router


@pytest.mark.asyncio
class TestAgentRouter:
    """测试智能体路由器"""

    async def test_register_agent(self, router):
        """测试注册智能体"""
        assert len(router.agents) == 3
        assert "researcher" in router.agents
        assert "coder" in router.agents
        assert "general" in router.agents

    async def test_list_agents(self, router):
        """测试列出智能体"""
        agents = router.list_agents()
        assert len(agents) == 3

        agent_names = [a["name"] for a in agents]
        assert "researcher" in agent_names
        assert "coder" in agent_names
        assert "general" in agent_names

    async def test_automatic_routing(self, router):
        """测试自动路由"""
        # 代码任务应该路由到 coder
        agent = router.route("帮我写一个Python函数")
        assert agent.name == "coder"

        # 研究任务应该路由到 researcher
        agent = router.route("研究一下人工智能的发展")
        assert agent.name == "researcher"

        # 通用任务应该路由到 general
        agent = router.route("今天天气怎么样")
        assert agent.name == "general"

    async def test_force_agent(self, router):
        """测试强制指定智能体"""
        agent = router.route("写代码", force_agent="researcher")
        assert agent.name == "researcher"

    async def test_session_binding(self, router):
        """测试会话绑定"""
        session_id = "test_session"

        # 绑定会话
        result = router.bind_session_agent(session_id, "coder")
        assert result is True
        assert router.get_session_agent(session_id) == "coder"

        # 验证路由使用绑定
        agent = router.route("随便什么任务", session_id=session_id)
        assert agent.name == "coder"

        # 解绑会话
        result = router.unbind_session(session_id)
        assert result is True
        assert router.get_session_agent(session_id) is None

    async def test_unbind_nonexistent_session(self, router):
        """测试解绑不存在的会话"""
        result = router.unbind_session("nonexistent")
        assert result is False

    async def test_bind_unknown_agent(self, router):
        """测试绑定到不存在的智能体"""
        result = router.bind_session_agent("test", "unknown")
        assert result is False

    async def test_get_agent(self, router):
        """测试获取智能体"""
        agent = router.get_agent("coder")
        assert agent is not None
        assert agent.name == "coder"

        agent = router.get_agent("unknown")
        assert agent is None

    async def test_router_stats(self, router):
        """测试路由器统计"""
        stats = router.get_stats()
        assert stats["total_agents"] == 3
        assert stats["default_agent"] == "general"
        assert "coder" in stats["agents"]
        assert len(stats["agents"]) == 3


@pytest.mark.asyncio
class TestAgentExecution:
    """测试智能体执行"""

    async def test_agent_execute(self, fastreact):
        """测试智能体执行"""
        agent = create_agent_from_fastreact(
            name="test_agent",
            role="测试",
            description="测试智能体",
            fastreact=fastreact
        )

        result = await agent.execute(
            task="计算 2+2"
        )

        assert result is not None
        assert "success" in result

    async def test_agent_error_handling(self, fastreact):
        """测试智能体错误处理"""
        agent = create_agent_from_fastreact(
            name="test_agent",
            role="测试",
            description="测试智能体",
            fastreact=fastreact
        )

        # 正常执行（会尝试连接API，可能失败）
        result1 = await agent.execute(task="简单任务")
        assert result1 is not None
        assert "success" in result1

        # 检查统计已更新
        assert "tasks_completed" in agent.stats
        assert "errors" in agent.stats


@pytest.mark.asyncio
class TestAgentCollaboration:
    """测试智能体协作"""

    async def test_parallel_execution(self, fastreact):
        """测试并行执行多个智能体"""
        router = AgentRouter()

        agent1 = create_agent_from_fastreact(
            name="agent1",
            role="助手1",
            description="助手1",
            fastreact=fastreact
        )
        router.register_agent(agent1)

        agent2 = create_agent_from_fastreact(
            name="agent2",
            role="助手2",
            description="助手2",
            fastreact=fastreact
        )
        router.register_agent(agent2)

        # 并行执行
        tasks = [
            agent1.execute(task="任务1"),
            agent2.execute(task="任务2")
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 2
        assert all(r is not None for r in results)

    async def test_task_delegation(self, router):
        """测试任务委派"""
        # 通用智能体可以将任务委派给专用智能体
        general_agent = router.get_agent("general")

        # 模拟通用智能体委派任务给代码智能体
        task = "帮我写一个排序算法"
        specialized_agent = router.route(task)

        assert specialized_agent.name == "coder"
