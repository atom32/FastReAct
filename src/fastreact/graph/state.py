"""
Graph State - 图执行状态管理

管理节点间的数据传递和状态共享。
支持引用语法（@node.output）来访问其他节点的输出。
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set, Union
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class NodeOutput:
    """
    节点输出包装器

    Attributes:
        node_id: 节点 ID
        outputs: 输出数据
        timestamp: 时间戳
        status: 执行状态
    """
    node_id: str
    outputs: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "completed"

    def get(self, key: str, default: Any = None) -> Any:
        """获取输出值"""
        return self.outputs.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """支持 dict 风格访问"""
        return self.outputs[key]

    def __contains__(self, key: str) -> bool:
        """支持 in 操作符"""
        return key in self.outputs


@dataclass
class ExecutionContext:
    """
    执行上下文

    在整个图执行期间共享的全局上下文。

    Attributes:
        variables: 全局变量
        metadata: 元数据
        start_time: 开始时间
    """
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)

    def set(self, key: str, value: Any):
        """设置全局变量"""
        self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取全局变量"""
        return self.variables.get(key, default)

    def update(self, data: Dict[str, Any]):
        """批量更新"""
        self.variables.update(data)


class ReferenceResolver:
    """
    引用解析器

    解析节点输出引用，支持语法：
    - @node_id : 引用节点的全部输出
    - @node_id.key : 引用节点的特定输出
    - @node_id.key.nested : 引用嵌套字段
    """

    REF_PATTERN = re.compile(r'@(\w+)(?:\.([\w.]+))?')

    @staticmethod
    def resolve_reference(
        reference: str,
        state: 'GraphState',
        default: Any = None
    ) -> Any:
        """
        解析引用

        Args:
            reference: 引用字符串（如 "@node1.result"）
            state: 图状态
            default: 默认值

        Returns:
            解析后的值

        Raises:
            KeyError: 引用无效
        """
        match = ReferenceResolver.REF_PATTERN.match(reference)
        if not match:
            # 不是引用，返回原值
            return reference

        node_id = match.group(1)
        path = match.group(2)

        # 获取节点输出
        if node_id not in state.node_outputs:
            raise KeyError(f"Node {node_id} output not found in state")

        node_output = state.node_outputs[node_id]

        # 如果没有指定路径，返回全部输出
        if not path:
            return node_output.outputs

        # 解析嵌套路径
        result = node_output.outputs
        for key in path.split('.'):
            if isinstance(result, dict):
                result = result.get(key)
            else:
                raise KeyError(f"Cannot access key '{key}' on non-dict value")

            if result is None:
                return default

        return result

    @staticmethod
    def extract_references(value: Any) -> Set[str]:
        """
        提取值中的所有引用

        Args:
            value: 任意值

        Returns:
            引用集合
        """
        references = set()

        if isinstance(value, str):
            for match in ReferenceResolver.REF_PATTERN.finditer(value):
                references.add(match.group(0))
        elif isinstance(value, dict):
            for v in value.values():
                references.update(ReferenceResolver.extract_references(v))
        elif isinstance(value, list):
            for item in value:
                references.update(ReferenceResolver.extract_references(item))

        return references

    @staticmethod
    def resolve_value(
        value: Any,
        state: 'GraphState',
        resolve_strings: bool = True
    ) -> Any:
        """
        递归解析值中的所有引用

        Args:
            value: 任意值
            state: 图状态
            resolve_strings: 是否解析字符串中的引用

        Returns:
            解析后的值
        """
        if isinstance(value, str) and resolve_strings:
            # 检查是否是纯引用
            match = ReferenceResolver.REF_PATTERN.fullmatch(value)
            if match:
                return ReferenceResolver.resolve_reference(value, state)

            # 替换字符串中的引用
            def replace_ref(match):
                try:
                    resolved = ReferenceResolver.resolve_reference(match.group(0), state)
                    return str(resolved)
                except KeyError:
                    return match.group(0)

            return ReferenceResolver.REF_PATTERN.sub(replace_ref, value)

        elif isinstance(value, dict):
            return {
                k: ReferenceResolver.resolve_value(v, state)
                for k, v in value.items()
            }

        elif isinstance(value, list):
            return [
                ReferenceResolver.resolve_value(item, state)
                for item in value
            ]

        return value


