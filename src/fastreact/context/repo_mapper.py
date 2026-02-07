"""
Repository Mapper - 项目结构扫描器

生成和维护项目的高层级地图，为 Coding Agent 提供"上帝视角"。
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class RepoMapConfig:
    """Repo Map 配置"""
    # 扫描深度限制
    max_depth: int = 3

    # 单个目录最多显示的文件数
    max_files_per_dir: int = 20

    # 总共最多显示的文件数
    max_total_files: int = 100

    # 缓存过期时间（秒，0 = 永不自动过期）
    cache_ttl: int = 60  # 默认 60 秒过期

    # 自动折叠的目录名模式
    fold_patterns: List[str] = field(default_factory=lambda: [
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        ".env",
        "dist",
        "build",
        "target",
        "bin",
        "obj",
        ".next",
        ".nuxt",
        "coverage",
        ".pytest_cache",
        ".mypy_cache",
        "*.egg-info",
    ])

    # 优先显示的文件扩展名（代码文件）
    priority_extensions: Set[str] = field(default_factory=lambda: {
        ".py", ".js", ".ts", ".tsx", ".jsx",
        ".java", ".cpp", ".c", ".h", ".cs",
        ".go", ".rs", ".rb", ".php",
        ".json", ".yaml", ".yml", ".toml",
        ".md", ".txt", ".cfg", ".conf"
    })

    # 优先显示的文件名
    priority_files: Set[str] = field(default_factory=lambda: {
        "README", "README.md", "LICENSE",
        "package.json", "requirements.txt", "setup.py",
        "tsconfig.json", ".gitignore", "Dockerfile",
        "Makefile", "CMakeLists.txt",
    })


@dataclass
class RepoMapEntry:
    """Repo Map 条目"""
    name: str
    path: str
    is_dir: bool
    children: List['RepoMapEntry'] = field(default_factory=list)
    is_folded: bool = False
    is_priority: bool = False


class RepoMapper:
    """
    项目结构映射器

    核心功能：
    1. 扫描目录结构（带深度限制）
    2. 自动折叠无关目录
    3. 优先显示重要文件
    4. 惰性更新（只在需要时扫描）
    5. Session 隔离（每个会话独立）
    """

    def __init__(
        self,
        root_path: str,
        config: Optional[RepoMapConfig] = None
    ):
        """
        初始化 Repo Mapper

        Args:
            root_path: 项目根目录
            config: 配置对象
        """
        self.root_path = Path(root_path).resolve()
        self.config = config or RepoMapConfig()

        # 缓存
        self._map: Optional[str] = None
        self._map_timestamp: float = 0
        self._map_dirty: bool = True

        # 当前工作目录（可能不同于 root_path）
        self._cwd: Path = self.root_path

    def should_fold(self, name: str) -> bool:
        """判断目录/文件是否应该被折叠"""
        name_lower = name.lower()

        # 检查折叠模式
        for pattern in self.config.fold_patterns:
            pattern_lower = pattern.lower()
            if pattern.startswith("*"):
                # 扩展名模式，如 *.egg-info
                if name_lower.endswith(pattern_lower[1:]):
                    return True
            elif name_lower == pattern_lower:
                return True

        return False

    def is_priority_file(self, name: str) -> bool:
        """判断是否是优先文件"""
        # 检查文件名
        if name in self.config.priority_files:
            return True

        # 检查扩展名
        ext = Path(name).suffix.lower()
        if ext in self.config.priority_extensions:
            return True

        return False

    def scan_directory(
        self,
        dir_path: Path,
        current_depth: int = 0,
        max_depth: int = None
    ) -> RepoMapEntry:
        """
        扫描目录

        Args:
            dir_path: 要扫描的目录路径
            current_depth: 当前深度
            max_depth: 最大深度（None 表示使用配置值）

        Returns:
            RepoMapEntry
        """
        if max_depth is None:
            max_depth = self.config.max_depth

        # 检查深度限制
        if current_depth >= max_depth:
            return RepoMapEntry(
                name=dir_path.name,
                path=str(dir_path),
                is_dir=True,
                is_folded=True
            )

        try:
            # 获取所有条目
            all_entries = []
            try:
                entries = list(dir_path.iterdir())
            except PermissionError:
                return RepoMapEntry(
                    name=dir_path.name + " [permission denied]",
                    path=str(dir_path),
                    is_dir=True,
                    is_folded=True
                )

            # 分离文件和目录
            dirs = []
            files = []

            for entry in entries:
                if entry.is_dir():
                    if not self.should_fold(entry.name):
                        dirs.append(entry)
                else:
                    files.append(entry)

            # 排序
            dirs.sort(key=lambda x: x.name.lower())
            files.sort(key=lambda x: (
                0 if self.is_priority_file(x.name) else 1,
                x.name.lower()
            ))

            # 限制文件数量
            files = files[:self.config.max_files_per_dir]

            # 递归扫描目录
            children = []
            total_files = 0

            for d in dirs:
                if total_files >= self.config.max_total_files:
                    break

                child = self.scan_directory(d, current_depth + 1, max_depth)
                children.append(child)
                total_files += self._count_entries(child)

            # 添加文件
            for f in files:
                if total_files >= self.config.max_total_files:
                    break

                children.append(RepoMapEntry(
                    name=f.name,
                    path=str(f),
                    is_dir=False,
                    is_priority=self.is_priority_file(f.name)
                ))
                total_files += 1

            return RepoMapEntry(
                name=dir_path.name,
                path=str(dir_path),
                is_dir=True,
                children=children,
                is_folded=False
            )

        except Exception as e:
            logger.error(f"Error scanning directory {dir_path}: {e}")
            return RepoMapEntry(
                name=dir_path.name + " [error]",
                path=str(dir_path),
                is_dir=True,
                is_folded=True
            )

    def _count_entries(self, entry: RepoMapEntry) -> int:
        """递归计算条目数量"""
        if not entry.is_dir or entry.is_folded:
            return 1
        return sum(self._count_entries(child) for child in entry.children)

    def format_map(self, entry: RepoMapEntry, indent: int = 0) -> str:
        """
        格式化 Repo Map 为树状文本

        Args:
            entry: 根条目
            indent: 缩进级别

        Returns:
            格式化的文本
        """
        if entry.is_folded:
            return "  " * indent + f"📁 {entry.name}/ [folded]"

        lines = []
        prefix = "  " * indent

        if entry.is_dir:
            lines.append(f"{prefix}📁 {entry.name}/")

            # 递归格式化子条目
            for child in entry.children:
                lines.append(self.format_map(child, indent + 1))
        else:
            # 文件
            icon = "⭐" if entry.is_priority else "📄"
            lines.append(f"{prefix}{icon} {entry.name}")

        return "\n".join(lines)

    def generate_map(
        self,
        force_refresh: bool = False,
        cwd: Optional[str] = None
    ) -> str:
        """
        生成或获取缓存的 Repo Map

        Args:
            force_refresh: 强制重新扫描
            cwd: 当前工作目录（如果与 cwd 不同，则标记为 dirty）

        Returns:
            格式化的 Repo Map 文本
        """
        # 检查 cwd 变化
        if cwd is not None:
            new_cwd = Path(cwd).resolve()
            if new_cwd != self._cwd:
                self._cwd = new_cwd
                self._map_dirty = True

        # 检查是否需要刷新（新增 TTL 检查）
        should_use_cache = (
            not force_refresh and
            not self._map_dirty and
            self._map is not None
        )

        # 如果配置了 TTL，检查缓存是否过期
        if should_use_cache and self.config.cache_ttl > 0:
            cache_age = time.time() - self._map_timestamp
            if cache_age > self.config.cache_ttl:
                logger.info(f"Cache expired (age: {cache_age:.1f}s > TTL: {self.config.cache_ttl}s)")
                should_use_cache = False

        if should_use_cache:
            logger.debug(f"Using cached repo map (age: {time.time() - self._map_timestamp:.1f}s)")
            return self._map

        # 扫描目录
        logger.info(f"Scanning directory: {self._cwd}")
        start_time = time.time()

        try:
            root_entry = self.scan_directory(self._cwd)
            scan_time = time.time() - start_time

            # 格式化
            map_text = self.format_map(root_entry)

            # 添加元信息
            header = f"""📁 Current Directory: {self._cwd}
