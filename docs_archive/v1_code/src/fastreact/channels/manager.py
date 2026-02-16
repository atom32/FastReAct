"""
Channel Manager

管理多个消息通道，统一接口和消息路由。
"""

from typing import Dict, List, Optional
import logging
import asyncio

from .base import Channel

logger = logging.getLogger(__name__)


class ChannelManager:
    """通道管理器

    统一管理多个消息通道，处理消息路由和分发。

    Usage:
        from fastreact.channels import ChannelManager
        from fastreact.channels.telegram import TelegramChannel
        from fastreact.channels.slack import SlackChannel

        manager = ChannelManager(gateway_url="ws://localhost:8000")

        # 注册通道
        telegram = TelegramChannel(bot_token="...")
        slack = SlackChannel(bot_token="...", app_token="...")

        manager.register_channel(telegram)
        manager.register_channel(slack)

        # 设置消息处理器（转发到 Gateway）
        async def handle_message(channel, user_id, message, metadata):
            await gateway.forward_to_agent(channel, user_id, message)

        manager.set_message_handler(handle_message)

        # 启动所有通道
        await manager.start_all()

        # 发送消息到特定通道
        await manager.send_to_channel("telegram", "user123", "Hello!")

        # 停止所有通道
        await manager.stop_all()
    """

    def __init__(self, gateway_url: str = "ws://localhost:8000"):
        """初始化通道管理器

        Args:
            gateway_url: Gateway WebSocket URL
        """
        self.gateway_url = gateway_url
        self.channels: Dict[str, Channel] = {}
        self.message_handler = None

    def register_channel(self, channel: Channel):
        """注册通道

        Args:
            channel: 通道实例

        Raises:
            ValueError: 通道名称已存在
        """
        if channel.name in self.channels:
            raise ValueError(f"Channel '{channel.name}' already registered")

        # 设置消息处理器
        if self.message_handler:
            channel.set_message_handler(self.message_handler)

        self.channels[channel.name] = channel
        logger.info(f"Registered channel: {channel.name}")

    def unregister_channel(self, name: str) -> bool:
        """注销通道

        Args:
            name: 通道名称

        Returns:
            是否成功注销
        """
        if name in self.channels:
            del self.channels[name]
            logger.info(f"Unregistered channel: {name}")
            return True
        return False

    def get_channel(self, name: str) -> Optional[Channel]:
        """获取通道

        Args:
            name: 通道名称

        Returns:
            通道实例，不存在返回 None
        """
        return self.channels.get(name)

    def list_channels(self) -> List[Dict]:
        """列出所有通道

        Returns:
            通道信息列表
        """
        return [
            {
                "name": name,
                "running": channel.running,
                "type": channel.__class__.__name__
            }
            for name, channel in self.channels.items()
        ]

    async def start_channel(self, name: str):
        """启动单个通道

        Args:
            name: 通道名称

        Raises:
            ValueError: 通道不存在
        """
        if name not in self.channels:
            raise ValueError(f"Channel '{name}' not found")

        channel = self.channels[name]
        if not channel.running:
            try:
                await channel.start()
                logger.info(f"Started channel: {name}")
            except Exception as e:
                logger.error(f"Failed to start channel {name}: {e}")
                raise

    async def stop_channel(self, name: str):
        """停止单个通道

        Args:
            name: 通道名称

        Raises:
            ValueError: 通道不存在
        """
        if name not in self.channels:
            raise ValueError(f"Channel '{name}' not found")

        channel = self.channels[name]
        if channel.running:
            try:
                await channel.stop()
                logger.info(f"Stopped channel: {name}")
            except Exception as e:
                logger.error(f"Failed to stop channel {name}: {e}")
                raise

    async def start_all(self):
        """启动所有通道

        按顺序启动每个通道，出错不影响其他通道。
        """
        logger.info(f"Starting {len(self.channels)} channels...")

        tasks = []
        for name, channel in self.channels.items():
            tasks.append(self._safe_start(name, channel))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        running_count = sum(1 for c in self.channels.values() if c.running)
        logger.info(f"Started {running_count}/{len(self.channels)} channels")

    async def stop_all(self):
        """停止所有通道

        按顺序停止每个通道，出错不影响其他通道。
        """
        logger.info(f"Stopping {len(self.channels)} channels...")

        tasks = []
        for name, channel in self.channels.items():
            tasks.append(self._safe_stop(name, channel))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        running_count = sum(1 for c in self.channels.values() if c.running)
        logger.info(f"Stopped {len(self.channels) - running_count}/{len(self.channels)} channels")

    async def _safe_start(self, name: str, channel: Channel):
        """安全启动通道（捕获异常）"""
        try:
            if not channel.running:
                await channel.start()
        except Exception as e:
            logger.error(f"Error starting channel {name}: {e}")

    async def _safe_stop(self, name: str, channel: Channel):
        """安全停止通道（捕获异常）"""
        try:
            if channel.running:
                await channel.stop()
        except Exception as e:
            logger.error(f"Error stopping channel {name}: {e}")

    async def send_to_channel(
        self,
        channel_name: str,
        user_id: str,
        message: str,
        **kwargs
    ):
        """发送消息到指定通道

        Args:
            channel_name: 通道名称
            user_id: 平台特定的用户ID
            message: 消息内容
            **kwargs: 通道特定参数

        Raises:
            ValueError: 通道不存在或未运行
        """
        channel = self.get_channel(channel_name)
        if not channel:
            raise ValueError(f"Channel '{channel_name}' not found")

        if not channel.running:
            raise ValueError(f"Channel '{channel_name}' is not running")

        await channel.send_message(user_id, message, **kwargs)

    def set_message_handler(self, handler):
        """设置全局消息处理器

        所有通道的消息都会通过此处理器转发。

        Args:
            handler: 消息处理函数，签名为：
                async def handler(
                    channel: str,
                    user_id: str,
                    message: str,
                    metadata: Dict
                ) -> None
        """
        self.message_handler = handler

        # 更新所有已注册通道的处理器
        for channel in self.channels.values():
            channel.set_message_handler(handler)

        logger.info("Set global message handler for all channels")

    def get_stats(self) -> Dict:
        """获取管理器统计信息

        Returns:
            统计信息字典
        """
        running_count = sum(1 for c in self.channels.values() if c.running)

        return {
            "total_channels": len(self.channels),
            "running_channels": running_count,
            "stopped_channels": len(self.channels) - running_count,
            "channels": self.list_channels()
        }

    async def health_check(self) -> Dict[str, bool]:
        """健康检查所有通道

        Returns:
            每个通道的健康状态
        """
        health_status = {}

        for name, channel in self.channels.items():
            try:
                # 简单的健康检查：检查运行状态
                health_status[name] = channel.running
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                health_status[name] = False

        return health_status
