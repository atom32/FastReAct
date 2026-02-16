"""
Tool Graph - 工具图的核心实现

定义有向无环图（DAG）结构，支持节点组合和并行执行。
"""

from typing import Dict, List, Set, Any, Optional, Union
from dataclasses import dataclass, field
import logging
import asyncio
from collections import defaultdict, deque

from .node import ToolNode, NodeResult, NodeStatus

logger = logging.getLogger(__name__)


@dataclass
class ToolEdge:
    """
    工具边 - 定义节点间的数据流

    Attributes:
        source: 源节点
        target: 目标节点
        condition: 执行条件（可选）
    """
    source: ToolNode
    target: ToolNode
    condition: Optional[str] = None

    def __repr__(self):
        return f"Edge({self.source.id} -> {self.target.id})"


class ParallelGroup:
    """
    并行组 - 支持多个节点并行执行

    Example:
        group = ParallelGroup([node1, node2, node3])
        group >> node4  # 所有节点完成后执行 node4
    """

    def __init__(self, nodes: List[ToolNode]):
        self.nodes = nodes
        self.id = f"parallel_{id(self)}"

    def __rshift__(self, other: Union[ToolNode, 'ParallelGroup']) -> 'ToolEdge':
        """支持 >> 操作符连接到下一个节点/组"""
        # 创建虚拟汇合节点
        from .node import create_tool_node

        async def join(**outputs):
            return {"joined": True}

        join_node = create_tool_node(
            id=f"{self.id}_join",
            tool=join,
            inputs={},
        )

        # 将所有节点连接到汇合节点
        edges = []
        for node in self.nodes:
            edge = ToolEdge(node, join_node)
            edges.append(edge)

        # 如果后面还有节点，继续连接
        if isinstance(other, ToolNode):
            edges.append(ToolEdge(join_node, other))
        elif isinstance(other, ParallelGroup):
            # 连接两个并行组
            for node in other.nodes:
                edges.append(ToolEdge(join_node, node))

        return edges[0] if len(edges) == 1 else edges

    def __repr__(self):
        return f"ParallelGroup({', '.join(n.id for n in self.nodes)})"


@dataclass
class GraphMetrics:
    """图执行指标"""
    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    skipped_nodes: int = 0
    total_execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_nodes": self.total_nodes,
            "completed_nodes": self.completed_nodes,
            "failed_nodes": self.failed_nodes,
            "skipped_nodes": self.skipped_nodes,
            "success_rate": self.completed_nodes / self.total_nodes if self.total_nodes > 0 else 0,
            "total_execution_time": self.total_execution_time,
        }


