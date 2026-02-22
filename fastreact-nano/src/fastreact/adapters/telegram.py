"""
Telegram Adapter for FastReAct Nano

Provides Telegram bot integration using python-telegram-bot library.
Uses long polling mode - no webhook or public IP needed.

Install with: pip install fastreact-nano[telegram]
"""

import asyncio
import re
from typing import Optional

from fastreact.adapters.base import BaseAdapter
from fastreact import Agent

try:
    from telegram import BotCommand, Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters
    from telegram.request import HTTPXRequest

    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

    BotCommand = None
    Update = None
    Application = None
    CommandHandler = None
    MessageHandler = None
    filters = None


def _markdown_to_telegram_html(text: str) -> str:
    """
    Convert markdown to Telegram-safe HTML.

    Reused from nanobot project with permission.
    """
    if not text:
        return ""

    # 1. Extract and protect code blocks
    code_blocks: list[str] = []

    def save_code_block(m: re.Match) -> str:
        code_blocks.append(m.group(1))
        return f"\x00CB{len(code_blocks) - 1}\x00"

    text = re.sub(r'```[\w]*\n?([\s\S]*?)```', save_code_block, text)

    # 2. Extract and protect inline code
    inline_codes: list[str] = []

    def save_inline_code(m: re.Match) -> str:
        inline_codes.append(m.group(1))
        return f"\x00IC{len(inline_codes) - 1}\x00"

    text = re.sub(r'`([^`]+)`', save_inline_code, text)

    # 3. Headers
    text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)

    # 4. Blockquotes
    text = re.sub(r'^>\s*(.*)$', r'\1', text, flags=re.MULTILINE)

    # 5. Escape HTML special characters
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # 6. Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    # 7. Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)

    # 8. Italic
    text = re.sub(r'(?<![a-zA-Z0-9])_([^_]+)_(?![a-zA-Z0-9])', r'<i>\1</i>', text)

    # 9. Strikethrough
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)

    # 10. Bullet lists
    text = re.sub(r'^[-*]\s+', '• ', text, flags=re.MULTILINE)

    # 11. Restore inline code
    for i, code in enumerate(inline_codes):
        escaped = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace(f"\x00IC{i}\x00", f"<code>{escaped}</code>")

    # 12. Restore code blocks
    for i, code in enumerate(code_blocks):
        escaped = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace(f"\x00CB{i}\x00", f"<pre><code>{escaped}</code></pre>")

    return text


def _split_message(content: str, max_len: int = 4000) -> list[str]:
    """
    Split content into chunks within max_len, preferring line breaks.

    Reused from nanobot project with permission.
    """
    if len(content) <= max_len:
        return [content]

    chunks: list[str] = []
    while content:
        if len(content) <= max_len:
            chunks.append(content)
            break

        cut = content[:max_len]
        pos = cut.rfind('\n')
        if pos == -1:
            pos = cut.rfind(' ')
        if pos == -1:
            pos = max_len

        chunks.append(content[:pos])
        content = content[pos:].lstrip()

    return chunks


