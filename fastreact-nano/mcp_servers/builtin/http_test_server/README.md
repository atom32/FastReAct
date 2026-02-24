# HTTP MCP Test Server

A test MCP server that implements HTTP transport for testing FastReAct's HTTP MCP client.

## Overview

This server provides a testbed for verifying HTTP transport functionality in FastReAct Nano. It implements the Model Context Protocol (MCP) over HTTP with JSON-RPC messaging.

## Features

- **HTTP Transport**: JSON-RPC over HTTP POST
- **SSE Support**: Server-Sent Events for event streaming
- **Test Tools**: 4 test tools for validation
- **Health Check**: Endpoint for monitoring server status

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `echo` | Echo back the input message | `message` (string) |
| `add_numbers` | Add two numbers together | `a` (number), `b` (number) |
| `get_info` | Get server information | None |
| `current_time` | Get current server time | `format` (optional: "iso", "timestamp", "readable") |

## Installation

```bash
# Install dependencies
pip install fastapi uvicorn pydantic
```

## Usage

### Starting the Server

```bash
# Default: localhost:8000
python server.py

# Custom host/port
python server.py --host 0.0.0.0 --port 9000
```

### Testing Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Initialize MCP session
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {}
    }
  }'

# List tools
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'

# Call echo tool
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "echo",
      "arguments": {
        "message": "Hello, FastReAct!"
      }
    }
  }'

# Call add_numbers tool
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "add_numbers",
      "arguments": {
        "a": 42,
        "b": 58
      }
    }
  }'
```

### Testing with FastReAct

Add to `~/.fastreact/config.json`:

```json
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
```

Then use via FastReAct:

```
fastreact "使用http_test工具echo hello world"
fastreact "使用http_test_add_numbers工具计算42加58"
```

### Testing with Authentication

1. Create `~/.fastreact/credentials.json`:

```json
{
  "mcp_api_keys": {
    "http_test": "test-token-12345"
  }
}
```

2. Update config with auth:

```json
{
  "mcp": {
    "servers": [
      {
        "name": "http_test",
        "transport": "http",
        "url": "http://localhost:8000",
        "auth_token_ref": "mcp.http_test",
        "isolation": "shared"
      }
    ]
  }
}
```

3. Test with curl:

```bash
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token-12345" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

## API Endpoints

### POST /message

JSON-RPC 2.0 endpoint for MCP protocol.

**Supported Methods:**
- `initialize` - Initialize MCP session
- `tools/list` - List available tools
- `tools/call` - Execute a tool

### GET /events

Server-Sent Events stream for real-time events.

Sends:
- Test events with counter and timestamp
- Keepalive comments every 10 seconds

### GET /health

Health check endpoint.

Returns server status and current timestamp.

## Response Format

All responses follow JSON-RPC 2.0 format:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Tool result here"
      }
    ]
  }
}
```

Error format:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32601,
    "message": "Method not found"
  }
}
```

## Configuration

The server can be configured via command-line arguments:

| Argument | Default | Description |
|----------|---------|-------------|
| `--host` | 127.0.0.1 | Host to bind to |
| `--port` | 8000 | Port to listen on |

## Directory Structure

```
http_test_server/
├── server.py       # Main server implementation
├── config.json     # Server metadata
├── README.md       # This file
└── requirements.txt # Dependencies (optional)
```

## Dependencies

```
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
```

## License

MIT
