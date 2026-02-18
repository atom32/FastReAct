"""
EditFileTool - Text replacement editing

Follows Pi's philosophy: Simple, focused tool.
For complex operations, use Bash with sed/awk.
"""

import asyncio
import re
from pathlib import Path
from typing import Any, Optional

from fastreact.core.tools import Tool


class EditFileTool(Tool):
    """
    Edit files using text replacement

    This is a simple tool for common edits.
    For complex operations, use the exec tool with sed/awk.
    """

    def __init__(
        self,
        max_size: int = 1024 * 1024,  # 1MB default
    ):
        """
        Initialize EditFileTool

        Args:
            max_size: Maximum file size in bytes
        """
        self._max_size = max_size

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return (
            "Edit a file by replacing text. "
            "Replaces all occurrences of old_text with new_text. "
            "For complex edits, use the exec tool with sed/awk."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to edit",
                },
                "old_text": {
                    "type": "string",
                    "description": "Text to replace (must be unique)",
                },
                "new_text": {
                    "type": "string",
                    "description": "Replacement text",
                },
            },
            "required": ["path", "old_text", "new_text"],
        }

    async def execute(
        self,
        path: str,
        old_text: str,
        new_text: str,
        user_context: Optional["UserContext"] = None,
        **kwargs
    ) -> str:
        """
        Edit file by replacing text

        Args:
            path: File path
            old_text: Text to replace
            new_text: Replacement text
            user_context: User context (ignored, for multi-tenant compatibility)
            **kwargs: Additional arguments (ignored)

        Returns:
            Success message with number of replacements
        """
        file_path = Path(path)

        # Check if file exists
        if not file_path.exists():
            return f"[ERROR] File not found: {path}"

        # Check file size
        try:
            file_size = file_path.stat().st_size
            if file_size > self._max_size:
                return f"[ERROR] File too large: {file_size} bytes"
        except Exception as e:
            return f"[ERROR] Cannot access file: {e}"

        # Read and edit in thread
        try:
            def edit_file():
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check if old_text exists
                if old_text not in content:
                    return 0, content

                # Count occurrences
                count = content.count(old_text)

                # Replace
                new_content = content.replace(old_text, new_text)

                return count, new_content

            count, new_content = await asyncio.to_thread(edit_file)

            if count == 0:
                return f"[WARNING] Text not found in file: {old_text[:50]}..."

            # Write back
            def write_file():
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

            await asyncio.to_thread(write_file)

            return f"[OK] Replaced {count} occurrence(s) in {path}"

        except Exception as e:
            return f"[ERROR] Failed to edit file: {type(e).__name__}: {e}"
