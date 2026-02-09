"""
Channel modules for FastReAct Nano
"""

from fastreact.channels.base import (
    Channel,
    ChannelStatus,
    ChannelMeta,
    MessageHandler,
    CLIChannel,
)
from fastreact.channels.registry import (
    ChannelRegistry,
    get_channel_registry,
    register_channel,
    list_channels,
)

__all__ = [
    # Base
    "Channel",
    "ChannelStatus",
    "ChannelMeta",
    "MessageHandler",
    # Implementations
    "CLIChannel",
    # Registry
    "ChannelRegistry",
    "get_channel_registry",
    "register_channel",
    "list_channels",
]
