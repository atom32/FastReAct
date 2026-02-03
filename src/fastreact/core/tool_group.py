"""
工具分组系统

将工具按功能分类组织，支持分组级别的权限控制和管理。
"""

from typing import Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

if TYPE_CHECKING:
    from fastreact.tools import Tool


class GroupPolicy(Enum):
    """工具分组策略"""
    # 默认：所有工具可用
    ALLOW_ALL = "allow_all"
    # 禁止：所有工具禁用
    DENY_ALL = "deny_all"
    # 显式允许：只有白名单中的工具可用
    ALLOW_WHITELIST = "allow_whitelist"
    # 显式禁止：黑名单中的工具禁用
    DENY_BLACKLIST = "deny_blacklist"


@dataclass
class ToolGroup:
    """
    工具分组

    将相关功能的工具组织在一起，便于管理和权限控制。

    Attributes:
        name: 分组名称（唯一标识符）
        display_name: 显示名称（中文/英文）
        description: 分组描述
        tools: 工具列表
        policy: 分组策略
        whitelist: 白名单（用于 ALLOW_WHITELIST 策略）
        blacklist: 黑名单（用于 DENY_BLACKLIST 策略）
        metadata: 额外的元数据
    """

    name: str
    display_name: str
    description: str
    tools: List['Tool'] = field(default_factory=list)
    policy: GroupPolicy = GroupPolicy.ALLOW_ALL
    whitelist: List[str] = field(default_factory=list)
    blacklist: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def add_tool(self, tool: 'Tool') -> None:
        """添加工具到分组"""
        if tool not in self.tools:
            self.tools.append(tool)

    def remove_tool(self, tool_name: str) -> bool:
        """从分组中移除工具"""
        for i, tool in enumerate(self.tools):
            if tool.name == tool_name:
                self.tools.pop(i)
                return True
        return False

    def get_tool(self, tool_name: str) -> Optional['Tool']:
        """获取工具"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        return [tool.name for tool in self.tools]

    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        检查工具是否允许使用

        根据分组策略判断工具是否可用：
        - ALLOW_ALL: 所有工具可用
        - DENY_ALL: 所有工具禁用
        - ALLOW_WHITELIST: 只允许白名单中的工具
        - DENY_BLACKLIST: 禁止黑名单中的工具
        """
        tool_exists = self.get_tool(tool_name) is not None

        if not tool_exists:
            return False

        if self.policy == GroupPolicy.ALLOW_ALL:
            return True
        elif self.policy == GroupPolicy.DENY_ALL:
            return False
        elif self.policy == GroupPolicy.ALLOW_WHITELIST:
            return tool_name in self.whitelist
        elif self.policy == GroupPolicy.DENY_BLACKLIST:
            return tool_name not in self.blacklist

        return False

    def get_allowed_tools(self) -> List['Tool']:
        """获取所有允许使用的工具"""
        return [
            tool for tool in self.tools
            if self.is_tool_allowed(tool.name)
        ]

    def to_dict(self) -> Dict:
        """转换为字典（用于序列化）"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "tool_count": len(self.tools),
            "policy": self.policy.value,
            "tools": self.list_tools(),
            "metadata": self.metadata,
        }


# 预定义的工具分组
PREDEFINED_GROUPS = {
    "file_ops": ToolGroup(
        name="file_ops",
        display_name="文件操作",
        description="文件读写、目录操作等文件系统相关功能",
        policy=GroupPolicy.ALLOW_ALL,
        metadata={"category": "filesystem", "risk_level": "medium"}
    ),
    "web": ToolGroup(
        name="web",
        display_name="Web 操作",
        description="网络请求、网页抓取、搜索等 Web 相关功能",
        policy=GroupPolicy.ALLOW_ALL,
        metadata={"category": "network", "risk_level": "medium"}
    ),
    "code": ToolGroup(
        name="code",
        display_name="代码操作",
        description="代码执行、验证、格式化等开发工具",
        policy=GroupPolicy.ALLOW_ALL,
        metadata={"category": "development", "risk_level": "high"}
    ),
    "data": ToolGroup(
        name="data",
        display_name="数据操作",
        description="JSON、CSV 等数据格式的读写和处理",
        policy=GroupPolicy.ALLOW_ALL,
        metadata={"category": "data", "risk_level": "low"}
    ),
    "system": ToolGroup(
        name="system",
        display_name="系统操作",
        description="Shell 命令、系统信息、进程管理等",
        policy=GroupPolicy.DENY_ALL,  # 默认禁用，高风险
        metadata={"category": "system", "risk_level": "critical"}
    ),
    "math": ToolGroup(
        name="math",
        display_name="数学计算",
        description="数学运算、统计分析、计算器等",
        policy=GroupPolicy.ALLOW_ALL,
        metadata={"category": "math", "risk_level": "low"}
    ),
    "text": ToolGroup(
        name="text",
        display_name="文本处理",
        description="文本分析、编码转换、正则表达式等",
        policy=GroupPolicy.ALLOW_ALL,
        metadata={"category": "text", "risk_level": "low"}
    ),
    "ai": ToolGroup(
        name="ai",
        display_name="AI 工具",
        description="RAG 搜索、向量操作等 AI 相关功能",
        policy=GroupPolicy.ALLOW_ALL,
        metadata={"category": "ai", "risk_level": "low"}
    ),
}


def get_predefined_group(group_name: str) -> Optional[ToolGroup]:
    """获取预定义的工具分组"""
    return PREDEFINED_GROUPS.get(group_name)


def list_predefined_groups() -> List[str]:
    """列出所有预定义分组名称"""
    return list(PREDEFINED_GROUPS.keys())
