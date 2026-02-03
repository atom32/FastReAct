"""
FastReAct - 企业级 Agent 基础设施框架

核心特性：
- 企业级上下文管理：Token-aware + 智能压缩 + 混合检索
- 完整的 Coding Agent 工具链：Shell + Repo Map + Edit + Pruning
- 异步并发：工具调用可并发执行（最多 3 个）
- 内置缓存：LRU 缓存减少重复计算
- 流式响应：支持流式输出
- 跨平台：Windows (APSW) + Linux (sqlite-vec)
- MCP 协议：完整的 Model Context Protocol 支持

战略定位："Bring Your Own Model & Data" - 让企业用 1/10 成本获得 80% Claude Code 体验
"""

__version__ = "1.0.0"
__author__ = "FastReAct Team"

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
from fastreact.core.streaming import (
    StreamChunk,
    StreamChunkType,
    StreamingContext,
    create_streaming_context,
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
    # Streaming V2
    "StreamChunk",
    "StreamChunkType",
    "StreamingContext",
    "create_streaming_context",
]
