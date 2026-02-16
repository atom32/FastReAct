"""
WriteFileTool - Write files with safety checks

Follows Pi's philosophy: Simple, focused tool.
"""

import asyncio
from pathlib import Path
from typing import Any, Optional

from fastreact.core.tools import Tool


class WriteFileTool(Tool):
    """
    Write files with safety features

    Safety features:
    - Path protection (prevents overwriting critical paths)
    - UTF-8 encoding enforcement
    - Atomic write (write to temp, then rename)
    - Size limit
    """

    def __init__(
        self,
        max_size: int = 1024 * 1024,  # 1MB default
        protected_paths: Optional[list[str]] = None,
    ):
        """
        Initialize WriteFileTool

        Args:
            max_size: Maximum file size in bytes (default: 1MB)
            protected_paths: List of protected path patterns
        """
        self._max_size = max_size
        self._protected_paths = protected_paths or []

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return (
            "Write content to a file. "
            "Use this to create or modify source code, configuration files, etc. "
            "Creates parent directories if they don't exist."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write (relative or absolute)",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        }

    async def execute(self, path: str, content: str) -> str:
        """
        Write content to file

        Args:
            path: File path
            content: Content to write

        Returns:
            Success message
        """
        file_path = Path(path)

        # Check protected paths
        for protected in self._protected_paths:
            if file_path.match(protected):
                return f"[ERROR] Protected path, cannot write: {path}"

        # Check content size
        content_size = len(content.encode("utf-8"))
        if content_size > self._max_size:
            return (
                f"[ERROR] Content too large: {content_size} bytes "
                f"(max: {self._max_size} bytes)"
            )

        # Create parent directories
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return f"[ERROR] Cannot create parent directory: {e}"

        # Write file in thread
        try:
            def write_file():
                # Write to temporary file first
                temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(content)

                # Atomic rename
                temp_path.replace(file_path)

            await asyncio.to_thread(write_file)

            bytes_written = len(content.encode("utf-8"))
            lines_written = content.count("\n") + 1

            return (
                f"[OK] Wrote {bytes_written} bytes ({lines_written} lines) to {path}"
            )

        except Exception as e:
            return f"[ERROR] Failed to write file: {type(e).__name__}: {e}"
