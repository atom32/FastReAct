"""
CLI 审批流程交互界面

提供命令行交互式工具审批功能，支持：
- 交互式批准/拒绝
- 自动审批规则
- 审批历史记录
- 批准规则配置
"""

import sys
from typing import Optional, Callable, Dict, Any
from enum import Enum

import click

from fastreact.core.approval import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalManager,
    ApprovalConfig,
    ApprovalMode,
)


class ApprovalDecision(Enum):
    """用户决策"""
    ALLOW = "allow"
    DENY = "deny"
    SKIP = "skip"
    ALLOW_ALL = "allow_all"
    DENY_ALL = "deny_all"


class CLIApprovalHandler:
    """
    CLI 审批处理器

    提供交互式命令行审批界面。
    """

    def __init__(
        self,
        default_decision: ApprovalDecision = ApprovalDecision.ALLOW,
        show_details: bool = True,
        timeout: int = 300,
    ):
        """
        初始化 CLI 审批处理器

        Args:
            default_decision: 默认决策
            show_details: 是否显示详细信息
            timeout: 默认超时时间（秒）
        """
        self.default_decision = default_decision
        self.show_details = show_details
        self.timeout = timeout

        # 自动审批规则
        self._auto_allow_patterns: list = []
        self._auto_deny_patterns: list = []

        # 统计
        self._stats = {
            "total": 0,
            "allowed": 0,
            "denied": 0,
            "skipped": 0,
        }

    def add_auto_allow_pattern(self, pattern: str) -> None:
        """添加自动允许规则（工具名称模式）"""
        self._auto_allow_patterns.append(pattern)

    def add_auto_deny_pattern(self, pattern: str) -> None:
        """添加自动拒绝规则（工具名称模式）"""
        self._auto_deny_patterns.append(pattern)

    def clear_rules(self) -> None:
        """清除所有规则"""
        self._auto_allow_patterns.clear()
        self._auto_deny_patterns.clear()

    def handle_request(self, request: ApprovalRequest) -> ApprovalResponse:
        """
        处理审批请求

        Args:
            request: 审批请求

        Returns:
            审批响应
        """
        self._stats["total"] += 1

        # 检查自动规则
        tool_name = request.tool_name

        # 自动拒绝规则
        for pattern in self._auto_deny_patterns:
            if pattern in tool_name:
                click.echo(f"[Auto-Deny] Tool '{tool_name}' matches deny pattern '{pattern}'")
                self._stats["denied"] += 1
                return ApprovalResponse.DENY

        # 自动允许规则
        for pattern in self._auto_allow_patterns:
            if pattern in tool_name:
                click.echo(f"[Auto-Allow] Tool '{tool_name}' matches allow pattern '{pattern}'")
                self._stats["allowed"] += 1
                return ApprovalResponse.ALLOW

        # 交互式审批
        return self._interactive_approval(request)

    def _interactive_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        """
        交互式审批

        Args:
            request: 审批请求

        Returns:
            审批响应
        """
        click.echo()
        click.echo("=" * 60)
        click.echo("[Approval Request] 工具执行审批请求", fg="yellow", bold=True)
        click.echo("=" * 60)

        # 显示工具信息
        click.echo(f"工具名称: {click.style(request.tool_name, fg='cyan', bold=True)}")

        # 显示风险等级
        if hasattr(request, 'risk_level'):
            risk_color = {
                "LOW": "green",
                "MEDIUM": "yellow",
                "HIGH": "orange",
                "CRITICAL": "red",
            }.get(request.risk_level.name, "white")
            click.echo(f"风险等级: {click.style(request.risk_level.name, fg=risk_color)}")

        # 显示原因
        if request.reason:
            click.echo(f"原因: {request.reason}")

        # 显示参数（如果启用详细信息）
        if self.show_details and request.parameters:
            click.echo()
            click.echo("参数:")
            for key, value in request.parameters.items():
                # 截断长值
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:50] + "..."
                click.echo(f"  {key}: {value_str}")

        click.echo()

        # 询问用户
        while True:
            try:
                response = click.prompt(
                    click.style("是否批准?", fg="yellow", bold=True),
                    type=click.Choice(
                        ["y", "n", "s", "ya", "na"],
                        case_sensitive=False
                    ),
                    default=self._default_response(),
                    show_choices=True,
                )

                if response == "y":
                    click.echo("[Decision] 批准执行", fg="green")
                    self._stats["allowed"] += 1
                    return ApprovalResponse.ALLOW

                elif response == "n":
                    click.echo("[Decision] 拒绝执行", fg="red")
                    self._stats["denied"] += 1
                    return ApprovalResponse.DENY

                elif response == "s":
                    click.echo("[Decision] 跳过", fg="yellow")
                    self._stats["skipped"] += 1
                    return ApprovalResponse.DENY  # 跳过视为拒绝

                elif response == "ya":
                    click.echo("[Decision] 批准并添加到自动允许列表", fg="green")
                    self.add_auto_allow_pattern(request.tool_name)
                    self._stats["allowed"] += 1
                    return ApprovalResponse.ALLOW

                elif response == "na":
                    click.echo("[Decision] 拒绝并添加到自动拒绝列表", fg="red")
                    self.add_auto_deny_pattern(request.tool_name)
                    self._stats["denied"] += 1
                    return ApprovalResponse.DENY

            except (KeyboardInterrupt, EOFError):
                click.echo("\n[Decision] 用户取消，默认拒绝", fg="red")
                self._stats["denied"] += 1
                return ApprovalResponse.DENY

    def _default_response(self) -> str:
        """获取默认响应"""
        decision_map = {
            ApprovalDecision.ALLOW: "y",
            ApprovalDecision.DENY: "n",
            ApprovalDecision.SKIP: "s",
            ApprovalDecision.ALLOW_ALL: "y",
            ApprovalDecision.DENY_ALL: "n",
        }
        return decision_map.get(self.default_decision, "y")

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self._stats.copy()

    def print_stats(self) -> None:
        """打印统计信息"""
        click.echo()
        click.echo("[Approval Statistics] 审批统计:")
        click.echo(f"  总请求数: {self._stats['total']}")
        click.echo(f"  批准: {click.style(str(self._stats['allowed']), fg='green')}")
        click.echo(f"  拒绝: {click.style(str(self._stats['denied']), fg='red')}")
        click.echo(f"  跳过: {click.style(str(self._stats['skipped']), fg='yellow')}")

        if self._auto_allow_patterns:
            click.echo(f"  自动允许规则: {len(self._auto_allow_patterns)}")
        if self._auto_deny_patterns:
            click.echo(f"  自动拒绝规则: {len(self._auto_deny_patterns)}")


