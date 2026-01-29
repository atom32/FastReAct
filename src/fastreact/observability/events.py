"""
事件流系统 - 分层事件定义

提供细粒度的、实时的 Agent 执行反馈。

三种事件类型：
1. LifecycleEvent - 生命周期事件（start, end, error）
2. AssistantEvent - 助手输出事件（文本增量）
3. ToolEvent - 工具执行事件（start, result, error）
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Literal, Optional, Union
from time import time
import asyncio
import inspect


@dataclass
class LifecycleEvent:
    """
    生命周期事件

    标记 Agent 执行的关键阶段。
    """
    type: Literal["lifecycle"] = "lifecycle"
    phase: Literal["start", "end", "error"] = "start"
    run_id: str = ""
    timestamp: float = field(default_factory=time)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if not self.run_id:
            import uuid
            self.run_id = f"run_{uuid.uuid4().hex[:12]}"


@dataclass
class AssistantEvent:
    """
    助手输出事件

    Agent 的文本输出，支持流式增量更新。
    """
    type: Literal["assistant"] = "assistant"
    run_id: str = ""
    delta: str = ""  # 文本增量
    timestamp: float = field(default_factory=time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.run_id:
            import uuid
            self.run_id = f"run_{uuid.uuid4().hex[:12]}"


@dataclass
class ToolEvent:
    """
    工具执行事件

    跟踪工具调用的完整生命周期。
    """
    type: Literal["tool"] = "tool"
    phase: Literal["start", "result", "error"] = "start"
    run_id: str = ""
    tool_name: str = ""
    tool_call_id: str = ""
    args: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    timestamp: float = field(default_factory=time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.run_id:
            import uuid
            self.run_id = f"run_{uuid.uuid4().hex[:12]}"
        if not self.tool_call_id:
            import uuid
            self.tool_call_id = f"tool_{uuid.uuid4().hex[:8]}"


# 事件类型联合
AgentEvent = Union[LifecycleEvent, AssistantEvent, ToolEvent]


# 事件回调函数类型
EventCallback = Callable[[AgentEvent], Any]
AsyncEventCallback = Callable[[AgentEvent], Any]  # 可以是协程函数


class EventManager:
    """
    事件管理器

    管理事件回调的执行，支持同步和异步回调。
    """

    def __init__(self):
        self.callbacks: list[AsyncEventCallback] = []

    def on_event(self, callback: AsyncEventCallback):
        """
        注册事件回调

        Args:
            callback: 事件回调函数（异步）
        """
        self.callbacks.append(callback)

    async def emit(self, event: AgentEvent):
        """
        发送事件给所有回调

        Args:
            event: 事件对象
        """
        for callback in self.callbacks:
            try:
                # 检查是否是协程函数
                if inspect.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    # 同步回调，在线程池中执行
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, callback, event)
            except Exception as e:
                # 回调错误不应中断主流程
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Event callback error: {e}", exc_info=True)

    def clear(self):
        """清除所有回调"""
        self.callbacks.clear()
