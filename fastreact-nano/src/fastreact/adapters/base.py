"""
Base adapter interface for all communication channels

This module provides the BaseAdapter abstract class that all adapters
(Gateway, Telegram, Discord, Slack, etc.) should inherit from.

The adapter pattern allows:
- Unified interface for all channels
- Easy addition of new channels
- Consistent lifecycle management
"""

from abc import ABC, abstractmethod
from typing import Optional, Any


class BaseAdapter(ABC):
    """
    Base adapter class for all communication channels

    All adapters (Gateway, Telegram, Discord, Slack, etc.) should inherit
    from this class to ensure consistent interface and behavior.

    Lifecycle:
    1. Create adapter instance
    2. Call start() to initialize and begin listening for messages
    3. Handle incoming messages
    4. Call stop() to cleanup and shutdown

    Example:
        class MyAdapter(BaseAdapter):
            name = "mychannel"

            async def start(self):
                # Initialize connection
                pass

            async def stop(self):
                # Cleanup
                pass
    """

    name: str = "base"

    def __init__(self, config: Optional[Any] = None):
        """
        Initialize adapter

        Args:
            config: Optional configuration object or dict
        """
        self.config = config
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """
        Start the adapter

        This should:
        1. Initialize connection to the platform (WebSocket, HTTP, SDK, etc.)
        2. Begin listening for incoming messages
        3. Block until stop() is called

        Implementation should be async and long-running.
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the adapter

        This should:
        1. Stop listening for new messages
        2. Close connections
        3. Cleanup resources

        After stop() returns, the adapter can be safely discarded.
        """
        pass

    @property
    def is_running(self) -> bool:
        """
        Check if adapter is currently running

        Returns:
            True if adapter is running, False otherwise
        """
        return self._running

    def __repr__(self) -> str:
        """String representation"""
        return f"<{self.__class__.__name__}(name='{self.name}', running={self._running})>"
