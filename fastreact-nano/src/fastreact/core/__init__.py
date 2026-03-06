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
from fastreact.core.multitenant import (
    MultiTenantManager,
    UserContext,
    get_global_agent,
    generate_temp_user_key,
    validate_user_key,
    reset_global_agent,
)
from fastreact.core.config_manager import ConfigManager

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
    # Credentials
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
    # Events
    "EventType",
    "AgentEvent",
    "EventStream",
    # Session
    "AgentSession",
    # Memory
    "MemoryManager",
    # Multi-tenant
    "MultiTenantManager",
    "UserContext",
    "get_global_agent",
    "generate_temp_user_key",
    "validate_user_key",
    "reset_global_agent",
    # Config Manager (Phase 2)
    "ConfigManager",
]
