"""
FastReAct - 轻量级ReACT框架

核心特性：
- 代码简洁：核心代码不到600行
- 异步支持：工具调用可并发执行
- 内置缓存：LRU缓存减少重复计算
- 流式响应：支持流式输出
- 易于理解：适合学习ReACT原理
"""

__version__ = "0.1.0"
__author__ = "Your Name"

from fastreact.core.engine import FastReAct
from fastreact.core.tool import Tool, ToolCall, ToolResult
from fastreact.core.cache import LRUCache
from fastreact.core.callbacks import (
    StreamingCallbacks,
    ConsoleCallbacks,
    CallbackRecorder,
    Phase,
    StepEvent
)

__all__ = [
    "FastReAct",
    "Tool",
    "ToolCall",
    "ToolResult",
    "LRUCache",
    # Streaming callbacks
    "StreamingCallbacks",
    "ConsoleCallbacks",
    "CallbackRecorder",
    "Phase",
    "StepEvent",
]
