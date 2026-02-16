"""
Channel 抽象层

支持多种消息平台的集成：
- Telegram
- Slack
- WeChat (微信公众号、企业微信)
- Discord
- 以及更多...

Usage:
    from fastreact.channels import ChannelManager
    from fastreact.channels.telegram import TelegramChannel
    from fastreact.channels.wechat import WeChatChannel

    manager = ChannelManager()

    # 注册通道
    manager.register_channel(TelegramChannel(bot_token="..."))
    manager.register_channel(WeChatChannel(app_id="...", app_secret="...", token="..."))

    # 启动所有通道
    await manager.start_all()
"""

from .base import Channel
from .manager import ChannelManager

__all__ = ["Channel", "ChannelManager"]
