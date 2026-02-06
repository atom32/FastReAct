"""
Message Schema - Standardized message format for Reactive Loop

Defines OpenAI-compatible message format with extensions for:
- Message source tracking (user, system, policy_engine, etc.)
- Metadata for debugging and observability
- Tool call support

Compliant with Sprint 4: The Reactive Loop architecture
"""

from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# Message Role Enumeration
# ============================================================================

class MessageRole(str, Enum):
    """Standard message roles (OpenAI compatible)"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# ============================================================================
# Message Source Tracking
# ============================================================================

class MessageSource(str, Enum):
    """
    Message source identifiers for observability

    Helps track where messages originated from:
    - USER: Direct user input
    - LLM: LLM-generated responses
    - TOOL: Tool execution results
    - SYSTEM: System-generated messages
    - POLICY_ENGINE: Policy interventions
    - INTERRUPT_QUEUE: User interruptions
    - FOLLOWUP_SCHEDULER: Task chaining
    - AUTO_REFLECTOR: Self-reflection suggestions
    """
    USER = "user"
    LLM = "llm"
    TOOL = "tool"
    SYSTEM = "system"
    POLICY_ENGINE = "policy_engine"
    INTERRUPT_QUEUE = "interrupt_queue"
    FOLLOWUP_SCHEDULER = "followup_scheduler"
    AUTO_REFLECTOR = "auto_reflector"


# ============================================================================
# Agent Message Schema
# ============================================================================

@dataclass
class AgentMessage:
    """
    Standardized message format for FastReAct Reactive Loop

    OpenAI-compatible format with source tracking and metadata.

    Attributes:
        role: Message role (user/assistant/system/tool)
        content: Message content string
        tool_calls: Optional list of tool calls (for assistant messages)
        tool_call_id: Optional tool call ID (for tool result messages)
        source: Message source identifier
        metadata: Optional metadata dictionary
        timestamp: Message creation timestamp

    Examples:
        # User message
        msg = AgentMessage(
            role=MessageRole.USER,
            content="Analyze this file",
            source=MessageSource.USER
        )

        # Assistant message with tool calls
        msg = AgentMessage(
            role=MessageRole.ASSISTANT,
            content="I'll read the file",
            tool_calls=[{"name": "read_file", "arguments": {...}}],
            source=MessageSource.LLM
        )

        # Policy intervention
        msg = AgentMessage(
            role=MessageRole.SYSTEM,
            content="[POLICY] Action denied: security risk",
            source=MessageSource.POLICY_ENGINE,
            metadata={"policy": "no_unapproved_shell_commands"}
        )

        # User interruption
        msg = AgentMessage(
            role=MessageRole.USER,
            content="Wait, check tests too",
            source=MessageSource.INTERRUPT_QUEUE,
            metadata={"interrupt_type": "steering"}
        )
    """

    role: MessageRole
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    source: MessageSource = MessageSource.SYSTEM
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to OpenAI-compatible dictionary

        Removes internal fields (source, metadata) for API calls.
        """
        result = {
            "role": self.role.value,
            "content": self.content,
        }

        # Add tool calls if present
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls

        # Add tool call ID if present (for tool results)
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id

        return result

    def to_dict_with_metadata(self) -> Dict[str, Any]:
        """
        Convert to dictionary with metadata preserved

        Used for debugging and observability.
        """
        result = self.to_dict()
        result["source"] = self.source.value
        result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """
        Create AgentMessage from dictionary

        Supports both OpenAI format (no metadata) and extended format (with metadata).
        """
        role = MessageRole(data.get("role", "system"))
        content = data.get("content", "")
        tool_calls = data.get("tool_calls")
        tool_call_id = data.get("tool_call_id")
        source = MessageSource(data.get("source", "system"))
        metadata = data.get("metadata", {})

        return cls(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            source=source,
            metadata=metadata
        )

    def is_from_user(self) -> bool:
        """Check if message originated from user"""
        return self.source == MessageSource.USER or self.role == MessageRole.USER

    def is_from_system(self) -> bool:
        """Check if message is a system message"""
        return self.source == MessageSource.SYSTEM or self.role == MessageRole.SYSTEM

    def is_interruption(self) -> bool:
        """Check if message is a user interruption"""
        return self.source == MessageSource.INTERRUPT_QUEUE

    def is_policy_intervention(self) -> bool:
        """Check if message is a policy intervention"""
        return self.source == MessageSource.POLICY_ENGINE

    def is_followup_task(self) -> bool:
        """Check if message is a follow-up task"""
        return self.source == MessageSource.FOLLOWUP_SCHEDULER

    def has_tool_calls(self) -> bool:
        """Check if message contains tool calls"""
        return bool(self.tool_calls)

    def __repr__(self) -> str:
        """String representation for debugging"""
        tool_info = f" [+{len(self.tool_calls)} tools]" if self.tool_calls else ""
        source_info = f" ({self.source.value})" if self.source != MessageSource.SYSTEM else ""
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content

        return f"AgentMessage({self.role.value}{source_info}{tool_info}): {content_preview}"


