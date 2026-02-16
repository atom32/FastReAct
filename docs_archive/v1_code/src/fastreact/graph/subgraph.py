"""
SubGraph - 子图/子流程复用

支持将图封装为可复用组件，支持参数化和嵌套。
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from copy import deepcopy

from .graph import ToolGraph, ToolNode
from .node import NodeResult, NodeStatus
from .state import GraphState, ExecutionContext
from .runtime import ToolRuntime, ExecutionConfig, ExecutionReport

logger = logging.getLogger(__name__)


@dataclass
class SubGraphConfig:
    """
    子图配置

    Attributes:
        name: 子图名称
        description: 描述
        parameters: 参数定义 {name: type_or_default}
        returns: 返回值定义
        default_inputs: 默认输入值
    """
    name: str
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    returns: Dict[str, Any] = field(default_factory=dict)
    default_inputs: Dict[str, Any] = field(default_factory=dict)


class SubGraph(ToolNode):
    """
    子图 - 可复用的图组件

    将 ToolGraph 封装为 ToolNode，支持参数化和嵌套。

    Example:
        # 创建子图
        sub = SubGraph(
            id="data_pipeline",
            graph=inner_graph,
            parameters={"source": str, "target": str},
        )

        # 像普通节点一样使用
        result = await sub.execute({
            "source": "input.csv",
            "target": "output.csv"
        })
    """

    def __init__(
        self,
        id: str,
        graph: ToolGraph,
        parameters: Optional[Dict[str, Any]] = None,
        config: Optional[SubGraphConfig] = None,
    ):
        """
        初始化子图

        Args:
            id: 节点 ID
            graph: 内部图结构
            parameters: 参数定义
            config: 子图配置
        """
        # 创建异步执行函数
        async def execute_subgraph(**kwargs):
            return await self._execute_graph(**kwargs)

        super().__init__(
            id=id,
            tool=execute_subgraph,
            inputs=config.default_inputs if config else {},
            config=config,
        )

        self.inner_graph = graph
        self.config = config or SubGraphConfig(name=id)
        self.parameters = parameters or {}

        # 验证参数定义
        for param_name, param_def in self.parameters.items():
            if isinstance(param_def, type):
                self.config.parameters[param_name] = param_def
            else:
                self.config.parameters[param_name] = type(param_def)

    async def _execute_graph(self, **kwargs) -> Dict[str, Any]:
        """
        执行内部图

        Args:
            **kwargs: 输入参数

        Returns:
            执行结果字典
        """
        logger.debug(f"Executing subgraph: {self.id}")

        # 合并默认参数和输入参数
        inputs = {**self.config.default_inputs, **kwargs}

        # 创建执行上下文
        context = ExecutionContext()
        for key, value in inputs.items():
            context.set(key, value)

        # 创建运行时
        runtime = ToolRuntime(state=GraphState(context=context))

        # 执行内部图
        report = await runtime.execute(self.inner_graph, initial_inputs=inputs)

        if not report.success:
            logger.error(f"Subgraph {self.id} execution failed")
            return {
                "_success": False,
                "_errors": report.errors,
                "_report": report.to_dict(),
            }

        # 收集输出
        outputs = self._collect_outputs(report)

        return {
            "_success": True,
            "_iterations": report.total_nodes,
            "_execution_time": report.execution_time,
            **outputs,
        }

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ):
        """
        执行子图

        Args:
            inputs: 输入数据
            context: 执行上下文

        Returns:
            NodeResult: 执行结果
        """
        import time
        from .node import NodeStatus

        start_time = time.time()

        try:
            logger.debug(f"Executing subgraph: {self.id}")

            # 调用内部执行
            outputs = await self._execute_graph(**inputs)

            return NodeResult(
                node_id=self.id,
                status=NodeStatus.COMPLETED,
                outputs=outputs,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"Subgraph {self.id} execution failed: {e}")
            return NodeResult(
                node_id=self.id,
                status=NodeStatus.FAILED,
                error=str(e),
                outputs={
                    "_success": False,
                    "_error": str(e),
                },
                execution_time=time.time() - start_time,
            )

    def _collect_outputs(self, report: ExecutionReport) -> Dict[str, Any]:
        """
        收集输出

        Args:
            report: 执行报告

        Returns:
            输出字典
        """
        outputs = {}

        # 如果定义了返回值，从特定节点提取
        if self.config.returns:
            for output_name, source in self.config.returns.items():
                if isinstance(source, str) and source.startswith("@"):
                    # 引用格式：@node_id.key
                    node_id = source[1:].split(".")[0]
                    if node_id in report.node_results:
                        node_result = report.node_results[node_id]
                        outputs[output_name] = node_result.outputs
                else:
                    # 直接引用节点 ID
                    if source in report.node_results:
                        outputs[output_name] = report.node_results[source].outputs
        else:
            # 没有定义返回值，返回所有节点的输出
            for node_id, result in report.node_results.items():
                if result.is_success():
                    outputs[node_id] = result.outputs

        return outputs

    def visualize(self, include_internal: bool = False) -> str:
        """
        可视化子图

        Args:
            include_internal: 是否包含内部结构

        Returns:
            Mermaid 代码
        """
        if include_internal:
            return self.inner_graph.visualize()
        else:
            # 简化视图，只显示子图作为单个节点
            return f'subgraph_{self.id}[{self.id}]'

    def get_parameter_info(self) -> Dict[str, type]:
        """获取参数信息"""
        return self.config.parameters.copy()


class SubGraphNode(ToolNode):
    """
    子图调用节点 - 在图中调用子图

    将子图嵌入到父图中，支持数据流连接。

    Example:
        subgraph = SubGraph("pipeline", inner_graph, {...})

        caller = SubGraphNode(
            id="call_pipeline",
            subgraph=subgraph,
            bindings={"source": "@input.file"}
        )
    """

    def __init__(
        self,
        id: str,
        subgraph: SubGraph,
        bindings: Dict[str, str],
        outputs: Optional[Dict[str, str]] = None,
    ):
        """
        初始化子图调用节点

        Args:
            id: 节点 ID
            subgraph: 子图实例
            bindings: 参数绑定 {param_name: value_expression}
            outputs: 输出映射 {output_name: source_expression}
        """
        async def call_subgraph(**kwargs):
            # 解析绑定
            resolved_inputs = {}
            for param_name, expr in bindings.items():
                # 这里需要解析表达式，暂时简化处理
                if expr.startswith("@"):
                    # 引用格式，需要从上下文解析
                    resolved_inputs[param_name] = kwargs.get(param_name)
                else:
                    # 直接值
                    resolved_inputs[param_name] = expr

            # 执行子图
            result = await subgraph.execute(**resolved_inputs)

            # 提取输出
            if outputs:
                extracted = {}
                for output_name, source in outputs.items():
                    if source.startswith("@") and source[1:] in result:
                        extracted[output_name] = result[source[1:]]
                    elif source in result:
                        extracted[output_name] = result[source]
                return extracted
            else:
                return result

        super().__init__(
            id=id,
            tool=call_subgraph,
            inputs=bindings,
        )

        self.subgraph = subgraph
        self.bindings = bindings
        self.outputs_mapping = outputs


def create_subgraph(
    name: str,
    graph: ToolGraph,
    parameters: Optional[Dict[str, Any]] = None,
    description: str = "",
    default_inputs: Optional[Dict[str, Any]] = None,
) -> SubGraph:
    """
    创建子图

    Args:
        name: 子图名称
        graph: 图结构
        parameters: 参数定义
        description: 描述
        default_inputs: 默认输入值

    Returns:
        SubGraph 实例

    Example:
        >>> inner_graph = create_graph("inner")
        >>> # ... 添加节点和边 ...
        >>> sub = create_subgraph(
        ...     "data_processor",
        ...     inner_graph,
        ...     parameters={"input_file": str, "output_file": str}
        ... )
    """
    config = SubGraphConfig(
        name=name,
        description=description,
        parameters=parameters or {},
        default_inputs=default_inputs or {},
    )

    return SubGraph(
        id=name,
        graph=graph,
        parameters=parameters,
        config=config,
    )


def compose_subgraph(
    name: str,
    nodes: List[ToolNode],
    connections: List[tuple[str, str]] = None,
    entry_point: Optional[str] = None,
) -> SubGraph:
    """
    组合子图 - 从节点列表快速创建子图

    Args:
        name: 子图名称
        nodes: 节点列表
        connections: 连接列表 [(source_id, target_id), ...]
        entry_point: 入口节点 ID（如果有）

    Returns:
        SubGraph 实例

    Example:
        >>> sub = compose_subgraph(
        ...     "process",
        ...     [node1, node2, node3],
        ...     connections=[("node1", "node2"), ("node2", "node3")],
        ...     entry_point="node1"
        ... )
    """
    graph = ToolGraph(name=name)

    # 添加所有节点
    for node in nodes:
        graph.add_node(node)

    # 添加连接
    if connections:
        for source_id, target_id in connections:
            if source_id in graph.nodes and target_id in graph.nodes:
                graph.connect(source_id, target_id)

    return SubGraph(id=name, graph=graph)


def inline_subgraph(
    parent_graph: ToolGraph,
    subgraph: SubGraph,
    node_id: str,
    position: Optional[tuple[str, str]] = None,
) -> ToolNode:
    """
    内联子图到父图中

    将子图的所有节点复制到父图中，创建封装节点。

    Args:
        parent_graph: 父图
        subgraph: 子图
        node_id: 新节点 ID
        position: 插入位置 (before_id, after_id)

    Returns:
        创建的调用节点

    Example:
        >>> caller = inline_subgraph(
        ...     parent_graph,
        ...     subgraph,
        ...     "call_subgraph"
        ... )
    """
    # 创建子图调用节点
    caller = SubGraphNode(
        id=node_id,
        subgraph=subgraph,
        bindings={},
    )

    # 添加到父图
    parent_graph.add_node(caller)

    # 如果指定了位置，添加连接
    if position:
        before_id, after_id = position
        if before_id and before_id in parent_graph.nodes:
            parent_graph.connect(before_id, node_id)
        if after_id and after_id in parent_graph.nodes:
            parent_graph.connect(node_id, after_id)

    return caller


# ============================================================================
# 预定义子图模板
# ============================================================================

class SubGraphTemplates:
    """常用子图模板"""

    @staticmethod
    def pipeline(steps: List[ToolNode], name: str = "pipeline") -> SubGraph:
        """
        线性流水线模板

        Args:
            steps: 步骤列表
            name: 子图名称

        Returns:
            SubGraph 实例
        """
        graph = ToolGraph(name=f"{name}_inner")

        for step in steps:
            graph.add_node(step)

        # 按顺序连接
        for i in range(len(steps) - 1):
            graph.connect(steps[i].id, steps[i + 1].id)

        return SubGraph(id=name, graph=graph)

    @staticmethod
    def parallel_parallel(
        parallel_steps: List[List[ToolNode]],
        final_step: ToolNode,
        name: str = "parallel_workflow",
    ) -> SubGraph:
        """
        并行工作流模板

        Args:
            parallel_steps: 并行步骤列表
            final_step: 汇聚步骤
            name: 子图名称

        Returns:
            SubGraph 实例
        """
        graph = ToolGraph(name=f"{name}_inner")

        # 添加所有节点
        for steps in parallel_steps:
            for step in steps:
                graph.add_node(step)
        graph.add_node(final_step)

        # 连接并行组到最终步骤
        for steps in parallel_steps:
            for step in steps:
                graph.connect(step.id, final_step.id)

        return SubGraph(id=name, graph=graph)

    @staticmethod
    def conditional_branch(
    condition_node,
    true_branch: ToolNode,
    false_branch: ToolNode,
    name: str = "conditional",
    ) -> SubGraph:
        """
        条件分支模板

        Args:
            condition_node: 条件节点
            true_branch: 真分支节点
            false_branch: 假分支节点
            name: 子图名称

        Returns:
            SubGraph 实例
        """
        graph = ToolGraph(name=f"{name}_inner")

        # 这里需要特殊的处理，因为条件节点已经包含了分支
        # 暂时简化：只添加条件节点
        graph.add_node(condition_node)

        # 注意：条件节点的分支已经内部处理，不需要额外的连接
        return SubGraph(id=name, graph=graph)
