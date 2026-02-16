"""
Tool Policy System

Provides security control for tool usage with Allow/Deny lists,
risk levels, and usage profiles.

Based on Moltbot's tool-policy.ts approach:
- Allow/Deny lists for tool access control
- Tool usage profiles (restrictive, permissive, custom)
- Risk levels (low, medium, high, critical)
- Policy enforcement in engine execution
"""

import logging
import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Any, Optional, Set, Pattern

logger = logging.getLogger(__name__)


class RiskLevel(IntEnum):
    """Tool risk levels"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class PolicyMode(IntEnum):
    """Policy enforcement modes"""

    # Allow all tools by default, deny specific ones
    PERMISSIVE = 1

    # Deny all tools by default, allow specific ones
    RESTRICTIVE = 2

    # Custom policy with explicit allow/deny lists
    CUSTOM = 3


@dataclass
class ToolPolicyRule:
    """Policy rule for a specific tool or pattern"""

    # Tool name or pattern (e.g., "bash", "shell*", "*_exec")
    pattern: str

    # Risk level for this tool
    risk_level: RiskLevel = RiskLevel.MEDIUM

    # Whether this tool is allowed
    allowed: bool = True

    # Maximum allowed executions per session (0 = unlimited)
    max_executions: int = 0

    # Required approval before execution
    requires_approval: bool = False

    # Reason for policy (for logging/debugging)
    reason: str = ""

    # Compiled pattern for matching
    _compiled_pattern: Optional[Pattern] = field(init=False, repr=False)

    def __post_init__(self):
        """Compile the pattern for matching"""
        try:
            # Convert glob-style pattern to regex
            regex_pattern = self.pattern.replace("*", ".*")
            self._compiled_pattern = re.compile(f"^{regex_pattern}$")
        except re.error:
            logger.warning(f"Invalid pattern: {self.pattern}")
            self._compiled_pattern = None

    def matches(self, tool_name: str) -> bool:
        """Check if this rule matches a tool name"""
        if self._compiled_pattern is None:
            return False
        return self._compiled_pattern.match(tool_name) is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "pattern": self.pattern,
            "risk_level": self.risk_level.name,
            "allowed": self.allowed,
            "max_executions": self.max_executions,
            "requires_approval": self.requires_approval,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolPolicyRule":
        """Create from dictionary"""
        risk_level_map = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }

        return cls(
            pattern=data.get("pattern", "*"),
            risk_level=risk_level_map.get(data.get("risk_level", "medium"), RiskLevel.MEDIUM),
            allowed=data.get("allowed", True),
            max_executions=data.get("max_executions", 0),
            requires_approval=data.get("requires_approval", False),
            reason=data.get("reason", ""),
        )


@dataclass
class ToolPolicyConfig:
    """Tool policy configuration"""

    # Policy mode (permissive, restrictive, custom)
    mode: PolicyMode = PolicyMode.PERMISSIVE

    # List of tool rules (evaluated in order)
    rules: List[ToolPolicyRule] = field(default_factory=list)

    # Default risk level for tools not in rules
    default_risk_level: RiskLevel = RiskLevel.MEDIUM

    # Global execution limit (0 = unlimited)
    global_max_executions: int = 0

    # Enable approval workflow for high-risk tools
    approval_enabled: bool = False

    # Allow list (used in RESTRICTIVE mode)
    allow_list: List[str] = field(default_factory=list)

    # Deny list (used in PERMISSIVE mode)
    deny_list: List[str] = field(default_factory=list)

    def add_rule(self, rule: ToolPolicyRule) -> None:
        """Add a policy rule"""
        self.rules.append(rule)
        logger.debug(f"Added policy rule: {rule.pattern} -> {rule.risk_level.name}")

    def remove_rule(self, pattern: str) -> bool:
        """Remove a policy rule by pattern"""
        original_len = len(self.rules)
        self.rules = [r for r in self.rules if r.pattern != pattern]
        removed = len(self.rules) < original_len
        if removed:
            logger.debug(f"Removed policy rule: {pattern}")
        return removed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "mode": self.mode.name,
            "rules": [r.to_dict() for r in self.rules],
            "default_risk_level": self.default_risk_level.name,
            "global_max_executions": self.global_max_executions,
            "approval_enabled": self.approval_enabled,
            "allow_list": self.allow_list,
            "deny_list": self.deny_list,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolPolicyConfig":
        """Create from dictionary"""
        mode_map = {
            "permissive": PolicyMode.PERMISSIVE,
            "restrictive": PolicyMode.RESTRICTIVE,
            "custom": PolicyMode.CUSTOM,
        }

        risk_level_map = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }

        rules = [ToolPolicyRule.from_dict(r) for r in data.get("rules", [])]

        return cls(
            mode=mode_map.get(data.get("mode", "permissive"), PolicyMode.PERMISSIVE),
            rules=rules,
            default_risk_level=risk_level_map.get(
                data.get("default_risk_level", "medium"),
                RiskLevel.MEDIUM
            ),
            global_max_executions=data.get("global_max_executions", 0),
            approval_enabled=data.get("approval_enabled", False),
            allow_list=data.get("allow_list", []),
            deny_list=data.get("deny_list", []),
        )


@dataclass
class ToolPolicyDecision:
    """Result of policy check for a tool execution"""

    # Whether the tool execution is allowed
    allowed: bool

    # Risk level of the tool
    risk_level: RiskLevel

    # Reason for the decision
    reason: str

    # Whether approval is required
    requires_approval: bool

    # Matching rule (if any)
    rule: Optional[ToolPolicyRule] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "allowed": self.allowed,
            "risk_level": self.risk_level.name,
            "reason": self.reason,
            "requires_approval": self.requires_approval,
            "rule": self.rule.to_dict() if self.rule else None,
        }


class ToolPolicy:
    """
    Tool policy enforcement system

    Controls which tools can be executed based on:
    - Policy mode (permissive/restrictive/custom)
    - Allow/deny lists
    - Risk levels
    - Execution limits
    - Approval requirements
    """

    def __init__(self, config: ToolPolicyConfig):
        """Initialize tool policy

        Args:
            config: Policy configuration
        """
        self.config = config
        self.execution_counts: Dict[str, int] = {}
        self.total_executions = 0

        logger.info(
            f"ToolPolicy initialized: mode={config.mode.name}, "
            f"rules={len(config.rules)}, "
            f"approval_enabled={config.approval_enabled}"
        )

    def check_tool_access(
        self,
        tool_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ToolPolicyDecision:
        """Check if a tool can be executed

        Args:
            tool_name: Name of the tool to check
            context: Optional execution context

        Returns:
            Policy decision
        """
        context = context or {}

        # Find matching rule
        matching_rule = self._find_matching_rule(tool_name)

        # Determine risk level
        risk_level = matching_rule.risk_level if matching_rule else self.config.default_risk_level

        # Check based on policy mode
        if self.config.mode == PolicyMode.RESTRICTIVE:
            allowed = self._check_restrictive_mode(tool_name, matching_rule)
            reason = "RESTRICTIVE mode: tool must be in allow list" if not allowed else "Tool is allowed"

        elif self.config.mode == PolicyMode.PERMISSIVE:
            allowed = self._check_permissive_mode(tool_name, matching_rule)
            reason = "Tool is allowed" if allowed else "PERMISSIVE mode: tool is in deny list"

        else:  # CUSTOM mode
            if matching_rule:
                allowed = matching_rule.allowed
                reason = matching_rule.reason or ("Tool is explicitly allowed" if allowed else "Tool is explicitly denied")
            else:
                allowed = True
                reason = "No matching rule, allowing by default"

        # Check execution limits
        if allowed:
            limit_check = self._check_execution_limits(tool_name, matching_rule)
            if not limit_check.allowed:
                allowed = False
                risk_level = limit_check.risk_level
                reason = limit_check.reason

        # Check approval requirement
        requires_approval = False
        if allowed and self.config.approval_enabled:
            if matching_rule and matching_rule.requires_approval:
                requires_approval = True
                reason = f"Tool requires approval: {matching_rule.reason}"
            elif risk_level >= RiskLevel.HIGH:
                requires_approval = True
                reason = f"Tool has {risk_level.name} risk level and requires approval"

        decision = ToolPolicyDecision(
            allowed=allowed,
            risk_level=risk_level,
            reason=reason,
            requires_approval=requires_approval,
            rule=matching_rule,
        )

        logger.debug(
            f"Policy check for '{tool_name}': "
            f"allowed={decision.allowed}, "
            f"risk={risk_level.name}, "
            f"reason={reason}"
        )

        return decision

    def record_execution(self, tool_name: str) -> None:
        """Record a tool execution

        Args:
            tool_name: Name of the tool that was executed
        """
        self.execution_counts[tool_name] = self.execution_counts.get(tool_name, 0) + 1
        self.total_executions += 1

        logger.debug(
            f"Recorded execution: {tool_name} "
            f"(count={self.execution_counts[tool_name]}, "
            f"total={self.total_executions})"
        )

    def reset_counts(self) -> None:
        """Reset execution counts"""
        self.execution_counts.clear()
        self.total_executions = 0
        logger.debug("Reset execution counts")

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics

        Returns:
            Dictionary with execution stats
        """
        return {
            "total_executions": self.total_executions,
            "tool_counts": self.execution_counts.copy(),
            "unique_tools": len(self.execution_counts),
        }

    def _find_matching_rule(self, tool_name: str) -> Optional[ToolPolicyRule]:
        """Find the first matching rule for a tool"""
        for rule in self.config.rules:
            if rule.matches(tool_name):
                return rule
        return None

    def _check_restrictive_mode(
        self,
        tool_name: str,
        rule: Optional[ToolPolicyRule]
    ) -> bool:
        """Check access in RESTRICTIVE mode"""
        # Check explicit deny first
        if rule and not rule.allowed:
            return False

        # Check allow list
        if tool_name in self.config.allow_list:
            return True

        # Check if tool matches allow pattern
        for pattern in self.config.allow_list:
            if self._matches_pattern(tool_name, pattern):
                return True

        # Check rule
        if rule and rule.allowed:
            return True

        # Default deny
        return False

    def _check_permissive_mode(
        self,
        tool_name: str,
        rule: Optional[ToolPolicyRule]
    ) -> bool:
        """Check access in PERMISSIVE mode"""
        # Check explicit deny
        if rule and not rule.allowed:
            return False

        # Check deny list
        if tool_name in self.config.deny_list:
            return False

        # Check if tool matches deny pattern
        for pattern in self.config.deny_list:
            if self._matches_pattern(tool_name, pattern):
                return False

        # Default allow
        return True

    def _check_execution_limits(
        self,
        tool_name: str,
        rule: Optional[ToolPolicyRule]
    ) -> ToolPolicyDecision:
        """Check execution limits"""
        # Check global limit
        if self.config.global_max_executions > 0:
            if self.total_executions >= self.config.global_max_executions:
                return ToolPolicyDecision(
                    allowed=False,
                    risk_level=RiskLevel.MEDIUM,
                    reason=f"Global execution limit reached: {self.total_executions}/{self.config.global_max_executions}",
                    requires_approval=False,
                )

        # Check tool-specific limit
        tool_count = self.execution_counts.get(tool_name, 0)
        tool_limit = rule.max_executions if rule else 0

        if tool_limit > 0 and tool_count >= tool_limit:
            return ToolPolicyDecision(
                allowed=False,
                risk_level=rule.risk_level if rule else RiskLevel.MEDIUM,
                reason=f"Tool execution limit reached: {tool_count}/{tool_limit}",
                requires_approval=False,
            )

        return ToolPolicyDecision(
            allowed=True,
            risk_level=rule.risk_level if rule else RiskLevel.MEDIUM,
            reason="",
            requires_approval=False,
        )

    def _matches_pattern(self, tool_name: str, pattern: str) -> bool:
        """Check if tool name matches a pattern"""
        try:
            regex_pattern = pattern.replace("*", ".*")
            return re.match(f"^{regex_pattern}$", tool_name) is not None
        except re.error:
            return False


def create_default_policy() -> ToolPolicy:
    """Create a default permissive policy

    Returns:
        ToolPolicy with default configuration
    """
    config = ToolPolicyConfig(
        mode=PolicyMode.PERMISSIVE,
        deny_list=[
            # Dangerous shell commands
            "rm -rf",
            "format",
            "shutdown",
        ],
    )

    return ToolPolicy(config)


def create_restrictive_policy(allowed_tools: List[str]) -> ToolPolicy:
    """Create a restrictive policy that only allows specific tools

    Args:
        allowed_tools: List of tool names to allow

    Returns:
        ToolPolicy with restrictive configuration
    """
    config = ToolPolicyConfig(
        mode=PolicyMode.RESTRICTIVE,
        allow_list=allowed_tools,
    )

    return ToolPolicy(config)
