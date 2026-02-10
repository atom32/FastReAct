"""
FastReAct Nano v2.0 - 轻量级高级 ReAct 智能体核心

核心特性:
- 双层循环: Moltbot 风格的内层/外层循环
- 转向消息: 实时干预能力
- 后续消息: 异步任务延续
- 极简工具: Pi 哲学（4个核心工具）
- Gateway 架构: WebSocket 实时通信
- Token 监控: 智能上下文管理
"""

__version__ = "2.0.0-alpha"
__author__ = "FastReAct Team"

# Core exports
from fastreact.core.bus import MessageBus, InboundMessage, OutboundMessage
from fastreact.core.messages import Message, MessageQueue
from fastreact.core.callbacks import CallbackManager
from fastreact.core.react import ReActCore, Phase, StepEvent
from fastreact.core.context import ContextManager
from fastreact.core.tools import Tool, ToolRegistry
from fastreact.core.config import Config, LLMConfig, ToolConfig, ReactConfig
from fastreact.core.streaming import (
    StreamChunk,
    StreamCallback,
    PrintStreamCallback,
    CollectStreamCallback,
    stream_with_callback,
)

# Gateway exports
from fastreact.gateway.server import GatewayServer, run_gateway
from fastreact.gateway.session import Session, SessionManager

# Channel exports
from fastreact.channels.base import Channel, ChannelMeta, CLIChannel
from fastreact.channels.registry import ChannelRegistry, get_channel_registry, list_channels

# Provider exports
from fastreact.providers.litellm import LiteLLMProvider

# Tool exports
from fastreact.tools import (
    ReadFileTool,
    WriteFileTool,
    ExecTool,
    EditFileTool,
)

__all__ = [
    # Version
    "__version__",
    # Core v1
    "MessageBus",
    "InboundMessage",
    "OutboundMessage",
    "ContextManager",
    "Tool",
    "ToolRegistry",
    # Core v2.0
    "Message",
    "MessageQueue",
    "CallbackManager",
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
    "stream_with_callback",
    # Gateway
    "GatewayServer",
    "run_gateway",
    "Session",
    "SessionManager",
    # Channels
    "Channel",
    "ChannelMeta",
    "CLIChannel",
    "ChannelRegistry",
    "get_channel_registry",
    "list_channels",
    # Providers
    "LiteLLMProvider",
    # Tools
    "ReadFileTool",
    "WriteFileTool",
    "ExecTool",
    "EditFileTool",
]
