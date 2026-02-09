"""
Channel base classes for FastReAct Nano

Based on Moltbot's channel system with unified interface.
Supports multiple platforms: Telegram, WeChat, CLI, HTTP, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable, Awaitable
from enum import Enum
import asyncio
import logging


logger = logging.getLogger(__name__)


class ChannelStatus(Enum):
    """Channel connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ChannelMeta:
    """Channel metadata"""
    id: str
    label: str
    description: str = ""
    docs_path: Optional[str] = None
    icon: Optional[str] = None
    enabled: bool = True


class MessageHandler(ABC):
    """
    Abstract message handler

    Channels implement this to handle incoming messages.
    """

    @abstractmethod
    async def handle_message(
        self,
        channel: str,
        user_id: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Handle incoming message

        Args:
            channel: Channel name
            user_id: User identifier
            content: Message content
            metadata: Additional metadata
        """
        pass


class Channel(ABC):
    """
    Base class for all channels

    Channels provide unified interface for different messaging platforms.
    """

    def __init__(
        self,
        name: str,
        meta: ChannelMeta,
        gateway_url: str = "ws://localhost:8765",
    ):
        """
        Initialize channel

        Args:
            name: Channel name (must be unique)
            meta: Channel metadata
            gateway_url: WebSocket gateway URL
        """
        self._name = name
        self._meta = meta
        self._gateway_url = gateway_url
        self._status = ChannelStatus.DISCONNECTED
        self._websocket: Optional[Any] = None
        self._message_handler: Optional[Callable] = None
        self._running = False
        self._tasks: list[asyncio.Task] = []

    @property
    def name(self) -> str:
        """Channel name"""
        return self._name

    @property
    def meta(self) -> ChannelMeta:
        """Channel metadata"""
        return self._meta

    @property
    def status(self) -> ChannelStatus:
        """Current connection status"""
        return self._status

    def set_message_handler(self, handler: Callable):
        """
        Set message handler callback

        Args:
            handler: Async callable that handles messages
        """
        self._message_handler = handler

    async def start(self):
        """Start channel connection"""
        if self._running:
            logger.warning(f"[{self._name}] Already running")
            return

        logger.info(f"[{self._name}] Starting...")
        self._status = ChannelStatus.CONNECTING
        self._running = True

        try:
            # Connect to gateway
            await self._connect_gateway()

            # Start channel-specific implementation
            await self._start_channel()

            self._status = ChannelStatus.CONNECTED
            logger.info(f"[{self._name}] Connected")

        except Exception as e:
            self._status = ChannelStatus.ERROR
            logger.error(f"[{self._name}] Failed to start: {e}")
            raise

    async def stop(self):
        """Stop channel connection"""
        if not self._running:
            return

        logger.info(f"[{self._name}] Stopping...")
        self._running = False
        self._status = ChannelStatus.DISCONNECTED

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # Stop channel-specific implementation
        await self._stop_channel()

        # Close gateway connection
        await self._disconnect_gateway()

        logger.info(f"[{self._name}] Stopped")

    async def send(
        self,
        user_id: str,
        content: str,
        **metadata,
    ):
        """
        Send message to user

        Args:
            user_id: User identifier
            content: Message content
            **metadata: Additional metadata
        """
        await self._send_to_platform(user_id, content, **metadata)

    @abstractmethod
    async def _start_channel(self):
        """Start channel-specific implementation"""
        pass

    @abstractmethod
    async def _stop_channel(self):
        """Stop channel-specific implementation"""
        pass

    @abstractmethod
    async def _send_to_platform(
        self,
        user_id: str,
        content: str,
        **metadata,
    ):
        """Send message to platform (channel-specific)"""
        pass

    async def _connect_gateway(self):
        """Connect to gateway WebSocket"""
        # This would connect to the gateway
        # For now, it's a placeholder
        pass

    async def _disconnect_gateway(self):
        """Disconnect from gateway WebSocket"""
        if self._websocket:
            await self._websocket.close()
            self._websocket = None

    async def _forward_to_gateway(
        self,
        user_id: str,
        content: str,
        metadata: Dict[str, Any],
    ):
        """Forward message to gateway"""
        if self._message_handler:
            await self._message_handler(
                self._name,
                user_id,
                content,
                metadata,
            )
        else:
            logger.warning(f"[{self._name}] No message handler set")

    def _create_task(self, coro):
        """Create and track background task"""
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        return task

    def get_stats(self) -> Dict[str, Any]:
        """Get channel statistics"""
        return {
            "name": self._name,
            "status": self._status.value,
            "running": self._running,
            "tasks": len(self._tasks),
        }


class CLIChannel(Channel):
    """
    CLI channel for interactive command-line usage

    Simplest channel implementation for testing and development.
    """

    def __init__(
        self,
        gateway_url: str = "ws://localhost:8765",
    ):
        meta = ChannelMeta(
            id="cli",
            label="CLI",
            description="Command-line interface",
            enabled=True,
        )
        super().__init__("cli", meta, gateway_url)
        self._user_id = "cli-user"

    async def _start_channel(self):
        """Start CLI channel (no-op)"""
        # CLI doesn't need to connect to anything
        pass

    async def _stop_channel(self):
        """Stop CLI channel (no-op)"""
        pass

    async def _send_to_platform(
        self,
        user_id: str,
        content: str,
        **metadata,
    ):
        """Send message to CLI (print)"""
        print(f"\n[Assistant] {content}")

    async def read_input(self) -> str:
        """Read input from user"""
        try:
            return await asyncio.to_thread(input, "[You] ")
        except EOFError:
            return "/exit"

    async def run_interactive(self):
        """Run interactive CLI loop"""
        print("=" * 60)
        print("FastReAct Nano CLI")
        print("=" * 60)
        print("Type your message and press Enter")
        print("Type /exit to quit")
        print("=" * 60)

        while self._running:
            # Read user input
            content = await self.read_input()

            if content.lower() == "/exit":
                print("[INFO] Exiting...")
                break

            if not content.strip():
                continue

            # Forward to gateway
            await self._forward_to_gateway(
                self._user_id,
                content,
                {"source": "cli"},
            )

            # Wait a bit for response
            await asyncio.sleep(0.5)

        await self.stop()
