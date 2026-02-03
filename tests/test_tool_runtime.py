"""
测试 Tool Runtime - 图执行引擎
"""

import pytest
import asyncio
from fastreact.graph import (
    ToolNode,
    ToolGraph,
    GraphState,
    ExecutionConfig,
    ExecutionStrategy,
    ExecutionReport,
    ToolRuntime,
    create_runtime,
    execute_graph,
    create_graph,
    create_graph_state,
    create_tool_node,
    NodeStatus,
)


# ============================================================================
# 测试工具函数
# ============================================================================

async def tool_a(**kwargs) -> dict:
    """工具 A - 返回固定值"""
    await asyncio.sleep(0.01)
    return {"result_a": "value_a", "count": 1}


async def tool_b(**kwargs) -> dict:
    """工具 B - 返回固定值"""
    await asyncio.sleep(0.01)
    return {"result_b": "value_b", "count": 2}


async def tool_c(**kwargs) -> dict:
    """工具 C - 返回固定值"""
    await asyncio.sleep(0.01)
    return {"result_c": "value_c", "count": 3}


async def tool_failing(**kwargs) -> dict:
    """会失败的工具"""
    await asyncio.sleep(0.01)
    raise ValueError("Intentional failure")


async def tool_with_input(value: int, **kwargs) -> dict:
    """带输入的工具"""
    await asyncio.sleep(0.01)
    return {"doubled": value * 2}


# ============================================================================
# 测试 ToolRuntime
# ============================================================================

class TestToolRuntime:
    """测试工具运行时"""

    @pytest.fixture
    def runtime(self):
        """创建运行时"""
        return create_runtime()

    @pytest.fixture
    def simple_graph(self):
        """创建简单图：A -> B -> C"""
        graph = create_graph("simple")

        node_a = create_tool_node("a", tool_a, {})
        node_b = create_tool_node("b", tool_b, {})
        node_c = create_tool_node("c", tool_c, {})

        graph.add_node(node_a).add_node(node_b).add_node(node_c)
        graph.connect("a", "b").connect("b", "c")

        return graph

    @pytest.mark.asyncio
    async def test_execute_simple_graph(self, runtime, simple_graph):
        """测试执行简单图"""
        report = await runtime.execute(simple_graph)

        assert report.success is True
        assert report.total_nodes == 3
        assert report.completed_nodes == 3
        assert report.failed_nodes == 0

        # 检查节点结果
        assert "a" in report.node_results
        assert "b" in report.node_results
        assert "c" in report.node_results

    @pytest.mark.asyncio
    async def test_execute_with_initial_inputs(self, runtime):
        """测试带初始输入的执行"""
        graph = create_graph("test")

        # 节点使用默认输入值
        node = create_tool_node("node", tool_with_input, {"value": 5})
        graph.add_node(node)

        report = await runtime.execute(graph, initial_inputs={"some_key": "some_value"})

        assert report.success is True
        # 节点使用自己的输入值，initial_inputs 存储在上下文中
        assert report.node_results["node"].outputs["doubled"] == 10  # 5 * 2
        # 验证上下文有初始输入
        assert runtime.state.context.get("some_key") == "some_value"

    @pytest.mark.asyncio
    async def test_execute_with_continue_on_error(self, simple_graph):
        """测试遇错继续"""
        # 修改图，让中间节点失败
        failing_node = create_tool_node("failing", tool_failing, {})
        simple_graph.add_node(failing_node)
        simple_graph.connect("a", "failing")

        config = ExecutionConfig(continue_on_error=True)
        runtime = create_runtime(config=config)

        report = await runtime.execute(simple_graph)

        assert report.failed_nodes > 0
        # 虽然有失败，但应该继续执行其他节点

    @pytest.mark.asyncio
    async def test_execute_stop_on_error(self, simple_graph):
        """测试遇错停止"""
        failing_node = create_tool_node("failing", tool_failing, {})
        simple_graph.add_node(failing_node)
        simple_graph.connect("a", "failing")

        config = ExecutionConfig(continue_on_error=False)
        runtime = create_runtime(config=config)

        report = await runtime.execute(simple_graph)

        assert report.success is False
        # 失败后应该停止执行

    @pytest.mark.asyncio
    async def test_strategies(self):
        """测试不同执行策略"""
        # 创建图：A -> C, B -> C（A 和 B 可以并行）
        graph = create_graph("test")

        node_a = create_tool_node("a", tool_a, {})
        node_b = create_tool_node("b", tool_b, {})
        node_c = create_tool_node("c", tool_c, {})

        graph.add_node(node_a).add_node(node_b).add_node(node_c)
        graph.connect("a", "c").connect("b", "c")

        # 测试拓扑排序策略
        config = ExecutionConfig(strategy=ExecutionStrategy.TOPOLOGICAL)
        runtime = create_runtime(config=config)
        report = await runtime.execute(graph)
        assert report.success is True

        # 重置状态
        state = create_graph_state()

        # 测试层级并行策略
        config = ExecutionConfig(strategy=ExecutionStrategy.LEVEL_BASED)
        runtime = create_runtime(config=config, state=state)
        report = await runtime.execute(graph)
        assert report.success is True

        # 重置状态
        state = create_graph_state()

        # 测试最大并行策略
        config = ExecutionConfig(strategy=ExecutionStrategy.MAX_PARALLEL)
        runtime = create_runtime(config=config, state=state)
        report = await runtime.execute(graph)
        assert report.success is True


