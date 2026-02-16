"""
IEL Type Definitions - Core data structures for Interactive Execution Loop

Defines the fundamental types for step-based, interruptible execution.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Status Enum
# ============================================================================

class Status(str, Enum):
    """
    Execution status for a single step

    Matches IEL specification:
    - SUCCESS: Step completed successfully
    - FAILED: Step failed (check failure_type for details)
    - NEEDS_INPUT: Step requires user input to proceed
    """
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NEEDS_INPUT = "NEEDS_INPUT"

    def is_terminal(self) -> bool:
        """Check if this is a terminal state (no further action possible)"""
        return self in (self.SUCCESS, self.FAILED)

    def allows_replan(self) -> bool:
        """Check if this status should trigger replanning"""
        return self in (self.FAILED, self.NEEDS_INPUT)


# ============================================================================
# Failure Type
# ============================================================================

class FailureType(str, Enum):
    """
    Classification of failure types

    ACTION: Tool execution failed (e.g., API error, file not found)
    LOGIC: Logic error (e.g., wrong tool choice, invalid plan)
    """
    ACTION = "ACTION"
    LOGIC = "LOGIC"


# ============================================================================
# External Observation
# ============================================================================

@dataclass
class ExternalObservation:
    """
    External observation (e.g., user input, system event)

    Created when user provides input during execution.
    Triggers immediate replanning.
    """
    source: str  # "user", "system", "interrupt"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_step_result(self) -> 'StepResult':
        """Convert to StepResult for history tracking"""
        return StepResult(
            status=Status.NEEDS_INPUT,
            payload=self.content,
            error=None,
            meta={
                "source": self.source,
                "timestamp": self.timestamp.isoformat(),
                **self.metadata
            }
        )


# ============================================================================
# Step Result
# ============================================================================

@dataclass
class StepResult:
    """
    Result of a single execution step

    Core data structure for IEL execution history.
    """
    status: Status
    payload: Any
    error: Optional[str] = None
    failure_type: Optional[FailureType] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    # Execution metrics
    node_id: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def is_success(self) -> bool:
        """Check if step was successful"""
        return self.status == Status.SUCCESS

    def is_failed(self) -> bool:
        """Check if step failed"""
        return self.status == Status.FAILED

    def needs_input(self) -> bool:
        """Check if step needs user input"""
        return self.status == Status.NEEDS_INPUT

    def should_replan(self) -> bool:
        """Check if this result should trigger replanning"""
        return self.status.allows_replan()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "status": self.status.value,
            "payload": self.payload,
            "error": self.error,
            "failure_type": self.failure_type.value if self.failure_type else None,
            "meta": self.meta,
            "node_id": self.node_id,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StepResult':
        """Create from dictionary"""
        return cls(
            status=Status(data["status"]),
            payload=data["payload"],
            error=data.get("error"),
            failure_type=FailureType(data["failure_type"]) if data.get("failure_type") else None,
            meta=data.get("meta", {}),
            node_id=data.get("node_id"),
            execution_time=data.get("execution_time", 0.0),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
        )

    @classmethod
    def success(cls, payload: Any, node_id: str = None, **meta) -> 'StepResult':
        """Create a successful result"""
        return cls(
            status=Status.SUCCESS,
            payload=payload,
            node_id=node_id,
            meta=meta
        )

    @classmethod
    def failure(cls, error: str, failure_type: FailureType = FailureType.ACTION, node_id: str = None, **meta) -> 'StepResult':
        """Create a failed result"""
        return cls(
            status=Status.FAILED,
            payload=None,
            error=error,
            failure_type=failure_type,
            node_id=node_id,
            meta=meta
        )

    @classmethod
    def needs_input(cls, prompt: str, node_id: str = None, **meta) -> 'StepResult':
        """Create a result that needs user input"""
        return cls(
            status=Status.NEEDS_INPUT,
            payload=prompt,
            node_id=node_id,
            meta=meta
        )


# ============================================================================
# Helper Functions
# ============================================================================

def from_node_result(node_result, payload_transform=None) -> StepResult:
    """
    Convert legacy NodeResult to StepResult

    Args:
        node_result: Legacy NodeResult from ToolNode
        payload_transform: Optional function to transform outputs

    Returns:
        StepResult
    """
    from .node import NodeStatus

    # Map NodeStatus to Status
    status_map = {
        NodeStatus.COMPLETED: Status.SUCCESS,
        NodeStatus.FAILED: Status.FAILED,
        NodeStatus.RUNNING: Status.NEEDS_INPUT,
        NodeStatus.PENDING: Status.NEEDS_INPUT,
        NodeStatus.SKIPPED: Status.SUCCESS,
    }

    status = status_map.get(node_result.status, Status.FAILED)

    # Transform payload if needed
    payload = node_result.outputs
    if payload_transform:
        payload = payload_transform(node_result.outputs)
    elif isinstance(node_result.outputs, dict) and len(node_result.outputs) == 1:
        # Extract single value from dict
        payload = list(node_result.outputs.values())[0]

    # Determine failure type for failed nodes
    failure_type = None
    if status == Status.FAILED:
        # Default to ACTION failure (tool execution error)
        failure_type = FailureType.ACTION

    return StepResult(
        status=status,
        payload=payload,
        error=node_result.error,
        failure_type=failure_type,
        node_id=node_result.node_id,
        execution_time=node_result.execution_time,
    )