class GraphState:
    """
    图状态管理

    管理图执行过程中的所有状态数据：
    - 节点输出
    - 执行上下文
    - 引用解析
    - 状态快照

    Attributes:
        node_outputs: 节点输出映射
        context: 执行上下文
        completed_nodes: 已完成节点集合
        failed_nodes: 失败节点集合
    """

    def __init__(self, context: Optional[ExecutionContext] = None):
        """
        初始化图状态

        Args:
            context: 执行上下文（可选）
        """
        self.node_outputs: Dict[str, NodeOutput] = {}
        self.context = context or ExecutionContext()
        self.completed_nodes: Set[str] = set()
        self.failed_nodes: Set[str] = set()
        self._snapshot_history: List[Dict[str, Any]] = []

    def set_node_output(
        self,
        node_id: str,
        outputs: Dict[str, Any],
        status: str = "completed"
    ):
        """
        设置节点输出

        Args:
            node_id: 节点 ID
            outputs: 输出数据
            status: 执行状态
        """
        self.node_outputs[node_id] = NodeOutput(
            node_id=node_id,
            outputs=outputs,
            status=status,
        )

        if status == "completed":
            self.completed_nodes.add(node_id)
        elif status == "failed":
            self.failed_nodes.add(node_id)

        logger.debug(f"State: Set output for node {node_id} (status={status})")

    def get_node_output(self, node_id: str) -> Optional[NodeOutput]:
        """获取节点输出"""
        return self.node_outputs.get(node_id)

    def get_output_value(
        self,
        node_id: str,
        key: str,
        default: Any = None
    ) -> Any:
        """
        获取节点的特定输出值

        Args:
            node_id: 节点 ID
            key: 输出键
            default: 默认值

        Returns:
            输出值
        """
        node_output = self.get_node_output(node_id)
        if node_output:
            return node_output.get(key, default)
        return default

    def is_completed(self, node_id: str) -> bool:
        """检查节点是否完成"""
        return node_id in self.completed_nodes

    def is_failed(self, node_id: str) -> bool:
        """检查节点是否失败"""
        return node_id in self.failed_nodes

    def resolve_inputs(
        self,
        inputs: Dict[str, Any],
        resolve_references: bool = True
    ) -> Dict[str, Any]:
        """
        解析输入中的引用

        Args:
            inputs: 输入参数
            resolve_references: 是否解析引用

        Returns:
            解析后的输入
        """
        if not resolve_references:
            return inputs

        return ReferenceResolver.resolve_value(inputs, self)

    def check_dependencies(
        self,
        dependencies: List[str]
    ) -> bool:
        """
        检查依赖是否都已满足

        Args:
            dependencies: 依赖节点 ID 列表

        Returns:
            是否所有依赖都已完成
        """
        return all(dep in self.completed_nodes for dep in dependencies)

    def get_pending_dependencies(
        self,
        dependencies: List[str]
    ) -> List[str]:
        """
        获取未完成的依赖

        Args:
            dependencies: 依赖节点 ID 列表

        Returns:
            未完成的依赖列表
        """
        return [dep for dep in dependencies if dep not in self.completed_nodes]

    def snapshot(self) -> Dict[str, Any]:
        """
        创建状态快照

        Returns:
            快照数据
        """
        snapshot = {
            "node_outputs": {
                node_id: output.outputs
                for node_id, output in self.node_outputs.items()
            },
            "completed_nodes": list(self.completed_nodes),
            "failed_nodes": list(self.failed_nodes),
            "context_vars": dict(self.context.variables),
            "timestamp": datetime.now().isoformat(),
        }

        self._snapshot_history.append(snapshot)
        return snapshot

    def restore(self, snapshot: Dict[str, Any]):
        """
        从快照恢复状态

        Args:
            snapshot: 快照数据
        """
        self.node_outputs = {
            node_id: NodeOutput(
                node_id=node_id,
                outputs=outputs,
            )
            for node_id, outputs in snapshot.get("node_outputs", {}).items()
        }

        self.completed_nodes = set(snapshot.get("completed_nodes", []))
        self.failed_nodes = set(snapshot.get("failed_nodes", []))
        self.context.variables = snapshot.get("context_vars", {})

        logger.debug(f"State: Restored from snapshot")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_outputs": {
                node_id: output.outputs
                for node_id, output in self.node_outputs.items()
            },
            "completed_nodes": list(self.completed_nodes),
            "failed_nodes": list(self.failed_nodes),
            "context_vars": dict(self.context.variables),
        }

    def clear(self):
        """清空状态"""
        self.node_outputs.clear()
        self.completed_nodes.clear()
        self.failed_nodes.clear()
        self.context.variables.clear()

    def __repr__(self):
        return (
            f"GraphState("
            f"completed={len(self.completed_nodes)}, "
            f"failed={len(self.failed_nodes)}, "
            f"outputs={len(self.node_outputs)})"
        )


# ============================================================================
# 工厂函数
# ============================================================================

def create_graph_state(
    context: Optional[ExecutionContext] = None
) -> GraphState:
    """
    创建图状态

    Args:
        context: 执行上下文（可选）

    Returns:
        GraphState 实例
    """
    return GraphState(context=context)


def create_execution_context(
    variables: Optional[Dict[str, Any]] = None
) -> ExecutionContext:
    """
    创建执行上下文

    Args:
        variables: 初始变量

    Returns:
        ExecutionContext 实例
    """
    return ExecutionContext(variables=variables or {})
