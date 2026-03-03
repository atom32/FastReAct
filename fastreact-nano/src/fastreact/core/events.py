"""
FastReAct Nano - Unified Event Protocol

This is the SINGLE source of truth for all agent events.
Core communicates with external world ONLY through AgentEvent.

Design Principles:
1. One protocol to rule them all - no StreamChunk, StepEvent, Message confusion
2. Session-based - support high concurrency
3. Structured - all data in typed fields, not buried in JSON
4. Extensible - metadata field for future needs
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, Dict, AsyncIterator
from datetime import datetime
import json


class EventType(str, Enum):
    """
    Unified event types for FastReAct Nano

    All agent communication flows through these events.
    External adapters (CLI/HTTP/WebSocket) subscribe to this stream.
    """

    # === Lifecycle Events ===
    SESSION_START = "session_start"  # Session begins
    SESSION_END = "session_end"      # Session completes
    ERROR = "error"                  # Error occurred

    # === ReAct Loop Events ===
    THINK = "think"                  # LLM reasoning (streaming chunks)
    TOOL_CALL = "tool_call"          # Deciding to use a tool
    TOOL_RESULT = "tool_result"      # Tool execution result

    # === Control Events ===
    STEP_END = "step_end"            # Core reasoning step complete
    INTERRUPT = "interrupt"          # User/system interruption
    ASK_USER = "ask_user"            # Require user confirmation


@dataclass
class AgentEvent:
    """
    Unified Agent Event - The ONLY protocol between core and external world

    This replaces:
    - StreamChunk (streaming.py)
    - StepEvent (react.py internal)
    - Callback-based events

    All adapters subscribe to AsyncIterator[AgentEvent].
    """

    # Event classification
    type: EventType

    # Primary content (textual data)
    content: str = ""

    # Session tracking (for concurrency)
    session_id: str = ""

    # Timestamp
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())

    # Structured data (payload)
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-init processing"""
        if self.metadata is None:
            self.metadata = {}

    # === Factory Methods ===

    @staticmethod
    def session_start(
        query: str,
        session_id: str,
        skills: Optional[list[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "AgentEvent":
        """Create session start event

        Args:
            query: User query
            session_id: Session identifier
            skills: List of selected skills (optional)
            metadata: Additional metadata (optional, merged with skills metadata)
        """
        event_metadata = {"skills": skills or []}  # Always include skills field (empty array if no skills)

        # Merge with provided metadata if any
        if metadata:
            event_metadata.update(metadata)

        return AgentEvent(
            type=EventType.SESSION_START,
            content=query,
            session_id=session_id,
            metadata=event_metadata,
        )

    @staticmethod
    def session_end(session_id: str, final_answer: str = "") -> "AgentEvent":
        """Create session end event"""
        return AgentEvent(
            type=EventType.SESSION_END,
            content=final_answer,
            session_id=session_id,
        )

    @staticmethod
    def think(content: str, session_id: str, **metadata) -> "AgentEvent":
        """Create think event (LLM reasoning chunk)"""
        return AgentEvent(
            type=EventType.THINK,
            content=content,
            session_id=session_id,
            metadata=metadata,
        )

    @staticmethod
    def tool_call(tool_name: str, tool_args: Dict[str, Any], session_id: str, call_id: str = "") -> "AgentEvent":
        """Create tool call event"""
        return AgentEvent(
            type=EventType.TOOL_CALL,
            tool_name=tool_name,
            tool_args=tool_args,
            session_id=session_id,
            metadata={"action": "calling", "call_id": call_id},
        )

    @staticmethod
    def tool_result(tool_name: str, result: str, session_id: str) -> "AgentEvent":
        """Create tool result event"""
        return AgentEvent(
            type=EventType.TOOL_RESULT,
            content=result,
            tool_name=tool_name,
            session_id=session_id,
            metadata={"action": "result"},
        )

    @staticmethod
    def error(error_message: str, session_id: str, error_type: str = "Exception") -> "AgentEvent":
        """Create error event"""
        return AgentEvent(
            type=EventType.ERROR,
            content=error_message,
            session_id=session_id,
            metadata={"error_type": error_type},
        )

    @staticmethod
    def ask_user(
        reason: str,
        tool_name: str,
        tool_args: Dict[str, Any],
        session_id: str,
    ) -> "AgentEvent":
        """Create user confirmation request event"""
        return AgentEvent(
            type=EventType.ASK_USER,
            content=reason,
            tool_name=tool_name,
            tool_args=tool_args,
            session_id=session_id,
        )

    @staticmethod
    def step_end(session_id: str, final_answer: str = "", has_tool_calls: bool = False) -> "AgentEvent":
        """Create step end event - Core reasoning complete, waiting for body execution"""
        return AgentEvent(
            type=EventType.STEP_END,
            content=final_answer,
            session_id=session_id,
            metadata={"has_tool_calls": has_tool_calls},
        )

    # === Utility Methods ===

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for JSON serialization)"""
        return {
            "type": self.type.value,
            "content": self.content,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentEvent":
        """Create from dictionary (for deserialization)"""
        return cls(
            type=EventType(data["type"]),
            content=data.get("content", ""),
            session_id=data.get("session_id", ""),
            timestamp=data.get("timestamp", datetime.utcnow().timestamp()),
            tool_name=data.get("tool_name"),
            tool_args=data.get("tool_args"),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        """Compact representation"""
        tool_info = f" tool={self.tool_name}" if self.tool_name else ""
        content_preview = self.content[:50] if self.content else ""
        return f"<AgentEvent {self.type.value}{tool_info} '{content_preview}...'>"


# === Type Alias ===

EventStream = AsyncIterator[AgentEvent]
"""Type alias for event stream"""
