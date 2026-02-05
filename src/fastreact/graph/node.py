"""
Tool Node - 工具图的基本执行单元

定义工具节点的抽象，支持输入输出端口、配置和状态管理。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Optional, List, Set
from enum import Enum
import logging
import asyncio
import inspect

logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """节点执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NodeConfig:
    """
    节点执行配置

    Attributes:
        retry: 重试次数（默认 0）
        timeout: 超时时间（秒，默认 30）
        fallback: 失败时的回退节点 ID
        condition: 执行条件表达式
        continue_on_error: 遇错是否继续
    """
    retry: int = 0
    timeout: float = 30.0
    fallback: Optional[str] = None
    condition: Optional[str] = None
    continue_on_error: bool = False


@dataclass
class NodePort:
    """
    节点端口定义

    Attributes:
        name: 端口名称
        type: 数据类型
        description: 描述
        required: 是否必需
    """
    name: str
    type: type
    description: str = ""
    required: bool = True


@dataclass
class NodeResult:
    """
    节点执行结果

    Attributes:
        node_id: 节点 ID
        status: 执行状态
        outputs: 输出数据
        error: 错误信息（如果有）
        execution_time: 执行时间（秒）
        metadata: 额外元数据
    """
    node_id: str
    status: NodeStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_success(self) -> bool:
        """检查执行是否成功"""
        return self.status == NodeStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "outputs": self.outputs,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }


class ToolNode:
    """
    工具节点 - 图中的基本执行单元

    封装工具函数，提供输入输出接口和配置管理。

    Attributes:
        id: 节点唯一标识
        tool: 工具函数
        inputs: 输入端口定义
        outputs: 输出端口定义
        config: 执行配置
    """

    def __init__(
        self,
        id: str,
        tool: Callable,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any] = None,
        config: Optional[NodeConfig] = None,
    ):
        """
        初始化工具节点

        Args:
            id: 节点 ID
            tool: 工具函数（同步或异步）
            inputs: 输入定义 {"name": type_or_default}
            outputs: 输出定义（可选，用于类型检查）
            config: 节点配置
        """
        self.id = id
        self.tool = tool
        self.inputs = inputs
        self.outputs = outputs or {}
        self.config = config or NodeConfig()

        # 推断工具类型（优先检查 execute_async，再检查 execute）
        if hasattr(tool, 'execute_async'):
            # 有 execute_async 方法，标记为异步
            self.is_async = True
        elif hasattr(tool, 'execute'):
            # 检查 execute 是否是协程函数
            self.is_async = inspect.iscoroutinefunction(tool.execute)
        else:
            self.is_async = False

        # 依赖和被依赖关系
        self._dependencies: Set[str] = set()
        self._dependents: Set[str] = set()

        logger.debug(f"Created ToolNode: {id} (async={self.is_async})")

    def __rshift__(self, other: 'ToolNode') -> 'ToolEdge':
        """
        支持 >> 操作符定义边

        Example:
            node1 >> node2  # 创建 node1 -> node2 的边
        """
        from .graph import ToolEdge
        return ToolEdge(self, other)

    def __or__(self, other: 'ToolNode') -> 'ParallelGroup':
        """
        支持 | 操作符定义并行组

        Example:
            (node1 | node2) >> node3  # node1 和 node2 并行，然后都完成后执行 node3
        """
        from .graph import ParallelGroup
        return ParallelGroup([self, other])

    def depends_on(self, node_id: str) -> 'ToolNode':
        """
        添加依赖关系

        Example:
            node3.depends_on(node1).depends_on(node2)
        """
        self._dependencies.add(node_id)
        # 同时更新被依赖节点的依赖者
        # 这里需要访问 graph，暂时跳过
        return self

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> NodeResult:
        """
        执行节点

        Args:
            inputs: 输入数据
            context: 执行上下文

        Returns:
            NodeResult: 执行结果
        """
        import time
        start_time = time.time()

        try:
            logger.debug(f"Executing node: {self.id}")

            # 合并默认输入
            resolved_inputs = {**self.inputs, **inputs}

            # 执行工具（优先使用 execute_async）
            if hasattr(self.tool, 'execute_async'):
                outputs = await self.tool.execute_async(**resolved_inputs)
            elif self.is_async:
                outputs = await self.tool.execute(**resolved_inputs)
            else:
                outputs = self.tool.execute(**resolved_inputs)

            # 处理输出
            if isinstance(outputs, dict):
                pass  # 已经是字典
            elif isinstance(outputs, (str, int, float, bool)):
                outputs = {"result": outputs}
            else:
                outputs = {"result": str(outputs)}

            return NodeResult(
                node_id=self.id,
                status=NodeStatus.COMPLETED,
                outputs=outputs,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"Node {self.id} execution failed: {e}")
            return NodeResult(
                node_id=self.id,
                status=NodeStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    def get_dependencies(self) -> Set[str]:
        """获取依赖的节点 ID"""
        return self._dependencies.copy()

    def get_dependents(self) -> Set[str]:
        """获取依赖此节点的节点 ID"""
        return self._dependents.copy()

    def add_dependent(self, node_id: str):
        """添加依赖者"""
        self._dependents.add(node_id)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "id": self.id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "config": {
                "retry": self.config.retry,
                "timeout": self.config.timeout,
                "fallback": self.config.fallback,
                "continue_on_error": self.config.continue_on_error,
            },
            "is_async": self.is_async,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolNode':
        """从字典创建节点"""
        config = NodeConfig(**data.get("config", {}))
        return cls(
            id=data["id"],
            tool=data["tool"],  # 注意：tool 是函数，无法从字典恢复
            inputs=data["inputs"],
            outputs=data.get("outputs", {}),
            config=config,
        )


# ============================================================================
# 工厂函数
# ============================================================================

def create_tool_node(
    id: str,
    tool: Callable,
    inputs: Dict[str, Any],
    config: Optional[NodeConfig] = None,
) -> ToolNode:
    """
    创建工具节点

    Args:
        id: 节点 ID
        tool: 工具函数
        inputs: 输入参数定义
        config: 节点配置

    Returns:
        ToolNode 实例

    Example:
        >>> node = create_tool_node(
        ...     "search",
        ...     search_tool,
        ...     {"query": str},
        ...     config=NodeConfig(retry=2)
        ... )
    """
    return ToolNode(
        id=id,
        tool=tool,
        inputs=inputs,
        config=config,
    )


def create_input_port(
    name: str,
    type: type,
    description: str = "",
    required: bool = True,
    default: Any = None,
) -> Dict[str, Any]:
    """
    创建输入端口定义

    Args:
        name: 端口名称
        type: 数据类型
        description: 描述
        required: 是否必需
        default: 默认值

    Returns:
        端口定义字典
    """
    port_def = {
        "type": type.__name__ if isinstance(type, type) else str(type),
        "description": description,
        "required": required,
    }

    if default is not None:
        port_def["default"] = default

    return {name: port_def}
