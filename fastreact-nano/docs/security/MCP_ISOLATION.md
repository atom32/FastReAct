# FastReAct Nano - MCP Tool User Isolation Guide

**Version**: 2.1.0
**Last Updated**: 2026-02-18
**Security Level**: Critical (P0)

---

## Executive Summary

FastReAct Nano supports **multi-tenant user isolation** for MCP (Model Context Protocol) tools to prevent cross-user data leakage in production deployments.

### Problem Statement

In multi-tenant scenarios (e.g., Feishu bot, web service), MCP tools previously shared a single server process across all users. This caused:

```
User A (feishu:ou_aaa) → MCP Server ← User B (feishu:ou_bbb)
                              ↓
                    Shared process state
                              ↓
            ❌ User B sees User A's search history
            ❌ User B discovers User A's file names
            ❌ GDPR/HIPAA compliance risks
```

### Solution

FastReAct Nano implements **3 isolation modes** to balance security and performance:

| Mode | Isolation | Resource Usage | Use Case |
|------|-----------|----------------|----------|
| `shared` | None | 1 process (all users) | Stateless tools (web_search) |
| `per_user` | Process-level | N processes (N = users) | High-security requirements |
| `lazy_per_user` | Process-level | M processes (M = active users) | **Recommended default** |

---

## Configuration

### Basic Configuration

Edit `config.json`:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "web_search",
        "command": "python3",
        "args": ["mcp_servers/web_search.py"],
        "isolation": "shared"
      },
      {
        "name": "graphrag",
        "command": "python3",
        "args": ["mcp_servers/graphrag_server.py"],
        "isolation": "lazy_per_user",
        "idle_timeout": 300,
        "max_instances": 10,
        "per_user_args_template": ["--user-dir", "{user_workspace}"]
      }
    ]
  }
}
```

### Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `isolation` | string | `"shared"` | Isolation mode: `"shared"`, `"per_user"`, `"lazy_per_user"` |
| `per_user_args_template` | list[string] | `null` | Argument template with `{user_key}` and `{user_workspace}` placeholders |
| `idle_timeout` | int | `300` | Seconds of inactivity before cleanup (lazy_per_user only) |
| `max_instances` | int | `10` | Maximum number of user instances (lazy_per_user only) |

---

## Isolation Modes

### Mode 1: Shared (Default)

**Description**: All users share the same MCP server process.

**Configuration**:
```json
{
  "name": "web_search",
  "command": "python3",
  "args": ["mcp_servers/web_search.py"],
  "isolation": "shared"
}
```

**Resource Usage**:
- 1 process for all users
- Minimal memory overhead (~50MB per server)

**Use Cases**:
- Stateless tools (web_search, calculator)
- Public data sources (weather, news)
- Low-security scenarios

**Security Considerations**:
- **No data isolation** between users
- MCP server must not store user-specific state
- Query history may be visible to other users

**When to Use**:
- Tool does not store user data
- Tool operates on public datasets
- Performance is critical

---

### Mode 2: Per-User

**Description**: Each user gets a dedicated MCP server process.

**Configuration**:
```json
{
  "name": "graphrag",
  "command": "python3",
  "args": ["mcp_servers/graphrag_server.py"],
  "isolation": "per_user",
  "per_user_args_template": ["--user-dir", "{user_workspace}"]
}
```

**Resource Usage**:
- N processes (N = number of users)
- Memory: ~50MB per user

**Use Cases**:
- High-security requirements
- Regulatory compliance (GDPR, HIPAA)
- Long-running user sessions

**Security Considerations**:
- **Complete process-level isolation**
- User data stored in separate workspaces
- No cross-user data leakage

**When to Use**:
- Tool stores sensitive user data
- Regulatory requirements demand isolation
- User count is manageable (<50)

---

### Mode 3: Lazy Per-User (Recommended)

**Description**: Create user processes on-demand, cleanup after timeout.

**Configuration**:
```json
{
  "name": "database",
  "command": "python3",
  "args": ["mcp_servers/database_server.py"],
  "isolation": "lazy_per_user",
  "idle_timeout": 300,
  "max_instances": 10,
  "per_user_args_template": ["--user-dir", "{user_workspace}"]
}
```

**Resource Usage**:
- M processes (M = active users, typically M << N)
- Memory: ~50MB per active user
- Auto-cleanup after idle timeout

**Use Cases**:
- **Balanced performance and security (recommended default)**
- Large user base (>100)
- Sporadic user activity patterns

**Security Considerations**:
- **Complete process-level isolation** (when active)
- User data cleaned up after timeout
- `max_instances` prevents resource exhaustion

**When to Use**:
- Default for most production deployments
- Tools with user-specific data
- Large user bases with varying activity

---

## User Argument Templates

### Supported Placeholders

When using `per_user` or `lazy_per_user` modes, you can customize arguments per user:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{user_key}` | Full user identifier | `"feishu:ou_123456"` |
| `{user_workspace}` | Path to user workspace | `"/workspace/feishu_ou_123456"` |

