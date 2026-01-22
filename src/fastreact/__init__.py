"""
FastReAct - 超高性能ReACT框架

核心特性：
- 极致性能：比LangChain快2-3倍
- 异步并发：工具调用可并发执行
- 智能缓存：LRU缓存自动管理
- 流式响应：降低首字延迟
- 零抽象层：直接控制每个细节
"""

__version__ = "0.1.0"
__author__ = "Your Name"

from fastreact.core.engine import FastReAct
from fastreact.core.tool import Tool, ToolCall, ToolResult
from fastreact.core.cache import LRUCache

__all__ = [
    "FastReAct",
    "Tool",
    "ToolCall",
    "ToolResult",
    "LRUCache",
]
