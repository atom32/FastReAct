"""
FastReAct Nano v2.4.1 - Ironclad + Professional

Modern AI Agent SDK with Next.js 14 Frontend
- Next.js 14 App: Chat interface, Admin panel, MCP Marketplace
- Ironclad Backend: Infinite loop protection, JSON repair, auto-reconnect
- MCP Zombie Resurrection: Automatic server crash recovery
- Multi-turn Memory: Conversation history with auto-pruning (50 turns)
- Professional UI: Unified themes, glassmorphism, gradient accents
- WebSocket Streaming: Real-time AgentEvent protocol
- 6 Themes: Cyber Dark, Midnight, Solar Light, Forest, Sunset, Matrix
"""

__version__ = "2.4.1"
__author__ = "FastReAct Team"

# Core v2.0 - Event-Driven Architecture
from fastreact.core.messages import Message, MessageQueue
from fastreact.core.react import ReActCore
from fastreact.core.tools import Tool, ToolRegistry
from fastreact.core.config import Config, LLMConfig, ToolConfig, ReactConfig, MCPConfig, FeishuConfig
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

# Multi-tenant
from fastreact.core.multitenant import MultiTenantManager, UserContext, SecurityError

# MCP
from fastreact.mcp.manager import MCPToolManager, MCPToolWrapper

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
    "MCPConfig",
    "FeishuConfig",
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
    # Multi-tenant
    "MultiTenantManager",
    "UserContext",
    # MCP
    "MCPToolManager",
    "MCPToolWrapper",
]
