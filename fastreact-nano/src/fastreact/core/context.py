"""
Context Monitor - Token circuit breaker for FastReAct Nano v2.0

Prevents token explosion by:
1. Monitoring total context size
2. Providing explicit preview/truncation helpers for diagnostics
3. Managing conversation history
4. Filesystem memory (Ghost Map)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import re

from fastreact.core.config import DEFAULT_MAX_TOOL_OUTPUT_CHARS

# Try to import tiktoken for accurate token counting
# Falls back to simple estimation if not available
try:
    import tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False


# Tool categories for intelligent truncation
TOOL_CATEGORIES = {
    # File operations - preserve structure and syntax
    "read_file": {
        "category": "file_content",
        "preserve": "structure",  # Preserve line numbers, syntax highlighting
        "head_ratio": 0.9,  # Keep 90% head for file content
        "tail_ratio": 0.1,
    },
    "write_file": {
        "category": "file_operation",
        "preserve": "result",  # Just need success/fail
        "max_chars": 500,  # Short result for write operations
    },
    "edit_file": {
        "category": "file_operation",
        "preserve": "result",  # Just need success/fail
        "max_chars": 500,
    },

    # Command execution - preserve errors and status
    "exec": {
        "category": "command",
        "preserve": "errors",  # Preserve error messages and exit status
        "head_ratio": 0.5,
        "tail_ratio": 0.5,
    },

    # Search/query - preserve matches and context
    "grep": {
        "category": "search",
        "preserve": "matches",  # Preserve matching lines
        "max_chars": 3000,  # Allow more for search results
    },
    "find": {
        "category": "search",
        "preserve": "results",
        "max_chars": 3000,
    },

    # External tools - preserve key information
    "web_search": {
        "category": "external",
        "preserve": "key_info",  # Preserve search results
        "max_chars": 2000,
    },
    "ask": {
        "category": "external",
        "preserve": "key_info",
        "max_chars": 2000,
    },

    # Default category for unknown tools
    "default": {
        "category": "generic",
        "preserve": "balanced",
        "head_ratio": 0.8,
        "tail_ratio": 0.2,
    }
}


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
    - Accurate token counting with tiktoken (when available)
    - Fallback to simple estimation (4:1 character ratio)
    - Smart tool output truncation
    - Context window monitoring
    - Usage statistics
    """

    def __init__(
        self,
        max_tokens: int = 128000,
        warning_threshold: float = 0.8,
        max_tool_output_chars: int = DEFAULT_MAX_TOOL_OUTPUT_CHARS,
        model: str = "gpt-4o",
        use_tiktoken: bool = True,
    ):
        """
        Initialize context monitor

        Args:
            max_tokens: Maximum context window size (default: 128k for GPT-4)
            warning_threshold: Warning threshold (0.0-1.0, default: 0.8)
            max_tool_output_chars: Maximum chars per tool output for explicit
                preview/truncation helpers (default: 20000)
            model: Model name for tiktoken encoding (default: gpt-4o)
            use_tiktoken: Whether to use tiktoken if available (default: True)
        """
        self._max_tokens = max_tokens
        self._warning_threshold = warning_threshold
        self._max_tool_output_chars = max_tool_output_chars
        self._stats = ContextStats()

        # Initialize tokenizer
        self._model = model
        self._use_tiktoken = use_tiktoken and _TIKTOKEN_AVAILABLE
        self._tokenizer = None

        if self._use_tiktoken:
            try:
                self._tokenizer = tiktoken.encoding_for_model(model)
            except KeyError:
                # Model not found, try cl100k_base encoding (GPT-4/GPT-3.5-turbo)
                try:
                    self._tokenizer = tiktoken.get_encoding("cl100k_base")
                except Exception:
                    # Fallback to simple estimation
                    self._use_tiktoken = False

    def estimate_tokens(self, text: str) -> int:
        """
        Token counting with tiktoken or fallback estimation

        Strategy:
        1. Use tiktoken for accurate counting (when available)
        2. Fallback to simple estimation (1 token ≈ 4 chars)

        Args:
            text: Text to count tokens

        Returns:
            Token count
        """
        if not text:
            return 0

        # Use tiktoken if available
        if self._use_tiktoken and self._tokenizer:
            try:
                return len(self._tokenizer.encode(text))
            except Exception:
                # Fallback to simple estimation on error
                pass

        # Fallback: simple estimation (1 token ≈ 4 characters)
        # This is reasonably accurate for English text
        # For mixed content, actual tokens may vary by ±20%
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

    def truncate_by_category(
        self,
        output: str,
        tool_name: str = "unknown",
    ) -> str:
        """
        Category-aware tool output truncation

        Different tools require different truncation strategies:
        - File content (read_file): Preserve structure, 90% head for syntax
        - File operations (write_file, edit_file): Just success/fail result
        - Commands (exec): Preserve errors and exit status, 50/50 split
        - Search (grep, find): Preserve matches, allow more content
        - External (web_search, ask): Preserve key info, remove fluff

        Args:
            output: Tool output to truncate
            tool_name: Name of the tool

        Returns:
            Truncated or original output
        """
        # Get tool category configuration
        tool_config = TOOL_CATEGORIES.get(tool_name, TOOL_CATEGORIES["default"])
        category = tool_config["category"]
        preserve_mode = tool_config["preserve"]

        # Get limit based on category
        if "max_chars" in tool_config:
            limit = tool_config["max_chars"]
        else:
            limit = self._max_tool_output_chars

        # If under limit, no truncation needed
        if len(output) <= limit:
            return output

        # Update stats
        self._stats.truncated_count += 1
        self._stats.last_truncated = tool_name

        # Truncate based on category
        if preserve_mode == "structure":
            # File content: preserve more head for syntax/structure
            return self._truncate_structure(output, limit, tool_name)

        elif preserve_mode == "result":
            # File operations: just show success/fail
            return self._truncate_to_result(output, limit, tool_name)

        elif preserve_mode == "errors":
            # Commands: preserve errors and exit status
            return self._truncate_preserve_errors(output, limit, tool_name)

        elif preserve_mode == "matches":
            # Search: preserve matching lines
            return self._truncate_preserve_matches(output, limit, tool_name)

        elif preserve_mode == "key_info":
            # External: preserve key information
            return self._truncate_key_info(output, limit, tool_name)

        else:  # "balanced" or unknown
            # Default: balanced head/tail
            head_ratio = tool_config.get("head_ratio", 0.8)
            tail_ratio = tool_config.get("tail_ratio", 0.2)
            return self._truncate_balanced(output, limit, tool_name, head_ratio, tail_ratio)

    def _truncate_structure(
        self,
        output: str,
        limit: int,
        tool_name: str
    ) -> str:
        """Truncate file content while preserving structure (line numbers, syntax)"""
        # For file content, keep more head to preserve imports/definitions
        head_ratio = 0.9
        tail_ratio = 0.1

        head_chars = int(limit * head_ratio)
        tail_chars = int(limit * tail_ratio)

        # Try to break at line boundaries
        head = output[:head_chars]
        if tail_chars > 0:
            last_newline = output.rfind("\n", 0, -tail_chars)
            if last_newline > 0:
                tail = output[last_newline+1:]
            else:
                tail = output[-tail_chars:]
        else:
            tail = ""

        truncated_msg = (
            f"\n... [File content truncated] ...\n"
            f"Tool: {tool_name}\n"
            f"Original: {len(output)} chars, Showing: {len(head) + len(tail)} chars\n"
            f"Use read_file with start_line/end_line for specific sections\n"
            f"... [End of truncation] ...\n\n"
        )

        return f"{head}{truncated_msg}{tail}"

    def _truncate_to_result(
        self,
        output: str,
        limit: int,
        tool_name: str
    ) -> str:
        """Truncate to just show success/fail result"""
        # For write/edit operations, we mainly care about success/fail
        # Check for error indicators
        error_indicators = ["[ERROR]", "Error:", "Failed", "Exception"]
        has_error = any(indicator in output for indicator in error_indicators)

        if has_error:
            # Keep the error message
            # Find the error message (usually at start or end)
            lines = output.split("\n")
            error_lines = []
            for line in lines[:10]:  # Check first 10 lines
                if any(indicator in line for indicator in error_indicators):
                    error_lines.append(line)
                elif error_lines:
                    error_lines.append(line)
                if len(error_lines) >= 3:  # Found enough context
                    break

            result = "\n".join(error_lines[:5])  # Max 5 lines of error
            if len(result) > limit:
                result = result[:limit]

            return result
        else:
            # Success - just show brief confirmation
            return f"[OK] {tool_name} completed successfully"

    def _truncate_preserve_errors(
        self,
        output: str,
        limit: int,
        tool_name: str
    ) -> str:
        """Truncate command output while preserving errors"""
        # Look for error patterns
        error_patterns = [
            r"error",
            r"failed",
            r"exception",
            r"traceback",
            r"exit code",
        ]

        lines = output.split("\n")
        important_lines = []
        error_sections = []

        for i, line in enumerate(lines):
            line_lower = line.lower()
            is_error = any(re.search(pattern, line_lower) for pattern in error_patterns)

            if is_error:
                # Keep this line and surrounding context
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                error_sections.extend(lines[start:end])
            elif len(important_lines) < 10:
                # Keep some normal output at the start
                important_lines.append(line)

        # Combine: important lines + error sections
        combined = important_lines + list(set(error_sections))

        # Build result
        result_lines = []
        total_chars = 0
        for line in combined:
            if total_chars + len(line) + 1 > limit:
                break
            result_lines.append(line)
            total_chars += len(line) + 1

        result = "\n".join(result_lines)

        if len(result) < len(output):
            result += f"\n... [Command output truncated from {len(output)} to {len(result)} chars]"

        return result

    def _truncate_preserve_matches(
        self,
        output: str,
        limit: int,
        tool_name: str
    ) -> str:
        """Truncate search results while preserving matches"""
        lines = output.split("\n")

        # Look for match lines (typically contain the search term or file:line format)
        match_lines = []
        context_lines = []

        for line in lines:
            # Keep match indicators, file references, line numbers
            if (":" in line or  # File:line format
                line.strip().startswith("-") or  # Bullet/context
                len(line.strip()) < 100):  # Short lines are likely matches
                match_lines.append(line)
            elif len(match_lines) + len(context_lines) < 100:  # Keep some context
                context_lines.append(line)

        # Prioritize matches
        result_lines = match_lines[:80] + context_lines[:20]

        # Build result respecting limit
        result = ""
        total_chars = 0
        for line in result_lines:
            if total_chars + len(line) + 1 > limit:
                break
            result += line + "\n"
            total_chars += len(line) + 1

        if not result:
            # Fallback to simple truncation
            return output[:limit]

        dropped = len(result_lines) - len(result.split("\n"))
        if dropped > 0:
            result += f"\n... [Dropped {dropped} more lines] ..."

        return result

    def _truncate_key_info(
        self,
        output: str,
        limit: int,
        tool_name: str
    ) -> str:
        """Truncate external tool output preserving key information"""
        # Remove common fluff patterns
        fluff_patterns = [
            r"Here are the (search )?results?",
            r"Based on my search?",
            r"I found?",
            r"According to",
        ]

        lines = output.split("\n")
        key_lines = []

        for line in lines:
            line_stripped = line.strip()

            # Skip fluff
            is_fluff = any(re.search(pattern, line, re.IGNORECASE)
                          for pattern in fluff_patterns)

            if not is_fluff and line_stripped:
                key_lines.append(line)

            if len("\n".join(key_lines)) > limit:
                break

        result = "\n".join(key_lines)

        # Trim to limit if needed
        if len(result) > limit:
            result = result[:limit]

        return result

    def _truncate_balanced(
        self,
        output: str,
        limit: int,
        tool_name: str,
        head_ratio: float = 0.8,
        tail_ratio: float = 0.2,
    ) -> str:
        """Default balanced truncation (head + tail)"""
        head_chars = int(limit * head_ratio)
        tail_chars = int(limit * tail_ratio)

        head = output[:head_chars]

        if tail_chars > 0:
            # Try to break at word boundary
            tail_start = max(0, len(output) - tail_chars)
            space_pos = output.rfind(" ", 0, tail_start)
            if space_pos > 0:
                tail = output[space_pos+1:]
            else:
                tail = output[-tail_chars:]
        else:
            tail = ""

        truncated_msg = (
            f"\n... [Output truncated] ...\n"
            f"Tool: {tool_name}\n"
            f"Original: {len(output)} chars, Showing: {len(head) + len(tail)} chars\n"
            f"... [End of truncation] ...\n\n"
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

        # Token counting method indicator
        method = "tiktoken" if self._use_tiktoken else "estimate"

        return f"{status} Context: {percentage:5.1f}% [{bar}] {self._stats.total_tokens}/{self._max_tokens} tokens ({method})"

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
    "TOOL_CATEGORIES",
]
