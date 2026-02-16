"""
Bootstrap 配置系统

允许用户通过配置文件自定义 Agent 行为，无需修改代码。

功能：
- 加载 Bootstrap 文件（AGENTS.md, SOUL.md, TOOLS.md）
- 构建自定义系统提示
- 支持热重载（可选）
- 工作区管理
- 自动配置加载（环境变量 + config.json）

使用示例：
    from fastreact.bootstrap import BootstrapLoader

    loader = BootstrapLoader(workspace="~/.fastreact")
    system_prompt = loader.build_system_prompt(base_prompt)

文件结构：
    ~/.fastreact/
    ├── AGENTS.md       # Agent 操作指令
    ├── SOUL.md         # 人格和边界
    ├── TOOLS.md        # 工具使用指南
    ├── WORKSPACE.md    # 工作区配置
    └── config.json     # 技术配置
"""

from .loader import BootstrapLoader
from .workspace import WorkspaceManager, init_workspace

# 导出配置加载功能
try:
    from .config_loader import (
        load_config,
        get_api_key,
        get_base_url,
        get_model,
    )
    _config_available = True
except ImportError:
    _config_available = False

__all__ = [
    "BootstrapLoader",
    "WorkspaceManager",
    "init_workspace",
]

# 如果可用，导出配置函数
if _config_available:
    __all__.extend([
        "load_config",
        "get_api_key",
        "get_base_url",
        "get_model",
    ])
