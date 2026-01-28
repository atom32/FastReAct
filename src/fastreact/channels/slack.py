"""
Slack 通道

支持 Slack RTM 和 Events API 集成。
"""

import os
import logging
from typing import Dict, Optional
import asyncio

from .base import Channel, ChannelConnectionError, ChannelMessageError

logger = logging.getLogger(__name__)


class SlackChannel(Channel):
    """Slack Bot 通道

    使用 slack_bolt 库实现 Slack Bot 集成。

    需要安装:
        pip install slack-bolt

    Usage:
        from fastreact.channels.slack import SlackChannel

        channel = SlackChannel(
            bot_token="xoxb-...",
            app_token="xapp-..."
        )
        await channel.start()
    """

    def __init__(
        self,
        bot_token: str = None,
        app_token: str = None,
        signing_secret: str = None,
        gateway_url: str = "ws://localhost:8000",
        config: Dict = None
    ):
        """初始化 Slack 通道

        Args:
            bot_token: Slack Bot Token (xoxb-...) (默认从 SLACK_BOT_TOKEN 读取)
            app_token: Slack App Token (xapp-...) (默认从 SLACK_APP_TOKEN 读取)
            signing_secret: Signing Secret (默认从 SLACK_SIGNING_SECRET 读取)
            gateway_url: Gateway WebSocket URL
            config: 额外配置
        """
        super().__init__(
            name="slack",
            gateway_url=gateway_url,
            config=config
        )

        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.app_token = app_token or os.getenv("SLACK_APP_TOKEN")
        self.signing_secret = signing_secret or os.getenv("SLACK_SIGNING_SECRET")

        if not self.bot_token or not self.app_token:
            raise ValueError("SLACK_BOT_TOKEN and SLACK_APP_TOKEN are required")

        self.app = None
        self.handler = None

    async def start(self):
        """启动 Slack Bot"""
        try:
            # 动态导入（避免硬依赖）
            from slack_bolt import App
            from slack_bolt.adapter.socket_mode import SocketModeHandler

            # 创建 App 实例
            self.app = App(
                token=self.bot_token,
                signing_secret=self.signing_secret
            )

            # 注册事件处理器
            self._register_handlers()

            # 创建 Socket Mode 处理器
            self.handler = SocketModeHandler(self.app, self.app_token)

            # 启动
            await self.handler.connect_async()

            self.running = True
            logger.info("Slack channel started successfully")

        except ImportError as e:
            raise ImportError(
                "slack-bolt is required. "
                "Install it with: pip install slack-bolt"
            ) from e
        except Exception as e:
            raise ChannelConnectionError(f"Failed to start Slack channel: {e}") from e

    async def stop(self):
        """停止 Slack Bot"""
        if self.handler:
            try:
                await self.handler.close()
            except Exception as e:
                logger.error(f"Error stopping Slack channel: {e}")

        self.running = False
        logger.info("Slack channel stopped")

    def _register_handlers(self):
        """注册 Slack 事件处理器"""

        @self.app.event("app_mention")
        async def handle_app_mentation(event):
            """处理应用提及"""
            await self._handle_event(event, "app_mention")

        @self.app.event("message")
        async def handle_message(event):
            """处理消息"""
            # 只处理 DM
            if event.get("channel_type") == "im":
                await self._handle_event(event, "message")

        @self.app.command("/agent")
        async def handle_agent_command(ack, body, respond):
            """处理 /agent 命令"""
            await ack()

            agent_name = body.get("text", "").strip()
            if not agent_name:
                await respond("Usage: /agent <name>")
                return

            # 转发到 Gateway
            await self._forward_to_gateway(
                user_id=body["user_id"],
                message=f"/switch_agent {agent_name}",
                metadata={
                    "command": "agent",
                    "agent_name": agent_name
                }
            )

        @self.app.event("app_home_opened")
        async def handle_app_home_opened(event):
            """处理 App Home 打开"""
            try:
                user_id = event["user"]
                await self.app.client.views_publish(
                    user_id=user_id,
                    view={
                        "type": "home",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*Welcome to FastReAct Bot!*\n\n"
                                          "Just send me a message to start chatting."
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*Available Commands:*\n"
                                          "/agent <name> - Switch agent"
                                }
                            }
                        ]
                    }
                )
            except Exception as e:
                logger.error(f"Error publishing home view: {e}")

    async def _handle_event(self, event, event_type):
        """处理 Slack 事件"""
        user_id = event.get("user")

        # 提取消息内容
        if event_type == "app_mention":
            # 移除机器人提及
            text = event.get("text", "")
            # TODO: 需要从 context 获取 bot_id 来正确移除提及
            message = text.strip()
        elif event_type == "message":
            message = event.get("text", "")
        else:
            return

        # 构建元数据
        metadata = {
            "event_type": event_type,
            "channel": event.get("channel"),
            "ts": event.get("ts"),
            "thread_ts": event.get("thread_ts")
        }

        # 转发到 Gateway
        await self._forward_to_gateway(
            user_id=user_id,
            message=message,
            metadata=metadata
        )

    # ====== 公共接口 ======

    async def send_message(
        self,
        user_id: str,
        message: str,
        channel: str = None,
        **kwargs
    ):
        """发送消息给用户

        Args:
            user_id: Slack user ID
            message: 消息内容
            channel: 额外的 channel 参数（如果指定，优先使用）
            **kwargs: 额外参数（thread_ts, blocks 等）
        """
        if not self.app:
            raise ChannelMessageError("Slack app not initialized")

        target = channel or user_id

        try:
            await self.app.client.chat_postMessage(
                channel=target,
                text=message,
                **kwargs
            )
            logger.debug(f"Sent message to Slack user {target}")
        except Exception as e:
            raise ChannelMessageError(f"Failed to send Slack message: {e}") from e

    async def get_user_info(self, user_id: str) -> Dict:
        """获取用户信息

        Args:
            user_id: Slack user ID

        Returns:
            用户信息字典
        """
        if not self.app:
            return {}

        try:
            user = await self.app.client.users_info(user=user_id)
            return {
                "id": user["user"]["id"],
                "name": user["user"]["name"],
                "real_name": user["user"].get("real_name"),
                "display_name": user["user"].get("profile", {}).get("display_name"),
                "email": user["user"].get("profile", {}).get("email"),
                "is_admin": user["user"].get("is_admin"),
                "is_bot": user["user"].get("is_bot")
            }
        except Exception as e:
            logger.error(f"Failed to get Slack user info: {e}")
            return {}

    async def send_ephemeral_message(
        self,
        user_id: str,
        channel: str,
        message: str,
        **kwargs
    ):
        """发送临时消息（仅对用户可见）

        Args:
            user_id: 用户ID
            channel: 频道ID
            message: 消息内容
            **kwargs: 额外参数
        """
        if not self.app:
            raise ChannelMessageError("Slack app not initialized")

        try:
            await self.app.client.chat_postEphemeral(
                channel=channel,
                user=user_id,
                text=message,
                **kwargs
            )
        except Exception as e:
            raise ChannelMessageError(f"Failed to send ephemeral message: {e}") from e

    def get_stats(self) -> Dict:
        """获取通道统计信息"""
        base_stats = super().get_stats()
        return {
            **base_stats,
            "bot_token": f"{self.bot_token[:10]}..." if self.bot_token else None,
            "app_token": f"{self.app_token[:10]}..." if self.app_token else None
        }
