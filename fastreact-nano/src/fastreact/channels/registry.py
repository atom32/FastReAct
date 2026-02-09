"""
Channel registry for managing channel plugins

Based on Moltbot's registry pattern with dynamic channel loading.
"""

from typing import Dict, Type, Optional, List
from fastreact.channels.base import Channel, ChannelMeta


class ChannelRegistry:
    """
    Registry for managing channel plugins

    Provides registration, lookup, and lifecycle management.
    """

    def __init__(self):
        self._channels: Dict[str, Type[Channel]] = {}

    def register(self, channel_class: Type[Channel]):
        """
        Register a channel class

        Args:
            channel_class: Channel class to register
        """
        channel_id = channel_class.__name__.lower().replace("channel", "")

        if channel_id in self._channels:
            raise ValueError(f"Channel '{channel_id}' already registered")

        self._channels[channel_id] = channel_class

    def unregister(self, channel_id: str):
        """
        Unregister a channel

        Args:
            channel_id: Channel identifier
        """
        if channel_id in self._channels:
            del self._channels[channel_id]

    def get(self, channel_id: str) -> Optional[Type[Channel]]:
        """
        Get channel class by ID

        Args:
            channel_id: Channel identifier

        Returns:
            Channel class or None
        """
        return self._channels.get(channel_id)

    def list_all(self) -> List[str]:
        """
        List all registered channel IDs

        Returns:
            List of channel IDs
        """
        return list(self._channels.keys())

    def get_meta(self, channel_id: str) -> Optional[ChannelMeta]:
        """
        Get channel metadata

        Args:
            channel_id: Channel identifier

        Returns:
            Channel metadata or None
        """
        channel_class = self.get(channel_id)
        if channel_class:
            # Try to get metadata from class
            if hasattr(channel_class, "meta"):
                return channel_class.meta
        return None

    def create(
        self,
        channel_id: str,
        **kwargs,
    ) -> Optional[Channel]:
        """
        Create channel instance

        Args:
            channel_id: Channel identifier
            **kwargs: Arguments to pass to channel constructor

        Returns:
            Channel instance or None
        """
        channel_class = self.get(channel_id)
        if channel_class:
            return channel_class(**kwargs)
        return None

    def is_registered(self, channel_id: str) -> bool:
        """
        Check if channel is registered

        Args:
            channel_id: Channel identifier

        Returns:
            True if registered
        """
        return channel_id in self._channels


# Global registry instance
_global_registry: Optional[ChannelRegistry] = None


def get_channel_registry() -> ChannelRegistry:
    """Get global channel registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ChannelRegistry()
    return _global_registry


def register_channel(channel_class: Type[Channel]):
    """
    Register a channel globally

    Args:
        channel_class: Channel class to register
    """
    registry = get_channel_registry()
    registry.register(channel_class)


def list_channels() -> List[str]:
    """List all registered channels"""
    return get_channel_registry().list_all()
