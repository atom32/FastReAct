"""
Sprint 3.5: 工具策略配置

为所有工具配置正确的 risk_level 和 approval 策略。
这个配置会被 ToolPolicy 和 Approval 系统使用。

策略设计原则：
- READ_ONLY 工具（ls, grep, view）: 自动批准
- LOW_RISK 工具（write 新建）: 显示提示但默认允许
- HIGH_RISK 工具（edit 修改, bash 执行, delete 删除）: 强制确认
"""

from fastreact.core.tool_policy import (
    ToolPolicyConfig,
    ToolPolicyRule,
    RiskLevel,
    PolicyMode,
)

# ============================================================================
# Sprint 3.5: 工具风险分级配置
# ============================================================================

SPRINT35_POLICY_CONFIG = ToolPolicyConfig(
    mode=PolicyMode.PERMISSIVE,
    approval_enabled=True,  # 启用审批系统
    default_risk_level=RiskLevel.MEDIUM,
    rules=[
        # ========================================================================
        # 侦察工具（READ_ONLY）- 自动批准，无需确认
        # ========================================================================
        ToolPolicyRule(
            pattern="ls_repo",
            risk_level=RiskLevel.LOW,
            allowed=True,
            requires_approval=False,
            reason="查看项目结构，安全操作"
        ),
        ToolPolicyRule(
            pattern="cd_repo",
            risk_level=RiskLevel.LOW,
            allowed=True,
            requires_approval=False,
            reason="切换工作目录，安全操作"
        ),
        ToolPolicyRule(
            pattern="refresh_repo",
            risk_level=RiskLevel.LOW,
            allowed=True,
            requires_approval=False,
            reason="刷新目录结构，安全操作"
        ),
        ToolPolicyRule(
            pattern="view_file",
            risk_level=RiskLevel.LOW,
            allowed=True,
            requires_approval=False,
            reason="只读文件查看，安全操作"
        ),
        ToolPolicyRule(
            pattern="grep_code",
            risk_level=RiskLevel.LOW,
            allowed=True,
            requires_approval=False,
            reason="代码搜索，只读操作"
        ),
        ToolPolicyRule(
            pattern="read_file",
            risk_level=RiskLevel.LOW,
            allowed=True,
            requires_approval=False,
            reason="只读文件查看，安全操作"
        ),
        ToolPolicyRule(
            pattern="smart_read",
            risk_level=RiskLevel.LOW,
            allowed=True,
            requires_approval=False,
            reason="智能文件读取，只读操作"
        ),
        ToolPolicyRule(
            pattern="search",
            risk_level=RiskLevel.LOW,
            allowed=True,
            requires_approval=False,
            reason="网络搜索，安全操作"
        ),
        ToolPolicyRule(
            pattern="calculator",
            risk_level=RiskLevel.LOW,
            allowed=True,
            requires_approval=False,
            reason="数学计算，安全操作"
        ),
        ToolPolicyRule(
            pattern="datetime",
            risk_level=RiskLevel.LOW,
            allowed=True,
            requires_approval=False,
            reason="获取时间信息，安全操作"
        ),

        # ========================================================================
        # 建设工具（LOW_RISK）- 显示提示，默认允许
        # ========================================================================
        ToolPolicyRule(
            pattern="write_file",
            risk_level=RiskLevel.MEDIUM,
            allowed=True,
            requires_approval=True,  # 需要确认（新建/覆盖文件）
            reason="写入文件，可能覆盖现有内容"
        ),
        ToolPolicyRule(
            pattern="create_*",
            risk_level=RiskLevel.MEDIUM,
            allowed=True,
            requires_approval=True,
            reason="创建新资源"
        ),

        # ========================================================================
        # 修改工具（HIGH_RISK）- 强制确认
        # ========================================================================
        ToolPolicyRule(
            pattern="edit_file",
            risk_level=RiskLevel.HIGH,
            allowed=True,
            requires_approval=True,
            reason="修改文件内容，可能破坏代码"
        ),
        ToolPolicyRule(
            pattern="bash",
            risk_level=RiskLevel.HIGH,
            allowed=True,
            requires_approval=True,
            reason="执行 Shell 命令，可能影响系统"
        ),
        ToolPolicyRule(
            pattern="shell*",
            risk_level=RiskLevel.HIGH,
            allowed=True,
            requires_approval=True,
            reason="执行系统命令，高风险操作"
        ),

        # ========================================================================
        # 危险工具（CRITICAL）- 最强确认
        # ========================================================================
        ToolPolicyRule(
            pattern="delete_*",
            risk_level=RiskLevel.CRITICAL,
            allowed=True,
            requires_approval=True,
            reason="删除操作，不可恢复"
        ),
        ToolPolicyRule(
            pattern="remove_*",
            risk_level=RiskLevel.CRITICAL,
            allowed=True,
            requires_approval=True,
            reason="删除操作，不可恢复"
        ),
        ToolPolicyRule(
            pattern="rm",
            risk_level=RiskLevel.CRITICAL,
            allowed=True,
            requires_approval=True,
            reason="删除操作，不可恢复"
        ),

        # ========================================================================
        # 其他工具 - 默认中等风险
        # ========================================================================
        ToolPolicyRule(
            pattern="http",
            risk_level=RiskLevel.MEDIUM,
            allowed=True,
            requires_approval=False,
            reason="HTTP 请求，中等风险"
        ),
        ToolPolicyRule(
            pattern="code_exec",
            risk_level=RiskLevel.HIGH,
            allowed=True,
            requires_approval=True,
            reason="代码执行，高风险操作"
        ),
    ],
)


def get_sprint35_policy() -> ToolPolicyConfig:
    """
    获取 Sprint 3.5 的工具策略配置

    Returns:
        ToolPolicyConfig 实例
    """
    return SPRINT35_POLICY_CONFIG


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    import json

    # 导出配置为 JSON（用于调试）
    config_dict = SPRINT35_POLICY_CONFIG.to_dict()
    print(json.dumps(config_dict, indent=2))

    # 打印工具分级统计
    risk_counts = {}
    for rule in SPRINT35_POLICY_CONFIG.rules:
        level = rule.risk_level.name
        risk_counts[level] = risk_counts.get(level, 0) + 1

    print("\n[工具分级统计]")
    for level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
        count = risk_counts.get(level, 0)
        print(f"  {level}: {count} tools")