# ============================================================================
# Convenience Factory Functions
# ============================================================================

def user_message(content: str, metadata: Dict[str, Any] = None) -> AgentMessage:
    """Create user message"""
    return AgentMessage(
        role=MessageRole.USER,
        content=content,
        source=MessageSource.USER,
        metadata=metadata or {}
    )


def assistant_message(
    content: str,
    tool_calls: List[Dict[str, Any]] = None,
    metadata: Dict[str, Any] = None
) -> AgentMessage:
    """Create assistant message"""
    return AgentMessage(
        role=MessageRole.ASSISTANT,
        content=content,
        tool_calls=tool_calls,
        source=MessageSource.LLM,
        metadata=metadata or {}
    )


def system_message(content: str, source: MessageSource = MessageSource.SYSTEM) -> AgentMessage:
    """Create system message"""
    return AgentMessage(
        role=MessageRole.SYSTEM,
        content=content,
        source=source
    )


def tool_result_message(
    content: str,
    tool_call_id: str,
    metadata: Dict[str, Any] = None
) -> AgentMessage:
    """Create tool result message"""
    return AgentMessage(
        role=MessageRole.TOOL,
        content=content,
        tool_call_id=tool_call_id,
        source=MessageSource.TOOL,
        metadata=metadata or {}
    )


def steering_message(content: str, metadata: Dict[str, Any] = None) -> AgentMessage:
    """Create steering/intervention message"""
    return AgentMessage(
        role=MessageRole.USER,
        content=f"[STEERING] {content}",
        source=MessageSource.INTERRUPT_QUEUE,
        metadata=metadata or {}
    )


def policy_intervention_message(content: str, policy_name: str = None) -> AgentMessage:
    """Create policy intervention message"""
    return AgentMessage(
        role=MessageRole.SYSTEM,
        content=f"[POLICY] {content}",
        source=MessageSource.POLICY_ENGINE,
        metadata={"policy": policy_name} if policy_name else {}
    )


def followup_message(content: str, task_number: int = 0, total_tasks: int = 0) -> AgentMessage:
    """Create follow-up task message"""
    return AgentMessage(
        role=MessageRole.USER,
        content=f"[FOLLOW-UP] {content}",
        source=MessageSource.FOLLOWUP_SCHEDULER,
        metadata={"task_number": task_number, "total_tasks": total_tasks}
    )


# ============================================================================
# Message Batch Utilities
# ============================================================================

def messages_to_openai_format(messages: List[AgentMessage]) -> List[Dict[str, Any]]:
    """
    Convert list of AgentMessage to OpenAI format

    Args:
        messages: List of AgentMessage objects

    Returns:
        List of dictionaries in OpenAI format
    """
    return [msg.to_dict() for msg in messages]


def filter_messages_by_source(
    messages: List[AgentMessage],
    source: MessageSource
) -> List[AgentMessage]:
    """Filter messages by source"""
    return [msg for msg in messages if msg.source == source]


def count_tool_calls(messages: List[AgentMessage]) -> int:
    """Count total tool calls in messages"""
    return sum(len(msg.tool_calls or []) for msg in messages if msg.tool_calls)
