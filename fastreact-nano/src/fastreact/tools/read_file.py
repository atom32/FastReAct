"""
ReadFileTool - Read file contents with safety limits

Follows Pi's philosophy: Simple, focused tool.
"""

import asyncio
from pathlib import Path
from typing import Any, Optional

from fastreact.core.tools import Tool


class ReadFileTool(Tool):
    """
    Read file contents with size limits and encoding support

    Safety features:
    - Size limit to prevent reading huge files
    - UTF-8 encoding with fallback
    - Line limit for preview mode
    """

    def __init__(
        self,
        max_size: int = 1024 * 1024,  # 1MB default
        max_lines: Optional[int] = None,  # No limit by default
    ):
        """
        Initialize ReadFileTool

        Args:
            max_size: Maximum file size in bytes (default: 1MB)
            max_lines: Maximum lines to read (None = no limit)
        """
        self._max_size = max_size
        self._max_lines = max_lines

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a file. "
            "Use this to examine source code, configuration files, logs, etc. "
            "Returns file contents as text."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read (relative or absolute)",
                },
                "start_line": {
                    "type": "integer",
                    "description": "Starting line number (1-indexed, optional)",
                },
                "end_line": {
                    "type": "integer",
                    "description": "Ending line number (optional, exclusive if start_line provided)",
                },
            },
            "required": ["path"],
        }

    async def execute(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        """
        Read file contents

        Args:
            path: File path
            start_line: Starting line (1-indexed)
            end_line: Ending line (exclusive if start_line provided)

        Returns:
            File contents
        """
        file_path = Path(path)

        # Check if file exists
        if not file_path.exists():
            return f"[ERROR] File not found: {path}"

        if not file_path.is_file():
            return f"[ERROR] Not a file: {path}"

        # Check file size
        try:
            file_size = file_path.stat().st_size
            if file_size > self._max_size:
                return (
                    f"[ERROR] File too large: {file_size} bytes "
                    f"(max: {self._max_size} bytes)"
                )
        except Exception as e:
            return f"[ERROR] Cannot access file: {e}"

        # Read file in thread
        try:
            def read_file():
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Apply line range if specified
                if start_line is not None:
                    start = max(0, start_line - 1)  # Convert to 0-indexed
                    if end_line is not None:
                        return lines[start:end_line]
                    else:
                        return lines[start:]
                elif end_line is not None:
                    return lines[:end_line]

                return lines

            lines = await asyncio.to_thread(read_file)

            # Apply max_lines limit
            if self._max_lines and len(lines) > self._max_lines:
                lines = lines[: self._max_lines]
                truncated = True
            else:
                truncated = False

            # Join lines with line numbers
            result = []
            for i, line in enumerate(lines, 1):
                result.append(f"{i:6d}\u2192{line}")

            content = "".join(result)

            if truncated:
                content += f"\n[... Truncated at {self._max_lines} lines ...]"

            return content

        except UnicodeDecodeError:
            return f"[ERROR] Cannot decode file (not UTF-8): {path}"
        except Exception as e:
            return f"[ERROR] Failed to read file: {type(e).__name__}: {e}"
