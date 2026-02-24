"""
Core modules for FastReAct Nano v2.0
"""

from fastreact.core.messages import Message, MessageQueue
from fastreact.core.react import ReActCore
from fastreact.core.config import Config, LLMConfig, ToolConfig, ReactConfig
from fastreact.core.credentials import Credentials, get_credentials
from fastreact.core.context import ContextMonitor, ContextStats, FilesystemMemory, FilesystemNode
from fastreact.core.safety import (
    SafetyLevel,
    SafetyDecision,
    SafetyPolicy,
    ConfirmationCallback,
    CLIConfirmationCallback,
    AlwaysAllowCallback,
    AlwaysDenyCallback,
)
from fastreact.core.tools import Tool, ToolRegistry
from fastreact.core.events import (
    EventType,
    AgentEvent,
    EventStream,
)
from fastreact.core.session import AgentSession
from fastreact.core.memory import MemoryManager

__all__ = [
    # Messages
    "Message",
    "MessageQueue",
    # Core
    "ReActCore",
    # Config
    "Config",
    "LLMConfig",
    "ToolConfig",
    "ReactConfig",
    # Credentials (NEW)
    "Credentials",
    "get_credentials",
    # Context
    "ContextMonitor",
    "ContextStats",
    "FilesystemMemory",
    "FilesystemNode",
    # Safety
    "SafetyLevel",
    "SafetyDecision",
    "SafetyPolicy",
    "ConfirmationCallback",
    "CLIConfirmationCallback",
    "AlwaysAllowCallback",
    "AlwaysDenyCallback",
    # Tools
    "Tool",
    "ToolRegistry",
    # Events (Unified Protocol)
    "EventType",
    "AgentEvent",
    "EventStream",
    # Session (NEW)
    "AgentSession",
    # Memory (NEW)
    "MemoryManager",
]
