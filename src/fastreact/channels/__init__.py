"""
Channel 抽象层

支持多种消息平台的集成：
- Telegram
- Slack
- Discord
- 以及更多...

Usage:
    from fastreact.channels import ChannelManager
    from fastreact.channels.telegram import TelegramChannel

    manager = ChannelManager()

    # 注册通道
    manager.register_channel(TelegramChannel(bot_token="..."))

    # 启动所有通道
    await manager.start_all()
"""

from .base import Channel
from .manager import ChannelManager

__all__ = ["Channel", "ChannelManager"]
