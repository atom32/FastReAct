"""
实时控制回调系统

提供细粒度的事件回调，支持实时监控和控制 Agent 执行过程。
"""

import asyncio
from typing import Any, Callable, Dict, Optional
from enum import Enum
from dataclasses import dataclass, field
import json
import time


class Phase(Enum):
    """执行阶段"""
    START = "start"
    THINK = "think"
    ACTION = "action"
    OBSERVATION = "observation"
    ANSWER = "answer"
    ERROR = "error"
    END = "end"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"


@dataclass
class StepEvent:
    """步骤事件"""
    phase: Phase
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "phase": self.phase.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class StreamingCallbacks:
    """流式回调管理器

    管理所有生命周期回调，支持同步和异步函数。
    """

    def __init__(
        self,
        on_thought: Optional[Callable[[str], Any]] = None,
        on_action: Optional[Callable[[Dict], Any]] = None,
        on_observation: Optional[Callable[[str], Any]] = None,
        on_answer_delta: Optional[Callable[[str], Any]] = None,
        on_tool_start: Optional[Callable[[str, Dict], Any]] = None,
        on_tool_end: Optional[Callable[[str, str, float], Any]] = None,
        on_error: Optional[Callable[[str], Any]] = None,
        on_start: Optional[Callable[[], Any]] = None,
        on_end: Optional[Callable[[Dict], Any]] = None
    ):
        """
        初始化回调管理器

        Args:
            on_thought: 思考阶段回调
            on_action: 行动阶段回调
            on_observation: 观察阶段回调
            on_answer_delta: 回复增量回调
            on_tool_start: 工具开始回调
            on_tool_end: 工具结束回调
            on_error: 错误回调
            on_start: 开始回调
            on_end: 结束回调
        """
        self.on_thought = self._wrap_async(on_thought)
        self.on_action = self._wrap_async(on_action)
        self.on_observation = self._wrap_async(on_observation)
        self.on_answer_delta = self._wrap_async(on_answer_delta)
        self.on_tool_start = self._wrap_async(on_tool_start)
        self.on_tool_end = self._wrap_async(on_tool_end)
        self.on_error = self._wrap_async(on_error)
        self.on_start = self._wrap_async(on_start)
        self.on_end = self._wrap_async(on_end)

    def _wrap_async(self, func: Optional[Callable]) -> Optional[Callable]:
        """包装函数使其支持异步"""
        if func is None:
            return None

        if asyncio.iscoroutinefunction(func):
            return func

        # 同步函数包装为异步
        async def async_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return async_wrapper

    async def emit(self, event: StepEvent):
        """
        发送事件到对应的回调

        Args:
            event: 步骤事件
        """
        try:
            # 开始事件
            if event.phase == Phase.THINK and self.on_thought:
                await self.on_thought(event.content)

            elif event.phase == Phase.ACTION and self.on_action:
                # 尝试解析为 JSON
                try:
                    action_data = json.loads(event.content) if isinstance(event.content, str) else event.content
                except:
                    action_data = {"raw": event.content}

                await self.on_action(action_data)

            elif event.phase == Phase.OBSERVATION and self.on_observation:
                await self.on_observation(event.content)

            elif event.phase == Phase.ANSWER and self.on_answer_delta:
                await self.on_answer_delta(event.content)

            elif event.phase == Phase.ERROR and self.on_error:
                await self.on_error(event.content)

            # 工具特定事件
            elif event.phase == Phase.TOOL_START and self.on_tool_start:
                tool_name = event.metadata.get("tool_name")
                params = event.metadata.get("parameters", {})
                await self.on_tool_start(tool_name, params)

            elif event.phase == Phase.TOOL_END and self.on_tool_end:
                tool_name = event.metadata.get("tool_name")
                result = event.content
                duration = event.metadata.get("duration", 0)
                await self.on_tool_end(tool_name, result, duration)

        except Exception as e:
            # 回调执行错误不应中断 Agent
            print(f"[Warning] Callback error: {e}")

    async def emit_start(self, query: str, metadata: Dict = None):
        """发送开始事件"""
        if self.on_start:
            await self.on_start()

    async def emit_end(self, result: Dict):
        """发送结束事件"""
        if self.on_end:
            await self.on_end(result)


