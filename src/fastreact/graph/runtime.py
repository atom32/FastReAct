"""
Tool Runtime - 图执行引擎

负责执行 ToolGraph，管理节点调度、并行执行、重试和错误处理。
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

from .node import ToolNode, NodeResult, NodeStatus
from .graph import ToolGraph
from .state import GraphState, create_graph_state

logger = logging.getLogger(__name__)


class ExecutionStrategy(Enum):
    """执行策略"""
    TOPOLOGICAL = "topological"  # 拓扑排序顺序执行
    LEVEL_BASED = "level_based"  # 按层级并行执行
    MAX_PARALLEL = "max_parallel"  # 最大并行度


@dataclass
class ExecutionConfig:
    """
    执行配置

    Attributes:
        max_parallel: 最大并行节点数
        strategy: 执行策略
        timeout: 全局超时时间（秒）
        retry_failed: 是否自动重试失败节点
        continue_on_error: 遇错是否继续
    """
    max_parallel: int = 3
    strategy: ExecutionStrategy = ExecutionStrategy.LEVEL_BASED
    timeout: float = 300.0
    retry_failed: bool = False
    continue_on_error: bool = False


@dataclass
class ExecutionReport:
    """
    执行报告

    Attributes:
        success: 是否成功
        total_nodes: 总节点数
        completed_nodes: 完成节点数
        failed_nodes: 失败节点数
        execution_time: 执行时间
        node_results: 节点结果映射
        errors: 错误列表
    """
    success: bool
    total_nodes: int
    completed_nodes: int
    failed_nodes: int
    execution_time: float
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "total_nodes": self.total_nodes,
            "completed_nodes": self.completed_nodes,
            "failed_nodes": self.failed_nodes,
            "execution_time": self.execution_time,
            "success_rate": self.completed_nodes / self.total_nodes if self.total_nodes > 0 else 0,
            "node_results": {
                node_id: result.to_dict()
                for node_id, result in self.node_results.items()
            },
            "errors": self.errors,
        }


class ToolRuntime:
    """
    工具图执行引擎

    执行 ToolGraph，支持：
    - 拓扑排序
    - 并行执行
    - 状态管理
    - 重试机制
    - 错误处理
    """

    def __init__(
        self,
        config: Optional[ExecutionConfig] = None,
        state: Optional[GraphState] = None,
    ):
        """
        初始化运行时

        Args:
            config: 执行配置
            state: 图状态（可选，新建一个）
        """
        self.config = config or ExecutionConfig()
        self.state = state or create_graph_state()
        self._executor: Optional[ThreadPoolExecutor] = None

    async def execute(
        self,
        graph: ToolGraph,
        initial_inputs: Optional[Dict[str, Any]] = None,
    ) -> ExecutionReport:
        """
        执行图

        Args:
            graph: 工具图
            initial_inputs: 初始输入（可选）

        Returns:
            ExecutionReport: 执行报告
        """
        start_time = time.time()

        logger.info(f"Starting execution of graph: {graph.name}")

        # 验证图
        is_valid, errors = graph.validate()
        if not is_valid:
            return ExecutionReport(
                success=False,
                total_nodes=len(graph.nodes),
                completed_nodes=0,
                failed_nodes=0,
                execution_time=0.0,
                errors=errors,
            )

        # 设置初始输入
        if initial_inputs:
            self.state.context.update(initial_inputs)

        # 选择执行策略
        if self.config.strategy == ExecutionStrategy.TOPOLOGICAL:
            node_results = await self._execute_topological(graph)
        elif self.config.strategy == ExecutionStrategy.LEVEL_BASED:
            node_results = await self._execute_level_based(graph)
        elif self.config.strategy == ExecutionStrategy.MAX_PARALLEL:
            node_results = await self._execute_max_parallel(graph)
        else:
            logger.error(f"Unknown execution strategy: {self.config.strategy}")
            node_results = {}

        # 生成报告
        execution_time = time.time() - start_time

        completed = sum(1 for r in node_results.values() if r.status == NodeStatus.COMPLETED)
        failed = sum(1 for r in node_results.values() if r.status == NodeStatus.FAILED)
        success = failed == 0

        errors = []
        for node_id, result in node_results.items():
            if result.status == NodeStatus.FAILED and result.error:
                errors.append(f"{node_id}: {result.error}")

        report = ExecutionReport(
            success=success,
            total_nodes=len(graph.nodes),
            completed_nodes=completed,
            failed_nodes=failed,
            execution_time=execution_time,
            node_results=node_results,
            errors=errors,
        )

        logger.info(
            f"Execution completed: {completed}/{len(graph.nodes)} nodes, "
            f"{execution_time:.2f}s"
        )

        return report

    async def _execute_topological(
        self,
        graph: ToolGraph
    ) -> Dict[str, NodeResult]:
        """按拓扑顺序执行"""
        results = {}
        sorted_nodes = graph.topological_sort()

        for node in sorted_nodes:
            # 检查依赖是否完成
            if not self.state.check_dependencies(node.get_dependencies()):
                logger.warning(f"Node {node.id} dependencies not satisfied, skipping")
                continue

            # 执行节点
            result = await self._execute_node(node, graph)
            results[node.id] = result

            # 如果失败且不继续，停止执行
            if result.status == NodeStatus.FAILED and not self.config.continue_on_error:
                break

        return results

    async def _execute_level_based(
        self,
        graph: ToolGraph
    ) -> Dict[str, NodeResult]:
        """按层级并行执行"""
        results = {}

        # 计算节点层级（距离入口的最长路径）
        levels = self._compute_node_levels(graph)

        # 按层级执行
        max_level = max(levels.values()) if levels else 0

        for level in range(max_level + 1):
            # 获取当前层级的节点
            level_nodes = [
                node for node in graph.nodes.values()
                if levels.get(node.id, 0) == level
            ]

            if not level_nodes:
                continue

            # 并行执行当前层级
            level_results = await self._execute_parallel(level_nodes, graph)

            for node_id, result in level_results.items():
                results[node_id] = result

                # 如果失败且不继续，停止执行
                if result.status == NodeStatus.FAILED and not self.config.continue_on_error:
                    return results

        return results

    async def _execute_max_parallel(
        self,
        graph: ToolGraph
    ) -> Dict[str, NodeResult]:
        """最大并行度执行"""
        results = {}
        pending: Set[str] = set(graph.nodes.keys())

        while pending:
            # 获取可执行节点
            ready_nodes = [
                graph.nodes[node_id]
                for node_id in pending
                if self.state.check_dependencies(graph.nodes[node_id].get_dependencies())
            ]

            if not ready_nodes:
                # 没有可执行节点，检查是否还有未完成的依赖
                if pending:
                    logger.error("Deadlock detected: no ready nodes but pending remain")
                break

            # 限制并行数量
            batch = ready_nodes[:self.config.max_parallel]

            # 并行执行
            batch_results = await self._execute_parallel(batch, graph)

            for node_id, result in batch_results.items():
                results[node_id] = result
                pending.discard(node_id)

                # 如果失败且不继续，停止执行
                if result.status == NodeStatus.FAILED and not self.config.continue_on_error:
                    pending.clear()
                    break

        return results

    async def _execute_parallel(
        self,
        nodes: List[ToolNode],
        graph: ToolGraph,
    ) -> Dict[str, NodeResult]:
        """并行执行节点列表"""
        tasks = [
            self._execute_node(node, graph)
            for node in nodes
        ]

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results = {}
        for node, result in zip(nodes, results_list):
            if isinstance(result, Exception):
                logger.error(f"Node {node.id} raised exception: {result}")
                results[node.id] = NodeResult(
                    node_id=node.id,
                    status=NodeStatus.FAILED,
                    error=str(result),
                )
            else:
                results[node.id] = result

        return results

    async def _execute_node(
        self,
        node: ToolNode,
        graph: ToolGraph,
    ) -> NodeResult:
        """执行单个节点"""
        logger.debug(f"Executing node: {node.id}")

        # 解析输入引用
        resolved_inputs = self.state.resolve_inputs(node.inputs)

        # 执行工具
        result = await node.execute(resolved_inputs, context=self.state.context.variables)

        # 保存输出到状态
        if result.status == NodeStatus.COMPLETED:
            self.state.set_node_output(node.id, result.outputs)
        else:
            self.state.set_node_output(node.id, {}, status="failed")

        return result

    def _compute_node_levels(self, graph: ToolGraph) -> Dict[str, int]:
        """计算节点层级（用于并行执行）"""
        levels = {}

        # 初始化入口节点为 0 层
        for entry in graph.get_entry_points():
            levels[entry.id] = 0

        # BFS 计算层级
        changed = True
        max_iterations = len(graph.nodes) + 1
        iteration = 0

        while changed and iteration < max_iterations:
            changed = False
            iteration += 1

            for edge in graph.edges:
                source_level = levels.get(edge.source.id, 0)
                target_level = levels.get(edge.target.id)

                new_level = source_level + 1
                if target_level is None or new_level > target_level:
                    levels[edge.target.id] = new_level
                    changed = True

        # 剩余未设置的节点为 0 层
        for node_id in graph.nodes:
            if node_id not in levels:
                levels[node_id] = 0

        return levels

    async def close(self):
        """关闭运行时，清理资源"""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

    async def __aenter__(self):
        """支持 async with"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """支持 async with"""
        await self.close()


# ============================================================================
# 工厂函数
# ============================================================================

def create_runtime(
    config: Optional[ExecutionConfig] = None,
    state: Optional[GraphState] = None,
) -> ToolRuntime:
    """
    创建工具运行时

    Args:
        config: 执行配置
        state: 图状态

    Returns:
        ToolRuntime 实例
    """
    return ToolRuntime(config=config, state=state)


async def execute_graph(
    graph: ToolGraph,
    inputs: Optional[Dict[str, Any]] = None,
    config: Optional[ExecutionConfig] = None,
) -> ExecutionReport:
    """
    快捷函数：执行工具图

    Args:
        graph: 工具图
        inputs: 初始输入
        config: 执行配置

    Returns:
        ExecutionReport: 执行报告
    """
    runtime = create_runtime(config=config)
    return await runtime.execute(graph, initial_inputs=inputs)
