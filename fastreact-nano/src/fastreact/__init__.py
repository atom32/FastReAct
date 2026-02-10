"""
FastReAct Nano v2.0 - 真正独立的AI Agent

基于Nanobot哲学的极简ReAct Agent:
- 双层循环: Moltbot风格的内层/外层循环
- 转向消息: 实时干预能力
- 后续消息: 异步任务延续
- 极简工具: Pi哲学(4个核心工具)
- Skills系统: Markdown渐进式披露
"""

__version__ = "2.0.0-alpha"
__author__ = "FastReAct Team"

# Core v2.0
from fastreact.core.messages import Message, MessageQueue
from fastreact.core.callbacks import CallbackManager
from fastreact.core.react import ReActCore, Phase, StepEvent
from fastreact.core.tools import Tool, ToolRegistry
from fastreact.core.config import Config, LLMConfig, ToolConfig, ReactConfig
from fastreact.core.streaming import (
    StreamChunk,
    StreamCallback,
    PrintStreamCallback,
    CollectStreamCallback,
    stream_with_callback,
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
    # Core
    "Message",
    "MessageQueue",
    "CallbackManager",
    "ReActCore",
    "Phase",
    "StepEvent",
    "Tool",
    "ToolRegistry",
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
    "stream_with_callback",
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
