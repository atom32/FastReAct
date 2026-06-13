"""
Safety Policy - Interactive guardrails for FastReAct Nano v2.0

Implements Human-in-the-loop for dangerous operations:
- Traffic light system (Green/Yellow/Red)
- Configurable safety policies
- User confirmation mechanism
- Audit logging
"""

import re
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable, Any, Dict, List
from enum import Enum
from datetime import datetime

from fastreact.core.time import utc_now


class SafetyLevel(Enum):
    """Safety classification for operations"""
    SAFE = "safe"           # Green: Auto-allow
    CAUTION = "caution"     # Yellow: Log and allow
    DANGER = "danger"       # Red: Require confirmation
    FORBIDDEN = "forbidden" # Black: Never allow


@dataclass
class SafetyDecision:
    """Result of safety check"""
    level: SafetyLevel
    reason: str = ""
    pattern_matched: Optional[str] = None
    requires_confirmation: bool = False
    policy_scope: Optional[str] = None
    policy_action: Optional[str] = None
    policy_matched: bool = False

    @property
    def should_allow(self) -> bool:
        """Check if operation should be allowed"""
        return self.level != SafetyLevel.FORBIDDEN

    @property
    def should_ask(self) -> bool:
        """Check if operation requires user confirmation"""
        return self.level == SafetyLevel.DANGER


@dataclass
class AuditLog:
    """Audit log entry for safety events"""
    timestamp: datetime = field(default_factory=utc_now)
    tool_name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    decision: SafetyDecision = None
    user_approved: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "tool_name": self.tool_name,
            "args": self.args,
            "decision_level": self.decision.level.value if self.decision else None,
            "decision_reason": self.decision.reason if self.decision else None,
            "user_approved": self.user_approved,
        }