### Examples

#### Example 1: User-specific data directory

```json
{
  "name": "graphrag",
  "command": "python3",
  "args": ["mcp_servers/graphrag_server.py"],
  "isolation": "per_user",
  "per_user_args_template": [
    "--user-dir",
    "{user_workspace}/graphrag"
  ]
}
```

For user `feishu:ou_abc`, this expands to:
```bash
python3 mcp_servers/graphrag_server.py --user-dir /workspace/feishu_ou_abc/graphrag
```

#### Example 2: User-specific configuration

```json
{
  "name": "database",
  "command": "python3",
  "args": ["mcp_servers/database_server.py"],
  "isolation": "lazy_per_user",
  "per_user_args_template": [
    "--config",
    "{user_workspace}/db_config.json",
    "--user-id",
    "{user_key}"
  ]
}
```

For user `web:user@example.com`, this expands to:
```bash
python3 mcp_servers/database_server.py --config /workspace/web_user@example.com/db_config.json --user-id web:user@example.com
```

---

## MCP Server Adaptation Guide

### Receiving User Context

When using per-user isolation, your MCP server will receive the `user_key` in tool call requests:

**Request Format**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {
      "query": "secret project"
    },
    "user_key": "feishu:ou_abc"
  }
}
```

### Server-Side Isolation Implementation

#### Option 1: User-Specific Data Directories

```python
# mcp_servers/graphrag_server.py
from mcp.server import Server
from pathlib import Path

server = Server("graphrag")

user_data_dirs = {}

@server.call_tool()
async def search(query: str, user_key: str = None) -> str:
    # Use user_key to isolate data
    if user_key:
        data_dir = Path(f"/data/{user_key.replace(':', '_')}")
    else:
        data_dir = Path("/data/default")

    # Load user-specific knowledge graph
    graph = load_graph(data_dir / "graph.pkl")

    # Search in user's graph only
    results = graph.search(query)
    return results
```

#### Option 2: User-Specific Database Schemas

```python
# mcp_servers/database_server.py
import asyncpg

@server.call_tool()
async def query(sql: str, user_key: str = None) -> str:
    # Connect to user-specific schema
    schema_name = f"user_{user_key.replace(':', '_')}" if user_key else "public"

    conn = await asyncpg.connect("postgresql://localhost/db")
    await conn.execute(f"SET search_path TO {schema_name}")

    # Execute query in user's schema
    results = await conn.fetch(sql)
    return results
```

#### Option 3: In-Memory User Partitioning

```python
# mcp_servers/cache_server.py
from collections import defaultdict

user_caches = defaultdict(dict)

@server.call_tool()
async def get(key: str, user_key: str = None) -> str:
    # Use user-specific cache
    cache = user_caches[user_key] if user_key else user_caches["default"]
    return cache.get(key, "not found")

@server.call_tool()
async def set(key: str, value: str, user_key: str = None) -> str:
    cache = user_caches[user_key] if user_key else user_caches["default"]
    cache[key] = value
    return "ok"
```

---

## Best Practices

### 1. Choose the Right Isolation Mode

```
Decision Tree:
┌─────────────────────────────────────┐
│ Does tool store user-specific data? │
└─────────────────────────────────────┘
        ↓
    Yes → No (use shared mode)
        ↓
  High security? ──Yes──→ per_user
        ↓ No
     lazy_per_user (recommended)
```

### 2. Validate User Input in MCP Servers

```python
@server.call_tool()
async def tool(user_key: str = None, **kwargs) -> str:
    # Validate user_key format
    if user_key and ":" not in user_key:
        raise ValueError("Invalid user_key format")

    # Sanitize user_key for filesystem paths
    safe_user_key = user_key.replace(":", "_").replace("/", "_")

    # Use safe_user_key for paths
    data_dir = Path(f"/data/{safe_user_key}")
