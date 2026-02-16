"""
Execution Approval System

Provides workflow for user approval before executing dangerous tool operations.

Key features:
- Pause execution before high-risk tools
- Request user approval (Allow/Deny)
- Integration with Tool Policy
- Timeout handling
- Approval history tracking
- Configurable approval modes
"""

import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Any, Optional, Callable
from threading import Thread, Event
from queue import Queue

from .tool_policy import RiskLevel, ToolPolicyDecision

logger = logging.getLogger(__name__)


class ApprovalMode(IntEnum):
    """Approval modes for tool execution"""

    # Auto-approve all requests
    AUTO_APPROVE = 1

    # Auto-deny all requests
    AUTO_DENY = 2

    # Ask user for every request
    ALWAYS_ASK = 3

    # Ask only for high-risk tools (HIGH, CRITICAL)
    ASK_HIGH_RISK = 4


class ApprovalResponse(IntEnum):
    """User response to approval request"""

    ALLOW = 1
    DENY = 2
    TIMEOUT = 3
    CANCEL = 4


@dataclass
class ApprovalRequest:
    """Request for user approval"""

    # Request ID
    request_id: str

    # Tool name
    tool_name: str

    # Tool parameters
    parameters: Dict[str, Any]

    # Risk level from policy
    risk_level: RiskLevel

    # Reason from policy decision
    reason: str

    # Timestamp when request was created
    created_at: float = field(default_factory=time.time)

    # Timeout in seconds (0 = no timeout)
    timeout: int = 60

    # Additional context
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "risk_level": self.risk_level.name,
            "reason": self.reason,
            "created_at": self.created_at,
            "timeout": self.timeout,
            "context": self.context,
        }


@dataclass
class ApprovalDecision:
    """Decision made for an approval request"""

    # Request ID
    request_id: str

    # User response
    response: ApprovalResponse

    # Timestamp when decision was made
    decided_at: float = field(default_factory=time.time)

    # Optional message from user
    message: str = ""

    # Whether decision was made within timeout
    is_timeout: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "response": self.response.name,
            "decided_at": self.decided_at,
            "message": self.message,
            "is_timeout": self.is_timeout,
        }

    @property
    def is_allowed(self) -> bool:
        """Check if decision allows execution"""
        return self.response == ApprovalResponse.ALLOW


@dataclass
class ApprovalConfig:
    """Configuration for approval system"""

    # Approval mode
    mode: ApprovalMode = ApprovalMode.ASK_HIGH_RISK

    # Default timeout for requests (seconds)
    default_timeout: int = 60

    # Maximum pending requests
    max_pending_requests: int = 10

    # Enable approval history
    enable_history: bool = True

    # Maximum history size
    max_history_size: int = 100

    # Auto-approve tools (list of tool names)
    auto_approve_list: List[str] = field(default_factory=list)

    # Auto-deny tools (list of tool names)
    auto_deny_list: List[str] = field(default_factory=list)

    # Risk threshold for ASK_HIGH_RISK mode
    risk_threshold: RiskLevel = RiskLevel.HIGH

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "mode": self.mode.name,
            "default_timeout": self.default_timeout,
            "max_pending_requests": self.max_pending_requests,
            "enable_history": self.enable_history,
            "max_history_size": self.max_history_size,
            "auto_approve_list": self.auto_approve_list,
            "auto_deny_list": self.auto_deny_list,
            "risk_threshold": self.risk_threshold.name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalConfig":
        """Create from dictionary"""
        mode_map = {
            "auto_approve": ApprovalMode.AUTO_APPROVE,
            "auto_deny": ApprovalMode.AUTO_DENY,
            "always_ask": ApprovalMode.ALWAYS_ASK,
            "ask_high_risk": ApprovalMode.ASK_HIGH_RISK,
        }

        risk_map = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }

        return cls(
            mode=mode_map.get(data.get("mode", "ask_high_risk"), ApprovalMode.ASK_HIGH_RISK),
            default_timeout=data.get("default_timeout", 60),
            max_pending_requests=data.get("max_pending_requests", 10),
            enable_history=data.get("enable_history", True),
            max_history_size=data.get("max_history_size", 100),
            auto_approve_list=data.get("auto_approve_list", []),
            auto_deny_list=data.get("auto_deny_list", []),
            risk_threshold=risk_map.get(data.get("risk_threshold", "high"), RiskLevel.HIGH),
        )


