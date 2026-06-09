"""
Mock Feishu Client for testing

Provides a mock implementation of Feishu SDK client for testing
without requiring real Feishu credentials or WebSocket connections.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict, Any

from fastreact.core.time import utc_iso


@dataclass
class MockFeishuEvent:
    """
    Mock Feishu message event

    Represents a message event from Feishu platform.
    """
    sender_id: str
    chat_id: str
    message_id: str
    content: str
    event_type: str = "message"
    timestamp: Optional[str] = None

    def __post_init__(self):
        """Generate timestamp if not provided"""
        if self.timestamp is None:
            self.timestamp = utc_iso()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (mimics Feishu event structure)"""
        return {
            "type": self.event_type,
            "sender_id": self.sender_id,
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "content": self.content,
            "timestamp": self.timestamp,
        }


@dataclass
class SentMessage:
    """
    Represents a message sent to Feishu (captured for testing)
    """
    chat_id: str
    content: str
    message_type: str = "text"
    timestamp: str = field(default_factory=utc_iso)


class MockFeishuClient:
    """
    Mock Feishu SDK client for testing

    This class simulates the behavior of FeishuSDKAdapter without
    requiring real Feishu credentials, WebSocket connections, or API calls.

    Features:
    - Simulate receiving message events
    - Capture messages that would be sent to Feishu
    - Support event callbacks for testing
    - No network dependencies

    Usage:
        mock_client = MockFeishuClient()

        # Simulate receiving a message
        await mock_client.send_message_event(
            sender_id="ou_test_user",
            chat_id="oc_test_chat",
            content="Hello, bot!"
        )

        # Check what messages were sent
        messages = mock_client.get_sent_messages()
        assert len(messages) > 0

        # Assert specific message was sent
        mock_client.assert_message_sent("oc_test_chat", "Hello!")
    """

    def __init__(self):
        """Initialize mock Feishu client"""
        self._sent_messages: List[SentMessage] = []
        self._received_events: List[MockFeishuEvent] = []
        self._message_callback: Optional[Callable] = None
        self._event_queue: asyncio.Queue = asyncio.Queue()

    def set_message_callback(
        self,
        callback: Callable[[MockFeishuEvent], Any]
    ) -> None:
        """
        Set callback for handling received messages

        Args:
            callback: Async function to call when message received
                     Signature: async callback(event: MockFeishuEvent)
        """
        self._message_callback = callback

    async def send_message_event(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        message_id: Optional[str] = None,
        event_type: str = "message",
    ) -> None:
        """
        Simulate receiving a message event from Feishu

        This mimics the behavior of FeishuSDKAdapter._handle_message_event_v2()

        Args:
            sender_id: Feishu user open_id (e.g., "ou_xxx")
            chat_id: Feishu chat ID (e.g., "oc_xxx")
            content: Message content
            message_id: Optional message ID (auto-generated if None)
            event_type: Event type (default: "message")
        """
        # Generate message_id if not provided
        if message_id is None:
            message_id = f"msg_{uuid.uuid4().hex[:16]}"

        # Create event
        event = MockFeishuEvent(
            sender_id=sender_id,
            chat_id=chat_id,
            message_id=message_id,
            content=content,
            event_type=event_type,
        )

        # Store received event
        self._received_events.append(event)
        await self._event_queue.put(event)

        # Call callback if set
        if self._message_callback:
            if asyncio.iscoroutinefunction(self._message_callback):
                await self._message_callback(event)
            else:
                self._message_callback(event)

    async def mock_send_text(
        self,
        chat_id: str,
        text: str,
        message_type: str = "text",
    ) -> None:
        """
        Mock sending a text message to Feishu

        This captures what would be sent to Feishu for test assertions.

        Args:
            chat_id: Target chat ID
            text: Message text
            message_type: Message type (default: "text")
        """
        message = SentMessage(
            chat_id=chat_id,
            content=text,
            message_type=message_type,
        )
        self._sent_messages.append(message)

    def get_sent_messages(
        self,
        chat_id: Optional[str] = None
    ) -> List[SentMessage]:
        """
        Get messages that were sent to Feishu

        Args:
            chat_id: Optional filter by chat_id

        Returns:
            List of SentMessage objects
        """
        if chat_id:
            return [m for m in self._sent_messages if m.chat_id == chat_id]
        return self._sent_messages.copy()

    def get_received_events(
        self,
        sender_id: Optional[str] = None,
    ) -> List[MockFeishuEvent]:
        """
        Get events that were received from Feishu

        Args:
            sender_id: Optional filter by sender_id

        Returns:
            List of MockFeishuEvent objects
        """
        if sender_id:
            return [e for e in self._received_events if e.sender_id == sender_id]
        return self._received_events.copy()

    def assert_message_sent(
        self,
        chat_id: str,
        expected_text: Optional[str] = None,
    ) -> None:
        """
        Assert that a message was sent to a specific chat

        Args:
            chat_id: Expected chat ID
            expected_text: Optional text to search for in message content

        Raises:
            AssertionError: If no message sent to chat_id or text not found
        """
        messages = self.get_sent_messages(chat_id=chat_id)
        assert len(messages) > 0, f"No messages sent to chat {chat_id}"

        if expected_text:
            found = any(expected_text in m.content for m in messages)
            assert found, f"Text '{expected_text}' not found in messages to {chat_id}"

    def assert_message_count(
        self,
        chat_id: str,
        expected_count: int,
    ) -> None:
        """
        Assert exact number of messages sent to chat

        Args:
            chat_id: Chat ID
            expected_count: Expected number of messages

        Raises:
            AssertionError: If count doesn't match
        """
        messages = self.get_sent_messages(chat_id=chat_id)
        assert len(messages) == expected_count, \
            f"Expected {expected_count} messages to {chat_id}, got {len(messages)}"

    def clear(self) -> None:
        """Clear all captured messages and events"""
        self._sent_messages.clear()
        self._received_events.clear()

        # Clear queue
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def wait_for_message(
        self,
        timeout: float = 5.0,
    ) -> MockFeishuEvent:
        """
        Wait for next message event

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            MockFeishuEvent

        Raises:
            asyncio.TimeoutError: If no message received within timeout
        """
        return await asyncio.wait_for(
            self._event_queue.get(),
            timeout=timeout
        )

    def create_test_event(
        self,
        sender_id: str = "ou_test_user",
        chat_id: str = "oc_test_chat",
        content: str = "Test message",
    ) -> MockFeishuEvent:
        """
        Helper to create a test event

        Args:
            sender_id: Test user ID
            chat_id: Test chat ID
            content: Test message content

        Returns:
            MockFeishuEvent object
        """
        return MockFeishuEvent(
            sender_id=sender_id,
            chat_id=chat_id,
            message_id=f"msg_{uuid.uuid4().hex[:16]}",
            content=content,
        )

    def simulate_agent_response(
        self,
        chat_id: str,
        thinking: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        final_answer: Optional[str] = None,
    ) -> None:
        """
        Simulate agent sending messages to Feishu

        This mimics the behavior of FeishuSDKAdapter._process_agent_stream()

        Args:
            chat_id: Target chat ID
            thinking: Optional thinking message
            tool_calls: Optional list of tool calls
            final_answer: Optional final answer
        """
        if thinking:
            # Simulate thinking message
            self._sent_messages.append(SentMessage(
                chat_id=chat_id,
                content=f"[THINK] {thinking[:100]}...",
                message_type="text",
            ))

        if tool_calls:
            # Simulate tool call messages
            for tc in tool_calls:
                tool_name = tc.get("name", "unknown")
                self._sent_messages.append(SentMessage(
                    chat_id=chat_id,
                    content=f"[TOOL] Calling {tool_name}",
                    message_type="text",
                ))

        if final_answer:
            # Simulate final answer
            self._sent_messages.append(SentMessage(
                chat_id=chat_id,
                content=f"[DONE]\n\n{final_answer}",
                message_type="text",
            ))