```

### 3. Set Resource Limits

```json
{
  "isolation": "lazy_per_user",
  "idle_timeout": 300,  // Cleanup after 5 minutes
  "max_instances": 20   // Max 20 concurrent users
}
```

### 4. Monitor Resource Usage

```python
# In your monitoring system
import psutil

def check_mcp_resources():
    # Count MCP server processes
    mcp_processes = len([p for p in psutil.process_iter()
                        if "mcp_servers" in p.name()])

    # Check memory usage
    total_memory = sum(p.memory_info().rss
                      for p in psutil.process_iter()
                      if "mcp_servers" in p.name())

    print(f"MCP Processes: {mcp_processes}")
    print(f"Total Memory: {total_memory / 1024 / 1024:.1f} MB")
```

### 5. Test Isolation

```python
# test_isolation.py
import pytest
from fastreact import Agent

@pytest.mark.asyncio
async def test_user_isolation():
    agent = Agent(multitenant=True)

    # User A stores data
    await agent.run("Store 'secret_A'", user_key="feishu:ou_aaa")

    # User B searches for User A's data
    result = await agent.run("Search for 'secret_A'", user_key="feishu:ou_bbb")

    # Verify: User B should NOT see User A's data
    assert "secret_A" not in result
    assert "no results" in result.lower()
```

---

## Troubleshooting

### Problem: High Memory Usage

**Symptoms**: Memory grows with number of users

**Diagnosis**:
```python
# Check number of MCP processes
import psutil
procs = [p for p in psutil.process_iter() if "mcp_servers" in p.name()]
print(f"Active MCP processes: {len(procs)}")
```

**Solutions**:
1. Reduce `idle_timeout` (default: 300s)
```json
{
  "idle_timeout": 60  // Cleanup after 1 minute
}
```

2. Reduce `max_instances`
```json
{
  "max_instances": 5  // Max 5 concurrent users
}
```

3. Switch to `shared` mode for stateless tools

---

### Problem: "Max instances reached" Error

**Symptoms**:
```
RuntimeError: Maximum MCP instances (10) reached
```

**Solutions**:
1. Increase `max_instances`:
```json
{
  "max_instances": 50  // Support more concurrent users
}
```

2. Reduce `idle_timeout` to free instances faster

3. Implement instance pooling

---

### Problem: User Data Leakage

**Symptoms**: User B sees User A's data

**Diagnosis**:
1. Check isolation mode:
```json
{
  "isolation": "shared"  // ❌ Wrong for stateful tools
}
```

2. Check MCP server implementation:
```python
# ❌ BUG: Shared state across users
shared_cache = {}

@server.call_tool()
async def search(query: str, user_key: str = None):
    # All users share this cache!
    return shared_cache.get(query)
```

**Solutions**:
1. Use `per_user` or `lazy_per_user` isolation
2. Implement user-specific data partitioning in MCP server
3. Add isolation tests to your test suite

---

## Security Checklist

Before deploying to production:

- [ ] All stateful MCP tools use `per_user` or `lazy_per_user` isolation
- [ ] MCP servers validate and sanitize `user_key` input
- [ ] User workspaces are separated (filesystem isolation)
- [ ] `max_instances` is set to prevent resource exhaustion
- [ ] `idle_timeout` is configured for lazy mode
- [ ] Isolation tests are passing
- [ ] No hardcoded paths in MCP server code
- [ ] User data is encrypted at rest (if required by compliance)
- [ ] Audit logging is enabled for sensitive operations
- [ ] Rate limiting is configured per user

---

## Performance Benchmarks

### Resource Usage (100 Users)

| Mode | Processes | Memory | Startup Time | Best For |
|------|-----------|--------|--------------|----------|
| `shared` | 1 | ~50MB | 1s | Stateless tools |
| `per_user` | 100 | ~5GB | 100s | High security |
| `lazy_per_user` (20 active) | 20 | ~1GB | 20s | **Production** |

### Latency (P95)

| Mode | Tool Execution | User Isolation |
|------|---------------|----------------|
| `shared` | <50ms | None |
| `per_user` | <100ms | Complete |
| `lazy_per_user` | <80ms | Complete |

---

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Multi-Tenant GraphRAG Guide](../../MULTITENANT_GRAPHRAG.md)
- [MCP Skill README](../../MCP_SKILL_README.md)
- [Security Best Practices](./SECURITY.md)

---

**Document Status**: Final
**Last Reviewed**: 2026-02-18
**Next Review**: 2026-05-18
