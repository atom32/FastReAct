"""
MessageBus - Async message queue for decoupling channels from core logic

Based on Nanobot's pattern: channels publish to inbound queue,
agent processes and publishes to outbound queue, channels consume.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime


@dataclass
class InboundMessage:
    """Message from channel to agent"""
    channel: str
    user_id: str
    content: str
    message_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for WebSocket transmission"""
        return {
            "type": "inbound",
            "channel": self.channel,
            "user_id": self.user_id,
            "content": self.content,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class OutboundMessage:
    """Message from agent to channel"""
    channel: str
    user_id: str
    content: str
    message_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Streaming support
    is_stream: bool = False
    is_final: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for WebSocket transmission"""
        return {
            "type": "outbound",
            "channel": self.channel,
            "user_id": self.user_id,
            "content": self.content,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "is_stream": self.is_stream,
            "is_final": self.is_final,
        }


class MessageBus:
    """
    Async message bus for decoupling channels and agent

    Channels publish inbound messages to the queue.
    Agent consumes inbound messages and publishes outbound messages.
    Channels consume outbound messages to send to users.
    """

    def __init__(self, max_size: int = 0):
        """
        Initialize message bus

        Args:
            max_size: Maximum queue size (0 = unlimited)
        """
        self._inbound = asyncio.Queue(maxsize=max_size)
        self._outbound = asyncio.Queue(maxsize=max_size)
        self._running = False

    async def publish_inbound(self, message: InboundMessage):
        """Publish inbound message from channel"""
        await self._inbound.put(message)

    async def consume_inbound(self) -> InboundMessage:
        """Consume inbound message (agent side)"""
        return await self._inbound.get()

    async def publish_outbound(self, message: OutboundMessage):
        """Publish outbound message from agent"""
        await self._outbound.put(message)

    async def consume_outbound(self) -> OutboundMessage:
        """Consume outbound message (channel side)"""
        return await self._outbound.get()

    def inbound_size(self) -> int:
        """Get current inbound queue size"""
        return self._inbound.qsize()

    def outbound_size(self) -> int:
        """Get current outbound queue size"""
        return self._outbound.qsize()

    async def clear(self):
        """Clear all queues"""
        while not self._inbound.empty():
            try:
                self._inbound.get_nowait()
            except asyncio.QueueEmpty:
                break

        while not self._outbound.empty():
            try:
                self._outbound.get_nowait()
            except asyncio.QueueEmpty:
                break

    def __repr__(self) -> str:
        return (
            f"MessageBus(inbound={self.inbound_size()}, "
            f"outbound={self.outbound_size()})"
        )