def create_cli_approval_handler(
    default_allow: bool = True,
    show_details: bool = True,
) -> CLIApprovalHandler:
    """
    创建 CLI 审批处理器

    Args:
        default_allow: 默认是否批准
        show_details: 是否显示详细信息

    Returns:
        CLIApprovalHandler 实例
    """
    default_decision = ApprovalDecision.ALLOW if default_allow else ApprovalDecision.DENY
    return CLIApprovalHandler(
        default_decision=default_decision,
        show_details=show_details,
    )


def auto_approve_safe_tools(request: ApprovalRequest) -> ApprovalResponse:
    """
    自动批准安全工具

    判断逻辑：
    - 只读工具（read_file, list_files 等）自动批准
    - 数学工具自动批准
    - 其他工具需要审批

    Args:
        request: 审批请求

    Returns:
        审批响应
    """
    safe_tools = {
        "read_file",
        "list_files",
        "file_exists",
        "calculator",
        "get_current_time",
        "datetime",
        "search",
    }

    if request.tool_name in safe_tools:
        return ApprovalResponse.ALLOW

    # 其他工具默认拒绝，需要手动审批
    return ApprovalResponse.DENY


def create_approval_manager_with_cli(
    mode: ApprovalMode = ApprovalMode.ASK_HIGH_RISK,
    default_timeout: int = 300,
) -> ApprovalManager:
    """
    创建带 CLI 处理器的审批管理器

    Args:
        mode: 审批模式
        default_timeout: 默认超时时间

    Returns:
        ApprovalManager 实例
    """
    config = ApprovalConfig(
        mode=mode,
        default_timeout=default_timeout,
    )

    manager = ApprovalManager(config)

    # 设置 CLI 处理器
    handler = create_cli_approval_handler(default_allow=True)
    manager.set_user_input_callback(handler.handle_request)

    return manager


# ============================================================================
# 便捷函数
# ============================================================================

def quick_approve(tool_name: str = None) -> Callable:
    """
    快速批准装饰器

    用于自动批准特定工具。

    Args:
        tool_name: 工具名称，None 表示所有工具

    Example:
        ```python
        @quick_approve("read_file")
        def my_handler(request):
            return ApprovalResponse.ALLOW
        ```
    """
    def decorator(func):
        def wrapper(request: ApprovalRequest):
            if tool_name is None or request.tool_name == tool_name:
                return ApprovalResponse.ALLOW
            return func(request)
        return wrapper
    return decorator
