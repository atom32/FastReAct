"""
Docker 沙箱配置管理

提供沙箱配置的定义、验证和管理功能。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from pathlib import Path


class NetworkMode(Enum):
    """网络模式"""
    DISABLED = "disabled"      # 禁用网络
    BRIDGE = "bridge"          # 桥接模式（默认）
    HOST = "host"              # 主机网络
    NONE = "none"              # 无网络


class SandboxPreset(Enum):
    """沙箱预设配置"""
    SAFE = "safe"              # 安全模式：网络禁用，低资源
    STANDARD = "standard"      # 标准模式：桥接网络，中等资源
    PERFORMANCE = "performance"  # 性能模式：更多资源
    UNRESTRICTED = "unrestricted"  # 无限制模式（危险！）


@dataclass
class SandboxConfig:
    """
    Docker 沙箱配置

    Attributes:
        image: Docker 镜像名称
        memory_limit: 内存限制（如 "512m", "1g"）
        cpu_limit: CPU 限制（如 0.5 表示 50%）
        network_mode: 网络模式
        working_dir: 容器内工作目录
        mount_points: 挂载点列表 [{"host": "/path", "container": "/path", "mode": "rw"}]
        environment: 环境变量字典
        auto_remove: 执行后自动删除容器
        timeout: 默认超时时间（秒）
        denylist: 默认关键词黑名单
        enable_network: 是否启用网络（兼容参数）
    """

    # Docker 镜像
    image: str = "python:3.11-slim"

    # 资源限制
    memory_limit: str = "512m"
    cpu_limit: float = 0.5  # 50% CPU

    # 网络配置
    network_mode: NetworkMode = NetworkMode.BRIDGE
    enable_network: bool = True  # 兼容参数

    # 工作目录
    working_dir: str = "/workspace"

    # 挂载点
    mount_points: List[Dict[str, str]] = field(default_factory=list)

    # 环境变量
    environment: Dict[str, str] = field(default_factory=dict)

    # 容器行为
    auto_remove: bool = True
    timeout: int = 30

    # 安全配置
    denylist: List[str] = field(default_factory=list)

    def __post_init__(self):
        """初始化后处理"""
        # 设置默认环境变量
        default_env = {
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "NODE_ENV": "production",
        }
        for key, value in default_env.items():
            if key not in self.environment:
                self.environment[key] = value

        # 处理 enable_network 兼容参数
        if not self.enable_network:
            self.network_mode = NetworkMode.DISABLED

    def to_docker_kwargs(self) -> Dict[str, Any]:
        """
        转换为 Docker SDK 参数

        Returns:
            Docker containers.run() 的参数字典
        """
        kwargs = {
            "mem_limit": self.memory_limit,
            "cpu_quota": int(self.cpu_limit * 100000),
            "cpu_period": 100000,
            "auto_remove": self.auto_remove,
            "working_dir": self.working_dir,
            "environment": self.environment,
        }

        # 网络配置
        if self.network_mode == NetworkMode.DISABLED:
            kwargs["network_disabled"] = True
        elif self.network_mode == NetworkMode.HOST:
            kwargs["network_mode"] = "host"
        elif self.network_mode == NetworkMode.BRIDGE:
            kwargs["network_mode"] = "bridge"

        # 挂载点
        if self.mount_points:
            volumes = {}
            for mount in self.mount_points:
                host_path = mount["host"]
                container_path = mount["container"]
                mode = mount.get("mode", "rw")
                volumes[host_path] = {"bind": container_path, "mode": mode}
            kwargs["volumes"] = volumes

        return kwargs

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "image": self.image,
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "network_mode": self.network_mode.value,
            "enable_network": self.enable_network,
            "working_dir": self.working_dir,
            "mount_points": self.mount_points,
            "environment": self.environment,
            "auto_remove": self.auto_remove,
            "timeout": self.timeout,
            "denylist": self.denylist,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SandboxConfig":
        """从字典创建配置"""
        # 处理 network_mode
        if "network_mode" in data:
            if isinstance(data["network_mode"], str):
                data["network_mode"] = NetworkMode(data["network_mode"])
            elif not isinstance(data["network_mode"], NetworkMode):
                data["network_mode"] = NetworkMode.BRIDGE

        return cls(**data)

    @classmethod
    def from_file(cls, path: str) -> "SandboxConfig":
        """从 JSON 文件加载配置"""
        config_file = Path(path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        data = json.loads(config_file.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def save(self, path: str):
        """保存配置到 JSON 文件"""
        config_file = Path(path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


# ============================================================================
# 预定义配置模板
# ============================================================================

PRESET_CONFIGS: Dict[SandboxPreset, SandboxConfig] = {
    SandboxPreset.SAFE: SandboxConfig(
        image="python:3.11-slim",
        memory_limit="256m",
        cpu_limit=0.25,
        network_mode=NetworkMode.DISABLED,
        enable_network=False,
        auto_remove=True,
        timeout=15,
        denylist=[
            "os.system",
            "subprocess",
            "eval",
            "exec",
            "compile",
            "__import__",
        ],
    ),

    SandboxPreset.STANDARD: SandboxConfig(
        image="python:3.11-slim",
        memory_limit="512m",
        cpu_limit=0.5,
        network_mode=NetworkMode.BRIDGE,
        enable_network=True,
        auto_remove=True,
        timeout=30,
        denylist=[],
    ),

    SandboxPreset.PERFORMANCE: SandboxConfig(
        image="python:3.11",
        memory_limit="2g",
        cpu_limit=2.0,
        network_mode=NetworkMode.BRIDGE,
        enable_network=True,
        auto_remove=True,
        timeout=60,
        denylist=[],
    ),

    SandboxPreset.UNRESTRICTED: SandboxConfig(
        image="python:3.11",
        memory_limit="4g",
        cpu_limit=4.0,
        network_mode=NetworkMode.HOST,
        enable_network=True,
        auto_remove=False,
        timeout=300,
        denylist=[],
    ),
}


def get_preset_config(preset: SandboxPreset) -> SandboxConfig:
    """获取预设配置"""
    return PRESET_CONFIGS.get(preset, PRESET_CONFIGS[SandboxPreset.STANDARD])


def create_config_with_mounts(
    preset: SandboxPreset = SandboxPreset.STANDARD,
    workspace_path: Optional[str] = None,
    read_only_paths: Optional[List[str]] = None,
) -> SandboxConfig:
    """
    创建带挂载点的沙箱配置

    Args:
        preset: 基础预设配置
        workspace_path: 工作区路径（读写挂载到 /workspace）
        read_only_paths: 只读路径列表

    Returns:
        沙箱配置
    """
    config = get_preset_config(preset)
    config.mount_points = []

    # 挂载工作区
    if workspace_path:
        config.mount_points.append({
            "host": str(Path(workspace_path).resolve()),
            "container": "/workspace",
            "mode": "rw",
        })

    # 挂载只读路径
    if read_only_paths:
        for path in read_only_paths:
            config.mount_points.append({
                "host": str(Path(path).resolve()),
                "container": str(Path(path).resolve()),
                "mode": "ro",
            })

    return config