class ApprovalManager:
    """
    Manages approval workflow for tool execution

    Coordinates between Tool Policy and user interaction to ensure
    dangerous operations are approved before execution.
    """

    def __init__(self, config: ApprovalConfig):
        """Initialize approval manager

        Args:
            config: Approval configuration
        """
        self.config = config
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        self.decisions: Dict[str, ApprovalDecision] = {}
        self.history: List[ApprovalDecision] = []
        self.request_counter = 0
        self.user_input_callback: Optional[Callable[[ApprovalRequest], ApprovalResponse]] = None

        logger.info(
            f"ApprovalManager initialized: mode={config.mode.name}, "
            f"timeout={config.default_timeout}s"
        )

    def set_user_input_callback(
        self,
        callback: Callable[[ApprovalRequest], ApprovalResponse]
    ) -> None:
        """Set callback for user input

        Args:
            callback: Function that receives ApprovalRequest and returns ApprovalResponse
        """
        self.user_input_callback = callback
        logger.debug("User input callback registered")

    def check_approval_required(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        policy_decision: ToolPolicyDecision
    ) -> bool:
        """Check if approval is required for a tool execution

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            policy_decision: Decision from ToolPolicy

        Returns:
            True if approval is required
        """
        # Check auto-approve list
        if tool_name in self.config.auto_approve_list:
            logger.debug(f"Tool {tool_name} in auto-approve list")
            return False

        # Check auto-deny list
        if tool_name in self.config.auto_deny_list:
            logger.debug(f"Tool {tool_name} in auto-deny list")
            return True

        # Check based on mode
        if self.config.mode == ApprovalMode.AUTO_APPROVE:
            return False

        elif self.config.mode == ApprovalMode.AUTO_DENY:
            return True

        elif self.config.mode == ApprovalMode.ALWAYS_ASK:
            return True

        elif self.config.mode == ApprovalMode.ASK_HIGH_RISK:
            # Ask only if risk level is at or above threshold
            return policy_decision.risk_level >= self.config.risk_threshold

        return False

    def request_approval(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        policy_decision: ToolPolicyDecision,
        context: Optional[Dict[str, Any]] = None
    ) -> ApprovalDecision:
        """Request user approval for tool execution

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            policy_decision: Decision from ToolPolicy
            context: Additional context

        Returns:
            Approval decision
        """
        # Generate request ID
        self.request_counter += 1
        request_id = f"req_{self.request_counter:04d}"

        # Create request
        request = ApprovalRequest(
            request_id=request_id,
            tool_name=tool_name,
            parameters=parameters,
            risk_level=policy_decision.risk_level,
            reason=policy_decision.reason,
            timeout=self.config.default_timeout,
            context=context or {},
        )

        # Check mode
        if self.config.mode == ApprovalMode.AUTO_APPROVE:
            decision = ApprovalDecision(
                request_id=request_id,
                response=ApprovalResponse.ALLOW,
                message="Auto-approved (AUTO_APPROVE mode)"
            )
            self._record_decision(decision)
            return decision

        if self.config.mode == ApprovalMode.AUTO_DENY:
            decision = ApprovalDecision(
                request_id=request_id,
                response=ApprovalResponse.DENY,
                message="Auto-denied (AUTO_DENY mode)"
            )
            self._record_decision(decision)
            return decision

        # Add to pending
        self.pending_requests[request_id] = request

        # Check if too many pending
        if len(self.pending_requests) > self.config.max_pending_requests:
            logger.warning(f"Too many pending requests: {len(self.pending_requests)}")
            # Remove oldest
            oldest = min(self.pending_requests.keys())
            del self.pending_requests[oldest]

        # Request user input
        try:
            if self.user_input_callback:
                # Use callback (async/blocking)
                response = self.user_input_callback(request)
            else:
                # Default: auto-deny if no callback
                logger.warning("No user input callback, auto-denying request")
                response = ApprovalResponse.DENY

        except Exception as e:
            logger.error(f"Error getting user input: {e}")
            response = ApprovalResponse.DENY

        # Create decision
        decision = ApprovalDecision(
            request_id=request_id,
            response=response,
            message=f"User response: {response.name}"
        )

        # Remove from pending
        self.pending_requests.pop(request_id, None)

        # Record decision
        self._record_decision(decision)

        logger.info(
            f"Approval decision: {request_id} -> {response.name} "
            f"(tool={tool_name}, risk={policy_decision.risk_level.name})"
        )

        return decision

    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get all pending approval requests

        Returns:
            List of pending requests
        """
        return list(self.pending_requests.values())

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a specific pending request

        Args:
            request_id: Request ID

        Returns:
            ApprovalRequest or None
        """
        return self.pending_requests.get(request_id)

    def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending approval request

        Args:
            request_id: Request ID

        Returns:
            True if request was cancelled
        """
        if request_id in self.pending_requests:
            del self.pending_requests[request_id]
            logger.info(f"Cancelled approval request: {request_id}")
            return True
        return False

    def get_decision(self, request_id: str) -> Optional[ApprovalDecision]:
        """Get a decision by request ID

        Args:
            request_id: Request ID

        Returns:
            ApprovalDecision or None
        """
        return self.decisions.get(request_id)

    def get_history(
        self,
        limit: Optional[int] = None
    ) -> List[ApprovalDecision]:
        """Get approval history

        Args:
            limit: Maximum number of history items to return

        Returns:
            List of past decisions
        """
        if limit:
            return self.history[-limit:]
        return self.history.copy()

    def clear_history(self) -> None:
        """Clear approval history"""
        self.history.clear()
        self.decisions.clear()
        logger.debug("Cleared approval history")

    def get_statistics(self) -> Dict[str, Any]:
        """Get approval statistics

        Returns:
            Dictionary with statistics
        """
        total = len(self.history)
        allowed = sum(1 for d in self.history if d.response == ApprovalResponse.ALLOW)
        denied = sum(1 for d in self.history if d.response == ApprovalResponse.DENY)
        timeout = sum(1 for d in self.history if d.response == ApprovalResponse.TIMEOUT)

        return {
            "total_requests": total,
            "allowed": allowed,
            "denied": denied,
            "timeout": timeout,
            "pending": len(self.pending_requests),
            "allow_rate": allowed / total if total > 0 else 0,
        }

    def _record_decision(self, decision: ApprovalDecision) -> None:
        """Record a decision in history

        Args:
            decision: Decision to record
        """
        # Store in decisions map
        self.decisions[decision.request_id] = decision

        # Add to history
        if self.config.enable_history:
            self.history.append(decision)

            # Trim history if needed
            if len(self.history) > self.config.max_history_size:
                self.history = self.history[-self.config.max_history_size:]


def create_default_approval_manager() -> ApprovalManager:
    """Create approval manager with default configuration

    Returns:
        ApprovalManager with ASK_HIGH_RISK mode
    """
    config = ApprovalConfig(mode=ApprovalMode.ASK_HIGH_RISK)
    return ApprovalManager(config)


def mock_approval_callback(
    request: ApprovalRequest,
    auto_response: Optional[ApprovalResponse] = None
) -> ApprovalResponse:
    """
    Mock callback for testing purposes

    In production, this should be replaced with actual user interaction.

    Args:
        request: Approval request
        auto_response: Pre-determined response (for testing)

    Returns:
        Approval response
    """
    if auto_response:
        return auto_response

    # Simple logic based on risk level
    if request.risk_level >= RiskLevel.CRITICAL:
        return ApprovalResponse.DENY
    elif request.risk_level >= RiskLevel.HIGH:
        return ApprovalResponse.ALLOW
    else:
        return ApprovalResponse.ALLOW
