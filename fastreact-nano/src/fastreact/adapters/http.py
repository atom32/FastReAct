"""
HTTP Adapter for FastReAct Nano

Provides SSE (Server-Sent Events) API interface.
Install with: pip install fastreact-nano[http]

This is a CONSUMER of the AgentEvent stream.
All HTTP responses are driven by AgentEvent protocol.
"""

import asyncio
import json
import uuid
from typing import Optional, List
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from fastreact import Agent, Config, EventType


# Request/Response models
class ChatRequest(BaseModel):
    """Chat completion request (OpenAI-compatible format)"""
    messages: List[dict]
    model: Optional[str] = None
    stream: bool = True
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat completion response"""
    content: str
    model: str
    session_id: str


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    type: str


# Global agent instance (stateless, so safe to share)
_agent: Optional[Agent] = None


def get_agent() -> Agent:
    """Get or create agent instance"""
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage agent lifecycle"""
    # Startup
    global _agent
    _agent = Agent()
    yield
    # Shutdown
    _agent = None


def create_app() -> FastAPI:
    """Create FastAPI application"""
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI not available. "
            "Install with: pip install fastreact-nano[http]"
        )

    app = FastAPI(
        title="FastReAct Nano API",
        description="Event-Driven SSE API for FastReAct Nano",
        version="2.0.0",
        lifespan=lifespan,
    )

    @app.get("/")
    async def root():
        """Root endpoint - API info"""
        return {
            "name": "FastReAct Nano",
            "version": "2.0.0",
            "architecture": "Event-Driven",
            "protocol": "AgentEvent (SSE)",
            "endpoints": {
                "chat_completions": "POST /v1/chat/completions",
                "health": "GET /health",
                "skills": "GET /v1/skills",
                "tools": "GET /v1/tools",
            }
        }

    @app.get("/health")
    async def health():
        """Health check"""
        return {
            "status": "healthy",
            "agent_ready": _agent is not None,
            "event_protocol": "AgentEvent",
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatRequest):
        """
        Chat completion endpoint with SSE streaming

        OpenAI-compatible format with AgentEvent streaming.

        Args:
            request: Chat request with messages

        Returns:
            SSE stream of AgentEvent objects
        """
        agent = get_agent()

        # Extract query from last message
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        last_message = request.messages[-1]
        query = last_message.get("content", "")

        # Generate session_id if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Extract skills from messages (optional enhancement)
        skills = None
        # TODO: Parse skills from request if needed

        async def event_generator():
            """Generate SSE events from AgentEvent stream"""
            try:
                async for event in agent.run_event_stream(query, skills=skills, session_id=session_id):
                    # Convert AgentEvent to SSE format
                    payload = {
                        "type": event.type.value,
                        "content": event.content,
                        "tool_name": event.tool_name,
                        "tool_args": event.tool_args,
                        "session_id": event.session_id,
                        "timestamp": event.timestamp,
                    }

                    # SSE format: data: {json}\n\n
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                # Signal completion
                yield f"data: [DONE]\n\n"

            except Exception as e:
                # Send error event
                error_payload = {
                    "type": "error",
                    "content": str(e),
                    "session_id": session_id,
                    "timestamp": asyncio.get_event_loop().time(),
                }
                yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
                yield f"data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    # Legacy endpoint for backward compatibility
    @app.post("/run")
    async def run_legacy(request: dict):
        """
        Legacy run endpoint (non-streaming)

        Deprecated: Use /v1/chat/completions instead.
        """
        agent = get_agent()

        query = request.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Query required")

        # Run agent (non-streaming)
        response = await agent.run(query)

        return {"response": response}

    @app.get("/v1/skills")
    async def list_skills():
        """List available skills"""
        agent = get_agent()
        skill_names = agent.list_skills()

        skills = []
        for name in skill_names:
            skill = agent.skills.get(name)
            if skill:
                skills.append({
                    "name": skill.name,
                    "description": skill.description,
                    "version": skill.metadata.version,
                })

        return {"skills": skills}

    @app.get("/v1/tools")
    async def list_tools():
        """List available tools"""
        agent = get_agent()
        return {"tools": agent.list_tools()}

    return app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    log_level: str = "info",
):
    """
    Run HTTP server

    Args:
        host: Host to bind to
        port: Port to bind to
        log_level: Log level
    """
    if not FASTAPI_AVAILABLE:
        print("[ERROR] FastAPI not available")
        print("Install with: pip install fastreact-nano[http]")
        return

    app = create_app()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
    )


if __name__ == "__main__":
    run_server()
