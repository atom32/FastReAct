"""
Tool Policy Demonstration

This example demonstrates the Tool Policy feature, which provides security
control for tool usage with Allow/Deny lists, risk levels, and usage profiles.

Key features:
- Allow/Deny lists for tool access control
- Tool usage profiles (restrictive, permissive, custom)
- Risk levels (low, medium, high, critical)
- Execution limits
- Approval workflow
"""

import sys
import io

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from fastreact.core.tool_policy import (
    ToolPolicy,
    ToolPolicyConfig,
    ToolPolicyRule,
    RiskLevel,
    PolicyMode,
    create_default_policy,
    create_restrictive_policy,
)


def print_separator(title: str):
    """Print a formatted separator"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def demo_permissive_mode():
    """Demonstrate permissive policy mode"""
    print_separator("Demo 1: Permissive Mode")

    # Create permissive policy with deny list
    config = ToolPolicyConfig(
        mode=PolicyMode.PERMISSIVE,
        deny_list=["dangerous_*", "rm_*", "format*"],
    )
    policy = ToolPolicy(config)

    print("Policy: PERMISSIVE mode with deny list")
    print(f"Deny list: {config.deny_list}\n")

    test_tools = [
        "bash",
        "ls",
        "dangerous_tool",
        "rm_file",
        "format_disk",
        "grep",
    ]

    for tool in test_tools:
        decision = policy.check_tool_access(tool)
        status = "[OK] ALLOWED" if decision.allowed else "[ERROR] DENIED"
        print(f"{status}: {tool:20s} | Risk: {decision.risk_level.name:8s} | {decision.reason}")


def demo_restrictive_mode():
    """Demonstrate restrictive policy mode"""
    print_separator("Demo 2: Restrictive Mode")

    # Create restrictive policy with allow list
    allowed_tools = ["bash", "ls", "grep", "cat", "find"]
    policy = create_restrictive_policy(allowed_tools)

    print(f"Policy: RESTRICTIVE mode with allow list")
    print(f"Allow list: {allowed_tools}\n")

    test_tools = [
        "bash",
        "ls",
        "grep",
        "rm",  # Not in allow list
        "python",  # Not in allow list
        "cat",
    ]

    for tool in test_tools:
        decision = policy.check_tool_access(tool)
        status = "[OK] ALLOWED" if decision.allowed else "[ERROR] DENIED"
        print(f"{status}: {tool:20s} | Risk: {decision.risk_level.name:8s} | {decision.reason}")


def demo_custom_rules():
    """Demonstrate custom policy with rules"""
    print_separator("Demo 3: Custom Policy with Rules")

    config = ToolPolicyConfig(
        mode=PolicyMode.CUSTOM,
        rules=[
            ToolPolicyRule(
                pattern="bash*",
                allowed=True,
                risk_level=RiskLevel.HIGH,
                reason="Shell access requires caution"
            ),
            ToolPolicyRule(
                pattern="*_read",
                allowed=True,
                risk_level=RiskLevel.LOW,
                reason="Read operations are safe"
            ),
            ToolPolicyRule(
                pattern="*_write",
                allowed=True,
                risk_level=RiskLevel.MEDIUM,
                reason="Write operations need monitoring"
            ),
            ToolPolicyRule(
                pattern="*_delete",
                allowed=False,
                risk_level=RiskLevel.CRITICAL,
                reason="Delete operations are blocked"
            ),
            ToolPolicyRule(
                pattern="*admin*",
                allowed=False,
                risk_level=RiskLevel.CRITICAL,
                requires_approval=True,
                reason="Admin operations require explicit approval"
            ),
        ],
    )
    policy = ToolPolicy(config)

    print("Policy: CUSTOM mode with rules")
    print(f"Rules: {len(config.rules)}\n")

    test_tools = [
        "bash_exec",
        "file_read",
        "file_write",
        "file_delete",
        "admin_panel",
        "other_tool",
    ]

    for tool in test_tools:
        decision = policy.check_tool_access(tool)
        status = "[OK] ALLOWED" if decision.allowed else "[ERROR] DENIED"
        approval = " [LOCK] APPROVAL" if decision.requires_approval else ""
        print(f"{status}{approval}: {tool:20s} | Risk: {decision.risk_level.name:8s}")
        if decision.reason:
            print(f"                      Reason: {decision.reason}")


def demo_execution_limits():
    """Demonstrate execution limit enforcement"""
    print_separator("Demo 4: Execution Limits")

    config = ToolPolicyConfig(
        mode=PolicyMode.PERMISSIVE,
        rules=[
            ToolPolicyRule(
                pattern="limited_tool",
                max_executions=3,
                risk_level=RiskLevel.MEDIUM,
                reason="Tool has usage limit"
            ),
        ],
        global_max_executions=10,
    )
    policy = ToolPolicy(config)

    print("Policy: PERMISSIVE with execution limits")
    print("Global limit: 10 executions")
    print("Tool limit: limited_tool → 3 executions\n")

    # Test tool-specific limit
    print("Testing tool-specific limit:")
    for i in range(5):
        decision = policy.check_tool_access("limited_tool")
        status = "[OK] ALLOWED" if decision.allowed else "[ERROR] DENIED (limit reached)"
        print(f"  Execution {i+1}: {status}")
        if decision.allowed:
            policy.record_execution("limited_tool")

    # Reset and test global limit
    policy.reset_counts()
    print("\nTesting global limit:")

    # Execute 9 times (should work)
    for i in range(9):
        policy.record_execution(f"tool_{i}")

    decision = policy.check_tool_access("any_tool")
    status = "[OK] ALLOWED" if decision.allowed else "[ERROR] DENIED"
    print(f"  After 9 executions: {status}")

    policy.record_execution("tool_9")

    decision = policy.check_tool_access("any_tool")
    status = "[OK] ALLOWED" if decision.allowed else "[ERROR] DENIED (limit reached)"
    print(f"  After 10 executions: {status}")


def demo_approval_workflow():
    """Demonstrate approval workflow for high-risk tools"""
    print_separator("Demo 5: Approval Workflow")

    config = ToolPolicyConfig(
        mode=PolicyMode.PERMISSIVE,
        approval_enabled=True,
        rules=[
            ToolPolicyRule(
                pattern="bash*",
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
                reason="Shell commands are high-risk"
            ),
            ToolPolicyRule(
                pattern="safe_*",
                risk_level=RiskLevel.LOW,
            ),
        ],
    )
    policy = ToolPolicy(config)

    print("Policy: PERMISSIVE with approval enabled")
    print("High-risk tools (HIGH/CRITICAL) require approval\n")

    test_tools = [
        ("bash_exec", "Shell execution"),
        ("safe_read", "Safe operation"),
        ("dangerous_delete", "Dangerous operation"),
    ]

    for tool, description in test_tools:
        decision = policy.check_tool_access(tool)

        if decision.requires_approval:
            print(f"[LOCK] {tool:20s} ({description})")
            print(f"   Risk Level: {decision.risk_level.name}")
            print(f"   Status: PENDING APPROVAL")
            print(f"   Reason: {decision.reason}")
        elif decision.allowed:
            print(f"[OK] {tool:20s} ({description})")
            print(f"   Risk Level: {decision.risk_level.name}")
            print(f"   Status: ALLOWED (no approval needed)")
        else:
            print(f"[ERROR] {tool:20s} ({description})")
            print(f"   Status: DENIED")
            print(f"   Reason: {decision.reason}")
        print()


def demo_execution_statistics():
    """Demonstrate execution statistics tracking"""
    print_separator("Demo 6: Execution Statistics")

    policy = create_default_policy()

    print("Recording tool executions...\n")

    # Simulate some executions
    executions = [
        ("bash", 5),
        ("ls", 3),
        ("grep", 2),
        ("cat", 1),
    ]

    for tool, count in executions:
        for _ in range(count):
            policy.record_execution(tool)
        print(f"  Executed {tool} {count} time(s)")

    print("\nExecution Statistics:")
    stats = policy.get_execution_stats()

    print(f"  Total executions: {stats['total_executions']}")
    print(f"  Unique tools: {stats['unique_tools']}")
    print(f"  Tool counts:")
    for tool, count in sorted(stats['tool_counts'].items(), key=lambda x: -x[1]):
        print(f"    - {tool}: {count}")


def demo_config_from_dict():
    """Demonstrate loading configuration from dictionary"""
    print_separator("Demo 7: Configuration from Dictionary")

    config_dict = {
        "mode": "custom",
        "default_risk_level": "medium",
        "approval_enabled": True,
        "rules": [
            {
                "pattern": "bash*",
                "risk_level": "high",
                "allowed": True,
                "max_executions": 10,
                "requires_approval": True,
                "reason": "Shell access is powerful",
            },
            {
                "pattern": "*_delete",
                "risk_level": "critical",
                "allowed": False,
                "reason": "Delete operations are blocked",
            },
        ],
        "allow_list": ["bash", "ls", "cat"],
        "deny_list": ["rm", "format"],
    }

    config = ToolPolicyConfig.from_dict(config_dict)

    print("Configuration loaded from dictionary:")
    print(f"  Mode: {config.mode.name}")
    print(f"  Default risk level: {config.default_risk_level.name}")
    print(f"  Approval enabled: {config.approval_enabled}")
    print(f"  Rules: {len(config.rules)}")
    print(f"  Allow list: {config.allow_list}")
    print(f"  Deny list: {config.deny_list}")

    # Create policy and test
    policy = ToolPolicy(config)

    print("\nTesting with loaded configuration:")
    decision = policy.check_tool_access("bash_exec")
    print(f"  bash_exec: {'[OK] ALLOWED' if decision.allowed else '[ERROR] DENIED'} | Approval: {decision.requires_approval}")

    decision = policy.check_tool_access("file_delete")
    print(f"  file_delete: {'[OK] ALLOWED' if decision.allowed else '[ERROR] DENIED'}")


def main():
    """Run all demonstrations"""
    print("\n" + "=" * 60)
    print("  Tool Policy Feature Demonstration")
    print("=" * 60)

    try:
        demo_permissive_mode()
        demo_restrictive_mode()
        demo_custom_rules()
        demo_execution_limits()
        demo_approval_workflow()
        demo_execution_statistics()
        demo_config_from_dict()

        print_separator("All Demos Complete")
        print("Tool Policy successfully provides security control for tools!")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