class ToolGraph:
    """
    工具图 - DAG 结构的执行流程

    支持声明式 API 构建执行流程：
    - 串行: node1 >> node2 >> node3
    - 并行: (node1 | node2) >> node3
    - 条件: node1.when(condition) >> node2

    Attributes:
        nodes: 所有节点
        edges: 所有边
        name: 图名称
    """

    def __init__(self, name: str = "tool_graph"):
        self.name = name
        self.nodes: Dict[str, ToolNode] = {}
        self.edges: List[ToolEdge] = []
        self._entry_points: Set[str] = set()
        self._exit_points: Set[str] = set()

        logger.debug(f"Created ToolGraph: {name}")

    def add_node(self, node: ToolNode) -> 'ToolGraph':
        """
        添加节点

        Args:
            node: 工具节点

        Returns:
            self（支持链式调用）
        """
        if node.id in self.nodes:
            logger.warning(f"Node {node.id} already exists, overwriting")

        self.nodes[node.id] = node
        return self

    def add_edge(self, edge: ToolEdge) -> 'ToolGraph':
        """
        添加边

        Args:
            edge: 工具边

        Returns:
            self（支持链式调用）
        """
        self.edges.append(edge)

        # 更新依赖关系
        edge.target.depends_on(edge.source.id)
        edge.source.add_dependent(edge.target.id)

        return self

    def connect(self, source_id: str, target_id: str, condition: Optional[str] = None) -> 'ToolGraph':
        """
        连接两个节点

        Args:
            source_id: 源节点 ID
            target_id: 目标节点 ID
            condition: 可选的执行条件

        Returns:
            self

        Raises:
            ValueError: 节点不存在
        """
        if source_id not in self.nodes:
            raise ValueError(f"Source node {source_id} not found")
        if target_id not in self.nodes:
            raise ValueError(f"Target node {target_id} not found")

        edge = ToolEdge(
            source=self.nodes[source_id],
            target=self.nodes[target_id],
            condition=condition,
        )

        return self.add_edge(edge)

    def parallel(self, *node_ids: str) -> 'ToolGraph':
        """
        创建并行组

        Args:
            *node_ids: 节点 ID 列表

        Returns:
            self

        Example:
            graph.parallel("node1", "node2", "node3")
        """
        # 这个方法用于标记哪些节点可以并行执行
        # 实际并行逻辑在 runtime 中处理
        for node_id in node_ids:
            if node_id not in self.nodes:
                logger.warning(f"Node {node_id} not found for parallel group")

        return self

    def validate(self) -> tuple[bool, List[str]]:
        """
        验证图结构

        Returns:
            (is_valid, errors): 是否有效和错误列表
        """
        errors = []

        # 检查是否有节点
        if not self.nodes:
            errors.append("Graph has no nodes")
            return False, errors

        # 检查是否有孤立节点
        connected_nodes = set()
        for edge in self.edges:
            connected_nodes.add(edge.source.id)
            connected_nodes.add(edge.target.id)

        orphaned = set(self.nodes.keys()) - connected_nodes
        if orphaned and len(orphaned) < len(self.nodes):
            errors.append(f"Orphaned nodes: {orphaned}")

        # 检查是否有环
        has_cycle, cycle_path = self._detect_cycle()
        if has_cycle:
            errors.append(f"Cycle detected: {' -> '.join(cycle_path)}")

        # 检查边的有效性
        for edge in self.edges:
            if edge.source.id not in self.nodes:
                errors.append(f"Edge source {edge.source.id} not in nodes")
            if edge.target.id not in self.nodes:
                errors.append(f"Edge target {edge.target.id} not in nodes")

        is_valid = len(errors) == 0
        return is_valid, errors

    def _detect_cycle(self) -> tuple[bool, List[str]]:
        """检测图中的环"""
        # 使用 DFS 检测环
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node_id: WHITE for node_id in self.nodes}
        parent = {}

        def dfs(node_id: str, path: List[str]) -> tuple[bool, List[str]]:
            color[node_id] = GRAY
            path.append(node_id)

            # 检查所有出边
            for edge in self.edges:
                if edge.source.id == node_id:
                    neighbor_id = edge.target.id

                    if color[neighbor_id] == GRAY:
                        # 找到环
                        cycle_start = path.index(neighbor_id)
                        return True, path[cycle_start:] + [neighbor_id]

                    if color[neighbor_id] == WHITE:
                        has_cycle, cycle_path = dfs(neighbor_id, path)
                        if has_cycle:
                            return True, cycle_path

            path.pop()
            color[node_id] = BLACK
            return False, []

        for node_id in self.nodes:
            if color[node_id] == WHITE:
                has_cycle, cycle_path = dfs(node_id, [])
                if has_cycle:
                    return True, cycle_path

        return False, []

    def get_entry_points(self) -> List[ToolNode]:
        """获取入口节点（没有依赖的节点）"""
        entry_ids = set(self.nodes.keys())

        for edge in self.edges:
            if edge.target.id in entry_ids:
                entry_ids.remove(edge.target.id)

        return [self.nodes[id] for id in entry_ids]

    def get_exit_points(self) -> List[ToolNode]:
        """获取出口节点（没有依赖者的节点）"""
        exit_ids = set(self.nodes.keys())

        for edge in self.edges:
            if edge.source.id in exit_ids:
                exit_ids.remove(edge.source.id)

        return [self.nodes[id] for id in exit_ids]

    def topological_sort(self) -> List[ToolNode]:
        """
        拓扑排序

        Returns:
            排序后的节点列表

        Raises:
            ValueError: 图中有环
        """
        # 计算入度
        in_degree = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            in_degree[edge.target.id] += 1

        # 找到所有入度为 0 的节点
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node_id = queue.popleft()
            result.append(self.nodes[node_id])

            # 减少所有邻居的入度
            for edge in self.edges:
                if edge.source.id == node_id:
                    neighbor_id = edge.target.id
                    in_degree[neighbor_id] -= 1
                    if in_degree[neighbor_id] == 0:
                        queue.append(neighbor_id)

        if len(result) != len(self.nodes):
            raise ValueError("Graph has a cycle, cannot perform topological sort")

        return result

    def get_ready_nodes(self, completed: Set[str]) -> List[ToolNode]:
        """
        获取可以执行的节点（所有依赖都已完成）

        Args:
            completed: 已完成的节点 ID 集合

        Returns:
            可执行的节点列表
        """
        ready = []

        for node_id, node in self.nodes.items():
            if node_id in completed:
                continue

            # 检查所有依赖是否已完成
            dependencies = node.get_dependencies()
            if dependencies.issubset(completed):
                ready.append(node)

        return ready

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "name": self.name,
            "nodes": {id: node.to_dict() for id, node in self.nodes.items()},
            "edges": [
                {
                    "source": edge.source.id,
                    "target": edge.target.id,
                    "condition": edge.condition,
                }
                for edge in self.edges
            ],
            "entry_points": [n.id for n in self.get_entry_points()],
            "exit_points": [n.id for n in self.get_exit_points()],
        }

    def to_mermaid(self) -> str:
        """
        生成 Mermaid 流程图

        Returns:
            Mermaid 格式的流程图字符串
        """
        lines = ["graph TD"]

        # 添加节点
        for node_id, node in self.nodes.items():
            label = node_id
            lines.append(f"    {node_id}[\"{label}\"]")

        # 添加边
        for edge in self.edges:
            if edge.condition:
                lines.append(f"    {edge.source.id} -->|{edge.condition}| {edge.target.id}")
            else:
                lines.append(f"    {edge.source.id} --> {edge.target.id}")

        # 添加样式
        lines.append("\n    classDef entry fill:#90EE90")
        lines.append("    classDef exit fill:#FFB6C1")

        entry_ids = [n.id for n in self.get_entry_points()]
        exit_ids = [n.id for n in self.get_exit_points()]

        if entry_ids:
            lines.append(f"    class {','.join(entry_ids)} entry")
        if exit_ids:
            lines.append(f"    class {','.join(exit_ids)} exit")

        return "\n".join(lines)

    def visualize(self) -> str:
        """可视化图结构（返回 Mermaid 代码）"""
        return self.to_mermaid()

    def __repr__(self):
        return f"ToolGraph(name={self.name}, nodes={len(self.nodes)}, edges={len(self.edges)})"

    def __rshift__(self, other: 'ToolGraph') -> 'ToolGraph':
        """
        支持图的串联

        Example:
            combined = graph1 >> graph2
        """
        # 创建新图
        new_graph = ToolGraph(name=f"{self.name}_combined")

        # 添加所有节点和边
        for node in self.nodes.values():
            new_graph.add_node(node)
        for edge in self.edges:
            new_graph.add_edge(edge)

        for node in other.nodes.values():
            new_graph.add_node(node)
        for edge in other.edges:
            new_graph.add_edge(edge)

        # 连接两个图的出口和入口
        self_exits = self.get_exit_points()
        other_entries = other.get_entry_points()

        for exit_node in self_exits:
            for entry_node in other_entries:
                new_graph.add_edge(ToolEdge(exit_node, entry_node))

        return new_graph


