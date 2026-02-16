"""
Docker 沙箱系统

安全的代码执行环境，使用 Docker 容器隔离。
"""

from .docker import DockerSandbox, SandboxError
from .config import (
    SandboxConfig,
    NetworkMode,
    SandboxPreset,
    get_preset_config,
    create_config_with_mounts,
    PRESET_CONFIGS,
    # 用户自定义预设
    register_custom_preset,
    unregister_custom_preset,
    get_custom_preset,
    list_custom_presets,
    list_all_presets,
    get_preset_by_name,
)

__all__ = [
    "DockerSandbox",
    "SandboxError",
    "SandboxConfig",
    "NetworkMode",
    "SandboxPreset",
    "get_preset_config",
    "create_config_with_mounts",
    "PRESET_CONFIGS",
    # 用户自定义预设
    "register_custom_preset",
    "unregister_custom_preset",
    "get_custom_preset",
    "list_custom_presets",
    "list_all_presets",
    "get_preset_by_name",
]
