# MCP Dual Transport Implementation

**Status**: Completed
**Date**: 2025-02-24
**Version**: 2.4.2

## Overview

FastReAct Nano now supports dual transport modes for MCP (Model Context Protocol) servers:

1. **stdio transport** - Local subprocess communication (original)
2. **HTTP transport** - JSON-RPC over HTTP with SSE support (new)

This implementation enables FastReAct to connect to both local MCP servers and remote HTTP MCP services, including enterprise GraphRAG services.

---

## What Was Implemented

### 1. Credentials Module (`src/fastreact/core/credentials.py`)

**Purpose**: Secure credential storage with environment variable support.

**Key Features**:
- Separate file: `~/.fastreact/credentials.json`
- File permissions: 0600 (user read/write only)
- Environment variable resolution: `${VAR_NAME}`
- Default values: `${VAR_NAME:-default}`
- Dot notation access: `credentials.get("mcp_api_keys.graphrag")`
- **Environment variable priority** (cloud-native deployment support)

**Usage**:
```python
from fastreact.core import Credentials, get_credentials

# Load credentials
creds = Credentials.load()  # Auto-searches default locations
token = creds.get_auth_token("mcp.graphrag")

# Or use singleton
creds = get_credentials()
```

**Environment Variable Priority** (Highest to Lowest):
1. Direct environment variable: `FASTRACT_LLM_API_KEYS_SILICONFLOW`
2. Value from credentials file
3. Default value

**Cloud-Native Deployment**:
```bash
# No credentials file needed! Just use environment variables
export FASTRACT_LLM_API_KEYS_SILICONFLOW="sk-xxx"
export FASTRACT_MCP_API_KEYS_GRAPHRAG="secret-key"
```

**Credentials File Format** (`~/.fastreact/credentials.json`):
```json
{
  "llm_api_keys": {
    "openai": "${OPENAI_API_KEY}",
    "siliconflow": "sk-xxx"
  },
  "mcp_api_keys": {
    "graphrag": "graphrag-secret-key",
    "http_test": "test-token-12345"
  },
  "custom": {
    "some_value": "${CUSTOM_VAR:-default_value}"
  }
}
```

### 2. HTTP MCP Client (`src/fastreact/mcp/http_client.py`)

**Purpose**: HTTP transport for MCP protocol.

**Key Features**:
- JSON-RPC over HTTP POST
- OAuth 2.1 Bearer token authentication
- SSE (Server-Sent Events) for streaming
- Compatible interface with SimpleMCPClient
- Connection pooling via httpx
- **SSE heartbeat detection** (prevents gateway timeouts)
- **Exponential backoff reconnection** (resilient to network issues)

**Class**: `StreamableHTTPMCPClient`

**Usage**:
```python
from fastreact.mcp import StreamableHTTPMCPClient

client = StreamableHTTPMCPClient(
    base_url="http://localhost:8000",
    auth_token="your-token"  # Optional
)

await client.connect()
tools = await client.list_tools()
result = await client.call_tool("echo", {"message": "hello"})
await client.close()
```

**SSE with Automatic Reconnection**:
```python
async for event in client.subscribe_events(
    heartbeat_interval=30.0,  # Send heartbeat after 30s of no data
    max_retries=5,            # Max reconnection attempts
    initial_backoff=1.0       # Start with 1s backoff (doubles each retry)
):
    print(f"Event: {event}")
```

### 3. Updated Configuration (`src/fastreact/core/config.py`)

**New Fields in MCPServerConfig**:
```python
@dataclass
class MCPServerConfig:
    # ... existing fields ...
    transport: str = "stdio"  # "stdio" | "http"
    url: Optional[str] = None  # HTTP server URL
    auth_token_ref: Optional[str] = None  # Reference to credentials.json
```

**New Configuration Format** (`~/.fastreact/config.json`):
```json
{
  "mcp": {
    "servers": [
      {
        "name": "graphrag",
        "transport": "stdio",
        "command": "python3",
        "args": ["mcp_servers/builtin/graphrag/server.py"],
        "isolation": "shared"
      },
      {
        "name": "remote_graphrag",
        "transport": "http",
        "url": "http://internal-service:8000",
        "auth_token_ref": "mcp.graphrag",
        "isolation": "shared"
      },
      {
        "name": "http_test",
        "transport": "http",
        "url": "http://localhost:8000",
        "isolation": "shared"
      }
    ]
  }
}
```

### 4. Updated MCP Manager (`src/fastreact/mcp/manager.py`)

**Changes**:
- `MCPToolWrapper` now supports both client types
- `MCPToolManager.add_server()` accepts transport parameter
- `is_server_alive()` handles both stdio and http
- `resurrect_server()` supports both transports
- **Magic path resolution** for cleaner configuration

**New Signature**:
```python
async def add_server(
    self,
    name: str,
    transport: str = "stdio",
    server_command: str = "",
    server_args: list[str] = None,
    url: Optional[str] = None,
    auth_token_ref: Optional[str] = None,
) -> None
```