class SafetyPolicy:
    """
    Safety policy for tool execution

    Implements traffic light system:
    - Green (Safe): Auto-allow for read-only operations
    - Yellow (Caution): Log but allow for modifications
    - Red (Danger): Require confirmation for destructive operations
    - Black (Forbidden): Never allow certain operations
    """

    # Dangerous command patterns (Red)
    DANGEROUS_PATTERNS = [
        r"\brm\s+",           # Remove files/directories
        r"\bmv\s+",           # Move files
        r"\brmdir\s+",        # Remove directory
        r"\bdelete\s+",       # Windows delete
        r"\bdel\s+",          # Windows delete
        r">\s*",              # File overwrite (redirect)
        r"\|.*rm\s+",         # Piped rm commands
        r"\bsudo\s+.*rm\b",   # sudo with rm
        r"\bchmod\s+",        # Change permissions (risky)
        r"\bchown\s+",        # Change owner (risky)
        r":\s*>$",            # Vim-style overwrite
    ]

    # Forbidden command patterns (Black)
    FORBIDDEN_PATTERNS = [
        r"\brm\s+-rf\s+/",    # rm -rf / (system destruction)
        r"\brm\s+-rf\s+\.",   # rm -rf . (current dir destruction)
        r"\bformat\s+",       # Disk formatting
        r"\bmkfs\s+",         # Filesystem creation
        r"\bdd\s+",           # Disk destroy
        r"\bshutdown\s+",     # System shutdown
    ]

    # Safe command patterns (Green)
    SAFE_PATTERNS = [
        r"\bls\b",            # List files
        r"\bcat\b",           # Read files
        r"\bhead\b",          # Read file start
        r"\btail\b",          # Read file end
        r"\bgrep\b",          # Search files
        r"\bfind\b",          # Find files (read-only)
        r"\bpwd\b",           # Print working directory
        r"\becho\b",          # Echo (when not redirecting)
        r"\bcd\b",            # Change directory
        r"\bmkdir\b",         # Create directory (safe)
        r"\bgit\s+(status|log|diff|branch|show)",  # Git read-only
    ]

    # Safe tools (Green)
    SAFE_TOOLS = {"read_file"}

    # Caution tools (Yellow)
    CAUTION_TOOLS = {"write_file", "edit_file"}

    # Danger tools (Red)
    DANGER_TOOLS = set()  # Could add delete_file if implemented

    def __init__(
        self,
        strict_mode: bool = False,
        allow_all: bool = False,
        custom_patterns: Optional[Dict[str, List[str]]] = None,
        policy_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize safety policy

        Args:
            strict_mode: If True, all modifications require confirmation
            allow_all: If True, disable all safety checks (DANGEROUS!)
            custom_patterns: Custom patterns for each safety level
        """
        self._strict_mode = strict_mode
        self._allow_all = allow_all
        self._custom_patterns = custom_patterns or {}
        self._policy_config = policy_config or {}
        self._audit_log: List[AuditLog] = []

        # Compile regex patterns
        self._dangerous_regex = [re.compile(p) for p in self.DANGEROUS_PATTERNS]
        self._forbidden_regex = [re.compile(p) for p in self.FORBIDDEN_PATTERNS]
        self._safe_regex = [re.compile(p) for p in self.SAFE_PATTERNS]

    def check(
        self,
        tool_name: str,
        args: Dict[str, Any],
        user_key: Optional[str] = None,
        tenant_key: Optional[str] = None,
    ) -> SafetyDecision:
        """
        Check if tool execution is safe

        Args:
            tool_name: Name of the tool being called
            args: Tool arguments

        Returns:
            SafetyDecision with classification
        """
        # Emergency override
        if self._allow_all:
            return SafetyDecision(
                level=SafetyLevel.SAFE,
                reason="Safety checks disabled (allow_all=True)",
            )

        # Check for forbidden patterns first (Black)
        if tool_name == "exec":
            command = args.get("command", "")
            for pattern in self._forbidden_regex:
                if pattern.search(command):
                    return SafetyDecision(
                        level=SafetyLevel.FORBIDDEN,
                        reason="Command matches forbidden pattern",
                        pattern_matched=pattern.pattern,
                    )

        policy_decision = self._check_config_policy(
            tool_name,
            user_key=user_key,
            tenant_key=tenant_key,
        )
        if policy_decision:
            return policy_decision

        # Check strict mode
        if self._strict_mode:
            if tool_name in self.CAUTION_TOOLS or tool_name in self.DANGER_TOOLS:
                return SafetyDecision(
                    level=SafetyLevel.DANGER,
                    reason="Strict mode: all modifications require confirmation",
                    requires_confirmation=True,
                )

        # Check safe tools (Green)
        if tool_name in self.SAFE_TOOLS:
            return SafetyDecision(
                level=SafetyLevel.SAFE,
                reason="Tool is in safe whitelist",
            )

        # Check caution tools (Yellow)
        if tool_name in self.CAUTION_TOOLS:
            return SafetyDecision(
                level=SafetyLevel.CAUTION,
                reason="Tool modifies files (logged but allowed)",
            )

        # Check exec tool commands
        if tool_name == "exec":
            command = args.get("command", "")

            # Check safe patterns (Green)
            for pattern in self._safe_regex:
                if pattern.search(command):
                    return SafetyDecision(
                        level=SafetyLevel.SAFE,
                        reason="Command matches safe pattern",
                        pattern_matched=pattern.pattern,
                    )

            # Check dangerous patterns (Red)
            for pattern in self._dangerous_regex:
                if pattern.search(command):
                    return SafetyDecision(
                        level=SafetyLevel.DANGER,
                        reason="Command matches dangerous pattern",
                        pattern_matched=pattern.pattern,
                        requires_confirmation=True,
                    )

            # Default to caution for unknown commands
            return SafetyDecision(
                level=SafetyLevel.CAUTION,
                reason="Unknown command (logged but allowed)",
            )

        # Default: caution
        return SafetyDecision(
            level=SafetyLevel.CAUTION,
            reason="Unclassified tool (logged but allowed)",
        )

    def _check_config_policy(
        self,
        tool_name: str,
        user_key: Optional[str] = None,
        tenant_key: Optional[str] = None,
    ) -> Optional[SafetyDecision]:
        tenant = tenant_key or (user_key.split(":", 1)[0] if user_key and ":" in user_key else None)
        candidates: list[tuple[str, Any]] = []
        user_rules = self._policy_config.get("user_rules") or {}
        tenant_rules = self._policy_config.get("tenant_rules") or {}
        tool_rules = self._policy_config.get("tool_rules") or {}

        if user_key and user_key in user_rules:
            candidates.append((f"user:{user_key}", user_rules[user_key]))
        if tenant and tenant in tenant_rules:
            candidates.append((f"tenant:{tenant}", tenant_rules[tenant]))
        if tool_name in tool_rules:
            candidates.append((f"tool:{tool_name}", tool_rules[tool_name]))
        if "*" in tool_rules:
            candidates.append(("tool:*", tool_rules["*"]))

        for scope, rule in candidates:
            action = self._rule_action(rule, tool_name)
            if action:
                return self._decision_from_action(action, scope)

        default_action = self._policy_config.get("default_action")
        if isinstance(default_action, str) and default_action.strip():
            return self._decision_from_action(default_action, "default")
        return None

    @staticmethod
    def _rule_action(rule: Any, tool_name: str) -> Optional[str]:
        if isinstance(rule, str):
            return rule
        if not isinstance(rule, dict):
            return None
        tools = rule.get("tools") or rule.get("tool_rules") or {}
        if isinstance(tools, dict):
            value = tools.get(tool_name) or tools.get("*")
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                action = value.get("action")
                return action if isinstance(action, str) else None
        action = rule.get("action") or rule.get("default_action")
        return action if isinstance(action, str) else None

    @staticmethod
    def _decision_from_action(action: str, scope: str) -> SafetyDecision:
        normalized = action.strip().lower().replace("-", "_")
        if normalized in {"allow", "safe"}:
            return SafetyDecision(
                level=SafetyLevel.SAFE,
                reason=f"Policy {scope} allows tool",
                policy_scope=scope,
                policy_action="allow",
                policy_matched=True,
            )
        if normalized in {"caution", "log"}:
            return SafetyDecision(
                level=SafetyLevel.CAUTION,
                reason=f"Policy {scope} allows with caution",
                policy_scope=scope,
                policy_action="caution",
                policy_matched=True,
            )
        if normalized in {"require_approval", "approval", "danger"}:
            return SafetyDecision(
                level=SafetyLevel.DANGER,
                reason=f"Policy {scope} requires approval",
                requires_confirmation=True,
                policy_scope=scope,
                policy_action="require_approval",
                policy_matched=True,
            )
        if normalized in {"deny", "forbid", "forbidden", "block"}:
            return SafetyDecision(
                level=SafetyLevel.FORBIDDEN,
                reason=f"Policy {scope} denies tool",
                policy_scope=scope,
                policy_action="deny",
                policy_matched=True,
            )
        return SafetyDecision(
            level=SafetyLevel.CAUTION,
            reason=f"Policy {scope} has unknown action",
            policy_scope=scope,
            policy_action=normalized,
            policy_matched=True,
        )

    def log(
        self,
        tool_name: str,
        args: Dict[str, Any],
        decision: SafetyDecision,
        user_approved: Optional[bool] = None,
    ) -> None:
        """
        Log safety event to audit log

        Args:
            tool_name: Tool that was called
            args: Tool arguments
            decision: Safety decision made
            user_approved: Whether user approved (for dangerous operations)
        """
        entry = AuditLog(
            tool_name=tool_name,
            args=args,
            decision=decision,
            user_approved=user_approved,
        )
        self._audit_log.append(entry)

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent audit log entries

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries as dictionaries
        """
        return [entry.to_dict() for entry in self._audit_log[-limit:]]

    def clear_audit_log(self) -> None:
        """Clear audit log"""
        self._audit_log = []


class ConfirmationCallback:
    """
    Base class for confirmation callbacks

    Subclasses implement actual user interaction (CLI, HTTP, WebSocket, etc.)
    """

    async def request_confirmation(
        self,
        tool_name: str,
        args: Dict[str, Any],
        reason: str,
    ) -> bool:
        """
        Request user confirmation for dangerous operation

        Args:
            tool_name: Tool being called
            args: Tool arguments
            reason: Why this operation requires confirmation

        Returns:
            True if user approved, False otherwise
        """
        raise NotImplementedError("Subclasses must implement request_confirmation")


class CLIConfirmationCallback(ConfirmationCallback):
    """
    CLI-based confirmation callback

    Asks user directly on stdin/stdout
    """

    async def request_confirmation(
        self,
        tool_name: str,
        args: Dict[str, Any],
        reason: str,
    ) -> bool:
        """
        Request confirmation via CLI

        Returns:
            True if user approves (types 'y' or 'yes')
        """
        # Format command display
        if tool_name == "exec":
            cmd_display = f'exec("{args.get("command", "")}")'
        else:
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            cmd_display = f"{tool_name}({args_str})"

        print(f"\n{'='*70}")
        print(f"[SECURITY ALERT] Dangerous operation detected")
        print(f"{'='*70}")
        print(f"Operation: {cmd_display}")
        print(f"Reason: {reason}")
        print(f"{'='*70}")

        # Get user input
        while True:
            try:
                response = input("Allow this operation? [y/N]: ").strip().lower()
                if response in ['y', 'yes']:
                    print("[APPROVED] Operation allowed by user")
                    return True
                elif response in ['n', 'no', '']:
                    print("[DENIED] Operation blocked by user")
                    return False
                else:
                    print("[Invalid] Please enter 'y' or 'n'")
            except (EOFError, KeyboardInterrupt):
                print("\n[INTERRUPTED] Operation blocked by user")
                return False


class AlwaysAllowCallback(ConfirmationCallback):
    """
    Testing callback that always approves

    WARNING: Only for automated testing!
    """

    async def request_confirmation(
        self,
        tool_name: str,
        args: Dict[str, Any],
        reason: str,
    ) -> bool:
        """Always return True (auto-approve)"""
        return True


class AlwaysDenyCallback(ConfirmationCallback):
    """
    Testing callback that always denies

    For testing safety mechanisms
    """

    async def request_confirmation(
        self,
        tool_name: str,
        args: Dict[str, Any],
        reason: str,
    ) -> bool:
        """Always return False (auto-deny)"""
        return False


__all__ = [
    "SafetyLevel",
    "SafetyDecision",
    "AuditLog",
    "SafetyPolicy",
    "ConfirmationCallback",
    "CLIConfirmationCallback",
    "AlwaysAllowCallback",
    "AlwaysDenyCallback",
]
