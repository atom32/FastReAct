"""
Bootstrap 文件加载器

负责加载和处理 Bootstrap 配置文件，构建自定义系统提示。
"""

import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

import logging

logger = logging.getLogger(__name__)


class BootstrapLoader:
    """
    Bootstrap 文件加载器

    从工作区加载配置文件并注入到系统提示中。

    属性：
        workspace: 工作区路径
        files: 加载的文件内容字典
        loaded_at: 加载时间
    """

    def __init__(self, workspace: Optional[str] = None):
        """
        初始化 Bootstrap 加载器

        Args:
            workspace: 工作区路径，默认为 ~/.fastreact
        """
        self.workspace = self._resolve_workspace(workspace)
        self.files: Dict[str, str] = {}
        self.loaded_at: Optional[datetime] = None

        logger.info(f"Bootstrap loader initialized: {self.workspace}")

    def _resolve_workspace(self, workspace: Optional[str]) -> Path:
        """解析工作区路径"""
        if workspace is None:
            # 默认工作区
            workspace = os.path.expanduser("~/.fastreact")

        path = Path(workspace).resolve()

        # 如果工作区不存在，创建它
        if not path.exists():
            logger.info(f"Creating workspace: {path}")
            path.mkdir(parents=True, exist_ok=True)

        return path

    def load(self, force_reload: bool = False) -> Dict[str, str]:
        """
        加载所有 Bootstrap 文件

        Args:
            force_reload: 是否强制重新加载

        Returns:
            文件名字典: {"agents": "内容", "soul": "内容", ...}
        """
        # 如果已加载且不强制重载，返回缓存
        if self.files and not force_reload:
            logger.debug("Using cached bootstrap files")
            return self.files

        # 加载文件
        self.files = {}
        bootstrap_files = {
            "agents": "AGENTS.md",
            "soul": "SOUL.md",
            "tools": "TOOLS.md",
            "workspace": "WORKSPACE.md",
        }

        for key, filename in bootstrap_files.items():
            content = self._read_file(filename)
            if content:
                self.files[key] = content
                logger.debug(f"Loaded {filename}: {len(content)} chars")
            else:
                logger.debug(f"File not found or empty: {filename}")

        self.loaded_at = datetime.now()
        logger.info(f"Loaded {len(self.files)} bootstrap files")

        return self.files

    def _read_file(self, filename: str) -> str:
        """
        读取文件内容

        Args:
            filename: 文件名

        Returns:
            文件内容，如果文件不存在则返回空字符串
        """
        path = self.workspace / filename

        if not path.exists():
            return ""

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading {filename}: {e}")
            return ""

    def build_system_prompt(
        self,
        base_prompt: str,
        inject_position: str = "after"
    ) -> str:
        """
        构建系统提示（注入 Bootstrap 文件）

        Args:
            base_prompt: 基础系统提示
            inject_position: 注入位置 ("before" | "after" | "replace")

        Returns:
            完整的系统提示
        """
        # 确保文件已加载
        self.load()

        # 构建 Bootstrap 部分
        sections = []

        for key in ["agents", "soul", "tools", "workspace"]:
            if key in self.files:
                content = self.files[key].strip()
                if content:
                    section_name = key.upper()
                    sections.append(f"=== {section_name} ===\n{content}")

        if not sections:
            # 没有 Bootstrap 内容，返回原始提示
            return base_prompt

        bootstrap_content = "\n\n".join(sections)

        # 根据位置组合
        if inject_position == "before":
            return bootstrap_content + "\n\n" + base_prompt
        elif inject_position == "replace":
            return bootstrap_content
        else:  # "after"
            return base_prompt + "\n\n" + bootstrap_content

    def get_file(self, name: str) -> Optional[str]:
        """
        获取单个文件内容

        Args:
            name: 文件名 ("agents" | "soul" | "tools" | "workspace")

        Returns:
            文件内容，如果不存在则返回 None
        """
        self.load()
        return self.files.get(name)

    def has_file(self, name: str) -> bool:
        """
        检查文件是否存在且非空

        Args:
            name: 文件名

        Returns:
            是否存在
        """
        self.load()
        return name in self.files and bool(self.files[name])

    def reload(self) -> Dict[str, str]:
        """
        重新加载所有文件

        Returns:
            重新加载的文件字典
        """
        logger.info("Reloading bootstrap files")
        return self.load(force_reload=True)

    def get_workspace_path(self) -> Path:
        """获取工作区路径"""
        return self.workspace

    def is_workspace_initialized(self) -> bool:
        """
        检查工作区是否已初始化

        Returns:
            是否至少有一个 Bootstrap 文件
        """
        self.load()
        return len(self.files) > 0

    def __repr__(self) -> str:
        return f"BootstrapLoader(workspace={self.workspace}, files={len(self.files)})"
