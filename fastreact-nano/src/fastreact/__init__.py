"""
FastReAct Nano v2.3 - The Visual Update

Modern AI Agent SDK with Vue 3 Frontend
- Vue 3 SPA: Chat interface and Admin panel
- MCP Marketplace: 12 tools across 8 categories
- Real-time Dashboard: System metrics and monitoring
- Configuration Editor: Visual LLM, MCP, and Agent settings
- Session Manager: Complete session lifecycle management
- Dark Mode: Full theme support
- WebSocket streaming: Real-time AgentEvent protocol
"""

__version__ = "2.3.0"
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
