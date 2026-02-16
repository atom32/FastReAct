"""
Loop Node - 循环执行节点

支持 for 和 while 循环结构。
"""

import logging
import time
from typing import Dict, Any, Optional, List, Callable, Union, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

from .node import ToolNode, NodeResult, NodeStatus
from .state import GraphState

logger = logging.getLogger(__name__)


class LoopType(Enum):
    """循环类型"""
    FOR = "for"           # 固定次数循环
    WHILE = "while"       # 条件循环
    FOR_EACH = "for_each" # 集合迭代


@dataclass
class LoopResult:
    """
    循环执行结果

    Attributes:
        iterations: 实际迭代次数
        outputs: 所有迭代输出列表
        break_triggered: 是否被 break 触发
        final_state: 最终状态
    """
    iterations: int
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    break_triggered: bool = False
    final_state: Dict[str, Any] = field(default_factory=dict)


class LoopNode(ToolNode):
    """
    循环节点 - 重复执行子节点

    Example:
        # For 循环
        loop = LoopNode.for_loop(
            id="repeat_5_times",
            node=tool_node,
            iterations=5,
        )

        # While 循环
        loop = LoopNode.while_loop(
            id="until_done",
            node=tool_node,
            condition="@output.status != 'done'",
            max_iterations=10,
        )

        # For-Each 循环
        loop = LoopNode.for_each(
            id="process_items",
            node=tool_node,
            items="@input.list",
            item_var="item",
        )
    """

    def __init__(
        self,
        id: str,
        node: ToolNode,
        loop_type: LoopType,
        iterations: Optional[int] = None,
        condition: Optional[str] = None,
        items_expr: Optional[str] = None,
        item_var: str = "item",
        max_iterations: int = 100,
        inputs: Dict[str, Any] = None,
        config=None,
    ):
        """
        初始化循环节点

        Args:
            id: 节点 ID
            node: 要重复执行的节点
            loop_type: 循环类型
            iterations: 迭代次数（for 循环）
            condition: 继续条件（while 循环）
            items_expr: 集合表达式（for_each 循环）
            item_var: 迭代变量名（for_each 循环）
            max_iterations: 最大迭代次数限制
            inputs: 输入定义
            config: 节点配置
        """
        async def loop_tool(**kwargs):
            return {"_loop": True}

        super().__init__(id=id, tool=loop_tool, inputs=inputs or {}, config=config)

        self.loop_node = node
        self.loop_type = loop_type
        self.iterations = iterations
        self.condition = condition
        self.items_expr = items_expr
        self.item_var = item_var
        self.max_iterations = max_iterations

        self._loop_result: Optional[LoopResult] = None

    async def execute(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> NodeResult:
        """
        执行循环

        Args:
            inputs: 输入数据
            context: 执行上下文

        Returns:
            NodeResult: 执行结果
        """
        import time
        start_time = time.time()

        try:
            logger.debug(f"Executing {self.loop_type.value} loop: {self.id}")

            if self.loop_type == LoopType.FOR:
                loop_result = await self._execute_for_loop(inputs, context)
            elif self.loop_type == LoopType.WHILE:
                loop_result = await self._execute_while_loop(inputs, context)
            elif self.loop_type == LoopType.FOR_EACH:
                loop_result = await self._execute_for_each(inputs, context)
            else:
                raise ValueError(f"Unknown loop type: {self.loop_type}")

            self._loop_result = loop_result

            # 返回结果
            return NodeResult(
                node_id=self.id,
                status=NodeStatus.COMPLETED,
                outputs={
                    "_iterations": loop_result.iterations,
                    "_outputs": loop_result.outputs,
                    "_break_triggered": loop_result.break_triggered,
                },
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"Loop node {self.id} execution failed: {e}")
            return NodeResult(
                node_id=self.id,
                status=NodeStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def _execute_for_loop(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> LoopResult:
        """执行 for 循环"""
        iterations = min(self.iterations or 0, self.max_iterations)
        outputs = []

        for i in range(iterations):
            # 添加迭代变量到 inputs
            loop_inputs = {
                **inputs,
                "_index": i,
                "_iteration": i + 1,
            }

            result = await self.loop_node.execute(loop_inputs, context)

            if result.status == NodeStatus.FAILED:
                logger.warning(f"Loop iteration {i} failed: {result.error}")
                if not self.config.continue_on_error:
                    break

            outputs.append(result.outputs)

        return LoopResult(
            iterations=len(outputs),
            outputs=outputs,
        )

    async def _execute_while_loop(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> LoopResult:
        """执行 while 循环"""
        if not self.condition:
            raise ValueError("While loop requires a condition")

        outputs = []
        iteration = 0
        loop_context = dict(context or {})

        # 执行至少一次（do-while 语义）
        while iteration < self.max_iterations:
            # 执行节点
            loop_inputs = {
                **inputs,
                "_index": iteration,
                "_iteration": iteration + 1,
            }

            result = await self.loop_node.execute(loop_inputs, loop_context)

            if result.status == NodeStatus.FAILED:
                logger.warning(f"While loop iteration {iteration} failed: {result.error}")
                if not self.config.continue_on_error:
                    break

            outputs.append(result.outputs)
            iteration += 1

            # 检查是否应该继续
            should_continue = self._evaluate_condition(
                self.condition,
                inputs,
                loop_context,
                outputs,
            )

            if not should_continue:
                logger.debug(f"While loop condition false at iteration {iteration}")
                break

        return LoopResult(
            iterations=len(outputs),
            outputs=outputs,
        )

    async def _execute_for_each(
        self,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> LoopResult:
        """执行 for-each 循环"""
        # 解析集合
        items = self._resolve_items(self.items_expr, inputs, context)

        if not items:
            return LoopResult(iterations=0, outputs=[])

        outputs = []
        iterations = min(len(items), self.max_iterations)

        for i, item in enumerate(items[:iterations]):
            # 添加迭代变量
            loop_inputs = {
                **inputs,
                self.item_var: item,
                "_index": i,
                "_iteration": i + 1,
            }

            result = await self.loop_node.execute(loop_inputs, context)

            if result.status == NodeStatus.FAILED:
                logger.warning(f"For-each iteration {i} failed: {result.error}")
                if not self.config.continue_on_error:
                    break

            outputs.append(result.outputs)

        return LoopResult(
            iterations=iterations,
            outputs=outputs,
        )

    def _evaluate_condition(
        self,
        condition: str,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
        outputs: List[Dict[str, Any]],
    ) -> bool:
        """
        评估 while 循环条件

        支持的特殊变量：
        - @_index: 当前索引
        - @_iteration: 当前迭代次数（从1开始）
        - @_last: 上一次迭代的输出
        """
        from .conditional import ConditionalNode

        # 创建临时条件节点用于评估
        temp_conditional = ConditionalNode(
            id="temp",
            branches=[],
        )

        # 添加上一次输出到 context（如果有）
        eval_context = dict(context or {})
        if outputs:
            eval_context["_last"] = outputs[-1]

        try:
            return temp_conditional._evaluate_condition(condition, inputs, eval_context)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}")
            return False

    def _resolve_items(
        self,
        expr: str,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> List[Any]:
        """
        解析集合表达式

        支持：
        - @input.list: 从 inputs 获取列表
        - @context.list: 从 context 获取列表
        - 直接列表字面量: [1, 2, 3]
        """
        from .conditional import ConditionalNode

        temp_conditional = ConditionalNode(id="temp", branches=[])
        value = temp_conditional._resolve_value(expr, inputs, context or {})

        if isinstance(value, list):
            return value
        elif isinstance(value, (str, bytes)):
            # 字符串转为字符列表
            return list(value)
        else:
            logger.warning(f"Items expression '{expr}' did not resolve to a list")
            return []

    def get_loop_result(self) -> Optional[LoopResult]:
        """获取循环结果"""
        return self._loop_result

    @classmethod
    def for_loop(
        cls,
        id: str,
        node: ToolNode,
        iterations: int,
        max_iterations: int = 100,
        inputs: Dict[str, Any] = None,
        config=None,
    ) -> 'LoopNode':
        """创建 for 循环节点"""
        return cls(
            id=id,
            node=node,
            loop_type=LoopType.FOR,
            iterations=iterations,
            max_iterations=max_iterations,
            inputs=inputs,
            config=config,
        )

    @classmethod
    def while_loop(
        cls,
        id: str,
        node: ToolNode,
        condition: str,
        max_iterations: int = 100,
        inputs: Dict[str, Any] = None,
        config=None,
    ) -> 'LoopNode':
        """创建 while 循环节点"""
        return cls(
            id=id,
            node=node,
            loop_type=LoopType.WHILE,
            condition=condition,
            max_iterations=max_iterations,
            inputs=inputs,
            config=config,
        )

    @classmethod
    def for_each(
        cls,
        id: str,
        node: ToolNode,
        items_expr: str,
        item_var: str = "item",
        max_iterations: int = 100,
        inputs: Dict[str, Any] = None,
        config=None,
    ) -> 'LoopNode':
        """创建 for-each 循环节点"""
        return cls(
            id=id,
            node=node,
            loop_type=LoopType.FOR_EACH,
            items_expr=items_expr,
            item_var=item_var,
            max_iterations=max_iterations,
            inputs=inputs,
            config=config,
        )


def create_loop_node(
    id: str,
    node: ToolNode,
    iterations: int = 1,
    max_iterations: int = 100,
) -> LoopNode:
    """
    创建循环节点

    Args:
        id: 节点 ID
        node: 要重复执行的节点
        iterations: 迭代次数
        max_iterations: 最大迭代次数限制

    Returns:
        LoopNode 实例

    Example:
        >>> loop = create_loop_node(
        ...     "repeat",
        ...     tool_node,
        ...     iterations=5
        ... )
    """
    return LoopNode.for_loop(
        id=id,
        node=node,
        iterations=iterations,
        max_iterations=max_iterations,
    )


def repeat(
    node: ToolNode,
    times: int,
    id: Optional[str] = None,
) -> LoopNode:
    """
    重复执行节点多次次

    Args:
        node: 要重复的节点
        times: 重复次数
        id: 节点 ID（可选）

    Returns:
        LoopNode 实例

    Example:
        >>> loop = repeat(tool_node, 5)
    """
    if id is None:
        id = f"repeat_{node.id}_{times}"

    return LoopNode.for_loop(
        id=id,
        node=node,
        iterations=times,
    )


def while_true(
    node: ToolNode,
    condition: str,
    id: Optional[str] = None,
    max_iterations: int = 100,
) -> LoopNode:
    """
    当条件为真时重复执行

    Args:
        node: 要重复的节点
        condition: 继续条件
        id: 节点 ID（可选）
        max_iterations: 最大迭代次数

    Returns:
        LoopNode 实例

    Example:
        >>> loop = while_true(
        ...     tool_node,
        ...     "@_last.status != 'done'"
        ... )
    """
    if id is None:
        id = f"while_{node.id}"

    return LoopNode.while_loop(
        id=id,
        node=node,
        condition=condition,
        max_iterations=max_iterations,
    )


def for_each(
    node: ToolNode,
    items_expr: str,
    id: Optional[str] = None,
    item_var: str = "item",
) -> LoopNode:
    """
    对集合中每个元素执行节点

    Args:
        node: 要执行的节点
        items_expr: 集合表达式（如 "@input.list"）
        id: 节点 ID（可选）
        item_var: 迭代变量名

    Returns:
        LoopNode 实例

    Example:
        >>> loop = for_each(
        ...     tool_node,
        ...     "@input.items",
        ...     item_var="item"
        ... )
    """
    if id is None:
        id = f"foreach_{node.id}"

    return LoopNode.for_each(
        id=id,
        node=node,
        items_expr=items_expr,
        item_var=item_var,
    )
