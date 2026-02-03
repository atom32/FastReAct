"""
测试 Tool Graph 系统
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from fastreact.graph import (
    ToolNode,
    ToolGraph,
    ToolEdge,
    ParallelGroup,
    NodeStatus,
    NodeConfig,
    NodeResult,
    create_graph,
    create_pipeline,
    create_parallel_workflow,
    create_tool_node,
)


# ============================================================================
# 测试工具函数
# ============================================================================

async def mock_tool_a(**kwargs) -> dict:
    """模拟工具 A"""
    await asyncio.sleep(0.01)
    return {"result_a": "data_a"}


async def mock_tool_b(**kwargs) -> dict:
    """模拟工具 B"""
    await asyncio.sleep(0.01)
    return {"result_b": "data_b"}


async def mock_tool_c(**kwargs) -> dict:
    """模拟工具 C"""
    await asyncio.sleep(0.01)
    return {"result_c": "data_c"}


def sync_tool(**kwargs) -> dict:
    """同步工具"""
    return {"sync_result": "sync_data"}


# ============================================================================
# 测试 ToolNode
# ============================================================================

class TestToolNode:
    """测试工具节点"""

    def test_create_node(self):
        """测试创建节点"""
        node = create_tool_node(
            id="test_node",
            tool=mock_tool_a,
            inputs={"param1": str},
        )

        assert node.id == "test_node"
        assert node.is_async is True
        assert "param1" in node.inputs

    def test_sync_node_detection(self):
        """测试同步节点检测"""
        node = create_tool_node(
            id="sync_node",
            tool=sync_tool,
            inputs={},
        )

        assert node.is_async is False

    def test_node_config(self):
        """测试节点配置"""
        config = NodeConfig(retry=3, timeout=60.0)
        node = create_tool_node(
            id="config_node",
            tool=mock_tool_a,
            inputs={},
            config=config,
        )

        assert node.config.retry == 3
        assert node.config.timeout == 60.0

    def test_node_dependencies(self):
        """测试节点依赖"""
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})

        # 使用图连接节点，这样会自动更新双向关系
        graph = create_graph()
        graph.add_node(node1).add_node(node2)
        graph.connect("node1", "node2")

        assert "node1" in node2.get_dependencies()
        assert node2.id in node1.get_dependents()

    def test_rshift_operator(self):
        """测试 >> 操作符"""
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})

        edge = node1 >> node2

        assert isinstance(edge, ToolEdge)
        assert edge.source.id == "node1"
        assert edge.target.id == "node2"

    def test_or_operator(self):
        """测试 | 操作符"""
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})

        group = node1 | node2

        assert isinstance(group, ParallelGroup)
        assert len(group.nodes) == 2

    @pytest.mark.asyncio
    async def test_execute_async_tool(self):
        """测试执行异步工具"""
        node = create_tool_node("async_node", mock_tool_a, {})

        result = await node.execute({})

        assert isinstance(result, NodeResult)
        assert result.status == NodeStatus.COMPLETED
        assert "result_a" in result.outputs

    @pytest.mark.asyncio
    async def test_execute_sync_tool(self):
        """测试执行同步工具"""
        node = create_tool_node("sync_node", sync_tool, {})

        result = await node.execute({})

        assert isinstance(result, NodeResult)
        assert result.status == NodeStatus.COMPLETED
        assert "sync_result" in result.outputs

    @pytest.mark.asyncio
    async def test_execute_with_inputs(self):
        """测试带输入的执行"""
        async def tool_with_input(x: int, y: int) -> dict:
            return {"sum": x + y}

        node = create_tool_node(
            "sum_node",
            tool_with_input,
            inputs={"x": 1, "y": 2},  # 默认值
        )

        # 覆盖默认值
        result = await node.execute({"x": 10, "y": 20})

        assert result.outputs["sum"] == 30

    @pytest.mark.asyncio
    async def test_execute_with_error(self):
        """测试执行错误处理"""
        async def failing_tool(**kwargs):
            raise ValueError("Test error")

        node = create_tool_node("failing_node", failing_tool, {})

        result = await node.execute({})

        assert result.status == NodeStatus.FAILED
        assert "Test error" in result.error


# ============================================================================
# 测试 ToolGraph
# ============================================================================

class TestToolGraph:
    """测试工具图"""

    def test_create_graph(self):
        """测试创建图"""
        graph = create_graph("test_graph")

        assert graph.name == "test_graph"
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_add_node(self):
        """测试添加节点"""
        graph = create_graph()
        node = create_tool_node("node1", mock_tool_a, {})

        result = graph.add_node(node)

        assert result is graph  # 链式调用
        assert "node1" in graph.nodes

    def test_add_edge(self):
        """测试添加边"""
        graph = create_graph()
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})

        graph.add_node(node1).add_node(node2)

        edge = ToolEdge(node1, node2)
        graph.add_edge(edge)

        assert len(graph.edges) == 1
        assert graph.edges[0].source.id == "node1"
        assert graph.edges[0].target.id == "node2"

    def test_connect_method(self):
        """测试 connect 方法"""
        graph = create_graph()
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})

        graph.add_node(node1).add_node(node2)
        graph.connect("node1", "node2")

        assert len(graph.edges) == 1
        assert "node1" in node2.get_dependencies()

    def test_connect_with_condition(self):
        """测试带条件的连接"""
        graph = create_graph()
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})

        graph.add_node(node1).add_node(node2)
        graph.connect("node1", "node2", condition="result.success")

        assert graph.edges[0].condition == "result.success"

    def test_connect_nonexistent_node(self):
        """测试连接不存在的节点"""
        graph = create_graph()
        node1 = create_tool_node("node1", mock_tool_a, {})

        graph.add_node(node1)

        # 目标节点不存在
        with pytest.raises(ValueError, match="Target node node2 not found"):
            graph.connect("node1", "node2")

    def test_validate_empty_graph(self):
        """测试验证空图"""
        graph = create_graph()

        is_valid, errors = graph.validate()

        assert is_valid is False
        assert "no nodes" in errors[0].lower()

    def test_validate_valid_graph(self):
        """测试验证有效图"""
        graph = create_graph()
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})

        graph.add_node(node1).add_node(node2)
        graph.connect("node1", "node2")

        is_valid, errors = graph.validate()

        assert is_valid is True
        assert len(errors) == 0

    def test_detect_cycle(self):
        """测试环检测"""
        graph = create_graph()
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})
        node3 = create_tool_node("node3", mock_tool_c, {})

        graph.add_node(node1).add_node(node2).add_node(node3)
        graph.connect("node1", "node2")
        graph.connect("node2", "node3")
        graph.connect("node3", "node1")  # 创建环

        is_valid, errors = graph.validate()

        assert is_valid is False
        assert any("cycle" in err.lower() for err in errors)

    def test_get_entry_points(self):
        """测试获取入口点"""
        graph = create_graph()
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})
        node3 = create_tool_node("node3", mock_tool_c, {})

        graph.add_node(node1).add_node(node2).add_node(node3)
        graph.connect("node1", "node2")
        graph.connect("node2", "node3")

        entries = graph.get_entry_points()

        assert len(entries) == 1
        assert entries[0].id == "node1"

    def test_get_exit_points(self):
        """测试获取出口点"""
        graph = create_graph()
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})
        node3 = create_tool_node("node3", mock_tool_c, {})

        graph.add_node(node1).add_node(node2).add_node(node3)
        graph.connect("node1", "node2")
        graph.connect("node2", "node3")

        exits = graph.get_exit_points()

        assert len(exits) == 1
        assert exits[0].id == "node3"

    def test_topological_sort(self):
        """测试拓扑排序"""
        graph = create_graph()
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})
        node3 = create_tool_node("node3", mock_tool_c, {})

        graph.add_node(node1).add_node(node2).add_node(node3)
        graph.connect("node1", "node2")
        graph.connect("node2", "node3")

        sorted_nodes = graph.topological_sort()

        assert [n.id for n in sorted_nodes] == ["node1", "node2", "node3"]

    def test_topological_sort_with_cycle(self):
        """测试有环时的拓扑排序"""
        graph = create_graph()
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})

        graph.add_node(node1).add_node(node2)
        graph.connect("node1", "node2")
        graph.connect("node2", "node1")

        with pytest.raises(ValueError, match="cycle"):
            graph.topological_sort()

    def test_get_ready_nodes(self):
        """测试获取可执行节点"""
        graph = create_graph()
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})
        node3 = create_tool_node("node3", mock_tool_c, {})

        graph.add_node(node1).add_node(node2).add_node(node3)
        graph.connect("node1", "node2")
        graph.connect("node2", "node3")

        # 初始状态：只有 node1 可执行
        ready = graph.get_ready_nodes(set())
        assert [n.id for n in ready] == ["node1"]

        # node1 完成后：node2 可执行
        ready = graph.get_ready_nodes({"node1"})
        assert [n.id for n in ready] == ["node2"]

        # node1, node2 完成后：node3 可执行
        ready = graph.get_ready_nodes({"node1", "node2"})
        assert [n.id for n in ready] == ["node3"]

    def test_to_dict(self):
        """测试转换为字典"""
        graph = create_graph("test")
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})

        graph.add_node(node1).add_node(node2)
        graph.connect("node1", "node2")

        data = graph.to_dict()

        assert data["name"] == "test"
        assert "nodes" in data
        assert "edges" in data
        assert "entry_points" in data
        assert "exit_points" in data

    def test_to_mermaid(self):
        """测试 Mermaid 可视化"""
        graph = create_graph("test")
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})
        node3 = create_tool_node("node3", mock_tool_c, {})

        graph.add_node(node1).add_node(node2).add_node(node3)
        graph.connect("node1", "node2")
        graph.connect("node2", "node3")

        mermaid = graph.to_mermaid()

        assert "graph TD" in mermaid
        assert "node1" in mermaid
        assert "node2" in mermaid
        assert "node3" in mermaid
        assert "-->" in mermaid
        assert "entry" in mermaid
        assert "exit" in mermaid


# ============================================================================
# 测试工厂函数
# ============================================================================

class TestFactoryFunctions:
    """测试工厂函数"""

    def test_create_pipeline(self):
        """测试创建流水线"""
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})
        node3 = create_tool_node("node3", mock_tool_c, {})

        pipeline = create_pipeline([node1, node2, node3])

        assert len(pipeline.nodes) == 3
        assert len(pipeline.edges) == 2

        # 验证连接顺序
        sorted_nodes = pipeline.topological_sort()
        assert [n.id for n in sorted_nodes] == ["node1", "node2", "node3"]

    def test_create_parallel_workflow(self):
        """测试创建并行工作流"""
        node1a = create_tool_node("node1a", mock_tool_a, {})
        node1b = create_tool_node("node1b", mock_tool_b, {})
        node2 = create_tool_node("node2", mock_tool_c, {})

        workflow = create_parallel_workflow(
            parallel_steps=[[node1a, node1b]],
            final_step=node2,
        )

        assert len(workflow.nodes) == 3
        # 应该有两条边：node1a -> node2 和 node1b -> node2
        assert len(workflow.edges) == 2


# ============================================================================
# 测试 ParallelGroup
# ============================================================================

class TestParallelGroup:
    """测试并行组"""

    def test_create_parallel_group(self):
        """测试创建并行组"""
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})

        group = ParallelGroup([node1, node2])

        assert len(group.nodes) == 2
        assert "parallel" in group.id

    def test_parallel_with_or_operator(self):
        """测试 | 操作符创建并行组"""
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})

        group = node1 | node2

        assert isinstance(group, ParallelGroup)
        assert len(group.nodes) == 2


# ============================================================================
# 测试图串联
# ============================================================================

class TestGraphCombination:
    """测试图串联"""

    def test_graph_rshift_operator(self):
        """测试图的 >> 操作符"""
        # 创建第一个图
        graph1 = create_graph("graph1")
        node1 = create_tool_node("node1", mock_tool_a, {})
        node2 = create_tool_node("node2", mock_tool_b, {})
        graph1.add_node(node1).add_node(node2).connect("node1", "node2")

        # 创建第二个图
        graph2 = create_graph("graph2")
        node3 = create_tool_node("node3", mock_tool_c, {})
        node4 = create_tool_node("node4", sync_tool, {})
        graph2.add_node(node3).add_node(node4).connect("node3", "node4")

        # 串联
        combined = graph1 >> graph2

        assert len(combined.nodes) == 4
        # 应该有 3 条边：graph1 的 1 条 + graph2 的 1 条 + 连接的 1 条
        assert len(combined.edges) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
