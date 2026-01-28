"""
Telegram 通道

支持 Telegram Bot API 集成。
"""

import os
import logging
from typing import Dict, Optional
import asyncio

from .base import Channel, ChannelConnectionError, ChannelMessageError

logger = logging.getLogger(__name__)


class TelegramChannel(Channel):
    """Telegram Bot 通道

    使用 python-telegram-bot 库实现 Telegram Bot 集成。

    需要安装:
        pip install python-telegram-bot

    Usage:
        from fastreact.channels.telegram import TelegramChannel

        channel = TelegramChannel(
            bot_token="YOUR_BOT_TOKEN"
        )
        await channel.start()
    """

    def __init__(
        self,
        bot_token: str = None,
        gateway_url: str = "ws://localhost:8000",
        config: Dict = None
    ):
        """初始化 Telegram 通道

        Args:
            bot_token: Telegram Bot Token (默认从 TELEGRAM_BOT_TOKEN 环境变量读取)
            gateway_url: Gateway WebSocket URL
            config: 额外配置
        """
        super().__init__(
            name="telegram",
            gateway_url=gateway_url,
            config=config
        )

        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

        self.application = None
        self.bot = None

    async def start(self):
        """启动 Telegram Bot"""
        try:
            # 动态导入（避免硬依赖）
            from telegram import Bot
            from telegram.ext import Application

            # 创建 Bot 实例
            self.bot = Bot(token=self.bot_token)

            # 测试连接
            await self.bot.get_me()

            # 创建 Application
            self.application = Application.builder().token(self.bot_token).build()

            # 注册消息处理器
            self._register_handlers()

            # 启动应用
            await self.application.initialize()
            await self.application.start()

            # 启动轮询
            await self.application.updater.start_polling()

            self.running = True
            logger.info("Telegram channel started successfully")

        except ImportError as e:
            raise ImportError(
                "python-telegram-bot is required. "
                "Install it with: pip install python-telegram-bot"
            ) from e
        except Exception as e:
            raise ChannelConnectionError(f"Failed to start Telegram channel: {e}") from e

    async def stop(self):
        """停止 Telegram Bot"""
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.error(f"Error stopping Telegram channel: {e}")

        self.running = False
        logger.info("Telegram channel stopped")

    def _register_handlers(self):
        """注册 Telegram 消息处理器"""
        from telegram.ext import CommandHandler, MessageHandler, filters

        # 命令处理器
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))
        self.application.add_handler(CommandHandler("agent", self._cmd_agent))

        # 消息处理器
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_message
            )
        )

    # ====== 命令处理器 ======

    async def _cmd_start(self, update, context):
        """处理 /start 命令"""
        await update.message.reply_text(
            "👋 Welcome to FastReAct Bot!\n\n"
            "Available commands:\n"
            "/help - Show help\n"
            "/agent <name> - Switch agent\n\n"
            "Just send me a message to start!"
        )

    async def _cmd_help(self, update, context):
        """处理 /help 命令"""
        await update.message.reply_text(
            "📖 *FastReAct Bot Help*\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help\n"
            "/agent <name> - Switch to a specific agent\n\n"
            "Agents:\n"
            "• `researcher` - Research and analysis\n"
            "• `coder` - Programming and debugging\n"
            "• `creator` - Content creation\n"
            "• `general` - General assistance\n\n"
            "Just send any message to start chatting!",
            parse_mode="Markdown"
        )

    async def _cmd_agent(self, update, context):
        """处理 /agent 命令"""
        if not context.args or len(context.args) == 0:
            await update.message.reply_text(
                "Usage: /agent <name>\n\n"
                "Available agents: researcher, coder, creator, general"
            )
            return

        agent_name = context.args[0]

        # 转发到 Gateway（用于切换智能体）
        await self._forward_to_gateway(
            user_id=str(update.effective_user.id),
            message=f"/switch_agent {agent_name}",
            metadata={
                "command": "agent",
                "agent_name": agent_name,
                "username": update.effective_user.username
            }
        )

    # ====== 消息处理器 ======

    async def _handle_message(self, update, context):
        """处理文本消息"""
        user_id = str(update.effective_user.id)
        message = update.message.text

        # 构建元数据
        metadata = {
            "username": update.effective_user.username,
            "first_name": update.effective_user.first_name,
            "last_name": update.effective_user.last_name,
            "language_code": update.effective_user.language_code,
            "message_id": update.message.message_id,
            "chat_id": update.message.chat.id
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
        parse_mode: str = "Markdown",
        **kwargs
    ):
        """发送消息给用户

        Args:
            user_id: Telegram user ID 或 chat ID
            message: 消息内容
            parse_mode: 解析模式 ("Markdown", "HTML", None)
            **kwargs: 额外参数（reply_to_message_id, disable_web_page_preview 等）
        """
        if not self.bot:
            raise ChannelMessageError("Telegram bot not initialized")

        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=parse_mode,
                **kwargs
            )
            logger.debug(f"Sent message to Telegram user {user_id}")
        except Exception as e:
            raise ChannelMessageError(f"Failed to send Telegram message: {e}") from e

    async def get_user_info(self, user_id: str) -> Dict:
        """获取用户信息

        Args:
            user_id: Telegram user ID

        Returns:
            用户信息字典
        """
        if not self.bot:
            return {}

        try:
            # 尝试获取 chat 信息（适用于 user 和 chat）
            chat = await self.bot.get_chat(user_id)

            return {
                "id": str(chat.id),
                "type": chat.type,
                "username": chat.username,
                "first_name": chat.first_name,
                "last_name": chat.last_name,
                "title": chat.title,
                "description": chat.description
            }
        except Exception as e:
            logger.error(f"Failed to get Telegram user info: {e}")
            return {}

    async def send_photo(
        self,
        user_id: str,
        photo: str,
        caption: str = None,
        **kwargs
    ):
        """发送图片

        Args:
            user_id: 用户ID
            photo: 图片 URL 或 file_id
            caption: 图片说明
            **kwargs: 额外参数
        """
        if not self.bot:
            raise ChannelMessageError("Telegram bot not initialized")

        try:
            await self.bot.send_photo(
                chat_id=user_id,
                photo=photo,
                caption=caption,
                **kwargs
            )
        except Exception as e:
            raise ChannelMessageError(f"Failed to send photo: {e}") from e

    async def send_document(
        self,
        user_id: str,
        document: str,
        caption: str = None,
        **kwargs
    ):
        """发送文档

        Args:
            user_id: 用户ID
            document: 文档 URL 或 file_id
            caption: 文档说明
            **kwargs: 额外参数
        """
        if not self.bot:
            raise ChannelMessageError("Telegram bot not initialized")

        try:
            await self.bot.send_document(
                chat_id=user_id,
                document=document,
                caption=caption,
                **kwargs
            )
        except Exception as e:
            raise ChannelMessageError(f"Failed to send document: {e}") from e

    def get_stats(self) -> Dict:
        """获取通道统计信息"""
        base_stats = super().get_stats()
        return {
            **base_stats,
            "bot_token": f"{self.bot_token[:10]}..." if self.bot_token else None,
            "bot_username": self.bot.username if self.bot else None
        }
