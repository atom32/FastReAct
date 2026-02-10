"""
Core modules for FastReAct Nano v2.0
"""

from fastreact.core.messages import Message, MessageQueue
from fastreact.core.callbacks import CallbackManager
from fastreact.core.react import ReActCore, Phase, StepEvent
from fastreact.core.config import Config, LLMConfig, ToolConfig, ReactConfig
from fastreact.core.streaming import (
    StreamChunk,
    StreamCallback,
    PrintStreamCallback,
    CollectStreamCallback,
    stream_to_iterator,
    stream_with_callback,
)

__all__ = [
    # Messages
    "Message",
    "MessageQueue",
    # Callbacks
    "CallbackManager",
    # Core
    "ReActCore",
    "Phase",
    "StepEvent",
    # Config
    "Config",
    "LLMConfig",
    "ToolConfig",
    "ReactConfig",
    # Streaming
    "StreamChunk",
    "StreamCallback",
    "PrintStreamCallback",
    "CollectStreamCallback",
    "stream_to_iterator",
    "stream_with_callback",
]