**Magic Paths** (Architecture Improvement):
- `@builtin/` - Auto-resolves to `mcp_servers/builtin/`
- `@cwd/` - Auto-resolves to current working directory

**Configuration with Magic Paths**:
```json
{
  "mcp": {
    "servers": [
      {
        "name": "graphrag",
        "transport": "stdio",
        "command": "python3",
        "args": ["@builtin/graphrag/server.py"]
      }
    ]
  }
}
```

### 5. HTTP Test Server (`mcp_servers/builtin/http_test_server/`)

**Purpose**: Test server for HTTP transport validation.

**Tools**:
- `echo` - Echo back input message
- `add_numbers` - Add two numbers
- `get_info` - Get server information
- `current_time` - Get current server time

**Running**:
```bash
cd mcp_servers/builtin/http_test_server
python server.py  # http://localhost:8000

# Custom port
python server.py --port 9000
```

**Testing**:
```bash
# Health check
curl http://localhost:8000/health

# List tools
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Call tool
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"echo","arguments":{"message":"hello"}}}'
```

### 6. Standardized MCP Server Directory Structure

**New Structure**:
```
mcp_servers/builtin/{server_name}/
├── server.py       # Main implementation
├── config.json     # Metadata
├── README.md       # Documentation
└── requirements.txt # Dependencies (optional)
```

**Migrated Servers**:
- `graph_rag_server.py` → `graphrag/server.py`
- `filesystem_server.py` → `filesystem/server.py`
- `http_test_server/` - New test server

**Backward Compatibility**: Old files remain with deprecation notices.

---

## Testing and Validation

### 1. Import Test

```bash
cd fastreact-nano
python3 -c "
from fastreact.core import Credentials, get_credentials
from fastreact.mcp import StreamableHTTPMCPClient
from fastreact.mcp import MCPToolManager
from fastreact.core.config import MCPServerConfig
print('[OK] All imports successful')
"
```

### 2. HTTP Server Test

```bash
# Terminal 1: Start test server
cd mcp_servers/builtin/http_test_server
python server.py

# Terminal 2: Test with curl
curl http://localhost:8000/health
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### 3. FastReAct Integration Test

```bash
# Configure HTTP transport
cat > ~/.fastreact/config.json << EOF
{
  "mcp": {
    "servers": [
      {
        "name": "http_test",
        "transport": "http",
        "url": "http://localhost:8000",
        "isolation": "shared"
      }
    ]
  }
}
EOF

# Run FastReAct query
fastreact "使用http_test工具echo hello world"
```

---

## Configuration Examples

### Local stdio MCP Server

```json
{
  "name": "graphrag",
  "transport": "stdio",
  "command": "python3",
  "args": ["mcp_servers/builtin/graphrag/server.py"],
  "isolation": "shared"
}
```

### Remote HTTP MCP Server (No Auth)

```json
{
  "name": "public_service",
  "transport": "http",
  "url": "https://api.example.com/mcp",
  "isolation": "shared"
}
```

### Remote HTTP MCP Server (With Auth)

**~/.fastreact/credentials.json**:
```json
{
  "mcp_api_keys": {
    "enterprise_graphrag": "${ENTERPRISE_GRAPHRAG_KEY}"
  }
}
```

**~/.fastreact/config.json**:
```json
{
  "name": "enterprise_graphrag",
  "transport": "http",
  "url": "https://internal.company.com/graphrag",
  "auth_token_ref": "mcp_api_keys.enterprise_graphrag",
  "isolation": "shared"
}
```

---

## API Reference

### StreamableHTTPMCPClient

```python
class StreamableHTTPMCPClient:
    def __init__(
        self,
        base_url: str,
        auth_token: Optional[str] = None,
        timeout: float = 30.0,
    )

    async def connect() -> None
    async def close() -> None
    async def list_tools() -> list[Dict]
    async def call_tool(name: str, arguments: Dict) -> str
    async def subscribe_events() -> AsyncIterator[Dict]
    def is_alive() -> bool
```

### Credentials

```python
class Credentials:
    llm_api_keys: Dict[str, str]
    mcp_api_keys: Dict[str, str]
    custom: Dict[str, Any]

    @classmethod
    def load(credentials_path: Optional[Path] = None) -> "Credentials"
    def get(key: str, default: Any = None) -> Any
    def get_auth_token(token_ref: str) -> Optional[str]
    def save(credentials_path: Optional[Path] = None) -> None

