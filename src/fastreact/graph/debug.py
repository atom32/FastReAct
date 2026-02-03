"""
Debug System - 断点调试功能

支持在执行过程中暂停、检查状态、单步执行。
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .node import ToolNode, NodeResult, NodeStatus
from .graph import ToolGraph
from .state import GraphState
from .runtime import ToolRuntime, ExecutionReport

logger = logging.getLogger(__name__)


class DebugCommand(Enum):
    """调试命令"""
    CONTINUE = "continue"           # 继续执行到下一个断点
    STEP = "step"                 # 单步执行
    STEP_OVER = "step_over"         # 跨步执行（跳过子调用）
    STEP_OUT = "step_out"          # 跳出当前函数
    PAUSE = "pause"                 # 暂停
    INSPECT = "inspect"             # 检查变量
    SET_VARIABLE = "set"            # 设置变量
    LIST_BREAKPOINTS = "list"       # 列出断点
    ADD_BREAKPOINT = "add"           # 添加断点
    REMOVE_BREAKPOINT = "remove"    # 移除断点
    CLEAR_BREAKPOINTS = "clear"     # 清除断点
    QUIT = "quit"                   # 退出调试器


@dataclass
class Breakpoint:
    """
    断点定义

    Attributes:
        node_id: 节点 ID
        condition: 触发条件（可选）
        hit_count: 命中次数
        enabled: 是否启用
    """
    node_id: str
    condition: Optional[str] = None
    hit_count: int = 0
    enabled: bool = True

    def should_trigger(
        self,
        node_id: str,
        context: Dict[str, Any],
        state: GraphState,
    ) -> bool:
        """检查是否应该触发断点"""
        if not self.enabled:
            return False

        if self.node_id != node_id:
            return False

        if self.condition:
            # 评估条件
            try:
                from .conditional import ConditionalNode
                temp = ConditionalNode("temp", branches=[])
                return temp._evaluate_condition(
                    self.condition,
                    context.get("_variables", {}),
                    context.get("_variables", {}),
                    [],  # 不需要 outputs
                )
            except Exception as e:
                logger.warning(f"Breakpoint condition evaluation failed: {e}")
                return True  # 条件评估失败时触发

        return True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "condition": self.condition,
            "hit_count": self.hit_count,
            "enabled": self.enabled,
        }


@dataclass
class DebugFrame:
    """
    调试栈帧

    Attributes:
        node_id: 当前节点 ID
        node: 节点实例
        inputs: 输入数据
        context: 执行上下文
        state: 图状态
        timestamp: 时间戳
    """
    node_id: str
    node: ToolNode
    inputs: Dict[str, Any]
    context: Dict[str, Any]
    state: GraphState
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "inputs": self.inputs,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class DebugSession:
    """
    调试会话

    管理调试状态、断点、栈帧等。

    Attributes:
        graph: 被调试的图
        breakpoints: 断点列表
        current_frame: 当前栈帧
        frames: 调用栈
        command_queue: 命令队列
        paused: 是否暂停
    """
    graph: ToolGraph
    breakpoints: List[Breakpoint] = field(default_factory=list)
    current_frame: Optional[DebugFrame] = None
    frames: List[DebugFrame] = field(default_factory=list)
    paused: bool = False
    step_mode: bool = False
    stop_on_entry: bool = False
    stop_on_node_start: bool = False

    async def _command_processor(self):
        """异步处理调试命令"""
        while self.paused or self.step_mode:
            if self.command_queue:
                cmd = await self.command_queue.get()
                await self._process_command(cmd)

                if cmd == DebugCommand.QUIT:
                    break

            await asyncio.sleep(0.1)

    async def _process_command(self, cmd: DebugCommand):
        """处理调试命令"""
        if cmd == DebugCommand.CONTINUE:
            self.paused = False
            self.step_mode = False

        elif cmd == DebugCommand.STEP:
            self.paused = False
            self.step_mode = True

        elif cmd == DebugCommand.PAUSE:
            self.paused = True

        # ... 其他命令处理


class Debugger:
    """
    调试器

    提供断点、单步执行、状态检查等功能。

    Attributes:
        session: 调试会话
        input_callback: 用户输入回调
    """

    def __init__(
        self,
        input_callback: Optional[Callable[[str], Awaitable[str]]] = None,
    ):
        """
        初始化调试器

        Args:
            input_callback: 用户输入回调函数
        """
        self.input_callback = input_callback
        self.session: Optional[DebugSession] = None

    async def debug_graph(
        self,
        graph: ToolGraph,
        inputs: Optional[Dict[str, Any]] = None,
        initial_breakpoints: List[str] = None,
    ) -> ExecutionReport:
        """
        调试图执行

        Args:
            graph: 要调试的图
            inputs: 初始输入
            initial_breakpoints: 初始断点列表

        Returns:
            ExecutionReport: 执行报告
        """
        # 创建调试会话
        self.session = DebugSession(graph=graph)

        # 添加初始断点
        if initial_breakpoints:
            for bp_id in initial_breakpoints:
                self.add_breakpoint(bp_id)

        # 使用自定义的调试运行时
        runtime = DebuggingRuntime(
            debugger=self,
            session=self.session,
        )

        # 执行图
        return await runtime.execute(graph, initial_inputs=inputs)

    def add_breakpoint(
        self,
        node_id: str,
        condition: Optional[str] = None,
    ) -> Breakpoint:
        """
        添加断点

        Args:
            node_id: 节点 ID
            condition: 触发条件

        Returns:
            Breakpoint 实例
        """
        # 懒初始化 session
        if self.session is None:
            self.session = DebugSession(graph=None)

        bp = Breakpoint(node_id=node_id, condition=condition)
        self.session.breakpoints.append(bp)
        logger.info(f"Added breakpoint at {node_id}")
        return bp

    def remove_breakpoint(self, node_id: str) -> bool:
        """
        移除断点

        Args:
            node_id: 节点 ID

        Returns:
            是否成功移除
        """
        if self.session is None:
            return False

        for i, bp in enumerate(self.session.breakpoints):
            if bp.node_id == node_id:
                del self.session.breakpoints[i]
                logger.info(f"Removed breakpoint at {node_id}")
                return True
        return False

    def list_breakpoints(self) -> List[Breakpoint]:
        """列出所有断点"""
        if self.session is None:
            return []
        return self.session.breakpoints.copy()

    def clear_breakpoints(self):
        """清空所有断点"""
        if self.session is not None:
            self.session.breakpoints.clear()
        logger.info("Cleared all breakpoints")

    async def inspect_frame(self, frame: DebugFrame) -> Dict[str, Any]:
        """
        检查栈帧

        Args:
            frame: 调试栈帧

        Returns:
            栈帧信息
        """
        return {
            "current_node": frame.node_id,
            "inputs": frame.inputs,
            "context": frame.context,
            "state_summary": {
                "completed": list(frame.state.completed_nodes),
                "failed": list(frame.state.failed_nodes),
            },
            "available_variables": self._get_available_variables(frame),
        }

    def _get_available_variables(
        self,
        frame: DebugFrame
    ) -> Dict[str, Any]:
        """获取可用变量"""
        variables = {}

        # 从 context
        if "_variables" in frame.context:
            variables.update(frame.context["_variables"])

        # 从 state
        for node_id, output in frame.state.node_outputs.items():
            variables[f"{node_id}_output"] = output.outputs

        return variables

    async def set_variable(
        self,
        name: str,
        value: Any,
        frame: Optional[DebugFrame] = None,
    ) -> bool:
        """
        设置变量

        Args:
            name: 变量名
            value: 变量值
            frame: 栈帧（可选，当前为默认）

        Returns:
            是否成功设置
        """
        target_frame = frame or self.session.current_frame
        if not target_frame:
            return False

        if "_variables" not in target_frame.context:
            target_frame.context["_variables"] = {}

        target_frame.context["_variables"][name] = value
        logger.info(f"Set variable: {name} = {value}")
        return True

    async def pause(self):
        """暂停执行"""
        if self.session is None:
            self.session = DebugSession(graph=None)
        self.session.paused = True
        logger.info("Execution paused")

    async def continue_exec(self):
        """继续执行"""
        if self.session is None:
            self.session = DebugSession(graph=None)
        self.session.paused = False
        self.session.step_mode = False
        logger.info("Execution continued")

    async def step(self):
        """单步执行"""
        if self.session is None:
            self.session = DebugSession(graph=None)
        self.session.paused = False
        self.session.step_mode = True
        logger.info("Single step execution")


class DebuggingRuntime(ToolRuntime):
    """
    调试运行时 - 支持断点的执行引擎

    在执行过程中检查断点，暂停执行，允许检查状态。
    """

    def __init__(
        self,
        debugger: Debugger,
        session: DebugSession,
        state: Optional[GraphState] = None,
        config=None,
    ):
        """
        初始化调试运行时

        Args:
            debugger: 调试器实例
            session: 调试会话
            state: 图状态
            config: 执行配置
        """
        super().__init__(state=state, config=config)
        self.debugger = debugger
        self.session = session

    async def execute(
        self,
        graph: ToolGraph,
        initial_inputs: Optional[Dict[str, Any]] = None,
    ) -> ExecutionReport:
        """
        执行图（带断点检查）

        Args:
            graph: 工具图
            initial_inputs: 初始输入

        Returns:
            ExecutionReport: 执行报告
        """
        from .node import NodeStatus

        # 存储节点执行前的状态
        node_results = {}

        # 准备执行上下文
        if initial_inputs:
            for key, value in initial_inputs.items():
                self.state.context.set(key, value)

        # 检查入口点断点
        entry_nodes = graph.get_entry_points()
        for entry in entry_nodes:
            for bp in self.session.breakpoints:
                if bp.should_trigger(entry.id, self.state.context.to_dict(), self.state):
                    self._trigger_breakpoint(bp)
                    await self._wait_for_continue()

        # 使用父类的执行逻辑，但包装节点执行
        start_time = asyncio.get_event_loop().time()

        try:
            # 简化版本：遍历拓扑排序的节点
            sorted_nodes = graph.topological_sort()

            for node in sorted_nodes:
                # 检查断点
                should_pause = self._check_breakpoints_before(node)
                if should_pause:
                    await self._handle_breakpoint(node, {})

                # 执行节点
                result = await self._execute_node_with_debug(
                    node,
                    initial_inputs or {},
                )

                node_results[node.id] = result

                # 更新状态
                if result.status == NodeStatus.COMPLETED:
                    self.state.set_node_output(node.id, result.outputs)
                elif result.status == NodeStatus.FAILED:
                    self.state.set_node_output(node.id, {}, status="failed")

                # 检查完成后断点
                should_pause_after = self._check_breakpoints_after(node)
                if should_pause_after:
                    await self._handle_breakpoint(node, {})

                # 检查是否应该停止
                if self.session.paused and not self.session.step_mode:
                    break

            # 生成报告
            execution_time = asyncio.get_event_loop().time() - start_time

            completed = sum(1 for r in node_results.values() if r.status == NodeStatus.COMPLETED)
            failed = sum(1 for r in node_results.values() if r.status == NodeStatus.FAILED)

            return ExecutionReport(
                success=failed == 0,
                total_nodes=len(graph.nodes),
                completed_nodes=completed,
                failed_nodes=failed,
                execution_time=execution_time,
                node_results=node_results,
                errors=[],
            )

        except Exception as e:
            logger.error(f"Debug execution failed: {e}")
            return ExecutionReport(
                success=False,
                total_nodes=len(graph.nodes),
                completed_nodes=0,
                failed_nodes=0,
                execution_time=0,
                node_results=node_results,
                errors=[str(e)],
            )

    def _check_breakpoints_before(self, node: ToolNode) -> bool:
        """检查节点执行前的断点"""
        for bp in self.session.breakpoints:
            if bp.should_trigger(node.id, self.state.context.to_dict(), self.state):
                logger.info(f"Breakpoint hit at {node.id} (before execution)")
                bp.hit_count += 1
                return True
        return False

    def _check_breakpoints_after(self, node: ToolNode) -> bool:
        """检查节点执行后的断点"""
        # 可以添加执行后的断点逻辑
        return False

    async def _execute_node_with_debug(
        self,
        node: ToolNode,
        inputs: Dict[str, Any],
    ) -> NodeResult:
        """执行节点（带调试支持）"""
        return await node.execute(inputs, self.state.context.to_dict())

    async def _trigger_breakpoint(self, breakpoint: Breakpoint):
        """触发断点"""
        logger.info(f"Breakpoint triggered: {breakpoint.node_id}")

        if self.debugger.input_callback:
            # 等待用户命令
            while self.session.paused:
                cmd_str = await self.debugger.input_callback("debug> ")
                cmd = self._parse_command(cmd_str)

                if cmd == DebugCommand.QUIT:
                    self.session.paused = False
                    break
                elif cmd == DebugCommand.CONTINUE:
                    await self.debugger.continue_exec()
                    break
                elif cmd == DebugCommand.STEP:
                    await self.debugger.step()
                    break
                elif cmd == DebugCommand.INSPECT:
                    # 显示当前状态
                    if self.session.current_frame:
                        info = await self.debugger.inspect_frame(self.session.current_frame)
                        print(f"Current state: {info}")

                await asyncio.sleep(0.1)

    async def _wait_for_continue(self):
        """等待继续命令"""
        self.session.paused = True
        await self._trigger_breakpoint(Breakpoint(node_id="pause"))

    def _parse_command(self, cmd_str: str) -> DebugCommand:
        """解析命令字符串"""
        cmd_str = cmd_str.strip().lower()

        if cmd_str in ["c", "continue", "cont"]:
            return DebugCommand.CONTINUE
        elif cmd_str in ["s", "step", "n", "next"]:
            return DebugCommand.STEP
        elif cmd_str in ["p", "pause"]:
            return DebugCommand.PAUSE
        elif cmd_str in ["q", "quit", "exit"]:
            return DebugCommand.QUIT
        elif cmd_str in ["i", "inspect", "info"]:
            return DebugCommand.INSPECT
        else:
            logger.debug(f"Unknown command: {cmd_str}")
            return DebugCommand.CONTINUE


# ============================================================================
# 工厂函数
# ============================================================================

def create_debugger(
    input_callback: Optional[Callable[[str], Awaitable[str]]] = None,
) -> Debugger:
    """
    创建调试器

    Args:
        input_callback: 用户输入回调

    Returns:
        Debugger 实例
    """
    return Debugger(input_callback=input_callback)


async def debug_graph(
    graph: ToolGraph,
    inputs: Optional[Dict[str, Any]] = None,
    breakpoints: List[str] = None,
    input_callback: Optional[Callable[[str], Awaitable[str]]] = None,
) -> ExecutionReport:
    """
    快捷函数：调试图执行

    Args:
        graph: 工具图
        inputs: 初始输入
        breakpoints: 断点列表
        input_callback: 用户输入回调

    Returns:
        ExecutionReport: 执行报告

    Example:
        >>> report = await debug_graph(
        ...     graph,
        ...     inputs={"query": "test"},
        ...     breakpoints=["node1", "node2"]
        ... )
    """
    debugger = create_debugger(input_callback=input_callback)
    return await debugger.debug_graph(graph, inputs, breakpoints)
