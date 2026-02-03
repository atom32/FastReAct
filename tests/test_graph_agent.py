"""
测试 GraphAgent - 基于 Tool Graph 的 Agent
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from fastreact.graph import (
    GraphAgent,
    AgentConfig,
    ExecutionStrategy,
    create_graph_agent,
)


# ============================================================================
# 测试工具函数
# ============================================================================

async def mock_search_tool(query: str) -> str:
    """模拟搜索工具"""
    await asyncio.sleep(0.01)
    return f"Search results for: {query}"


async def mock_write_tool(path: str, content: str) -> str:
    """模拟写入工具"""
    await asyncio.sleep(0.01)
    return f"Written to {path}"


async def mock_read_tool(path: str) -> str:
    """模拟读取工具"""
    await asyncio.sleep(0.01)
    return f"Content of {path}"


# ============================================================================
# Mock LLM Client
# ============================================================================

class MockLLMClient:
    """模拟 LLM 客户端"""

    def __init__(self):
        self.model = "gpt-4"

    class ChatCompletions:
        def __init__(self, parent):
            self.parent = parent

        async def create(self, **kwargs):
            response = MagicMock()
            response.choices = [MagicMock()]

            # 根据提示词返回不同的响应
            messages = kwargs.get("messages", [])
            content = messages[-1].get("content", "") if messages else ""

            if "planning" in content.lower() or "plan" in content.lower():
                # 返回计划格式的 JSON
                response.choices[0].message.content = '''```json
{
  "goal": "Search and write results",
  "description": "Search for information and write to file",
  "steps": [
    {
      "step_id": "search",
      "tool": "search",
      "description": "Search for information",
      "inputs": {"query": "test query"},
      "dependencies": []
    },
    {
      "step_id": "write",
      "tool": "write",
      "description": "Write results to file",
      "inputs": {"path": "output.txt", "content": "Results"},
      "dependencies": ["search"]
    }
  ]
}
```'''
            else:
                # 返回普通响应
                response.choices[0].message.content = "Task completed successfully. Search was performed and results were written to file."

            return response

    def __init__(self):
        self.model = "gpt-4"
        self.chat = MagicMock()
        self.chat.completions = self.ChatCompletions(self)


# ============================================================================
# 测试 GraphAgent
# ============================================================================

class TestGraphAgent:
    """测试 GraphAgent"""

    @pytest.fixture
    def llm_client(self):
        """创建模拟 LLM 客户端"""
        return MockLLMClient()

    @pytest.fixture
    def tools(self):
        """创建工具字典"""
        return {
            "search": mock_search_tool,
            "write": mock_write_tool,
            "read": mock_read_tool,
        }

    @pytest.fixture
    def agent(self, llm_client, tools):
        """创建 GraphAgent"""
        return create_graph_agent(llm_client=llm_client, tools=tools)

    @pytest.mark.asyncio
    async def test_agent_creation(self, llm_client, tools):
        """测试创建 Agent"""
        agent = GraphAgent(llm_client=llm_client, tools=tools)

        assert agent.llm_client is llm_client
        assert agent.tools == tools
        assert agent.config is not None

    @pytest.mark.asyncio
    async def test_agent_run(self, agent):
        """测试运行 Agent"""
        result = await agent.run("Search for Python info and write to file")

        assert result is not None
        assert "response" in result
        assert "plan" in result
        assert "report" in result
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_agent_run_with_context(self, agent):
        """测试带上下文运行 Agent"""
        result = await agent.run(
            "Search and write",
            context={"user_id": "123"},
        )

        assert result is not None
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_agent_stream(self, agent):
        """测试流式运行 Agent"""
        events = []

        async for event in agent.stream("Search for info"):
            events.append(event)

        # 应该包含多种事件类型
        event_types = [e["type"] for e in events]

        assert "start" in event_types
        assert "planning" in event_types
        assert "plan_generated" in event_types
        assert "graph_ready" in event_types
        assert "execution_complete" in event_types
        assert "done" in event_types

    @pytest.mark.asyncio
    async def test_agent_with_custom_config(self, llm_client, tools):
        """测试自定义配置"""
        config = AgentConfig(
            execution_strategy=ExecutionStrategy.TOPOLOGICAL,
            max_parallel=5,
            enable_visualization=False,
        )

        agent = GraphAgent(llm_client=llm_client, tools=tools, config=config)

        assert agent.config.execution_strategy == ExecutionStrategy.TOPOLOGICAL
        assert agent.config.max_parallel == 5
        assert agent.config.enable_visualization is False


class TestAgentConfig:
    """测试 Agent 配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = AgentConfig()

        assert config.execution_strategy == ExecutionStrategy.LEVEL_BASED
        assert config.max_parallel == 3
        assert config.timeout == 300.0
        assert config.continue_on_error is False
        assert config.enable_visualization is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = AgentConfig(
            execution_strategy=ExecutionStrategy.MAX_PARALLEL,
            max_parallel=10,
            timeout=600.0,
            continue_on_error=True,
            enable_visualization=False,
        )

        assert config.execution_strategy == ExecutionStrategy.MAX_PARALLEL
        assert config.max_parallel == 10
        assert config.timeout == 600.0
        assert config.continue_on_error is True
        assert config.enable_visualization is False


# ============================================================================
# 测试工厂函数
# ============================================================================

class TestFactoryFunctions:
    """测试工厂函数"""

    @pytest.mark.asyncio
    async def test_create_graph_agent(self):
        """测试创建 GraphAgent"""
        llm_client = MockLLMClient()
        tools = {"test": mock_search_tool}

        agent = create_graph_agent(llm_client=llm_client, tools=tools)

        assert isinstance(agent, GraphAgent)


# ============================================================================
# 测试边界情况
# ============================================================================

class TestEdgeCases:
    """测试边界情况"""

    @pytest.fixture
    def llm_client(self):
        """创建模拟 LLM 客户端"""
        return MockLLMClient()

    @pytest.mark.asyncio
    async def test_empty_tools(self):
        """测试空工具列表"""
        llm_client = MockLLMClient()

        agent = create_graph_agent(llm_client=llm_client, tools={})

        # 计划生成会失败，因为没有可用工具
        result = await agent.run("Test query")

        # 应该返回某种结果（即使失败）
        assert result is not None

    @pytest.mark.asyncio
    async def test_plan_with_missing_tool(self, llm_client):
        """测试计划包含不存在的工具"""
        tools = {
            "search": mock_search_tool,
            # "write" 工具不存在
        }

        agent = create_graph_agent(llm_client=llm_client, tools=tools)

        result = await agent.run("Search and write")

        # 应该跳过不存在的工具
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