def get_credentials(credentials_path: Optional[Path] = None) -> Credentials
```

---

## Files Changed

### New Files

| File | Purpose |
|------|---------|
| `src/fastreact/core/credentials.py` | Credentials management |
| `src/fastreact/mcp/http_client.py` | HTTP MCP Client |
| `mcp_servers/builtin/http_test_server/server.py` | Test server |
| `mcp_servers/builtin/http_test_server/config.json` | Server metadata |
| `mcp_servers/builtin/http_test_server/README.md` | Documentation |
| `mcp_servers/builtin/http_test_server/requirements.txt` | Dependencies |
| `mcp_servers/builtin/graphrag/server.py` | Migrated GraphRAG server |
| `mcp_servers/builtin/graphrag/config.json` | Server metadata |
| `mcp_servers/builtin/graphrag/README.md` | Documentation |
| `mcp_servers/builtin/filesystem/server.py` | Migrated Filesystem server |
| `mcp_servers/builtin/filesystem/config.json` | Server metadata |
| `mcp_servers/builtin/filesystem/README.md` | Documentation |

### Modified Files

| File | Changes |
|------|---------|
| `src/fastreact/core/config.py` | Added transport fields to MCPServerConfig |
| `src/fastreact/mcp/manager.py` | Added HTTP transport support |
| `src/fastreact/mcp/__init__.py` | Exported StreamableHTTPMCPClient |
| `src/fastreact/core/__init__.py` | Exported Credentials |
| `mcp_servers/builtin/graph_rag_server.py` | Added deprecation notice |
| `mcp_servers/builtin/filesystem_server.py` | Added deprecation notice |

---

## Architecture Improvements

Based on production feedback, three critical improvements were added:

### 1. SSE Long-Connection Heartbeat

**Problem**: HTTP SSE connections can be silently dropped by gateways (Nginx, firewalls) due to idle timeouts.

**Solution**: Built-in heartbeat detection with exponential backoff reconnection.

```python
async for event in client.subscribe_events(
    heartbeat_interval=30.0,  # Detect stale connections after 30s
    max_retries=5,            # Retry up to 5 times
    initial_backoff=1.0       # Start with 1s, double each retry
):
    # Automatically reconnects if connection drops
    process_event(event)
```

### 2. Cloud-Native Credential Priority

**Problem**: Docker/K8s deployments prefer environment variables over file secrets.

**Solution**: Environment variables have highest priority in credential resolution.

```bash
# No credentials.json needed!
export FASTRACT_LLM_API_KEYS_SILICONFLOW="sk-xxx"
export FASTRACT_MCP_API_KEYS_GRAPHRAG="secret-key"
```

Priority order:
1. `FASTRACT_*` environment variables (highest)
2. `~/.fastreact/credentials.json`
3. Default value (fallback)

### 3. Magic Path Support

**Problem**: Long absolute paths make configuration verbose and fragile.

**Solution**: Magic path prefixes for common directories.

```json
{
  "args": ["@builtin/graphrag/server.py"]  // Auto-resolves
}
```

Supported prefixes:
- `@builtin/` → `mcp_servers/builtin/`
- `@cwd/` → Current working directory

---

## Dependencies

All required dependencies are already included in FastReAct:

- `httpx>=0.25.0` - HTTP client (already in core dependencies)
- `fastapi>=0.104.0` - For test server (in `http` optional dependency)
- `uvicorn>=0.24.0` - For test server (in `http` optional dependency)

---

## Migration Guide

### For Existing Users

If you have existing MCP server configurations, they will continue to work without changes.

To use HTTP transport:

1. **Update `~/.fastreact/config.json`**:
   ```json
   {
     "mcp": {
       "servers": [
         {
           "name": "my_http_server",
           "transport": "http",
           "url": "http://my-server:8000",
           "isolation": "shared"
         }
       ]
     }
   }
   ```

2. **For authenticated servers, create `~/.fastreact/credentials.json`**:
   ```json
   {
     "mcp_api_keys": {
       "my_http_server": "your-secret-token"
     }
   }
   ```

3. **Add auth reference to config**:
   ```json
   {
     "name": "my_http_server",
     "transport": "http",
     "url": "http://my-server:8000",
     "auth_token_ref": "mcp_api_keys.my_http_server"
   }
   ```

### For MCP Server Developers

Follow the standard directory structure:

```
your_server/
├── server.py       # Required
├── config.json     # Recommended
├── README.md       # Recommended
└── requirements.txt # If needed
```

---

## Troubleshooting

### HTTP Connection Fails

1. Check if server is running:
   ```bash
   curl http://your-server:8000/health
   ```

2. Verify URL in config.json

3. Check authentication token if required

### Credentials Not Loading

1. Verify file location: `~/.fastreact/credentials.json`
2. Check file permissions: Should be 0600
3. Validate JSON syntax

### Zombie Resurrection Not Working for HTTP

- HTTP transport uses connection check instead of process check
- Resurrection recreates the HTTP client and reconnects
- Verify server is actually reachable

---

## Future Enhancements

Potential improvements for future versions:

1. Connection pooling for multiple HTTP requests
2. WebSocket transport support
3. Automatic retry with exponential backoff
4. Circuit breaker pattern for failing servers
5. Metrics and observability for HTTP connections
6. mTLS support for enterprise deployments

---

## References

- [MCP Specification 2025-03-26](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports/)
- [Streamable HTTP Transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports/streamable-http/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [httpx Documentation](https://www.python-httpx.org/)

---

**Implementation completed**: 2025-02-24
**FastReAct Nano version**: 2.4.2+
