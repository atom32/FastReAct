"""
FastReAct Nano - 轻量级多渠道 ReAct 智能体框架

核心特性:
- Gateway 架构: WebSocket 实时通信
- 多渠道支持: Telegram, WeChat, CLI, HTTP
- Token 监控: 智能上下文管理
- 插件系统: 技能/工具热加载
- 文件存储: 简单可靠的 JSONL
"""

__version__ = "2.0.0-alpha"
__author__ = "FastReAct Team"

# Core exports
from fastreact.core.bus import MessageBus, InboundMessage, OutboundMessage
from fastreact.core.react import ReActCore
from fastreact.core.context import ContextManager
from fastreact.core.tools import Tool, ToolRegistry

# Gateway exports
from fastreact.gateway.server import GatewayServer, run_gateway
from fastreact.gateway.session import Session, SessionManager

# Channel exports
from fastreact.channels.base import Channel, ChannelMeta, CLIChannel
from fastreact.channels.registry import ChannelRegistry, get_channel_registry, list_channels

# Provider exports
from fastreact.providers.litellm import LiteLLMProvider

__all__ = [
    # Version
    "__version__",
    # Core
    "MessageBus",
    "InboundMessage",
    "OutboundMessage",
    "ReActCore",
    "ContextManager",
    "Tool",
    "ToolRegistry",
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
]
