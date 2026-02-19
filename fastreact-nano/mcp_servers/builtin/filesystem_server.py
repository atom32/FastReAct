#!/usr/bin/env python3
"""
FastReAct Nano - File Operations MCP Server

A standalone MCP server implementing file operations.
Can be run independently or used by FastReAct Agent.

Usage:
    # Run standalone
    python file_mcp_server.py

    # Used by FastReAct Agent
    from fastreact.mcp.protocol import SimpleMCPStdio
    mcp = SimpleMCPStdio("python", ["file_mcp_server.py"])
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastreact.mcp.server import SimpleMCPServer


class FileMCPServer(SimpleMCPServer):
    """
    MCP Server for file operations

    Implements:
    - read_file: Read file contents
    - write_file: Write/create files
    - list_dir: List directory contents
    - file_info: Get file metadata
    """

    def __init__(self, base_path: str = "."):
        """
        Initialize file MCP server

        Args:
            base_path: Base directory for file operations (sandbox)
        """
        super().__init__()
        self._base_path = Path(base_path).resolve()

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register file operation tools"""

        # read_file
        self.register_tool(
            name="read_file",
            description="Read contents of a text file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to base directory",
                    },
                },
                "required": ["path"],
            },
        )

        # write_file
        self.register_tool(
            name="write_file",
            description="Write content to a file (creates parent dirs if needed)",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to base directory",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write",
                    },
                },
                "required": ["path", "content"],
            },
        )

        # list_dir
        self.register_tool(
            name="list_dir",
            description="List contents of a directory",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (default: base directory)",
                    },
                },
                "required": [],
            },
        )

        # file_info
        self.register_tool(
            name="file_info",
            description="Get file metadata (size, type, permissions)",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to base directory",
                    },
                },
                "required": ["path"],
            },
        )

    async def handle_tool_call(
        self,
        name: str,
        arguments: dict,
    ) -> str:
        """Handle tool execution"""
        try:
            if name == "read_file":
                return await self._read_file(arguments.get("path"))

            elif name == "write_file":
                return await self._write_file(
                    arguments.get("path"),
                    arguments.get("content"),
                )

            elif name == "list_dir":
                return await self._list_dir(arguments.get("path", "."))

            elif name == "file_info":
                return await self._file_info(arguments.get("path"))

            else:
                return f"[ERROR] Unknown tool: {name}"

        except Exception as e:
            return f"[ERROR] {e}"

    async def _read_file(self, path: str) -> str:
        """Read file contents"""
        full_path = self._resolve_path(path)

        if not full_path.exists():
            return f"[ERROR] File not found: {path}"

        if not full_path.is_file():
            return f"[ERROR] Not a file: {path}"

        # Check file size (limit to 1MB)
        file_size = full_path.stat().st_size
        if file_size > 1024 * 1024:
            return f"[ERROR] File too large: {file_size} bytes (max 1MB)"

        # Read file
        content = full_path.read_text(encoding="utf-8")

        # Add metadata
        return f"# File: {path} ({file_size} bytes)\n\n{content}"

    async def _write_file(self, path: str, content: str) -> str:
        """Write content to file"""
        full_path = self._resolve_path(path)

        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        full_path.write_text(content, encoding="utf-8")

        return f"[OK] Written {len(content)} bytes to {path}"

    async def _list_dir(self, path: str) -> str:
        """List directory contents"""
        full_path = self._resolve_path(path)

        if not full_path.exists():
            return f"[ERROR] Directory not found: {path}"

        if not full_path.is_dir():
            return f"[ERROR] Not a directory: {path}"

        # List entries
        entries = []
        for entry in full_path.iterdir():
            entry_type = "DIR" if entry.is_dir() else "FILE"
            size = entry.stat().st_size if entry.is_file() else 0
            entries.append(f"{entry_type:6} {size:10} {entry.name}")

        if not entries:
            return f"[INFO] Directory is empty: {path}"

        header = f"# Directory: {path}\n"
        header += f"# Total: {len(entries)} entries\n\n"

        return header + "\n".join(entries)

    async def _file_info(self, path: str) -> str:
        """Get file metadata"""
        full_path = self._resolve_path(path)

        if not full_path.exists():
            return f"[ERROR] Path not found: {path}"

        stat = full_path.stat()

        info = [
            f"# File Info: {path}",
            f"",
            f"Type:      {'Directory' if full_path.is_dir() else 'File'}",
            f"Size:      {stat.st_size} bytes",
            f"Modified:  {stat.st_mtime}",
            f"Permissions: {oct(stat.st_mode)[-3:]}",
        ]

        if full_path.is_file():
            ext = full_path.suffix or "(no extension)"
            info.append(f"Extension: {ext}")

        return "\n".join(info)

    def _resolve_path(self, path: str) -> Path:
        """
        Resolve path relative to base directory

        Args:
            path: Relative path

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path escapes base directory
        """
        full_path = (self._base_path / path).resolve()

        # Security check: ensure we don't escape base directory
        try:
            full_path.relative_to(self._base_path)
        except ValueError:
            raise ValueError(f"Path escapes base directory: {path}")

        return full_path


async def main():
    """Run MCP server"""
    import argparse

    parser = argparse.ArgumentParser(description="File Operations MCP Server")
    parser.add_argument(
        "--base-path",
        default=".",
        help="Base directory for file operations (default: current directory)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (list tools and exit)",
    )

    args = parser.parse_args()

    # Create server
    server = FileMCPServer(base_path=args.base_path)

    if args.test:
        # Test mode: list tools and exit
        print("[TEST] Available tools:")
        for tool_name, tool_def in server._tools.items():
            print(f"\n{tool_name}:")
            print(f"  Description: {tool_def['description']}")
            print(f"  Schema: {tool_def['inputSchema']}")
        return

    # Run server
    print("[INFO] Starting File MCP Server...", file=sys.stderr)
    print(f"[INFO] Base path: {args.base_path}", file=sys.stderr)
    print("[INFO] Waiting for MCP requests...", file=sys.stderr)

    try:
        await server.run()
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