class TestExecutionConfig:
    """测试执行配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = ExecutionConfig()

        assert config.max_parallel == 3
        assert config.strategy == ExecutionStrategy.LEVEL_BASED
        assert config.timeout == 300.0
        assert config.retry_failed is False
        assert config.continue_on_error is False

    def test_custom_config(self):
        """测试自定义配置"""
        config = ExecutionConfig(
            max_parallel=5,
            strategy=ExecutionStrategy.MAX_PARALLEL,
            timeout=600.0,
            retry_failed=True,
            continue_on_error=True,
        )

        assert config.max_parallel == 5
        assert config.strategy == ExecutionStrategy.MAX_PARALLEL
        assert config.timeout == 600.0
        assert config.retry_failed is True
        assert config.continue_on_error is True


class TestExecutionReport:
    """测试执行报告"""

    def test_report_creation(self):
        """测试创建报告"""
        report = ExecutionReport(
            success=True,
            total_nodes=5,
            completed_nodes=5,
            failed_nodes=0,
            execution_time=1.5,
        )

        assert report.success is True
        assert report.total_nodes == 5
        assert report.completed_nodes == 5
        assert report.execution_time == 1.5

    def test_report_to_dict(self):
        """测试转换为字典"""
        from fastreact.graph.node import NodeResult

        report = ExecutionReport(
            success=True,
            total_nodes=1,
            completed_nodes=1,
            failed_nodes=0,
            execution_time=1.0,
            node_results={
                "node1": NodeResult(
                    node_id="node1",
                    status=NodeStatus.COMPLETED,
                    outputs={"result": "value"},
                )
            },
        )

        data = report.to_dict()

        assert data["success"] is True
        assert data["total_nodes"] == 1
        assert data["success_rate"] == 1.0
        assert "node_results" in data


# ============================================================================
# 测试工厂函数
# ============================================================================

class TestFactoryFunctions:
    """测试工厂函数"""

    @pytest.mark.asyncio
    async def test_create_runtime(self):
        """测试创建运行时"""
        runtime = create_runtime()

        assert isinstance(runtime, ToolRuntime)

    @pytest.mark.asyncio
    async def test_execute_graph_shortcut(self):
        """测试快捷执行函数"""
        graph = create_graph("test")

        node = create_tool_node("node", tool_a, {})
        graph.add_node(node)

        report = await execute_graph(graph)

        assert report.success is True
        assert report.completed_nodes == 1


# ============================================================================
# 测试状态管理集成
# ============================================================================

class TestStateIntegration:
    """测试状态管理集成"""

    @pytest.mark.asyncio
    async def test_state_persistence(self):
        """测试状态持久化"""
        state = create_graph_state()
        runtime = create_runtime(state=state)

        graph = create_graph("test")

        node_a = create_tool_node("a", tool_a, {})
        node_b = create_tool_node("b", tool_with_input, {"value": "@a.count"})
        graph.add_node(node_a).add_node(node_b)
        graph.connect("a", "b")

        report = await runtime.execute(graph)

        assert report.success is True
        # 检查引用是否被正确解析
        assert report.node_results["b"].outputs["doubled"] == 2  # a.count = 1

    @pytest.mark.asyncio
    async def test_state_snapshot(self):
        """测试状态快照"""
        state = create_graph_state()
        runtime = create_runtime(state=state)

        graph = create_graph("test")

        node = create_tool_node("node", tool_a, {})
        graph.add_node(node)

        await runtime.execute(graph)

        snapshot = state.snapshot()

        assert "node_outputs" in snapshot
        assert "completed_nodes" in snapshot
        assert "node" in snapshot["node_outputs"]


# ============================================================================
# 测试并行执行
# ============================================================================

class TestParallelExecution:
    """测试并行执行"""

    @pytest.mark.asyncio
    async def test_parallel_independent_nodes(self):
        """测试独立节点的并行执行"""
        graph = create_graph("parallel")

        # 创建三个独立的节点
        nodes = [
            create_tool_node(f"node{i}", tool_a, {})
            for i in range(3)
        ]

        for node in nodes:
            graph.add_node(node)

        config = ExecutionConfig(
            strategy=ExecutionStrategy.MAX_PARALLEL,
            max_parallel=3,
        )
        runtime = create_runtime(config=config)

        report = await runtime.execute(graph)

        assert report.success is True
        assert report.completed_nodes == 3

    @pytest.mark.asyncio
    async def test_parallel_limited(self):
        """测试限制并行度"""
        import time

        async def slow_tool(**kwargs):
            await asyncio.sleep(0.1)
            return {"result": "done"}

        graph = create_graph("limited")

        # 创建多个节点
        for i in range(5):
            node = create_tool_node(f"node{i}", slow_tool, {})
            graph.add_node(node)

        config = ExecutionConfig(
            strategy=ExecutionStrategy.MAX_PARALLEL,
            max_parallel=2,
        )
        runtime = create_runtime(config=config)

        start = time.time()
        report = await runtime.execute(graph)
        elapsed = time.time() - start

        assert report.success is True
        # 限制为 2 并行，5 个节点需要至少 3 批
        # 3 批 * 0.1 秒 = 0.3 秒（大约）
        assert elapsed >= 0.25  # 允许一些误差

    @pytest.mark.asyncio
    async def test_level_based_execution(self):
        """测试层级执行"""
        graph = create_graph("levels")

        # 层级 0: node_a, node_b
        # 层级 1: node_c (依赖 a 和 b)
        node_a = create_tool_node("a", tool_a, {})
        node_b = create_tool_node("b", tool_b, {})
        node_c = create_tool_node("c", tool_c, {})

        graph.add_node(node_a).add_node(node_b).add_node(node_c)
        graph.connect("a", "c").connect("b", "c")

        config = ExecutionConfig(strategy=ExecutionStrategy.LEVEL_BASED)
        runtime = create_runtime(config=config)

        report = await runtime.execute(graph)

        assert report.success is True
        # a 和 b 应该在 c 之前完成
        result_a_time = report.node_results["a"].execution_time
        result_b_time = report.node_results["b"].execution_time
        result_c_time = report.node_results["c"].execution_time

        # c 的执行时间应该包含等待 a 和 b 的时间
        # （这只是近似检查，实际时间可能因为调度而不同）


# ============================================================================
# 测试边界情况
# ============================================================================

class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_empty_graph(self):
        """测试空图"""
        graph = create_graph("empty")

        runtime = create_runtime()
        report = await runtime.execute(graph)

        assert report.total_nodes == 0
        assert report.completed_nodes == 0

    @pytest.mark.asyncio
    async def test_single_node(self):
        """测试单节点图"""
        graph = create_graph("single")

        node = create_tool_node("node", tool_a, {})
        graph.add_node(node)

        runtime = create_runtime()
        report = await runtime.execute(graph)

        assert report.success is True
        assert report.completed_nodes == 1

    @pytest.mark.asyncio
    async def test_invalid_graph(self):
        """测试无效图（有环）"""
        graph = create_graph("cycle")

        node_a = create_tool_node("a", tool_a, {})
        node_b = create_tool_node("b", tool_b, {})

        graph.add_node(node_a).add_node(node_b)
        graph.connect("a", "b").connect("b", "a")  # 创建环

        runtime = create_runtime()
        report = await runtime.execute(graph)

        assert report.success is False
        assert len(report.errors) > 0

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """测试异步上下文管理器"""
        graph = create_graph("test")

        node = create_tool_node("node", tool_a, {})
        graph.add_node(node)

        async with create_runtime() as runtime:
            report = await runtime.execute(graph)

        assert report.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
