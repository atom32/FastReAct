"""
FastReAct Nano v2.4.2 - Dual Transport MCP

Modern AI Agent SDK with Next.js 14 Frontend
- Next.js App: Daemon service console
- Ironclad Backend: Infinite loop protection, JSON repair, auto-reconnect
- MCP Zombie Resurrection: Automatic server crash recovery
- Multi-turn Memory: Conversation history with auto-pruning (50 turns)
- Professional UI: Unified themes, glassmorphism, gradient accents
- HTTP/SSE Streaming: AgentEvent protocol
- DUAL TRANSPORT MCP: stdio + HTTP for local and remote servers
- Secure Credentials: Separate credentials.json with env var support
"""

__version__ = "2.4.2"
__author__ = "FastReAct Team"

# Core v2.0 - Event-Driven Architecture
from fastreact.core.messages import Message, MessageQueue
from fastreact.core.react import ReActCore
from fastreact.core.tools import Tool, ToolRegistry
from fastreact.core.config import Config, LLMConfig, ToolConfig, ReactConfig, MCPConfig, PolicyConfig
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
    "PolicyConfig",
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
