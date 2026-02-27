# MCP Server Implementation Strategy

## Important Update (2025-02-27)

### Custom Servers → Reference Implementations

The RSS and HackerNews MCP servers have been moved to:
**`mcp_servers/builtin/examples/`**

These are now **educational examples** showing how to implement MCP servers.

---

## Recommended Approach: Use Official Servers

### FastReAct Supports Any stdio MCP Server

FastReAct uses the standard MCP protocol (JSON-RPC over stdio).
This means you can directly use servers from npm ecosystem!

### Example: Official Fetch Server

Instead of custom RSS server, use the official `fetch` server:

```json
{
  "name": "fetch",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-fetch"],
  "isolation": "shared"
}
```

This ONE server handles:
- RSS feeds
- REST APIs  
- HackerNews Firebase API
- Any HTTP request

---

## Why This Matters

✅ **FastReAct is mature** - Works with standard MCP protocol
✅ **Ecosystem integration** - Direct npm support
✅ **Less maintenance** - Use community servers
✅ **Best practice** - Don't reinvent the wheel

---

## When to Create Custom Servers

Only when:
1. No official alternative exists
2. Proprietary integration needed
3. Educational purpose (→ label as examples/)

---

## Configuration

All MCP servers are configured in `~/.fastreact/config.json`:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "fetch",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-fetch"],
        "isolation": "shared"
      }
    ]
  }
}
```

## See Also

- `docs/MCP_CALLING_MECHANISM.md` - MCP usage guide
- `docs/PLATFORM/SKILLS_AND_MCP.md` - Extension mechanisms
