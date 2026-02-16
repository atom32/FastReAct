"""
Execution Approval Demonstration

This example demonstrates the Execution Approval workflow, which provides
user control over dangerous tool operations.

Key features:
- Pause execution before high-risk tools
- Request user approval (Allow/Deny)
- Integration with Tool Policy
- Approval history tracking
- Configurable approval modes
"""

import sys
import io

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from fastreact.core.approval import (
    ApprovalManager,
    ApprovalConfig,
    ApprovalMode,
    ApprovalResponse,
    RiskLevel,
    create_default_approval_manager,
)
from fastreact.core.tool_policy import ToolPolicyDecision


def print_separator(title: str):
    """Print a formatted separator"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def demo_auto_approve_mode():
    """Demonstrate AUTO_APPROVE mode"""
    print_separator("Demo 1: AUTO_APPROVE Mode")

    config = ApprovalConfig(mode=ApprovalMode.AUTO_APPROVE)
    manager = ApprovalManager(config)

    print("Policy: AUTO_APPROVE - All requests automatically approved\n")

    # Create a high-risk decision
    policy_decision = ToolPolicyDecision(
        allowed=True,
        risk_level=RiskLevel.CRITICAL,
        reason="Dangerous operation",
        requires_approval=True,
    )

    decision = manager.request_approval(
        tool_name="dangerous_tool",
        parameters={"action": "delete_all"},
        policy_decision=policy_decision,
    )

    print(f"Tool: dangerous_tool")
    print(f"Risk: {policy_decision.risk_level.name}")
    print(f"Decision: {decision.response.name}")
    print(f"Message: {decision.message}")
    print(f"Allowed: {decision.is_allowed}")


def demo_auto_deny_mode():
    """Demonstrate AUTO_DENY mode"""
    print_separator("Demo 2: AUTO_DENY Mode")

    config = ApprovalConfig(mode=ApprovalMode.AUTO_DENY)
    manager = ApprovalManager(config)

    print("Policy: AUTO_DENY - All requests automatically denied\n")

    policy_decision = ToolPolicyDecision(
        allowed=True,
        risk_level=RiskLevel.LOW,
        reason="Safe operation",
        requires_approval=False,
    )

    decision = manager.request_approval(
        tool_name="safe_tool",
        parameters={"action": "read_file"},
        policy_decision=policy_decision,
    )

    print(f"Tool: safe_tool")
    print(f"Risk: {policy_decision.risk_level.name}")
    print(f"Decision: {decision.response.name}")
    print(f"Message: {decision.message}")
    print(f"Allowed: {decision.is_allowed}")


def demo_ask_high_risk_mode():
    """Demonstrate ASK_HIGH_RISK mode"""
    print_separator("Demo 3: ASK_HIGH_RISK Mode")

    config = ApprovalConfig(mode=ApprovalMode.ASK_HIGH_RISK)
    manager = ApprovalManager(config)

    # Mock callback: allow HIGH, deny CRITICAL
    def mock_callback(request):
        if request.risk_level >= RiskLevel.CRITICAL:
            print(f"→ User denied: {request.tool_name} (CRITICAL risk)")
            return ApprovalResponse.DENY
        else:
            print(f"→ User allowed: {request.tool_name} ({request.risk_level.name} risk)")
            return ApprovalResponse.ALLOW

    manager.set_user_input_callback(mock_callback)

    print("Policy: ASK_HIGH_RISK - Ask only for HIGH/CRITICAL risk tools\n")

    # Test LOW risk (should not ask)
    policy_decision_low = ToolPolicyDecision(
        allowed=True,
        risk_level=RiskLevel.LOW,
        reason="Safe operation",
        requires_approval=False,
    )

    required = manager.check_approval_required("safe_tool", {}, policy_decision_low)
    print(f"safe_tool (LOW): Approval required = {required}")

    # Test HIGH risk (should ask and allow)
    policy_decision_high = ToolPolicyDecision(
        allowed=True,
        risk_level=RiskLevel.HIGH,
        reason="High risk operation",
        requires_approval=True,
    )

    required = manager.check_approval_required("bash", {}, policy_decision_high)
    print(f"bash (HIGH): Approval required = {required}")

    decision = manager.request_approval(
        tool_name="bash",
        parameters={"command": "rm -rf /"},
        policy_decision=policy_decision_high,
    )

    print(f"Final decision: {decision.response.name}")

    # Test CRITICAL risk (should ask and deny)
    policy_decision_critical = ToolPolicyDecision(
        allowed=True,
        risk_level=RiskLevel.CRITICAL,
        reason="Critical operation",
        requires_approval=True,
    )

    required = manager.check_approval_required("format_disk", {}, policy_decision_critical)
    print(f"\nformat_disk (CRITICAL): Approval required = {required}")

    decision = manager.request_approval(
        tool_name="format_disk",
        parameters={"device": "/dev/sda"},
        policy_decision=policy_decision_critical,
    )

    print(f"Final decision: {decision.response.name}")


def demo_always_ask_mode():
    """Demonstrate ALWAYS_ASK mode"""
    print_separator("Demo 4: ALWAYS_ASK Mode")

    config = ApprovalConfig(mode=ApprovalMode.ALWAYS_ASK)
    manager = ApprovalManager(config)

    # Mock callback that allows everything
    def mock_callback(request):
        print(f"→ User approved: {request.tool_name}")
        return ApprovalResponse.ALLOW

    manager.set_user_input_callback(mock_callback)

    print("Policy: ALWAYS_ASK - Ask for EVERY tool execution\n")

    tools = [
        ("read_file", {"path": "test.txt"}, RiskLevel.LOW),
        ("write_file", {"path": "test.txt"}, RiskLevel.MEDIUM),
        ("bash", {"command": "ls"}, RiskLevel.HIGH),
    ]

    for tool_name, params, risk in tools:
        policy_decision = ToolPolicyDecision(
            allowed=True,
            risk_level=risk,
            reason=f"{risk.name} risk operation",
            requires_approval=True,
        )

        required = manager.check_approval_required(tool_name, params, policy_decision)
        print(f"{tool_name}: Approval required = {required}")

        decision = manager.request_approval(tool_name, params, policy_decision)
        print(f"Decision: {decision.response.name}\n")


def demo_approval_lists():
    """Demonstrate auto-approve and auto-deny lists"""
    print_separator("Demo 5: Auto-Approve/Deny Lists")

    config = ApprovalConfig(
        mode=ApprovalMode.ALWAYS_ASK,
        auto_approve_list=["safe_read", "safe_write"],
        auto_deny_list=["dangerous_delete", "format_*"],
    )
    manager = ApprovalManager(config)

    print("Policy: ALWAYS_ASK with custom lists")
    print(f"Auto-approve: {config.auto_approve_list}")
    print(f"Auto-deny: {config.auto_deny_list}\n")

    policy_decision = ToolPolicyDecision(
        allowed=True,
        risk_level=RiskLevel.HIGH,
        reason="High risk",
        requires_approval=True,
    )

    # Test auto-approve list
    tools_to_test = [
        ("safe_read", "In auto-approve list"),
        ("safe_write", "In auto-approve list"),
        ("format_disk", "Matches auto-deny pattern"),
        ("bash", "Not in any list"),
    ]

    for tool, description in tools_to_test:
        required = manager.check_approval_required(tool, {}, policy_decision)
        status = "REQUIRED" if required else "NOT REQUIRED"
        print(f"{tool:15s} ({description}): {status}")


def demo_approval_history():
    """Demonstrate approval history tracking"""
    print_separator("Demo 6: Approval History")

    config = ApprovalConfig(mode=ApprovalMode.ASK_HIGH_RISK)
    manager = ApprovalManager(config)

    # Mock callback
    def mock_callback(request):
        # Allow based on risk
        if request.risk_level >= RiskLevel.CRITICAL:
            return ApprovalResponse.DENY
        return ApprovalResponse.ALLOW

    manager.set_user_input_callback(mock_callback)

    print("Making several approval requests...\n")

    # Create various decisions
    tools = [
        ("bash", {"command": "ls"}, RiskLevel.HIGH),
        ("rm", {"path": "/tmp/file"}, RiskLevel.CRITICAL),
        ("grep", {"pattern": "test"}, RiskLevel.HIGH),
        ("cat", {"file": "test.txt"}, RiskLevel.HIGH),
    ]

    for tool, params, risk in tools:
        policy_decision = ToolPolicyDecision(
            allowed=True,
            risk_level=risk,
            reason=f"{risk.name} risk",
            requires_approval=True,
        )

        manager.request_approval(tool, params, policy_decision)

    # Show statistics
    stats = manager.get_statistics()

    print("Approval Statistics:")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Allowed: {stats['allowed']}")
    print(f"  Denied: {stats['denied']}")
    print(f"  Pending: {stats['pending']}")
    print(f"  Allow rate: {stats['allow_rate']:.1%}")

    # Show history
    print(f"\nRecent History (last {stats['total_requests']}):")
    for i, decision in enumerate(manager.get_history(), 1):
        print(f"  {i}. {decision.request_id}: {decision.response.name}")


def demo_config_from_dict():
    """Demonstrate loading configuration from dictionary"""
    print_separator("Demo 7: Configuration from Dictionary")

    config_dict = {
        "mode": "ask_high_risk",
        "default_timeout": 120,
        "max_pending_requests": 20,
        "enable_history": True,
        "max_history_size": 200,
        "auto_approve_list": ["read_*", "list_*"],
        "auto_deny_list": ["delete_*", "format_*"],
        "risk_threshold": "high",
    }

    config = ApprovalConfig.from_dict(config_dict)

    print("Configuration loaded from dictionary:")
    print(f"  Mode: {config.mode.name}")
    print(f"  Timeout: {config.default_timeout}s")
    print(f"  Max pending: {config.max_pending_requests}")
    print(f"  History size: {config.max_history_size}")
    print(f"  Auto-approve: {config.auto_approve_list}")
    print(f"  Auto-deny: {config.auto_deny_list}")
    print(f"  Risk threshold: {config.risk_threshold.name}")


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 60)
    print("  Execution Approval Feature Demonstration")
    print("=" * 60)

    try:
        demo_auto_approve_mode()
        demo_auto_deny_mode()
        demo_ask_high_risk_mode()
        demo_always_ask_mode()
        demo_approval_lists()
        demo_approval_history()
        demo_config_from_dict()

        print_separator("All Demos Complete")
        print("Execution Approval successfully provides user control!")
        print("\nKey benefits:")
        print("  → Safety: Prevent accidental dangerous operations")
        print("  → Control: User decides what executes")
        print("  → Flexibility: Multiple approval modes")
        print("  → Audit: Complete history of all decisions")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