# ============================================================================
# Test User Data
# ============================================================================

TEST_FEISHU_USERS = {
    "user_a": {
        "user_id": "ou_test_user_a",
        "chat_id": "oc_chat_a",
        "name": "Test User A",
    },
    "user_b": {
        "user_id": "ou_test_user_b",
        "chat_id": "oc_chat_b",
        "name": "Test User B",
    },
    "user_c": {
        "user_id": "ou_test_user_c",
        "chat_id": "oc_chat_c",
        "name": "Test User C",
    },
    "admin": {
        "user_id": "ou_admin",
        "chat_id": "oc_admin_chat",
        "name": "Admin User",
    },
}


def get_test_user(user_key: str) -> Dict[str, str]:
    """
    Get test user data by key

    Args:
        user_key: User key (e.g., "user_a", "user_b")

    Returns:
        Dict with user_id, chat_id, name
    """
    return TEST_FEISHU_USERS.get(user_key, TEST_FEISHU_USERS["user_a"])


def create_test_user_event(
    user_key: str = "user_a",
    content: str = "Test message",
) -> MockFeishuEvent:
    """
    Create a test event for a specific user

    Args:
        user_key: User key from TEST_FEISHU_USERS
        content: Message content

    Returns:
        MockFeishuEvent
    """
    user = get_test_user(user_key)
    return MockFeishuEvent(
        sender_id=user["user_id"],
        chat_id=user["chat_id"],
        message_id=f"msg_{uuid.uuid4().hex[:16]}",
        content=content,
    )
