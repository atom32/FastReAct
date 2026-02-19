# MCP Servers

This directory contains MCP (Model Context Protocol) server configurations and implementations.

## Directory Structure

```
mcp_servers/
├── builtin/              # Built-in MCP server implementations
│   └── .gitkeep          # Add custom MCP server scripts here
├── config/               # MCP server configurations
│   ├── shared.json       # Shared mode servers (single instance)
│   └── per_user.json     # Per-user mode servers (isolated instances)
└── README.md             # This file
```

## MCP Server Modes

### Shared Mode
- **Definition**: Single server instance shared across all users
- **Use Case**: Stateless operations, read-only resources, shared knowledge bases
- **Example**: GraphRAG knowledge search, web search
- **Configuration**: `config/shared.json`

### Per-User Mode
- **Definition**: Isolated server instance per user
- **Use Case**: User-specific resources, filesystem access, sensitive operations
- **Example**: Filesystem operations, user-specific databases
- **Configuration**: `config/per_user.json`

## Adding a New MCP Server

### 1. Built-in Server (Python)

Create a Python script in `mcp_servers/builtin/`:

```python
# mcp_servers/builtin/my_server.py
from mcp.server import Server
import asyncio

server = Server("my-server")

@server.tool()
async def my_tool(param: str) -> str:
    """Tool description"""
    return f"Result: {param}"

async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. External Server (NPM)

Add to `config/shared.json` or `config/per_user.json`:

```json
{
  "name": "my-external-server",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-my-server", "--option", "value"],
  "isolation": "shared",
  "description": "My external MCP server"
}
```

## Configuration Format

### Shared Server Configuration

```json
{
  "schema_version": "1.0",
  "description": "Shared MCP servers (single instance for all users)",
  "servers": [
    {
      "name": "server-name",
      "command": "python3",
      "args": ["mcp_servers/builtin/server.py"],
      "isolation": "shared",
      "description": "Server description",
      "env": {
        "ENV_VAR": "value"
      }
    }
  ]
}
```

### Per-User Server Configuration

```json
{
  "schema_version": "1.0",
  "description": "Per-user MCP servers (isolated instance per user)",
  "servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "{user_workspace}"],
      "isolation": "per_user",
      "description": "Filesystem operations (per-user workspace access)",
      "template_vars": {
        "user_workspace": "Path to user workspace"
      }
    }
  ]
}
```

## Template Variables

Per-user configurations support template variables:

- `{user_workspace}` - Automatically replaced with user's workspace path
- `{user_id}` - User identifier
- `{tenant_id}` - Tenant identifier (for multi-tenant deployments)

## Best Practices

1. **Isolation**: Use per-user mode for any server accessing user-specific resources
2. **Stateless**: Prefer shared mode for stateless, read-only operations
3. **Error Handling**: Implement proper error handling in built-in servers
4. **Documentation**: Document tool parameters and return values
5. **Testing**: Test MCP servers independently before integration

## See Also

- [MCP Specification](https://modelcontextprotocol.io/)
- FastReAct Skills and MCP documentation: `docs/SKILLS_AND_MCP.md`