# ============================================================================
# 工厂函数
# ============================================================================

def create_graph(name: str = "tool_graph") -> ToolGraph:
    """
    创建工具图

    Args:
        name: 图名称

    Returns:
        ToolGraph 实例

    Example:
        >>> graph = create_graph("my_pipeline")
        >>> graph.add_node(node1).add_node(node2)
        >>> graph.connect("node1", "node2")
    """
    return ToolGraph(name=name)


def create_pipeline(steps: List[ToolNode], name: str = "pipeline") -> ToolGraph:
    """
    创建线性流水线

    Args:
        steps: 步骤列表（按顺序执行）
        name: 流水线名称

    Returns:
        ToolGraph 实例

    Example:
        >>> pipeline = create_pipeline([step1, step2, step3])
    """
    graph = create_graph(name)

    # 添加所有节点
    for step in steps:
        graph.add_node(step)

    # 按顺序连接
    for i in range(len(steps) - 1):
        graph.connect(steps[i].id, steps[i + 1].id)

    return graph


def create_parallel_workflow(
    parallel_steps: List[List[ToolNode]],
    final_step: Optional[ToolNode] = None,
    name: str = "parallel_workflow",
) -> ToolGraph:
    """
    创建并行工作流

    Args:
        parallel_steps: 并行步骤列表（每个列表中的步骤会并行执行）
        final_step: 所有并行步骤完成后执行的最终步骤
        name: 工作流名称

    Returns:
        ToolGraph 实例

    Example:
        >>> workflow = create_parallel_workflow(
        ...     [[step1a, step1b], [step2a, step2b]],
        ...     final_step=final
        ... )
    """
    graph = create_graph(name)

    # 添加所有节点
    for steps in parallel_steps:
        for step in steps:
            graph.add_node(step)

    if final_step:
        graph.add_node(final_step)

    # 连接并行组到最终步骤
    if final_step:
        for steps in parallel_steps:
            for step in steps:
                graph.connect(step.id, final_step.id)

    return graph
