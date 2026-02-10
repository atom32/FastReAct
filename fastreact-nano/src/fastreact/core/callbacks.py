"""
Callback system for FastReAct Nano v2.0

Provides steering and follow-up message support for dual-layer loop.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Callable, Any
from datetime import datetime

from fastreact.core.messages import Message


class SteeringCallback(ABC):
    """
    Abstract base class for steering message callbacks

    Steering messages allow real-time intervention in the agent loop:
    - User corrections during execution
    - Admin overrides
    - Testing and debugging
    """

    @abstractmethod
    async def get_steering_messages(self) -> Optional[list[Message]]:
        """
        Get steering messages to process

        Returns:
            List of messages or None
        """
        pass


class FileSteeringCallback(SteeringCallback):
    """
    File-based steering callback

    Monitors a steering file (JSONL format) for intervention messages.
    Messages are read and file is cleared after processing.
    """

    def __init__(self, steering_file: Path):
        """
        Initialize file steering callback

        Args:
            steering_file: Path to steering file (e.g., .steering.jsonl)
        """
        self._steering_file = steering_file

    async def get_steering_messages(self) -> Optional[list[Message]]:
        """Read steering messages from file"""
        if not self._steering_file.exists():
            return None

        messages = []

        try:
            # Read file in thread
            def read_file():
                with open(self._steering_file, "r", encoding="utf-8") as f:
                    return f.readlines()

            lines = await asyncio.to_thread(read_file)

            # Parse messages
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        messages.append(Message(
                            role="steering",
                            content=data.get("content", ""),
                            metadata=data.get("metadata", {}),
                        ))
                    except json.JSONDecodeError:
                        continue

        except Exception:
            pass

        # Clear file after reading
        if messages:
            try:
                await asyncio.to_thread(self._steering_file.unlink)
            except Exception:
                pass

        return messages if messages else None


class FollowUpCallback(ABC):
    """
    Abstract base class for follow-up message callbacks

    Follow-up messages allow async tasks to continue the conversation:
    - Background search finished
    - Scheduled task triggered
    - Webhook callback received
    """

    @abstractmethod
    async def get_followup_messages(self) -> Optional[list[Message]]:
        """
        Get follow-up messages from async tasks

        Returns:
            List of messages or None
        """
        pass

    @abstractmethod
    async def schedule_followup(
        self,
        delay: float,
        message: Message,
    ):
        """
        Schedule a follow-up message after delay

        Args:
            delay: Delay in seconds
            message: Message to deliver
        """
        pass


class QueueFollowUpCallback(FollowUpCallback):
    """
    Queue-based follow-up callback

    Manages async tasks that produce follow-up messages.
    """

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()

    async def get_followup_messages(self) -> Optional[list[Message]]:
        """Get all pending follow-up messages"""
        messages = []

        while not self._queue.empty():
            try:
                msg = self._queue.get_nowait()
                messages.append(msg)
            except asyncio.QueueEmpty:
                break

        return messages if messages else None

    async def schedule_followup(
        self,
        delay: float,
        message: Message,
    ) -> asyncio.Task:
        """
        Schedule a follow-up message after delay

        Returns:
            The scheduled task
        """
        async def delayed():
            await asyncio.sleep(delay)
            await self._queue.put(message)

        return asyncio.create_task(delayed())


class CallbackManager:
    """
    Manager for steering and follow-up callbacks

    Provides unified interface for managing both callback types.
    """

    def __init__(
        self,
        steering_callback: Optional[SteeringCallback] = None,
        followup_callback: Optional[FollowUpCallback] = None,
    ):
        """
        Initialize callback manager

        Args:
            steering_callback: Steering message callback
            followup_callback: Follow-up message callback
        """
        self._steering = steering_callback
        self._followup = followup_callback

    async def get_steering_messages(self) -> Optional[list[Message]]:
        """Get steering messages from callback"""
        if self._steering:
            return await self._steering.get_steering_messages()
        return None

    async def get_followup_messages(self) -> Optional[list[Message]]:
        """Get follow-up messages from callback"""
        if self._followup:
            return await self._followup.get_followup_messages()
        return None

    async def schedule_followup(
        self,
        delay: float,
        message: Message,
    ) -> Optional[asyncio.Task]:
        """Schedule follow-up message"""
        if self._followup:
            return await self._followup.schedule_followup(delay, message)
        return None

    @property
    def has_steering(self) -> bool:
        """Check if steering callback is configured"""
        return self._steering is not None

    @property
    def has_followup(self) -> bool:
        """Check if follow-up callback is configured"""
        return self._followup is not None
