"""
工具管理器

集中管理所有工具分组，提供注册、查询、过滤等功能。
集成策略和审批系统，实现完整的工具访问控制。
"""

from typing import Dict, List, Optional, TYPE_CHECKING, Tuple, Any
import logging

from .tool_group import ToolGroup, get_predefined_group, list_predefined_groups, GroupPolicy

if TYPE_CHECKING:
    from fastreact.tools import Tool

logger = logging.getLogger(__name__)


class ToolManager:
    """
    工具管理器

    负责管理所有工具分组，提供统一的工具查询和管理接口。

    Attributes:
        groups: 工具分组字典 {group_name: ToolGroup}
        auto_register: 是否自动注册工具到默认分组
    """

    def __init__(self, auto_register: bool = True):
        """
        初始化工具管理器

        Args:
            auto_register: 是否自动加载预定义分组
        """
        self.groups: Dict[str, ToolGroup] = {}
        self._tool_index: Dict[str, str] = {}  # {tool_name: group_name}

        if auto_register:
            self._load_predefined_groups()

    def _load_predefined_groups(self):
        """加载预定义的工具分组"""
        for group_name in list_predefined_groups():
            group = get_predefined_group(group_name)
            if group:
                self.register_group(group)
                logger.debug(f"Loaded predefined group: {group_name}")

    def register_group(self, group: ToolGroup) -> None:
        """
        注册工具分组

        Args:
            group: 工具分组对象
        """
        if group.name in self.groups:
            logger.warning(f"Group '{group.name}' already exists, overwriting")

        self.groups[group.name] = group

        # 更新工具索引
        for tool in group.tools:
            self._tool_index[tool.name] = group.name

        logger.info(f"Registered group: {group.name} with {len(group.tools)} tools")

    def unregister_group(self, group_name: str) -> bool:
        """
        注销工具分组

        Args:
            group_name: 分组名称

        Returns:
            是否成功注销
        """
        if group_name not in self.groups:
            return False

        # 清理工具索引
        group = self.groups[group_name]
        for tool in group.tools:
            self._tool_index.pop(tool.name, None)

        del self.groups[group_name]
        logger.info(f"Unregistered group: {group_name}")
        return True

    def get_group(self, group_name: str) -> Optional[ToolGroup]:
        """
        获取工具分组

        Args:
            group_name: 分组名称

        Returns:
            ToolGroup 对象或 None
        """
        return self.groups.get(group_name)

    def list_groups(self) -> List[str]:
        """
        列出所有分组名称

        Returns:
            分组名称列表
        """
        return list(self.groups.keys())

    def list_groups_details(self) -> List[Dict]:
        """
        列出所有分组的详细信息

        Returns:
            分组信息字典列表
        """
        return [group.to_dict() for group in self.groups.values()]

    def register_tool(
        self,
        tool: 'Tool',
        group_name: str,
        overwrite: bool = False
    ) -> bool:
        """
        注册工具到指定分组

        Args:
            tool: 工具对象
            group_name: 目标分组名称
            overwrite: 如果工具已存在，是否覆盖

        Returns:
            是否成功注册
        """
        group = self.get_group(group_name)
        if not group:
            logger.error(f"Group '{group_name}' not found")
            return False

        # 检查工具是否已在其他分组
        existing_group = self._tool_index.get(tool.name)
        if existing_group and existing_group != group_name:
            if not overwrite:
                logger.warning(
                    f"Tool '{tool.name}' already in group '{existing_group}', "
                    f"use overwrite=True to move it"
                )
                return False
            # 从原分组移除
            old_group = self.get_group(existing_group)
            if old_group:
                old_group.remove_tool(tool.name)

        group.add_tool(tool)
        self._tool_index[tool.name] = group_name
        logger.debug(f"Registered tool '{tool.name}' to group '{group_name}'")
        return True

    def get_tool(self, tool_name: str) -> Optional['Tool']:
        """
        获取工具

        Args:
            tool_name: 工具名称

        Returns:
            Tool 对象或 None
        """
        group_name = self._tool_index.get(tool_name)
        if not group_name:
            return None

        group = self.get_group(group_name)
        if not group:
            return None

        return group.get_tool(tool_name)

    def get_tool_group(self, tool_name: str) -> Optional[str]:
        """
        获取工具所属的分组

        Args:
            tool_name: 工具名称

        Returns:
            分组名称或 None
        """
        return self._tool_index.get(tool_name)

    def list_tools(self, group_name: Optional[str] = None) -> List[str]:
        """
        列出工具名称

        Args:
            group_name: 分组名称，None 表示列出所有工具

        Returns:
            工具名称列表
        """
        if group_name:
            group = self.get_group(group_name)
            return group.list_tools() if group else []
        else:
            return list(self._tool_index.keys())

    def list_tools_details(self, group_name: Optional[str] = None) -> List[Dict]:
        """
        列出工具详细信息

        Args:
            group_name: 分组名称，None 表示列出所有工具

        Returns:
            工具信息字典列表
        """
        if group_name:
            group = self.get_group(group_name)
            if not group:
                return []
            tools = group.tools
        else:
            tools = []
            for group in self.groups.values():
                tools.extend(group.tools)

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "group": self._tool_index.get(tool.name),
            }
            for tool in tools
        ]

    def get_tools_by_groups(
        self,
        group_names: List[str],
        respect_policies: bool = True
    ) -> List['Tool']:
        """
        获取指定分组的工具

        Args:
            group_names: 分组名称列表
            respect_policies: 是否遵守分组的访问策略

        Returns:
            工具列表
        """
        tools = []

        for group_name in group_names:
            group = self.get_group(group_name)
            if not group:
                continue

            if respect_policies:
                tools.extend(group.get_allowed_tools())
            else:
                tools.extend(group.tools)

        # 去重（保留顺序）
        seen = set()
        unique_tools = []
        for tool in tools:
            if tool.name not in seen:
                seen.add(tool.name)
                unique_tools.append(tool)

        return unique_tools

    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        检查工具是否允许使用

        Args:
            tool_name: 工具名称

        Returns:
            是否允许使用
        """
        group_name = self._tool_index.get(tool_name)
        if not group_name:
            return False

        group = self.get_group(group_name)
        if not group:
            return False

        return group.is_tool_allowed(tool_name)

    def set_group_policy(
        self,
        group_name: str,
        policy,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None
    ) -> bool:
        """
        设置分组的访问策略

        Args:
            group_name: 分组名称
            policy: 策略类型
            whitelist: 白名单（用于 ALLOW_WHITELIST 策略）
            blacklist: 黑名单（用于 DENY_BLACKLIST 策略）

        Returns:
            是否成功设置
        """
        group = self.get_group(group_name)
        if not group:
            return False

        group.policy = policy
        if whitelist is not None:
            group.whitelist = whitelist
        if blacklist is not None:
            group.blacklist = blacklist

        logger.info(
            f"Updated group '{group_name}' policy to {policy.value}, "
            f"whitelist={whitelist}, blacklist={blacklist}"
        )
        return True

    def get_stats(self) -> Dict:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        total_tools = len(self._tool_index)
        total_groups = len(self.groups)

        group_stats = {}
        for name, group in self.groups.items():
            group_stats[name] = {
                "tool_count": len(group.tools),
                "policy": group.policy.value,
                "allowed_count": len(group.get_allowed_tools()),
            }

        return {
            "total_groups": total_groups,
            "total_tools": total_tools,
            "groups": group_stats,
        }

    # ============================================================================
    # 策略与审批系统集成
    # ============================================================================

    def check_tool_access_with_policy(
        self,
        tool_name: str,
        policy_engine=None,
        approval_manager=None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        检查工具访问权限（集成策略和审批系统）

        检查顺序：
        1. 分组策略检查 (GroupPolicy)
        2. 工具策略检查 (ToolPolicy if provided)
        3. 审批检查 (ApprovalManager if provided)

        Args:
            tool_name: 工具名称
            policy_engine: 策略引擎实例（可选）
            approval_manager: 审批管理器实例（可选）
            context: 额外上下文信息

        Returns:
            (allowed, reason, approval_request_id) 元组
            - allowed: 是否允许执行
            - reason: 原因说明
            - approval_request_id: 审批请求ID（如果需要审批）
        """
        context = context or {}

        # 1. 检查工具是否存在
        group_name = self._tool_index.get(tool_name)
        if not group_name:
            return False, f"Tool '{tool_name}' not found", None

        group = self.get_group(group_name)
        if not group:
            return False, f"Group '{group_name}' not found", None

        # 2. 检查分组策略
        if not group.is_tool_allowed(tool_name):
            return False, f"Tool '{tool_name}' not allowed by group policy '{group.policy.value}'", None

        # 3. 检查工具策略（如果提供）
        if policy_engine is not None:
            try:
                # 获取工具所属分组用于策略检查
                from .tool_policy import ToolPolicyDecision
                decision = policy_engine.check_tool_access(tool_name, context)

                if not decision.allowed:
                    return False, f"Blocked by tool policy: {decision.reason}", None

                # 如果需要审批
                if decision.requires_approval:
                    if approval_manager is not None:
                        # 创建审批请求
                        try:
                            from .approval import ApprovalRequest, ApprovalMode
                            from .tool_policy import RiskLevel

                            req = approval_manager.create_request(
                                policy_name="tool_policy",
                                tool_name=tool_name,
                                tool_args=context.get("parameters", {}),
                                reason=decision.reason,
                                context=context,
                            )
                            return False, f"Approval required: {decision.reason}", req.request_id
                        except Exception as e:
                            logger.warning(f"Failed to create approval request: {e}")
                            return False, f"Approval required but approval system unavailable: {decision.reason}", None
                    else:
                        return False, f"Approval required but no approval manager: {decision.reason}", None
            except Exception as e:
                logger.warning(f"Policy engine check failed: {e}")
                # 继续执行，不阻塞

        # 所有检查通过
        return True, "Access granted", None

    def set_policy_engine(self, policy_engine) -> None:
        """
        设置策略引擎

        Args:
            policy_engine: 策略引擎实例
        """
        self._policy_engine = policy_engine
        logger.info("Policy engine attached to tool manager")

    def set_approval_manager(self, approval_manager) -> None:
        """
        设置审批管理器

        Args:
            approval_manager: 审批管理器实例
        """
        self._approval_manager = approval_manager
        logger.info("Approval manager attached to tool manager")

    def get_policy_engine(self):
        """获取策略引擎"""
        return getattr(self, '_policy_engine', None)

    def get_approval_manager(self):
        """获取审批管理器"""
        return getattr(self, '_approval_manager', None)


# 全局工具管理器实例
_global_manager: Optional[ToolManager] = None


def get_global_manager() -> ToolManager:
    """获取全局工具管理器（单例）"""
    global _global_manager
    if _global_manager is None:
        _global_manager = ToolManager()
    return _global_manager


def reset_global_manager():
    """重置全局工具管理器"""
    global _global_manager
    _global_manager = None
