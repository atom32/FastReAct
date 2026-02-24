# Filesystem MCP Server

Safe filesystem operations with path validation for FastReAct Nano.

## Overview

This server provides safe file operations through the MCP protocol with built-in path validation and size limits to prevent unauthorized access to sensitive system files.

## Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with size limit |
| `write_file` | Write content to file |
| `list_directory` | List directory contents |
| `file_exists` | Check if file exists |

## Configuration

Add to `~/.fastreact/config.json`:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "filesystem",
        "transport": "stdio",
        "command": "python3",
        "args": ["mcp_servers/builtin/filesystem/server.py"],
        "isolation": "shared"
      }
    ]
  }
}
```

## Usage

The server is automatically loaded when FastReAct starts. Tools are available with the `filesystem_` prefix:

```
fastreact "使用filesystem_read_file工具读取config.json"
```

## Security

- Protected paths are blocked (e.g., `/etc/passwd`, `C:\\Windows\\System32`)
- File size limits prevent memory issues
- Path traversal attacks are prevented

## Directory Structure

```
filesystem/
├── server.py       # Main server implementation
├── config.json     # Server metadata
└── README.md       # This file
```

## Migration

This server was migrated from `mcp_servers/builtin/filesystem_server.py` to follow the standard MCP server structure.
