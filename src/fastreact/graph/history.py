"""
Execution History - 执行历史回放

支持记录图执行过程，保存快照，回放执行。
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import copy

from .node import ToolNode, NodeResult, NodeStatus
from .graph import ToolGraph
from .state import GraphState
from .runtime import ToolRuntime, ExecutionReport

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型"""
    GRAPH_START = "graph_start"
    GRAPH_END = "graph_end"
    NODE_START = "node_start"
    NODE_END = "node_end"
    NODE_ERROR = "node_error"
    SNAPSHOT = "snapshot"


@dataclass
class ExecutionEvent:
    """
    执行事件

    Attributes:
        event_type: 事件类型
        timestamp: 时间戳
        node_id: 节点 ID（可选）
        data: 事件数据
    """
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    node_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "node_id": self.node_id,
            "data": self.data,
        }


@dataclass
class ExecutionSnapshot:
    """
    执行快照

    保存执行过程中的完整状态。

    Attributes:
        timestamp: 时间戳
        state: 图状态快照
        current_node: 当前节点
        completed_nodes: 已完成节点
        failed_nodes: 失败节点
        metadata: 元数据
    """
    timestamp: datetime = field(default_factory=datetime.now)
    state: Optional[Dict[str, Any]] = None
    current_node: Optional[str] = None
    completed_nodes: List[str] = field(default_factory=list)
    failed_nodes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "state": self.state,
            "current_node": self.current_node,
            "completed_nodes": self.completed_nodes,
            "failed_nodes": self.failed_nodes,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionHistory:
    """
    执行历史

    Attributes:
        graph_id: 图 ID
        start_time: 开始时间
        end_time: 结束时间
        events: 事件列表
        snapshots: 快照列表
        initial_inputs: 初始输入
        final_report: 最终报告
    """
    graph_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    events: List[ExecutionEvent] = field(default_factory=list)
    snapshots: List[ExecutionSnapshot] = field(default_factory=list)
    initial_inputs: Dict[str, Any] = field(default_factory=dict)
    final_report: Optional[ExecutionReport] = None

    def add_event(self, event: ExecutionEvent):
        """添加事件"""
        self.events.append(event)

    def add_snapshot(self, snapshot: ExecutionSnapshot):
        """添加快照"""
        self.snapshots.append(snapshot)

    def get_events_by_node(self, node_id: str) -> List[ExecutionEvent]:
        """获取指定节点的事件"""
        return [e for e in self.events if e.node_id == node_id]

    def get_events_by_type(self, event_type: EventType) -> List[ExecutionEvent]:
        """获取指定类型的事件"""
        return [e for e in self.events if e.event_type == event_type]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "graph_id": self.graph_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "events": [e.to_dict() for e in self.events],
            "snapshots": [s.to_dict() for s in self.snapshots],
            "initial_inputs": self.initial_inputs,
            "final_report": self.final_report.to_dict() if self.final_report else None,
        }

    def save(self, filepath: str):
        """保存到文件"""
        data = self.to_dict()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved execution history to {filepath}")

    @classmethod
    def load(cls, filepath: str) -> 'ExecutionHistory':
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        history = cls(
            graph_id=data["graph_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            initial_inputs=data.get("initial_inputs", {}),
        )

        if data.get("end_time"):
            history.end_time = datetime.fromisoformat(data["end_time"])

        for event_data in data.get("events", []):
            event = ExecutionEvent(
                event_type=EventType(event_data["event_type"]),
                timestamp=datetime.fromisoformat(event_data["timestamp"]),
                node_id=event_data.get("node_id"),
                data=event_data.get("data", {}),
            )
            history.add_event(event)

        for snapshot_data in data.get("snapshots", []):
            snapshot = ExecutionSnapshot(
                timestamp=datetime.fromisoformat(snapshot_data["timestamp"]),
                state=snapshot_data.get("state"),
                current_node=snapshot_data.get("current_node"),
                completed_nodes=snapshot_data.get("completed_nodes", []),
                failed_nodes=snapshot_data.get("failed_nodes", []),
                metadata=snapshot_data.get("metadata", {}),
            )
            history.add_snapshot(snapshot)

        # 加载 final_report
        if data.get("final_report"):
            report_data = data["final_report"]
            history.final_report = ExecutionReport(
                success=report_data.get("success", False),
                total_nodes=report_data.get("total_nodes", 0),
                completed_nodes=report_data.get("completed_nodes", 0),
                failed_nodes=report_data.get("failed_nodes", 0),
                execution_time=report_data.get("execution_time", 0.0),
                node_results=report_data.get("node_results", {}),
                errors=report_data.get("errors", []),
            )

        return history


class ExecutionRecorder:
    """
    执行记录器

    记录图执行过程中的所有事件和状态变化。
    """

    def __init__(
        self,
        graph_id: str,
        snapshot_on_node_complete: bool = False,
        snapshot_on_error: bool = True,
    ):
        """
        初始化记录器

        Args:
            graph_id: 图 ID
            snapshot_on_node_complete: 节点完成时是否创建快照
            snapshot_on_error: 错误时是否创建快照
        """
        self.graph_id = graph_id
        self.snapshot_on_node_complete = snapshot_on_node_complete
        self.snapshot_on_error = snapshot_on_error
        self.history = ExecutionHistory(graph_id=graph_id)

    def record_start(self, inputs: Dict[str, Any]):
        """记录执行开始"""
        self.history.initial_inputs = inputs
        event = ExecutionEvent(
            event_type=EventType.GRAPH_START,
            data={"inputs": inputs},
        )
        self.history.add_event(event)
        logger.info(f"Recording started for {self.graph_id}")

    def record_end(self, report: ExecutionReport):
        """记录执行结束"""
        self.history.end_time = datetime.now()
        self.history.final_report = report
        event = ExecutionEvent(
            event_type=EventType.GRAPH_END,
            data={
                "success": report.success,
                "total_nodes": report.total_nodes,
                "completed_nodes": report.completed_nodes,
                "failed_nodes": report.failed_nodes,
                "execution_time": report.execution_time,
            },
        )
        self.history.add_event(event)
        logger.info(f"Recording ended for {self.graph_id}")

    def record_node_start(self, node_id: str, inputs: Dict[str, Any]):
        """记录节点开始"""
        event = ExecutionEvent(
            event_type=EventType.NODE_START,
            node_id=node_id,
            data={"inputs": inputs},
        )
        self.history.add_event(event)

    def record_node_end(self, node_id: str, result: NodeResult):
        """记录节点结束"""
        event = ExecutionEvent(
            event_type=EventType.NODE_END,
            node_id=node_id,
            data={
                "status": result.status.value,
                "outputs": result.outputs,
                "execution_time": result.execution_time,
            },
        )
        self.history.add_event(event)

        # 如果配置了快照，创建快照
        if self.snapshot_on_node_complete:
            self._create_snapshot(node_id, "node_complete")

    def record_node_error(self, node_id: str, error: Exception):
        """记录节点错误"""
        event = ExecutionEvent(
            event_type=EventType.NODE_ERROR,
            node_id=node_id,
            data={"error": str(error), "error_type": type(error).__name__},
        )
        self.history.add_event(event)

        # 如果配置了快照，创建快照
        if self.snapshot_on_error:
            self._create_snapshot(node_id, "error")

    def record_snapshot(self, state: GraphState, current_node: Optional[str] = None):
        """记录快照"""
        snapshot = ExecutionSnapshot(
            state=state.to_dict(),
            current_node=current_node,
            completed_nodes=list(state.completed_nodes),
            failed_nodes=list(state.failed_nodes),
        )
        self.history.add_snapshot(snapshot)
        logger.debug(f"Snapshot recorded at {snapshot.timestamp}")

    def _create_snapshot(self, node_id: str, reason: str):
        """创建快照（内部方法）"""
        snapshot = ExecutionSnapshot(
            current_node=node_id,
            metadata={"reason": reason},
        )
        self.history.add_snapshot(snapshot)

    def get_history(self) -> ExecutionHistory:
        """获取执行历史"""
        return self.history

    def save(self, filepath: str):
        """保存历史到文件"""
        self.history.save(filepath)


class RecordingRuntime(ToolRuntime):
    """
    录制运行时 - 记录执行的运行时

    在执行过程中自动记录所有事件。
    """

    def __init__(
        self,
        recorder: ExecutionRecorder,
        state: Optional[GraphState] = None,
        config=None,
    ):
        """
        初始化录制运行时

        Args:
            recorder: 执行记录器
            state: 图状态
            config: 执行配置
        """
        super().__init__(state=state, config=config)
        self.recorder = recorder

    async def execute(
        self,
        graph: ToolGraph,
        initial_inputs: Optional[Dict[str, Any]] = None,
    ) -> ExecutionReport:
        """
        执行图（带录制）

        Args:
            graph: 工具图
            initial_inputs: 初始输入

        Returns:
            ExecutionReport: 执行报告
        """
        inputs = initial_inputs or {}

        # 记录开始
        self.recorder.record_start(inputs)

        try:
            # 使用父类执行逻辑，但包装事件记录
            result = await self._execute_with_recording(graph, inputs)

            # 记录结束
            self.recorder.record_end(result)

            return result

        except Exception as e:
            logger.error(f"Execution with recording failed: {e}")
            # 记录错误
            report = ExecutionReport(
                success=False,
                total_nodes=len(graph.nodes),
                completed_nodes=0,
                failed_nodes=0,
                execution_time=0,
                node_results={},
                errors=[str(e)],
            )
            self.recorder.record_end(report)
            return report

    async def _execute_with_recording(
        self,
        graph: ToolGraph,
        inputs: Dict[str, Any],
    ) -> ExecutionReport:
        """执行图并记录事件"""
        from .node import NodeStatus

        node_results = {}
        start_time = asyncio.get_event_loop().time()

        # 准备上下文
        if inputs:
            for key, value in inputs.items():
                self.state.context.set(key, value)

        # 拓扑排序执行
        sorted_nodes = graph.topological_sort()

        for node in sorted_nodes:
            # 记录节点开始
            self.recorder.record_node_start(node.id, inputs.copy())

            try:
                # 执行节点 - context is ExecutionContext, need to pass as dict
                context_dict = {
                    "_variables": self.state.context.variables.copy(),
                    "_metadata": self.state.context.metadata.copy(),
                }
                result = await node.execute(inputs, context_dict)

                # 记录节点结束
                self.recorder.record_node_end(node.id, result)

                node_results[node.id] = result

                # 更新状态
                if result.status == NodeStatus.COMPLETED:
                    self.state.set_node_output(node.id, result.outputs)
                    # 更新 inputs 给下一个节点使用
                    inputs.update(result.outputs)
                elif result.status == NodeStatus.FAILED:
                    self.state.set_node_output(node.id, {}, status="failed")
                    break

            except Exception as e:
                # 记录错误
                self.recorder.record_node_error(node.id, e)

                node_results[node.id] = NodeResult(
                    status=NodeStatus.FAILED,
                    outputs={},
                    error=str(e),
                )

                self.state.set_node_output(node.id, {}, status="failed")
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


class PlaybackRuntime(ToolRuntime):
    """
    回放运行时 - 回放执行历史

    从历史记录中重新执行或模拟执行。
    """

    def __init__(
        self,
        history: ExecutionHistory,
        replay_mode: str = "replay",  # "replay" or "simulate"
        state: Optional[GraphState] = None,
        config=None,
    ):
        """
        初始化回放运行时

        Args:
            history: 执行历史
            replay_mode: 回放模式（"replay" 重新执行, "simulate" 模拟）
            state: 图状态
            config: 执行配置
        """
        super().__init__(state=state, config=config)
        self.history = history
        self.replay_mode = replay_mode

    async def execute(
        self,
        graph: ToolGraph,
        initial_inputs: Optional[Dict[str, Any]] = None,
    ) -> ExecutionReport:
        """
        回放执行

        Args:
            graph: 工具图
            initial_inputs: 初始输入（可选，默认使用历史输入）

        Returns:
            ExecutionReport: 执行报告
        """
        if self.replay_mode == "simulate":
            return await self._simulate_execution()
        else:
            return await self._replay_execution(graph, initial_inputs)

    async def _replay_execution(
        self,
        graph: ToolGraph,
        initial_inputs: Optional[Dict[str, Any]] = None,
    ) -> ExecutionReport:
        """重新执行"""
        from .node import NodeStatus

        # 使用历史输入或提供的新输入
        inputs = initial_inputs or self.history.initial_inputs

        node_results = {}
        start_time = asyncio.get_event_loop().time()

        # 按照历史事件顺序执行
        node_events = [e for e in self.history.events if e.event_type == EventType.NODE_START]

        for event in node_events:
            node_id = event.node_id
            if node_id not in graph.nodes:
                continue

            node = graph.nodes[node_id]

            try:
                context_dict = {
                    "_variables": self.state.context.variables.copy(),
                    "_metadata": self.state.context.metadata.copy(),
                }
                result = await node.execute(inputs, context_dict)
                node_results[node_id] = result

                if result.status == NodeStatus.COMPLETED:
                    self.state.set_node_output(node_id, result.outputs)
                    inputs.update(result.outputs)

            except Exception as e:
                node_results[node_id] = NodeResult(
                    node_id=node_id,
                    status=NodeStatus.FAILED,
                    outputs={},
                    error=str(e),
                )
                break

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

    async def _simulate_execution(self) -> ExecutionReport:
        """模拟执行（不实际执行，返回历史报告）"""
        logger.info("Simulating execution from history")

        # 等待一小段时间模拟执行
        await asyncio.sleep(0.01)

        return self.history.final_report or ExecutionReport(
            success=False,
            total_nodes=0,
            completed_nodes=0,
            failed_nodes=0,
            execution_time=0,
            node_results={},
            errors=["No final report available in history"],
        )


# ============================================================================
# 工厂函数
# ============================================================================

def create_recorder(
    graph_id: str,
    snapshot_on_node_complete: bool = False,
    snapshot_on_error: bool = True,
) -> ExecutionRecorder:
    """
    创建执行记录器

    Args:
        graph_id: 图 ID
        snapshot_on_node_complete: 节点完成时是否创建快照
        snapshot_on_error: 错误时是否创建快照

    Returns:
        ExecutionRecorder 实例
    """
    return ExecutionRecorder(
        graph_id=graph_id,
        snapshot_on_node_complete=snapshot_on_node_complete,
        snapshot_on_error=snapshot_on_error,
    )


async def record_execution(
    graph: ToolGraph,
    inputs: Optional[Dict[str, Any]] = None,
    save_path: Optional[str] = None,
    **recorder_kwargs,
) -> ExecutionReport:
    """
    快捷函数：记录图执行

    Args:
        graph: 工具图
        inputs: 初始输入
        save_path: 保存路径（可选）
        **recorder_kwargs: 记录器参数

    Returns:
        ExecutionReport: 执行报告

    Example:
        >>> report = await record_execution(
        ...     graph,
        ...     inputs={"query": "test"},
        ...     save_path="history.json",
        ...     snapshot_on_node_complete=True,
        ... )
    """
    recorder = create_recorder(graph.name, **recorder_kwargs)
    runtime = RecordingRuntime(recorder=recorder)

    report = await runtime.execute(graph, inputs)

    if save_path:
        recorder.save(save_path)

    return report


async def replay_execution(
    graph: ToolGraph,
    history_path: str,
    replay_mode: str = "replay",
    initial_inputs: Optional[Dict[str, Any]] = None,
) -> ExecutionReport:
    """
    快捷函数：回放执行

    Args:
        graph: 工具图
        history_path: 历史文件路径
        replay_mode: 回放模式（"replay" 或 "simulate"）
        initial_inputs: 初始输入（仅 replay 模式）

    Returns:
        ExecutionReport: 执行报告

    Example:
        >>> report = await replay_execution(
        ...     graph,
        ...     "history.json",
        ...     replay_mode="simulate",
        ... )
    """
    history = ExecutionHistory.load(history_path)

    if replay_mode == "simulate":
        runtime = PlaybackRuntime(history=history, replay_mode="simulate")
        return await runtime.execute(graph)
    else:
        runtime = PlaybackRuntime(history=history, replay_mode="replay")
        return await runtime.execute(graph, initial_inputs)
