"""
Conditional Node - 条件执行节点

支持基于表达式的条件分支执行。
"""

import logging
import re
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass
from enum import Enum

from .node import ToolNode, NodeResult, NodeStatus
from .state import GraphState

logger = logging.getLogger(__name__)


class ConditionType(Enum):
    """条件类型"""
    EQUAL = "=="
    NOT_EQUAL = "!="
    GREATER = ">"
    LESS = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    REGEX = "regex"
    AND = "and"
    OR = "or"


@dataclass
class Branch:
    """
    分支定义

    Attributes:
        condition: 条件表达式
        node: 要执行的节点
        name: 分支名称（可选）
    """
    condition: str
    node: ToolNode
    name: Optional[str] = None

    def __post_init__(self):
        if self.name is None:
            self.name = f"branch_{id(self)}"


class ConditionalNode(ToolNode):
    """
    条件节点 - 根据条件选择执行分支

    Example:
        # 创建 if/else 结构
        true_branch = create_tool_node("true_node", tool_a, {})
        false_branch = create_tool_node("false_node", tool_b, {})

        conditional = ConditionalNode(
            id="if_check",
            branches=[
                Branch("@input.value > 10", true_branch, "high"),
                Branch("@input.value <= 10", false_branch, "low"),
            ],
            default_branch=false_branch,
        )
    """

    def __init__(
        self,
        id: str,
        branches: List[Branch],
        default_branch: Optional[ToolNode] = None,
        inputs: Dict[str, Any] = None,
        config=None,
    ):
        """
        初始化条件节点

        Args:
            id: 节点 ID
            branches: 分支列表（按顺序评估）
            default_branch: 默认分支（所有条件都不满足时执行）
            inputs: 输入定义
            config: 节点配置
        """
        # 创建一个空的 tool 函数（实际执行在 evaluate_branches 中）
        async def conditional_tool(**kwargs):
            return {"_conditional": True}

        super().__init__(id=id, tool=conditional_tool, inputs=inputs or {}, config=config)

        self.branches = branches
        self.default_branch = default_branch
        self._selected_branch: Optional[Branch] = None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> NodeResult:
        """
        执行条件节点

        Args:
            inputs: 输入数据
            context: 执行上下文

        Returns:
            NodeResult: 执行结果
        """
        import time
        start_time = time.time()

        try:
            logger.debug(f"Evaluating conditional node: {self.id}")

            # 评估条件，选择分支
            selected_branch = self._evaluate_conditions(inputs, context or {})

            if selected_branch is None:
                if self.default_branch:
                    selected_branch = Branch(
                        condition="default",
                        node=self.default_branch,
                        name="default",
                    )
                    logger.debug(f"Using default branch for {self.id}")
                else:
                    # 没有匹配的分支和默认值
                    return NodeResult(
                        node_id=self.id,
                        status=NodeStatus.SKIPPED,
                        outputs={"skipped": "No condition matched"},
                        execution_time=time.time() - start_time,
                    )

            self._selected_branch = selected_branch

            # 执行选中的分支
            logger.debug(f"Executing branch: {selected_branch.name} for {self.id}")
            result = await selected_branch.node.execute(inputs, context)

            # 包装结果
            return NodeResult(
                node_id=self.id,
                status=result.status,
                outputs={
                    "_branch": selected_branch.name,
                    "_condition": selected_branch.condition,
                    **result.outputs,
                },
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"Conditional node {self.id} execution failed: {e}")
            return NodeResult(
                node_id=self.id,
                status=NodeStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    def _evaluate_conditions(
        self,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Optional[Branch]:
        """
        评估条件，返回第一个匹配的分支

        Args:
            inputs: 输入数据
            context: 执行上下文

        Returns:
            匹配的分支，如果没有匹配返回 None
        """
        for branch in self.branches:
            try:
                if self._evaluate_condition(branch.condition, inputs, context):
                    return branch
            except Exception as e:
                logger.warning(f"Failed to evaluate condition '{branch.condition}': {e}")
                continue

        return None

    def _evaluate_condition(
        self,
        condition: str,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """
        评估单个条件

        支持的语法：
        - @input.key == value  或  @key == value
        - @node.result > 10
        - @key in [a, b, c]
        - @key contains "substring"

        Args:
            condition: 条件表达式
            inputs: 输入数据
            context: 执行上下文

        Returns:
            条件是否为真
        """
        # 解析条件
        parsed = self._parse_condition(condition)
        if not parsed:
            raise ValueError(f"Invalid condition: {condition}")

        # 解析左侧值
        left_val = self._resolve_value(parsed["left"], inputs, context)
        # 解析右侧值
        right_val = self._resolve_value(parsed["right"], inputs, context)

        # 执行比较
        return self._compare(parsed["op"], left_val, right_val)

    def _resolve_value(
        self,
        value_ref: str,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        解析值引用

        支持的格式：
        - @key: 从 inputs 或 context 获取
        - @input.key: 从 inputs 获取
        - @_last.key: 从上次输出获取
        - @node_id.key: 从 node outputs 获取（暂不支持）
        - 直接值：数字、字符串等
        """
        value_ref = value_ref.strip()

        # 如果不是引用格式，直接返回
        if not value_ref.startswith("@"):
            # 尝试解析为字面量
            return self._parse_literal(value_ref)

        # 移除 @ 前缀
        ref = value_ref[1:]

        # 检查是否是 node.key 格式
        if "." in ref:
            prefix, key = ref.split(".", 1)
            if prefix == "input":
                # @input.key 格式
                return inputs.get(key)
            elif prefix == "_last":
                # @_last.key 格式 - 从 context 获取上次输出
                if "_last" in context:
                    return context["_last"].get(key)
                return None
            else:
                # @node_id.key 格式 - 暂不支持，返回 None
                return None
        else:
            # @key 格式 - 先从 inputs 查找，再从 context 查找
            if ref in inputs:
                return inputs[ref]
            elif ref in context:
                return context[ref]
            else:
                return None

    def _parse_literal(self, value: str) -> Any:
        """
        解析字面量值

        支持数字、布尔值、字符串、列表
        """
        value = value.strip()

        # 布尔值
        if value == "True":
            return True
        elif value == "False":
            return False
        elif value == "None":
            return None

        # 数字
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # 字符串（去掉引号）
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]

        # 列表
        if value.startswith("[") and value.endswith("]"):
            try:
                import ast
                return ast.literal_eval(value)
            except:
                pass

        # 默认返回字符串
        return value

    def _parse_condition(self, condition: str) -> Optional[Dict[str, Any]]:
        """
        解析条件表达式

        支持格式：
        - left == right
        - left > right
        - left in right
        - left contains "substring"
        """
        # 按优先级尝试匹配操作符
        operators = [
            (r"\s+contains\s+", "contains"),
            (r"\s+not_contains\s+", "not_contains"),
            (r"\s+not_in\s+", "not_in"),
            (r"\s+in\s+", "in"),
            (r"\s+>=\s+", ">="),
            (r"\s+<=\s+", "<="),
            (r"\s+!=\s+", "!="),
            (r"\s+==\s+", "=="),
            (r"\s+>\s+", ">"),
            (r"\s+<\s+", "<"),
        ]

        for pattern, op in operators:
            if re.search(pattern, condition):
                parts = re.split(pattern, condition, maxsplit=1)
                if len(parts) == 2:
                    return {
                        "left": parts[0].strip(),
                        "op": op,
                        "right": parts[1].strip(),
                    }

        return None

    def _compare(self, op: str, left: Any, right: Any) -> bool:
        """执行比较操作"""
        try:
            if op == "==":
                return left == right
            elif op == "!=":
                return left != right
            elif op == ">":
                return left > right
            elif op == "<":
                return left < right
            elif op == ">=":
                return left >= right
            elif op == "<=":
                return left <= right
            elif op == "in":
                return left in right if isinstance(right, (list, tuple, set)) else False
            elif op == "not_in":
                return left not in right if isinstance(right, (list, tuple, set)) else True
            elif op == "contains":
                return str(right) in str(left) if left is not None else False
            elif op == "not_contains":
                return str(right) not in str(left) if left is not None else True
            else:
                raise ValueError(f"Unknown operator: {op}")
        except Exception as e:
            logger.warning(f"Comparison failed: {op} {left} {right}: {e}")
            return False

    def get_selected_branch(self) -> Optional[Branch]:
        """获取实际执行的分支"""
        return self._selected_branch

    def get_branch_nodes(self) -> List[ToolNode]:
        """获取所有分支节点"""
        nodes = [branch.node for branch in self.branches]
        if self.default_branch:
            nodes.append(self.default_branch)
        return nodes


def create_conditional_node(
    id: str,
    branches: List[Branch],
    default_branch: Optional[ToolNode] = None,
    inputs: Dict[str, Any] = None,
) -> ConditionalNode:
    """
    创建条件节点

    Args:
        id: 节点 ID
        branches: 分支列表
        default_branch: 默认分支
        inputs: 输入定义

    Returns:
        ConditionalNode 实例

    Example:
        >>> high_node = create_tool_node("high", tool_a, {})
        >>> low_node = create_tool_node("low", tool_b, {})
        >>> conditional = create_conditional_node(
        ...     "check",
        ...     branches=[
        ...         Branch("@value > 10", high_node),
        ...         Branch("@value <= 10", low_node),
        ...     ]
        ... )
    """
    return ConditionalNode(
        id=id,
        branches=branches,
        default_branch=default_branch,
        inputs=inputs,
    )


def if_then_else(
    condition: str,
    then_node: ToolNode,
    else_node: ToolNode,
    id: str = "if_then_else",
) -> ConditionalNode:
    """
    创建 if-then-else 条件节点

    Args:
        condition: 条件表达式
        then_node: 条件为真时执行的节点
        else_node: 条件为假时执行的节点
        id: 节点 ID

    Returns:
        ConditionalNode 实例

    Example:
        >>> conditional = if_then_else(
        ...     "@input.value > 10",
        ...     high_node,
        ...     low_node
        ... )
    """
    return create_conditional_node(
        id=id,
        branches=[
            Branch(condition, then_node, "then"),
        ],
        default_branch=else_node,
    )


def switch_case(
    value_expr: str,
    cases: Dict[Any, ToolNode],
    default_node: Optional[ToolNode] = None,
    id: str = "switch",
) -> ConditionalNode:
    """
    创建 switch-case 条件节点

    Args:
        value_expr: 值表达式（如 "@input.choice"）
        cases: case 映射 {value: node}
        default_node: 默认节点
        id: 节点 ID

    Returns:
        ConditionalNode 实例

    Example:
        >>> conditional = switch_case(
        ...     "@input.type",
        ...     {
        ...         "A": node_a,
        ...         "B": node_b,
        ...         "C": node_c,
        ...     },
        ...     default_node=node_default
        ... )
    """
    branches = []
    for value, node in cases.items():
        condition = f"{value_expr} == {value}"
        branches.append(Branch(condition, node, f"case_{value}"))

    return create_conditional_node(
        id=id,
        branches=branches,
        default_branch=default_node,
    )