class ConsoleCallbacks(StreamingCallbacks):
    """控制台输出回调（默认）

    提供美观的控制台输出，用于演示和调试。
    """

    def __init__(
        self,
        show_thoughts: bool = True,
        show_actions: bool = True,
        show_observations: bool = True,
        show_timing: bool = True,
        color_output: bool = True
    ):
        """
        初始化控制台回调

        Args:
            show_thoughts: 是否显示思考过程
            show_actions: 是否显示工具调用
            show_observations: 是否显示观察结果
            show_timing: 是否显示时间统计
            color_output: 是否使用颜色
        """
        self.show_thoughts = show_thoughts
        self.show_actions = show_actions
        self.show_observations = show_observations
        self.show_timing = show_timing
        self.color_output = color_output

        self.iteration = 0
        self.tool_start_time = None
        self.start_time = None

        super().__init__(
            on_thought=self._on_thought,
            on_action=self._on_action,
            on_observation=self._on_observation,
            on_answer_delta=self._on_answer_delta,
            on_tool_start=self._on_tool_start,
            on_tool_end=self._on_tool_end,
            on_start=self._on_start,
            on_end=self._on_end
        )

    def _colorize(self, text: str, color: str) -> str:
        """添加 ANSI 颜色"""
        if not self.color_output:
            return text

        colors = {
            "thought": "\033[93m",      # 黄色
            "action": "\033[94m",       # 蓝色
            "observation": "\033[92m", # 绿色
            "error": "\033[91m",       # 红色
            "reset": "\033[0m",
            "bold": "\033[1m",
        }
        return f"{colors.get(color, '')}{text}{colors['reset']}"

    async def _on_start(self):
        """开始回调"""
        self.start_time = time.time()
        print("=" * 60)
        print("🤖 FastReAct Agent 启动")
        print("=" * 60)
        print()

    async def _on_end(self, result: Dict):
        """结束回调"""
        if self.show_timing and self.start_time:
            total_time = time.time() - self.start_time
            stats = result.get("stats", {})
            iterations = stats.get("iterations", 0)

            print()
            print("=" * 60)
            print(f"[OK] 完成 - 耗时: {total_time:.2f}s, 迭代: {iterations} 次")
            print("=" * 60)

    async def _on_thought(self, thought: str):
        """思考回调"""
        if self.show_thoughts:
            print(self._colorize(f"🤔 思考 {self.iteration + 1}: {thought}", "thought"))

    async def _on_action(self, action: Dict):
        """行动回调"""
        if self.show_actions:
            tool_name = action.get("tool_name", "unknown")
            params = action.get("parameters", {})
            print(self._colorize(f"🔧 工具: {tool_name}", "action"))

            # 简化参数显示
            if params:
                params_str = ", ".join(f"{k}={v}" for k, v in params.items())
                print(f"   参数: {params_str}")
            else:
                print("   参数: (无)")

    async def _on_observation(self, observation: str):
        """观察回调"""
        if self.show_observations:
            # 截断过长的输出
            max_len = 200
            if len(observation) > max_len:
                observation = observation[:max_len] + "..."

            print(self._colorize(f"[CHART] 结果: {observation}", "observation"))

    async def _on_answer_delta(self, delta: str):
        """回复增量回调"""
        # 直接输出，不加前缀
        print(delta, end="", flush=True)

    async def _on_tool_start(self, tool_name: str, params: Dict):
        """工具开始回调"""
        self.tool_start_time = time.time()

    async def _on_tool_end(self, tool_name: str, result: str, duration: float):
        """工具结束回调"""
        if self.show_timing and self.tool_start_time:
            print(f"   ⏱️ 耗时: {duration:.2f}s")

        self.iteration += 1


class CallbackRecorder(StreamingCallbacks):
    """回调记录器

    记录所有事件到日志，用于调试和分析。
    """

    def __init__(self):
        self.events = []
        self.start_time = None
        self.end_time = None

        # 注册回调到父类
        super().__init__(
            on_start=self._on_start,
            on_end=self._on_end,
            on_error=self._on_error
        )

    async def _record_event(self, event: StepEvent):
        """记录事件"""
        self.events.append(event)

    async def emit(self, event: StepEvent):
        """记录事件"""
        await self._record_event(event)

        # 转发给原始 emit（如果有的话）
        await super().emit(event)

    async def _on_start(self):
        """开始记录"""
        self.start_time = time.time()
        await self._record_event(StepEvent(
            phase=Phase.START,
            content="Agent started",
            metadata={"timestamp": self.start_time}
        ))

    async def _on_end(self, result: Dict):
        """结束记录"""
        self.end_time = time.time()
        await self._record_event(StepEvent(
            phase=Phase.END,
            content="Agent ended",
            metadata={
                "timestamp": self.end_time,
                "duration": self.end_time - self.start_time,
                "result": result
            }
        ))

    async def _on_error(self, error: str):
        """错误记录"""
        await self._record_event(StepEvent(
            phase=Phase.ERROR,
            content=error,
            metadata={"timestamp": time.time()}
        ))

    def get_events(self) -> list:
        """获取所有事件"""
        return self.events

    def get_timeline(self) -> str:
        """获取时间线"""
        lines = []
        for event in self.events:
            timestamp = event.timestamp
            phase = event.phase.value.upper()
            content = event.content[:100]
            lines.append(f"{timestamp:.2f} [{phase}] {content}")
        return "\n".join(lines)

    def get_summary(self) -> Dict:
        """获取统计摘要"""
        summary = {
            "total_events": len(self.events),
            "duration": self.end_time - self.start_time if self.end_time else 0,
            "phases": {}
        }

        for event in self.events:
            phase = event.phase.value
            summary["phases"][phase] = summary["phases"].get(phase, 0) + 1

        return summary
