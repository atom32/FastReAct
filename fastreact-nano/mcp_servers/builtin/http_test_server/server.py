"""
FastReAct Nano - HTTP MCP Test Server

A test MCP server that implements HTTP transport for testing.
Implements three test tools: echo, add_numbers, get_info.
Supports SSE (Server-Sent Events) for event streaming.
"""

import json
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


# JSON-RPC Request/Response models
class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


# Tool definitions
TOOLS = [
    {
        "name": "echo",
        "description": "Echo back the input message",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to echo back"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "add_numbers",
        "description": "Add two numbers together",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "First number"
                },
                "b": {
                    "type": "number",
                    "description": "Second number"
                }
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "get_info",
        "description": "Get server information",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "current_time",
        "description": "Get the current server time",
        "inputSchema": {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "description": "Time format (iso, timestamp, or readable)",
                    "enum": ["iso", "timestamp", "readable"],
                    "default": "iso"
                }
            }
        }
    }
]


# Create FastAPI app
app = FastAPI(
    title="HTTP MCP Test Server",
    description="Test server for HTTP MCP transport",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "name": "HTTP MCP Test Server",
        "version": "1.0.0",
        "endpoints": {
            "message": "POST /message - JSON-RPC endpoint",
            "events": "GET /events - SSE event stream",
            "health": "GET /health - Health check"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/message")
async def handle_message(request: JSONRPCRequest):
    """
    Handle JSON-RPC messages (MCP protocol endpoint).

    Supports:
    - initialize: Initialize MCP session
    - tools/list: List available tools
    - tools/call: Call a tool
    """
    request_id = request.id

    # Handle initialize
    if request.method == "initialize":
        return JSONRPCResponse(
            id=request_id,
            result={
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "http-test-server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        )

    # Handle tools/list
    elif request.method == "tools/list":
        return JSONRPCResponse(
            id=request_id,
            result={"tools": TOOLS}
        )

    # Handle tools/call
    elif request.method == "tools/call":
        params = request.params or {}
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        # Find tool
        tool = next((t for t in TOOLS if t["name"] == tool_name), None)
        if not tool:
            return JSONRPCResponse(
                id=request_id,
                error={
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            )

        # Execute tool
        try:
            result = await execute_tool(tool_name, arguments)
            return JSONRPCResponse(
                id=request_id,
                result={"content": [{"type": "text", "text": result}]}
            )
        except Exception as e:
            return JSONRPCResponse(
                id=request_id,
                error={
                    "code": -32603,
                    "message": str(e)
                }
            )

    # Unknown method
    else:
        return JSONRPCResponse(
            id=request_id,
            error={
                "code": -32601,
                "message": f"Method not found: {request.method}"
            }
        )


async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute a tool and return the result"""

    if tool_name == "echo":
        message = arguments.get("message", "")
        return f"Echo: {message}"

    elif tool_name == "add_numbers":
        a = arguments.get("a", 0)
        b = arguments.get("b", 0)
        try:
            result = float(a) + float(b)
            return f"The sum of {a} and {b} is {result}"
        except (ValueError, TypeError):
            return "Error: Invalid numbers provided"

    elif tool_name == "get_info":
        return json.dumps({
            "server": "HTTP MCP Test Server",
            "version": "1.0.0",
            "transport": "HTTP",
            "tools_count": len(TOOLS),
            "timestamp": datetime.now().isoformat()
        }, indent=2)

    elif tool_name == "current_time":
        time_format = arguments.get("format", "iso")
        now = datetime.now()

        if time_format == "iso":
            return now.isoformat()
        elif time_format == "timestamp":
            return str(int(now.timestamp()))
        else:  # readable
            return now.strftime("%Y-%m-%d %H:%M:%S")

    else:
        return f"Unknown tool: {tool_name}"


@app.get("/events")
async def events_stream(request: Request):
    """
    SSE (Server-Sent Events) endpoint for event streaming.

    Sends periodic keepalive messages and test events.
    """
    async def event_generator():
        """Generate SSE events"""
        try:
            counter = 0
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                counter += 1

                # Send different event types
                if counter % 5 == 0:
                    # Send keepalive every 5th iteration
                    yield ": keepalive\n\n"
                else:
                    # Send test event
                    event = {
                        "type": "test_event",
                        "data": {
                            "counter": counter,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    yield f"data: {json.dumps(event)}\n\n"

                await asyncio.sleep(2)  # Send event every 2 seconds

        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """
    Run the HTTP MCP test server.

    Args:
        host: Host to bind to (default: 127.0.0.1)
        port: Port to listen on (default: 8000)
    """
    import uvicorn

    print(f"[INFO] Starting HTTP MCP Test Server on http://{host}:{port}")
    print(f"[INFO] Endpoints:")
    print(f"  - POST /message  - JSON-RPC endpoint")
    print(f"  - GET  /events   - SSE event stream")
    print(f"  - GET  /health   - Health check")
    print(f"[INFO] Available tools: echo, add_numbers, get_info, current_time")

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HTTP MCP Test Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)
