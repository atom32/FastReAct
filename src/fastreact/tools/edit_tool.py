"""
Edit File Tool - 精准代码编辑工具

使用 Search & Replace Block 模式，避免 LLM 重写整个文件。
支持模糊匹配，容忍空格和缩进的差异。
"""

import os
import difflib
from pathlib import Path
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class EditFileTool:
    """
    文件编辑工具

    核心特性：
    1. Search & Replace Block 模式
    2. Fuzzy Matching（模糊匹配）
    3. Diff View 显示变更
    4. 智能错误提示

    使用示例：
        tool = EditFileTool()
        result = await tool.execute_async(
            path="src/main.py",
            search_block="def hello():\\n    print('hi')",
            replace_block="def hello():\\n    print('hello world')"
        )
    """

    def __init__(self, fuzzy_match: bool = True):
        """
        初始化编辑工具

        Args:
            fuzzy_match: 是否启用模糊匹配
        """
        self.fuzzy_match = fuzzy_match

    def _normalize_whitespace(self, text: str) -> str:
        """
        标准化空白字符（用于模糊匹配）

        将连续空白压缩为单个空格，但保留换行
        """
        lines = text.splitlines()
        normalized_lines = []

        for line in lines:
            # 压缩行内空白，但保留行首缩进
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            # 压缩行内空白
            compressed = ' '.join(stripped.split())

            # 恢复缩进
            if compressed:
                normalized_lines.append(' ' * indent + compressed)
            else:
                normalized_lines.append('')

        return '\n'.join(normalized_lines)

    def _find_match_fuzzy(
        self,
        content: str,
        search_block: str,
        threshold: float = 0.8
    ) -> Tuple[Optional[int], Optional[int], float]:
        """
        模糊搜索查找匹配块

        Args:
            content: 文件内容
            search_block: 要搜索的块
            threshold: 相似度阈值（0-1）

        Returns:
            (start_index, end_index, similarity) 或 (None, None, 0.0)
        """
        search_lines = search_block.splitlines()
        content_lines = content.splitlines()

        if len(search_lines) == 0:
            return None, None, 0.0

        # 标准化搜索块（用于比较）
        normalized_search = self._normalize_whitespace(search_block)
        normalized_search_lines = normalized_search.splitlines()

        best_match = (None, None, 0.0)

        # 滑动窗口搜索
        for i in range(len(content_lines) - len(search_lines) + 1):
            # 提取候选块
            candidate = '\n'.join(content_lines[i:i + len(search_lines)])

            # 计算相似度
            similarity = self._calculate_similarity(
                candidate,
                search_block,
                normalized_search
            )

            if similarity > best_match[2]:
                best_match = (i, i + len(search_lines), similarity)

        return best_match

    def _calculate_similarity(
        self,
        candidate: str,
        search_block: str,
        normalized_search: Optional[str] = None
    ) -> float:
        """
        计算候选块与搜索块的相似度

        使用多重策略：
        1. 完全匹配
        2. 标准化后匹配
        3. SequenceMatcher
        """
        # 策略1: 完全匹配
        if candidate == search_block:
            return 1.0

        # 策略2: 标准化后匹配
        if normalized_search is not None:
            normalized_candidate = self._normalize_whitespace(candidate)
            if normalized_candidate == normalized_search:
                return 0.95  # 标准化匹配，给高分

        # 策略3: SequenceMatcher
        # 先比较行级别的相似度
        candidate_lines = candidate.splitlines()
        search_lines = search_block.splitlines()

        if len(candidate_lines) != len(search_lines):
            # 行数不同，直接用字符串匹配
            matcher = difflib.SequenceMatcher(None, candidate, search_block)
            return matcher.ratio()

        # 逐行比较，计算平均相似度
        line_similarities = []
        for c_line, s_line in zip(candidate_lines, search_lines):
            if c_line == s_line:
                line_similarities.append(1.0)
            else:
                # 使用 SequenceMatcher
                matcher = difflib.SequenceMatcher(None, c_line, s_line)
                line_similarities.append(matcher.ratio())

        return sum(line_similarities) / len(line_similarities) if line_similarities else 0.0

    def _find_suggestions(
        self,
        content: str,
        search_block: str,
        top_n: int = 3
    ) -> List[Tuple[int, int, float, str]]:
        """
        找到最相似的匹配块（用于错误提示）

        Returns:
            List of (start, end, similarity, preview)
        """
        search_lines = search_block.splitlines()
        content_lines = content.splitlines()

        if len(search_lines) == 0:
            return []

        matches = []

        # 搜索所有可能的块
        for i in range(len(content_lines) - len(search_lines) + 1):
            end = i + len(search_lines)
            candidate = '\n'.join(content_lines[i:end])

            similarity = self._calculate_similarity(candidate, search_block)

            # 生成预览
            preview = candidate[:100] + "..." if len(candidate) > 100 else candidate

            matches.append((i, end, similarity, preview))

        # 按相似度排序，返回 top_n
        matches.sort(key=lambda x: x[2], reverse=True)
        return matches[:top_n]

    def _generate_diff(
        self,
        original: str,
        modified: str,
        filepath: str
    ) -> str:
        """
        生成 unified diff

        Args:
            original: 原始内容
            modified: 修改后的内容
            filepath: 文件路径（用于 diff header）

        Returns:
            Unified diff 文本
        """
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
            lineterm=""
        )

        return ''.join(diff)

    async def execute_async(
        self,
        path: str,
        search_block: str,
        replace_block: str,
        fuzzy: bool = True
    ) -> str:
        """
        编辑文件（搜索并替换代码块）

        Args:
            path: 文件路径（相对或绝对）
            search_block: 要搜索的代码块
            replace_block: 替换的代码块
            fuzzy: 是否启用模糊匹配

        Returns:
            操作结果（包含 diff）
        """
        # 解析路径
        if not os.path.isabs(path):
            # 相对路径，从当前目录解析
            path = os.path.abspath(path)

        # 检查文件是否存在
        if not os.path.exists(path):
            return f"""❌ File not found: {path}

Current directory: {os.getcwd()}
💡 Hint: Use 'ls' or 'ls_repo' to see available files."""

        if not os.path.isfile(path):
            return f"❌ Not a file: {path}"

        # 读取文件内容
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return f"❌ Failed to read file: {e}"

        # 标准化搜索块（去除首尾空白）
        search_block = search_block.strip()
        replace_block = replace_block.strip()

        # 查找匹配
        start_idx = None
        end_idx = None
        similarity = 0.0

        if fuzzy:
            # 模糊匹配
            start_idx, end_idx, similarity = self._find_match_fuzzy(
                content, search_block
            )

            if start_idx is None or similarity < 0.5:
                # 未找到好的匹配，提供建议
                suggestions = self._find_suggestions(content, search_block)

                error_msg = f"""❌ Could not find matching code block.

Search block:
```
{search_block[:200]}{'...' if len(search_block) > 200 else ''}
```

Similarity: {similarity:.2%} (threshold: 50%)

💡 Did you mean to match one of these?
"""

                for i, (start, end, sim, preview) in enumerate(suggestions[:3], 1):
                    error_msg += f"\n{i}. Similarity: {sim:.1%}\n   {preview}\n"

                return error_msg
        else:
            # 精确匹配
            lines = content.splitlines()
            search_lines = search_block.splitlines()

            # 查找完全匹配
            for i in range(len(lines) - len(search_lines) + 1):
                candidate = '\n'.join(lines[i:i + len(search_lines)])
                if candidate == search_block:
                    start_idx = i
                    end_idx = i + len(search_lines)
                    similarity = 1.0
                    break

            if start_idx is None:
                return f"""❌ Exact match not found.

Search block:
```
{search_block[:200]}{'...' if len(search_block) > 200 else ''}
```

💡 Hint: Try with fuzzy=True to tolerate whitespace differences."""

        # 执行替换
        content_lines = content.splitlines()
        original_lines = content_lines[:]

        # 替换内容
        replacement_lines = replace_block.splitlines()
        content_lines[start_idx:end_idx] = replacement_lines

        # 生成新内容
        new_content = '\n'.join(content_lines)

        # 生成 diff
        diff = self._generate_diff(
            '\n'.join(original_lines),
            new_content,
            os.path.basename(path)
        )

        # 写入文件
        try:
            # 创建备份
            backup_path = path + ".bak"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # 写入新内容
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            logger.info(f"File edited: {path} (similarity: {similarity:.2%})")

            # 返回成功信息
            return f"""✅ File edited successfully

📄 File: {path}
📊 Match similarity: {similarity:.1%}

📝 Changes:
```diff
{diff}
```

💾 Backup saved to: {backup_path}
"""

        except Exception as e:
            # 写入失败，尝试恢复备份
            if os.path.exists(backup_path):
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    return f"❌ Failed to write file: {e}\n✅ Restored from backup."
                except Exception as restore_error:
                    return f"❌ Failed to write: {e}\n❌ Failed to restore: {restore_error}"
            else:
                return f"❌ Failed to write file: {e}"

    def _get_description(self) -> str:
        return """精准编辑文件（Search & Replace 模式）

使用搜索和替换的方式修改代码，而不是重写整个文件。

**核心特性**：
- Search & Replace Block：指定要替换的代码块
- Fuzzy Matching：容忍空格和缩进的差异
- Diff View：显示变更内容
- 自动备份：修改前自动创建 .bak 备份

**使用场景**：
- 修改函数实现
- 更新配置
- 修复 bug
- 重构代码

**注意事项**：
- search_block 必须与文件内容精确匹配（或足够相似）
- replace_block 会完全替换 search_block
- 建议先用 ls_repo 或 cat 查看文件内容
- 修改失败会自动恢复"""

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径（相对或绝对）"
                },
                "search_block": {
                    "type": "string",
                    "description": "要搜索的代码块（精确匹配或模糊匹配）"
                },
                "replace_block": {
                    "type": "string",
                    "description": "替换的代码块"
                },
                "fuzzy": {
                    "type": "boolean",
                    "description": "是否启用模糊匹配（默认 True）",
                    "default": True
                }
            },
            "required": ["path", "search_block", "replace_block"]
        }


# ============================================================================
# 函数式接口（兼容 fn_registry）
# ============================================================================

_global_edit_tool: Optional[EditFileTool] = None


def get_edit_tool(fuzzy_match: bool = True) -> EditFileTool:
    """获取全局 EditFileTool 实例"""
    global _global_edit_tool
    if _global_edit_tool is None:
        _global_edit_tool = EditFileTool(fuzzy_match=fuzzy_match)
    return _global_edit_tool
