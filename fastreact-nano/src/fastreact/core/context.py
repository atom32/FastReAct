"""
Context Monitor - Token circuit breaker for FastReAct Nano v2.0

Prevents token explosion by:
1. Monitoring total context size
2. Truncating tool outputs
3. Managing conversation history
4. Filesystem memory (Ghost Map)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import re


@dataclass
class ContextStats:
    """Context usage statistics"""
    total_tokens: int = 0
    message_count: int = 0
    tool_outputs: int = 0
    truncated_count: int = 0
    last_truncated: Optional[str] = None


class ContextMonitor:
    """
    Context monitor and token circuit breaker

    Features:
    - Fast token estimation (no tiktoken dependency)
    - Smart tool output truncation
    - Context window monitoring
    - Usage statistics
    """

    def __init__(
        self,
        max_tokens: int = 128000,
        warning_threshold: float = 0.8,
        max_tool_output_chars: int = 5000,
    ):
        """
        Initialize context monitor

        Args:
            max_tokens: Maximum context window size (default: 128k for GPT-4)
            warning_threshold: Warning threshold (0.0-1.0, default: 0.8)
            max_tool_output_chars: Maximum chars per tool output (default: 5000)
        """
        self._max_tokens = max_tokens
        self._warning_threshold = warning_threshold
        self._max_tool_output_chars = max_tool_output_chars
        self._stats = ContextStats()

    def estimate_tokens(self, text: str) -> int:
        """
        Fast token estimation

        Strategy: 1 token ≈ 4 chars (English) / 1 char (Chinese)
        Uses simple length-based estimation for speed.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Simple estimation: 1 token ≈ 4 characters
        # This is fast but not perfectly accurate
        # For better accuracy, we could use tiktoken, but that adds dependency
        return int(len(text) * 0.25)

    def truncate_tool_output(
        self,
        output: str,
        tool_name: str = "unknown",
    ) -> str:
        """
        Truncate tool output if too large

        Strategy: Keep 80% head + 20% tail for context awareness

        Args:
            output: Tool output to truncate
            tool_name: Name of the tool (for logging)

        Returns:
            Truncated or original output
        """
        if len(output) <= self._max_tool_output_chars:
            return output

        # Update stats
        self._stats.truncated_count += 1
        self._stats.last_truncated = tool_name

        # Smart truncation: 80% head + 20% tail
        head_chars = int(self._max_tool_output_chars * 0.8)
        tail_chars = int(self._max_tool_output_chars * 0.2)

        head = output[:head_chars]
        tail = output[-tail_chars:] if tail_chars > 0 else ""

        truncated_msg = (
            f"\n... [System: Tool output truncated] ...\n"
            f"Tool: {tool_name}\n"
            f"Original size: {len(output)} chars\n"
            f"Shown: {head_chars + len(tail)} chars\n"
            f"Use filtering commands (head, tail, grep) to view specific parts\n"
            f"... [End of truncation notice] ...\n\n"
        )

        return f"{head}{truncated_msg}{tail}"

    def check_context_size(self, messages: list[dict]) -> tuple[bool, float]:
        """
        Check if context size is within limits

        Args:
            messages: List of message dicts

        Returns:
            (is_safe, usage_ratio) - Safety status and usage ratio
        """
        total_tokens = 0

        for msg in messages:
            content = msg.get("content", "")
            total_tokens += self.estimate_tokens(content)

        # Update stats
        self._stats.total_tokens = total_tokens
        self._stats.message_count = len(messages)

        usage_ratio = total_tokens / self._max_tokens if self._max_tokens > 0 else 0

        is_safe = usage_ratio < self._warning_threshold

        return is_safe, usage_ratio

    def get_stats(self) -> dict:
        """Get current statistics"""
        return {
            "total_tokens": self._stats.total_tokens,
            "message_count": self._stats.message_count,
            "tool_outputs": self._stats.tool_outputs,
            "truncated_count": self._stats.truncated_count,
            "usage_ratio": self._stats.total_tokens / self._max_tokens if self._max_tokens > 0 else 0,
            "last_truncated": self._stats.last_truncated,
        }

    def get_progress_bar(self) -> str:
        """
        Get visual progress bar for context usage

        Returns:
            String representation of context usage
        """
        usage_ratio = self._stats.total_tokens / self._max_tokens if self._max_tokens > 0 else 0
        percentage = min(usage_ratio * 100, 100)

        # Build progress bar
        bar_width = 30
        filled = int(bar_width * usage_ratio)
        bar = "=" * filled + " " * (bar_width - filled)

        # Color indicator
        if usage_ratio < 0.5:
            status = "[OK]"
        elif usage_ratio < 0.8:
            status = "[WARN]"
        else:
            status = "[ALERT]"

        return f"{status} Context: {percentage:5.1f}% [{bar}] {self._stats.total_tokens}/{self._max_tokens} tokens"

    def reset_stats(self):
        """Reset statistics"""
        self._stats = ContextStats()