class TelegramAdapter(BaseAdapter):
    """
    Telegram adapter using long polling mode

    Features:
    - No webhook needed (long polling)
    - No public IP required
    - Supports text messages
    - Markdown formatting
    - /start, /new, /help commands
    - Message splitting (4096 char limit)

    Reuses business logic from AgentSession.
    """

    name = "telegram"

    @property
    def BOT_COMMANDS(self):
        """Commands registered with Telegram"""
        if not TELEGRAM_AVAILABLE:
            return []
        return [
            BotCommand("start", "Start the bot"),
            BotCommand("new", "Start a new conversation"),
            BotCommand("help", "Show available commands"),
        ]

    def __init__(self, token: str, agent: Agent):
        """
        Initialize Telegram adapter

        Args:
            token: Telegram bot token from @BotFather
            agent: FastReAct Agent instance
        """
        if not TELEGRAM_AVAILABLE:
            raise RuntimeError(
                "python-telegram-bot is required for Telegram adapter. "
                "Install with: pip install python-telegram-bot[job-queue]"
            )

        super().__init__(config={"token": token})

        self.token = token
        self.agent = agent
        self._app: Optional["Application"] = None
        self._sessions: dict[str, dict] = {}  # chat_id -> history

    async def start(self) -> None:
        """Start Telegram bot with long polling"""
        if not self.token:
            print("[ERROR] Telegram bot token not configured")
            return

        self._running = True

        # Build application with larger connection pool
        req = HTTPXRequest(
            connection_pool_size=16,
            pool_timeout=5.0,
            connect_timeout=30.0,
            read_timeout=30.0
        )
        builder = Application.builder().token(self.token).request(req)

        self._app = builder.build()
        self._app.add_error_handler(self._on_error)

        # Add command handlers
        self._app.add_handler(CommandHandler("start", self._on_start))
        self._app.add_handler(CommandHandler("new", self._on_new))
        self._app.add_handler(CommandHandler("help", self._on_help))

        # Add message handler
        self._app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._on_message
            )
        )

        print("[INFO] Starting Telegram bot (polling mode)...")

        # Initialize and start
        await self._app.initialize()
        await self._app.start()

        # Get bot info
        try:
            bot_info = await self._app.bot.get_me()
            print(f"[INFO] Telegram bot @{bot_info.username} connected")
        except Exception as e:
            print(f"[WARNING] Could not get bot info: {e}")

        # Register commands
        try:
            await self._app.bot.set_my_commands(self.BOT_COMMANDS)
            print("[INFO] Telegram bot commands registered")
        except Exception as e:
            print(f"[WARNING] Failed to register commands: {e}")

        # Start polling
        await self._app.updater.start_polling(
            allowed_updates=["message"],
            drop_pending_updates=True
        )

        # Keep running
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop Telegram bot"""
        self._running = False

        if self._app:
            print("[INFO] Stopping Telegram bot...")
            try:
                await self._app.updater.stop()
            except Exception:
                pass

            try:
                await self._app.stop()
            except Exception:
                pass

            try:
                await self._app.shutdown()
            except Exception:
                pass

            self._app = None
            print("[OK] Telegram bot stopped")

    async def _on_start(self, update: "Update", context) -> None:
        """Handle /start command"""
        if not update.message or not update.effective_user:
            return

        user = update.effective_user
        await update.message.reply_text(
            f"[Hi] Hello {user.first_name}! I'm FastReAct Nano.\n\n"
            "I'm an AI assistant powered by ReAct architecture.\n\n"
            "Commands:\n"
            "/new - Start a new conversation\n"
            "/help - Show help"
        )

    async def _on_new(self, update: "Update", context) -> None:
        """Handle /new command"""
        if not update.message:
            return

        chat_id = str(update.effective_chat.id)

        # Clear session - will be recreated on next message
        if chat_id in self._sessions:
            agent_session = self._sessions[chat_id].get("agent_session")
            if agent_session:
                # Clear history in AgentSession
                agent_session._history.clear()

        await update.message.reply_text(
            "[OK] New conversation started. Previous context cleared."
        )

    async def _on_help(self, update: "Update", context) -> None:
        """Handle /help command"""
        if not update.message:
            return

        await update.message.reply_text(
            "[FastReAct Nano] Commands:\n\n"
            "/start - Start the bot\n"
            "/new - Start a new conversation\n"
            "/help - Show this help message\n\n"
            "Just send me a message and I'll respond!"
        )

    async def _on_error(self, update: "Update", context) -> None:
        """Handle errors"""
        print(f"[ERROR] Telegram update error: {update.error}")

    async def _on_message(self, update: "Update", context) -> None:
        """Handle regular text messages"""
        if not update.message or not update.effective_user:
            return

        chat_id = str(update.effective_chat.id)
        content = update.message.text

        # Get or create session for this chat
        if chat_id not in self._sessions:
            # Create AgentSession for this chat
            agent_session = self.agent.create_session(
                session_id=f"telegram:{chat_id}",
                max_history=50,
            )
            self._sessions[chat_id] = {
                "agent_session": agent_session,
            }
        else:
            agent_session = self._sessions[chat_id]["agent_session"]

        # Process query with AgentSession
        try:
            # Send "thinking" notification
            await update.message.chat.send_action("typing...")

            # Process query (AgentSession handles business logic)
            # Callback will send final response to user
            async for event in agent_session.process_message(
                {"type": "query", "content": content},
                on_event=self._create_send_callback(update, chat_id),
            ):
                # Events are sent via callback
                pass

        except Exception as e:
            import sys
            print(f"[ERROR] Failed to process message: {e}", file=sys.stderr)
            await update.message.reply_text(f"[ERROR] {str(e)}")

    def _create_send_callback(self, update: "Update", chat_id: str):
        """
        Create callback function for sending events to Telegram

        Args:
            update: Telegram Update object
            chat_id: Target chat ID

        Returns:
            Async callback function
        """

        async def send_callback(message: dict) -> None:
            """Send message dict to Telegram"""
            msg_type = message.get("type")

            if msg_type == "event":
                # Handle event messages
                event_type = message.get("event_type")

                if event_type == "session_end":
                    # Send final response
                    content = message.get("content", "")
                    if content:
                        # Convert markdown to Telegram HTML and split if needed
                        html_content = _markdown_to_telegram_html(content)
                        chunks = _split_message(html_content, max_len=4000)

                        for chunk in chunks:
                            await update.message.reply_text(
                                chunk,
                                parse_mode="HTML"
                            )
                elif event_type == "error":
                    # Send error event
                    await update.message.reply_text(f"[ERROR] {message.get('content', '')}")

            elif msg_type == "info":
                # Send info message
                await update.message.reply_text(message.get("content", ""))

            elif msg_type == "error":
                # Send error message
                await update.message.reply_text(f"[ERROR] {message.get('content', '')}")

        return send_callback
