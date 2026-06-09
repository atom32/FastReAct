"""
Message types for FastReAct Nano v2.0

Extended message system supporting dual-layer loop:
- Standard messages: user, assistant, tool
- Steering messages: Real-time intervention
- Follow-up messages: Async task continuation
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Literal
from datetime import datetime
import json
import logging

from fastreact.core.time import utc_now

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """
    Unified message type for dual-layer loop

    Roles:
    - user: User input
    - assistant: LLM response
    - tool: Tool execution result
    - steering: Real-time intervention message
    - followup: Async task continuation message
    """

    role: Literal["user", "assistant", "tool", "steering", "followup"]
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "role": self.role,
            "content": self.content,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def to_llm_format(self) -> dict[str, str]:
        """
        Convert to LLM message format

        Steering and followup messages are converted to user messages
        for LLM processing.
        """
        if self.role in ("steering", "followup"):
            return {
                "role": "user",
                "content": f"[{self.role.upper()}] {self.content}",
            }
        elif self.role == "tool":
            return {
                "role": "tool",
                "content": self.content,
                "tool_call_id": self.tool_call_id,
                "name": self.tool_name,
            }
        else:
            return {
                "role": self.role,
                "content": self.content,
            }

    @classmethod
    def user(cls, content: str, **metadata) -> "Message":
        """Create user message"""
        return cls(role="user", content=content, metadata=metadata)

    @classmethod
    def assistant(cls, content: str, **metadata) -> "Message":
        """Create assistant message"""
        return cls(role="assistant", content=content, metadata=metadata)

    @classmethod
    def tool(
        cls,
        name: str,
        result: str,
        call_id: str,
        **metadata
    ) -> "Message":
        """Create tool result message"""
        return cls(
            role="tool",
            content=result,
            tool_name=name,
            tool_call_id=call_id,
            metadata=metadata,
        )

    @classmethod
    def steering(cls, content: str, **metadata) -> "Message":
        """
        Create steering message for real-time intervention

        Steering messages allow external systems to intervene in the
        agent loop, e.g.:
        - User correction during execution
        - Admin override
        - Testing and debugging
        """
        return cls(role="steering", content=content, metadata=metadata)

    @classmethod
    def followup(cls, content: str, **metadata) -> "Message":
        """
        Create follow-up message for async task continuation

        Follow-up messages allow async tasks to continue the conversation
        after completion, e.g.:
        - Background search finished
        - Scheduled task triggered
        - Webhook callback received
        """
        return cls(role="followup", content=content, metadata=metadata)


class MessageQueue:
    """
    Pending message queue for dual-layer loop

    Manages messages that need to be processed before the next LLM call.
    """

    def __init__(self):
        self._messages: list[Message] = []

    def push(self, message: Message):
        """Push message to queue"""
        logger.debug("MessageQueue push before=%s", len(self._messages))
        self._messages.append(message)
        logger.debug("MessageQueue push after=%s", len(self._messages))

    def extend(self, messages: list[Message]):
        """Extend queue with multiple messages"""
        self._messages.extend(messages)

    def peek(self) -> list[Message]:
        """Get all messages without clearing"""
        return self._messages.copy()

    def drain(self) -> list[Message]:
        """Get and clear all messages"""
        logger.debug("MessageQueue drain count=%s", len(self._messages))
        messages = self._messages
        self._messages = []
        return messages

    def clear(self):
        """Clear queue"""
        self._messages = []

    def __len__(self) -> int:
        return len(self._messages)

    def __bool__(self) -> bool:
        return len(self._messages) > 0