@dataclass
class FilesystemNode:
    """A node in the filesystem memory tree"""
    name: str
    type: str  # "file", "dir", "symlink"
    full_path: str
    children: Dict[str, "FilesystemNode"] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FilesystemMemory:
    """
    Filesystem memory (Ghost Map) for spatial awareness

    Maintains an in-memory representation of the filesystem
    that the agent has explored, reducing the need for repeated ls commands.

    Features:
    - Passive observation: learns from tool usage
    - ASCII tree rendering: clear visual representation
    - Smart injection: provides context before LLM thinks
    - Cross-platform: handles Windows/Unix paths
    """

    def __init__(
        self,
        max_tree_depth: int = 3,
        max_files_per_dir: int = 50,
        enable_tree_rendering: bool = True,
    ):
        """
        Initialize filesystem memory

        Args:
            max_tree_depth: Maximum depth to render (default: 3)
            max_files_per_dir: Max files to show per directory (default: 50)
            enable_tree_rendering: Enable ASCII tree rendering (default: True)
        """
        self._tree: Dict[str, FilesystemNode] = {}
        self._cwd = str(Path.cwd())
        self._max_tree_depth = max_tree_depth
        self._max_files_per_dir = max_files_per_dir
        self._enable_tree_rendering = enable_tree_rendering

        # Statistics
        self._total_nodes = 0
        self._last_updated = None

    def update_from_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: str,
    ) -> None:
        """
        Update filesystem memory based on tool execution

        Args:
            tool_name: Name of the tool executed
            args: Tool arguments
            result: Tool result/output
        """
        if tool_name == "exec":
            # Parse ls commands
            command = args.get("command", "")
            if self._is_ls_command(command):
                self._parse_ls_output(command, result)
            # Parse cd commands
            elif self._is_cd_command(command):
                self._parse_cd_command(command, result)

        elif tool_name == "read_file":
            # Record that we've seen this file
            path = args.get("path", "")
            if path:
                self._add_file(path)

        elif tool_name == "write_file":
            # Record file creation/modification
            path = args.get("path", "")
            if path:
                self._add_file(path)

        elif tool_name == "edit_file":
            # Record file modification
            path = args.get("path", "")
            if path:
                self._add_file(path)

        self._last_updated = None  # Mark as updated

    def _is_ls_command(self, command: str) -> bool:
        """Check if command is an ls variant"""
        cmd_lower = command.lower().strip()
        return cmd_lower.startswith("ls") or "ls" in cmd_lower

    def _is_cd_command(self, command: str) -> bool:
        """Check if command is a cd variant"""
        cmd_lower = command.lower().strip()
        return cmd_lower.startswith("cd")

    def _parse_ls_output(self, command: str, output: str) -> None:
        """
        Parse ls command output and update tree

        Handles:
        - ls (current dir)
        - ls <path> (specific dir)
        - ls -R (recursive)
        """
        if not output or "[ERROR]" in output:
            return

        # Extract path from command
        parts = command.strip().split()
        if len(parts) > 1 and not parts[1].startswith("-"):
            # ls <path>
            target_path = parts[1]
        else:
            # ls (current dir)
            target_path = "."

        # Normalize path
        base_path = Path(self._cwd) / target_path
        try:
            base_path = base_path.resolve()
        except Exception:
            return

        # Parse output lines
        lines = output.split("\n")
        entries = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("[") or line.startswith("total"):
                continue

            # Parse directory indicator
            is_dir = line.endswith("/") or line.startswith("d")
            name = line.rstrip("/").strip()

            # Skip hidden files (usually)
            if name.startswith("."):
                continue

            entries.append((name, "dir" if is_dir else "file"))

        # Add to tree
        self._add_directory(str(base_path), entries)

    def _parse_cd_command(self, command: str, output: str) -> None:
        """Parse cd command and update cwd"""
        if "[ERROR]" in output:
            return

        parts = command.strip().split()
        if len(parts) > 1:
            target = parts[1]
            new_path = Path(self._cwd) / target
            try:
                self._cwd = str(new_path.resolve())
            except Exception:
                pass

    def _add_directory(self, dir_path: str, entries: list) -> None:
        """
        Add directory with entries to tree

        Args:
            dir_path: Directory path
            entries: List of (name, type) tuples
        """
        dir_path = str(Path(dir_path).resolve())

        # Get or create parent nodes
        parts = Path(dir_path).parts
        current = self._tree

        for i, part in enumerate(parts):
            if part not in current:
                current[part] = FilesystemNode(
                    name=part,
                    type="dir" if i < len(parts) - 1 else "dir",
                    full_path=str(Path(*parts[:i+1])),
                )
                self._total_nodes += 1
            current = current[part].children

        # Add entries
        for name, entry_type in entries:
            if name not in current:
                current[name] = FilesystemNode(
                    name=name,
                    type=entry_type,
                    full_path=str(Path(dir_path) / name),
                )
                self._total_nodes += 1

    def _add_file(self, file_path: str) -> None:
        """Add file to tree"""
        try:
            file_path = str(Path(file_path).resolve())
        except Exception:
            return

        parts = Path(file_path).parts
        current = self._tree

        # Navigate/create parent dirs
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = FilesystemNode(
                    name=part,
                    type="dir",
                    full_path=str(Path(*parts[:i+1])),
                )
                self._total_nodes += 1
            current = current[part].children

        # Add file
        filename = parts[-1]
        if filename and filename not in current:
            current[filename] = FilesystemNode(
                name=filename,
                type="file",
                full_path=file_path,
            )
            self._total_nodes += 1

    def _render_ascii_tree(
        self,
        node_dict: Dict[str, FilesystemNode],
        prefix: str = "",
        is_last: bool = True,
        depth: int = 0,
    ) -> list:
        """
        Render subtree as ASCII tree

        Args:
            node_dict: Dictionary of nodes
            prefix: Line prefix for indentation
            is_last: Whether this is the last sibling
            depth: Current depth

        Returns:
            List of strings (tree lines)
        """
        if depth > self._max_tree_depth:
            return ["... (truncated, max depth reached)"]

        lines = []
        items = list(node_dict.items())

        # Limit items per directory
        if len(items) > self._max_files_per_dir:
            items = items[:self._max_files_per_dir]
            truncated = True
        else:
            truncated = False

        for i, (name, node) in enumerate(items):
            is_last_item = i == len(items) - 1 and not truncated

            # Tree connector
            if is_last_item:
                connector = "└── "
                child_prefix = prefix + "    "
            else:
                connector = "├── "
                child_prefix = prefix + "│   "

            # Node icon (use text markers for cross-platform compatibility)
            if node.type == "dir":
                icon = "[DIR]"
            elif node.type == "file":
                icon = "[FILE]"
            else:
                icon = "[LINK]"

            # Add line
            lines.append(f"{prefix}{connector}{icon} {name}")

            # Recursively render children
            if node.children and depth < self._max_tree_depth:
                child_lines = self._render_ascii_tree(
                    node.children,
                    child_prefix,
                    is_last_item,
                    depth + 1,
                )
                lines.extend(child_lines)

        if truncated:
            lines.append(f"{prefix}└── ... ({len(node_dict) - self._max_files_per_dir} more items)")

        return lines

    def get_prompt_injection(self) -> str:
        """
        Generate context injection for system prompt

        Returns:
            String to inject before LLM thinking
        """
        if not self._tree:
            return ""

        if not self._enable_tree_rendering:
            return ""

        lines = [
            "\n[FileSystem Memory]",
            f"Current Directory: {self._cwd}",
            f"Known Structure ({self._total_nodes} nodes):",
        ]

        tree_lines = self._render_ascii_tree(self._tree)
        lines.extend(tree_lines)

        lines.append(
            f"\n[Note: This is a partial map based on exploration. "
            f"Max depth: {self._max_tree_depth}, "
            f"Max items per dir: {self._max_files_per_dir}]"
        )

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get filesystem memory statistics"""
        return {
            "total_nodes": self._total_nodes,
            "current_dir": self._cwd,
            "tree_depth": self._max_tree_depth,
            "max_files_per_dir": self._max_files_per_dir,
            "last_updated": self._last_updated,
        }

    def reset(self):
        """Reset filesystem memory"""
        self._tree = {}
        self._cwd = str(Path.cwd())
        self._total_nodes = 0
        self._last_updated = None


__all__ = [
    "ContextMonitor",
    "ContextStats",
    "FilesystemMemory",
    "FilesystemNode",
]
