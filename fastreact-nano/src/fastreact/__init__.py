"""
FastReAct Nano v2.0 - Event-Driven AI Agent SDK

极简ReAct Agent核心:
- 事件驱动架构: AgentEvent统一协议
- Cortex组件: Token Guard, Ghost Map, Safety
- 极简工具: 4个核心工具 (Pi哲学)
- Skills系统: Markdown渐进式披露
"""

__version__ = "2.0.0-alpha"
__author__ = "FastReAct Team"

# Core v2.0 - Event-Driven Architecture
from fastreact.core.messages import Message, MessageQueue
from fastreact.core.react import ReActCore
from fastreact.core.tools import Tool, ToolRegistry
from fastreact.core.config import Config, LLMConfig, ToolConfig, ReactConfig
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
from fastreact.core.events import (
    EventType,
    AgentEvent,
    EventStream,
)

# Provider
from fastreact.providers.litellm import LiteLLMProvider

# Tools
from fastreact.tools import (
    ReadFileTool,
    WriteFileTool,
    ExecTool,
    EditFileTool,
)

# Skills
from fastreact.skills import (
    Skill,
    SkillMetadata,
    SkillLoader,
    SkillRegistry,
    SkillParser,
    ParsedSkill,
)

# Agent
from fastreact.agent import Agent, ask, ask_sync

__all__ = [
    # Version
    "__version__",
    # Core Messages
    "Message",
    "MessageQueue",
    # Core Engine
    "ReActCore",
    # Tools
    "Tool",
    "ToolRegistry",
    # Config
    "Config",
    "LLMConfig",
    "ToolConfig",
    "ReactConfig",
    # Context (Cortex)
    "ContextMonitor",
    "ContextStats",
    "FilesystemMemory",
    "FilesystemNode",
    # Safety (Cortex)
    "SafetyLevel",
    "SafetyDecision",
    "SafetyPolicy",
    "ConfirmationCallback",
    "CLIConfirmationCallback",
    "AlwaysAllowCallback",
    "AlwaysDenyCallback",
    # Events (Unified Protocol)
    "EventType",
    "AgentEvent",
    "EventStream",
    # Provider
    "LiteLLMProvider",
    # Tools
    "ReadFileTool",
    "WriteFileTool",
    "ExecTool",
    "EditFileTool",
    # Skills
    "Skill",
    "SkillMetadata",
    "SkillLoader",
    "SkillRegistry",
    "SkillParser",
    "ParsedSkill",
    # Agent
    "Agent",
    "ask",
    "ask_sync",
]
