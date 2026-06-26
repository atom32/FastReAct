"""
ExecTool - Execute bash commands with safety checks

Follows Pi's philosophy: The AI can use this for complex operations.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Optional

from fastreact.core.tools import Tool
from fastreact.tools.path_guard import user_working_dir


class ExecTool(Tool):
    """
    Execute bash/shell commands

    Safety features:
    - Timeout to prevent hanging
    - Working directory control
    - No interactive commands
    - Windows (cmd) and Unix (bash) support
    """

    def __init__(
        self,
        timeout: int = 30,  # 30 seconds default
        working_dir: Optional[Path] = None,
    ):
        """
        Initialize ExecTool

        Args:
            timeout: Command timeout in seconds
            working_dir: Working directory (default: current directory)
        """
        self._timeout = timeout
        self._working_dir = working_dir or Path.cwd()

    @property
    def name(self) -> str:
        return "exec"

    @property
    def description(self) -> str:
        return (
            "Execute a shell command and return the output. "
            "Use this for running build tools, tests, git commands, etc. "
            "The command runs in a subprocess with a timeout."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                },
            },
            "required": ["command"],
        }

    async def execute(self, command: str, user_context: Optional["UserContext"] = None, **kwargs) -> str:
        """
        Execute shell command

        Args:
            command: Command to execute
            user_context: User context (ignored, for multi-tenant compatibility)
            **kwargs: Additional arguments (ignored)

        Returns:
            Command output
        """
        # Detect dangerous commands
        dangerous = ["rm -rf /", "del /q /s c:\\", "format", "mkfs"]
        if any(d in command.lower() for d in dangerous):
            return "[ERROR] Dangerous command blocked"

        # Prepare shell
        if sys.platform == "win32":
            shell = True  # Use cmd.exe on Windows
        else:
            shell = True  # Use bash on Unix

        try:
            working_dir = user_working_dir(self._working_dir, user_context=user_context)

            # Run command in subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=shell,
                cwd=str(working_dir),
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self._timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return f"[ERROR] Command timed out after {self._timeout}s"

            # Decode output
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            # Build result
            result_parts = []

            if stdout_text:
                result_parts.append(stdout_text)

            if stderr_text:
                result_parts.append(f"[STDERR]\n{stderr_text}")

            if process.returncode != 0:
                result_parts.append(f"[EXIT CODE: {process.returncode}]")

            return "\n".join(result_parts) if result_parts else "[OK] No output"

        except Exception as e:
            return f"[ERROR] Failed to execute command: {type(e).__name__}: {e}"
