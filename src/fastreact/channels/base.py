"""
Channel 基类

定义所有消息通道的通用接口。
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Callable, Any, List
import logging
import asyncio

logger = logging.getLogger(__name__)


class Channel(ABC):
    """通道基类

    所有消息通道（Telegram, Slack, Discord 等）的抽象基类。

    Attributes:
        name: 通道名称
        gateway_url: Gateway WebSocket URL
        config: 通道配置
        running: 通道是否运行中
        message_handler: 消息处理回调函数
    """

    def __init__(
        self,
        name: str,
        gateway_url: str = "ws://localhost:8000",
        config: Dict = None
    ):
        """初始化通道

        Args:
            name: 通道名称（如 "telegram", "slack"）
            gateway_url: Gateway WebSocket URL
            config: 通道特定配置
        """
        self.name = name
        self.gateway_url = gateway_url
        self.config = config or {}
        self.running = False
        self.message_handler: Optional[Callable] = None

    @abstractmethod
    async def start(self):
        """启动通道

        建立连接，注册处理器，开始监听消息。
        """
        pass

    @abstractmethod
    async def stop(self):
        """停止通道

        断开连接，清理资源。
        """
        pass

    @abstractmethod
    async def send_message(
        self,
        user_id: str,
        message: str,
        **kwargs
    ):
        """发送消息给用户

        Args:
            user_id: 平台特定的用户ID
            message: 消息内容
            **kwargs: 额外参数（如 parse_mode, attachments 等）
        """
        pass

    @abstractmethod
    async def get_user_info(self, user_id: str) -> Dict:
        """获取用户信息

        Args:
            user_id: 平台特定的用户ID

        Returns:
            用户信息字典
        """
        pass

    def set_message_handler(self, handler: Callable):
        """设置消息处理器

        处理器签名为：
        async def handler(
            channel: str,
            user_id: str,
            message: str,
            metadata: Dict
        ) -> None

        Args:
            handler: 消息处理函数
        """
        self.message_handler = handler

    async def _forward_to_gateway(
        self,
        user_id: str,
        message: str,
        metadata: Dict = None
    ):
        """转发消息到 Gateway

        Args:
            user_id: 用户ID
            message: 消息内容
            metadata: 额外元数据
        """
        if self.message_handler:
            try:
                await self.message_handler(
                    channel=self.name,
                    user_id=user_id,
                    message=message,
                    metadata=metadata or {}
                )
            except Exception as e:
                logger.error(f"Error forwarding message from {self.name}: {e}")
        else:
            logger.warning(f"No message handler set for {self.name}")

    def get_stats(self) -> Dict:
        """获取通道统计信息

        Returns:
            统计信息字典
        """
        return {
            "name": self.name,
            "running": self.running,
            "gateway_url": self.gateway_url
        }


class ChannelError(Exception):
    """通道错误基类"""

    pass


class ChannelConfigError(ChannelError):
    """通道配置错误"""

    pass


class ChannelConnectionError(ChannelError):
    """通道连接错误"""

    pass


class ChannelMessageError(ChannelError):
    """通道消息错误"""

    pass
