"""
FastReAct核心模块
"""

from fastreact.core.engine import FastReAct
from fastreact.core.tool import Tool, ToolCall, ToolResult
from fastreact.core.cache import LRUCache
from fastreact.core.tool_policy import (
    ToolPolicy,
    ToolPolicyConfig,
    ToolPolicyRule,
    ToolPolicyDecision,
    RiskLevel,
    PolicyMode,
    create_default_policy,
    create_restrictive_policy,
)
from fastreact.core.approval import (
    ApprovalManager,
    ApprovalConfig,
    ApprovalRequest,
    ApprovalDecision,
    ApprovalMode,
    ApprovalResponse,
    create_default_approval_manager,
    mock_approval_callback,
)

__all__ = [
    "FastReAct",
    "Tool",
    "ToolCall",
    "ToolResult",
    "LRUCache",
    # Tool Policy
    "ToolPolicy",
    "ToolPolicyConfig",
    "ToolPolicyRule",
    "ToolPolicyDecision",
    "RiskLevel",
    "PolicyMode",
    "create_default_policy",
    "create_restrictive_policy",
    # Execution Approval
    "ApprovalManager",
    "ApprovalConfig",
    "ApprovalRequest",
    "ApprovalDecision",
    "ApprovalMode",
    "ApprovalResponse",
    "create_default_approval_manager",
    "mock_approval_callback",
]