[STATS] Project Structure (scanned {scan_time:.2f}s, {self._count_entries(root_entry)} items):

"""
            footer = f"""

[INFO] Tip: Use 'cd_repo' to change directory, 'refresh_repo' to rescan.
[SEARCH] Hidden: {', '.join(self.config.fold_patterns[:5])}...
"""

            self._map = header + map_text + footer
            self._map_timestamp = time.time()
            self._map_dirty = False

            logger.info(f"Repo map generated: {len(self._map)} chars")
            return self._map

        except Exception as e:
            logger.error(f"Failed to generate repo map: {e}")
            return f"[ERROR] Failed to scan directory: {e}\n📁 Current: {self._cwd}"

    def change_directory(self, new_path: str) -> str:
        """
        切换工作目录并刷新 map

        Args:
            new_path: 新目录路径（相对或绝对）

        Returns:
            新的 repo map
        """
        try:
            # 解析路径
            if os.path.isabs(new_path):
                new_cwd = Path(new_path).resolve()
            else:
                new_cwd = (self._cwd / new_path).resolve()

            # 检查路径是否存在
            if not new_cwd.exists():
                return f"[ERROR] Directory not found: {new_path}\n📁 Current: {self._cwd}"

            if not new_cwd.is_dir():
                return f"[ERROR] Not a directory: {new_path}\n📁 Current: {self._cwd}"

            # 切换目录
            self._cwd = new_cwd
            self._map_dirty = True

            # 生成新的 map
            return self.generate_map(force_refresh=True)

        except Exception as e:
            return f"[ERROR] Failed to change directory: {e}\n📁 Current: {self._cwd}"

    @property
    def current_directory(self) -> str:
        """获取当前工作目录"""
        return str(self._cwd)

    @property
    def is_dirty(self) -> bool:
        """检查 map 是否需要刷新"""
        return self._map_dirty

    def mark_dirty(self) -> None:
        """标记 map 需要刷新"""
        self._map_dirty = True

    def invalidate_cache(self) -> None:
        """
        使缓存失效

        强制下次调用 generate_map() 重新扫描目录。
        应在文件系统操作（创建、删除、移动文件）后调用。
        """
        self._map_dirty = True
        logger.debug("Repo map cache invalidated")


# ============================================================================
# Session 管理器：为每个 session 维护独立的 RepoMapper
# ============================================================================

_session_repo_mappers: Dict[str, RepoMapper] = {}


def get_repo_mapper(
    session_id: str,
    root_path: Optional[str] = None,
    config: Optional[RepoMapConfig] = None
) -> RepoMapper:
    """
    获取 session 的 RepoMapper（单例模式）

    Args:
        session_id: 会话 ID
        root_path: 项目根目录（仅首次创建时使用）
        config: 配置（仅首次创建时使用）

    Returns:
        RepoMapper 实例
    """
    if session_id not in _session_repo_mappers:
        if root_path is None:
            root_path = os.getcwd()
        _session_repo_mappers[session_id] = RepoMapper(root_path, config)
        logger.info(f"Created new RepoMapper for session {session_id}")

    return _session_repo_mappers[session_id]


def remove_session(session_id: str) -> None:
    """移除 session 的 RepoMapper"""
    if session_id in _session_repo_mappers:
        del _session_repo_mappers[session_id]
        logger.info(f"Removed RepoMapper for session {session_id}")
