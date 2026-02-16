"""
Precision Tools - 精细化工具集

"手术刀"级工具，用于替代"大锤"级工具：
- view_file: 精准读取文件的部分行
- grep_code: 正则表达式搜索代码
- smart_read: 智能文件读取（小文件全量，大文件部分）

基于 Claude Code 的设计理念：
- 节省 Token
- 提供精准控制
- 复用现有基础设施（repo_mapper）
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# 辅助函数
# ============================================================================

def _should_fold_file(filename: str, fold_patterns: List[str]) -> bool:
    """
    判断文件是否应该被过滤（复用 repo_mapper 的逻辑）

    Args:
        filename: 文件名
        fold_patterns: 过滤模式列表

    Returns:
        True 表示应该过滤
    """
    filename_lower = filename.lower()

    for pattern in fold_patterns:
        pattern_lower = pattern.lower()
        if pattern.startswith("*"):
            # 扩展名模式，如 *.egg-info
            if filename_lower.endswith(pattern_lower[1:]):
                return True
        elif filename_lower == pattern_lower:
            return True

    return False


# ============================================================================
# 精准读取工具
# ============================================================================

async def view_file(
    path: str,
    start_line: int = 1,
    end_line: Optional[int] = None,
    context_lines: int = 3
) -> str:
    """
    [Precision Tool] 精准读取文件的指定行范围

    用于替代全量读取，节省 Token。支持上下文行以便 Agent 理解代码结构。

    Args:
        path: 文件路径（相对或绝对）
        start_line: 起始行号（从1开始）
        end_line: 结束行号（None 表示到文件末尾）
        context_lines: 上下文行数，方便理解代码结构

    Returns:
        格式化的文件内容（带行号）

    Examples:
        >>> await view_file("src/main.py", start_line=50, end_line=100)
        >>> await view_file("src/main.py", start_line=50, end_line=50, context_lines=5)
    """
    try:
        file_path = Path(path)

        if not file_path.exists():
            return f"[ERROR] File not found: {file_path}"

        if not file_path.is_file():
            return f"[ERROR] Not a file: {file_path}"

        # 读取文件
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        total_lines = len(lines)

        # 规范化参数
        if start_line < 1:
            start_line = 1
        if end_line is None or end_line > total_lines:
            end_line = total_lines

        # 添加上下文
        real_start = max(1, start_line - context_lines)
        real_end = min(total_lines, end_line + context_lines)

        # 构建输出
        output = []
        output.append(f"--- File: {file_path} (lines {real_start}-{real_end} of {total_lines}) ---")
        output.append("")

        for i in range(real_start - 1, real_end):
            # 标记用户请求的核心区域
            if start_line <= (i + 1) <= end_line:
                prefix = " > "  # 用户请求的行
            else:
                prefix = "   "  # 上下文行

            # 去除行尾的换行符
            line_content = lines[i].rstrip()
            output.append(f"{i + 1:4d} |{prefix}{line_content}")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error viewing file {path}: {e}")
        return f"[ERROR] Failed to view file: {str(e)}"


async def smart_read(
    path: str,
    max_full_lines: int = 300,
    preview_lines: int = 100
) -> str:
    """
    [Smart Routing] 智能文件读取

    小文件（<300行）：返回全文
    大文件（>300行）：返回前100行 + 提示使用 view_file

    Args:
        path: 文件路径
        max_full_lines: 全量读取的最大行数
        preview_lines: 大文件预览行数

    Returns:
        文件内容或预览

    Examples:
        >>> await smart_read("config.json")  # 小文件，全文
        >>> await smart_read("large_log.txt")  # 大文件，预览
    """
    try:
        file_path = Path(path)

        if not file_path.exists():
            return f"[ERROR] File not found: {file_path}"

        # 读取文件
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        total_lines = len(lines)

        if total_lines <= max_full_lines:
            # 小文件：返回全文
            content = ''.join(lines).rstrip()
            return f"[OK] File: {file_path} ({total_lines} lines)\n{content}"
        else:
            # 大文件：返回预览
            preview = ''.join(lines[:preview_lines]).rstrip()
            return (
                f"[INFO] File is too large ({total_lines} lines). "
                f"Showing first {preview_lines} lines.\n"
                f"Use view_file(path={path}, start_line=1, end_line={preview_lines + 100}) to read more.\n"
                f"--- File: {file_path} (preview) ---\n{preview}\n"
                f"... ({total_lines - preview_lines} more lines)"
            )

    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        return f"[ERROR] Failed to read file: {str(e)}"


# ============================================================================
# 代码搜索工具
# ============================================================================

async def grep_code(
    pattern: str,
    path: str = ".",
    file_pattern: str = "*.py",
    context_lines: int = 2,
    case_sensitive: bool = False
) -> str:
    """
    [Precision Tool] 在指定目录中搜索代码内容

    使用正则表达式搜索，自动过滤无关目录（.git, __pycache__, node_modules 等）。
    复用 repo_mapper 的过滤逻辑。

    Args:
        pattern: 正则表达式模式
        path: 搜索路径（默认当前目录）
        file_pattern: 文件名模式（如 "*.py", "*.js"）
        context_lines: 上下文行数
        case_sensitive: 是否区分大小写

    Returns:
        搜索结果（带行号和上下文）

    Examples:
        >>> await grep_code("def calculate_", "src/", "*.py", context_lines=3)
        >>> await grep_code("TODO|FIXME", ".", "*.py", case_sensitive=False)
    """
    try:
        search_path = Path(path)

        if not search_path.exists():
            return f"[ERROR] Path not found: {search_path}"

        # 编译正则表达式
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return f"[ERROR] Invalid regex pattern: {e}"

        # 过滤模式（复用 repo_mapper 的逻辑）
        fold_patterns = [
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            ".env", "dist", "build", "target", "bin", "obj",
            ".next", ".nuxt", "coverage", ".pytest_cache", ".mypy_cache",
            "*.egg-info", ".pytest_cache", ".tox", "*.pyc",
        ]

        # 编译文件名模式
        file_regex = re.compile(file_pattern.replace("*", ".*"))

        results = []
        total_matches = 0

        # 遍历文件
        for root, dirs, files in os.walk(search_path):
            root_path = Path(root)

            # 过滤目录
            dirs[:] = [d for d in dirs if not _should_fold_file(d, fold_patterns)]

            # 搜索文件
            for filename in files:
                if not file_regex.match(filename):
                    continue

                if _should_fold_file(filename, fold_patterns):
                    continue

                file_path = root_path / filename

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()

                    # 搜索匹配的行
                    for i, line in enumerate(lines):
                        if regex.search(line):
                            # 添加上下文
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)

                            # 格式化输出
                            relative_path = file_path.relative_to(search_path)
                            results.append(f"\n--- {relative_path}:{i + 1} ---")

                            for j in range(start, end):
                                prefix = " > " if j == i else "   "
                                results.append(f"{j + 1:4d} |{prefix}{lines[j].rstrip()}")

                            total_matches += 1

                except Exception as e:
                    logger.warning(f"Failed to search {file_path}: {e}")
                    continue

        if total_matches == 0:
            return f"[INFO] No matches found for pattern: {pattern}"

        header = f"[OK] Found {total_matches} matches for '{pattern}' in {path}\n"
        return header + "\n".join(results)

    except Exception as e:
        logger.error(f"Error searching code: {e}")
        return f"[ERROR] Failed to search: {str(e)}"


# ============================================================================
# 工厂函数（保持与其他工具一致的风格）
# ============================================================================

def create_view_file_tool() -> Dict:
    """创建 view_file 工具定义"""
    from .fn_registry import Tool

    return Tool(
        name="view_file",
        label="View File",
        description="精准读取文件的指定行范围。节省 Token，适合查看大文件的部分内容。",
        group="file_ops",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径（相对或绝对）"
                },
                "start_line": {
                    "type": "integer",
                    "description": "起始行号（从1开始）",
                    "default": 1
                },
                "end_line": {
                    "type": "integer",
                    "description": "结束行号（None 表示到文件末尾）"
                },
                "context_lines": {
                    "type": "integer",
                    "description": "上下文行数，方便理解代码结构",
                    "default": 3
                }
            },
            "required": ["path"]
        },
        execute=view_file,
    )


def create_smart_read_tool() -> Dict:
    """创建 smart_read 工具定义"""
    from .fn_registry import Tool

    return Tool(
        name="smart_read",
        label="Smart Read",
        description="智能文件读取。小文件返回全文，大文件返回预览并提示使用 view_file。",
        group="file_ops",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径（相对或绝对）"
                },
                "max_full_lines": {
                    "type": "integer",
                    "description": "全量读取的最大行数",
                    "default": 300
                },
                "preview_lines": {
                    "type": "integer",
                    "description": "大文件预览行数",
                    "default": 100
                }
            },
            "required": ["path"]
        },
        execute=smart_read,
    )


def create_grep_code_tool() -> Dict:
    """创建 grep_code 工具定义"""
    from .fn_registry import Tool

    return Tool(
        name="grep_code",
        label="Grep Code",
        description="在代码中搜索正则表达式模式。自动过滤无关目录（.git, node_modules 等）。",
        group="code",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "正则表达式搜索模式"
                },
                "path": {
                    "type": "string",
                    "description": "搜索路径（默认当前目录）",
                    "default": "."
                },
                "file_pattern": {
                    "type": "string",
                    "description": "文件名模式（如 *.py, *.js）",
                    "default": "*.py"
                },
                "context_lines": {
                    "type": "integer",
                    "description": "匹配行的上下文行数",
                    "default": 2
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "是否区分大小写",
                    "default": False
                }
            },
            "required": ["pattern"]
        },
        execute=grep_code,
    )


# ============================================================================
# 批量创建函数
# ============================================================================

def create_precision_tools() -> List[Dict]:
    """
    创建所有精细化工具

    Returns:
        工具定义列表
    """
    return [
        create_view_file_tool(),
        # smart_read 已删除（与 view_file 功能重复）
        create_grep_code_tool(),
    ]
