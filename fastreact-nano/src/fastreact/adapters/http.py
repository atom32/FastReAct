"""
HTTP Adapter for FastReAct Nano

Provides REST API interface for the Nano kernel.
Install with: pip install fastreact-nano[http]
"""

import asyncio
from typing import Optional, List
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from fastreact import Agent, Config


# Request/Response models
class RunRequest(BaseModel):
    query: str
    model: Optional[str] = None
    skills: Optional[List[str]] = None
    stream: bool = False


class RunResponse(BaseModel):
    response: str
    model: str
    iterations: int


class SkillListResponse(BaseModel):
    skills: List[dict]


class ToolListResponse(BaseModel):
    tools: List[str]


# Global agent instance
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
        description="REST API for FastReAct Nano kernel",
        version="2.0.0",
        lifespan=lifespan,
    )

    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "FastReAct Nano",
            "version": "2.0.0",
            "description": "Lightweight ReAct agent with kernel + adapters architecture",
            "endpoints": {
                "run": "POST /run",
                "skills": "GET /skills",
                "tools": "GET /tools",
                "health": "GET /health",
            }
        }

    @app.get("/health")
    async def health():
        """Health check"""
        return {"status": "healthy", "agent": _agent is not None}

    @app.post("/run", response_model=RunResponse)
    async def run(request: RunRequest):
        """
        Run agent query

        Args:
            request: Run request with query and optional parameters

        Returns:
            Agent response
        """
        agent = get_agent()

        # Override model if specified
        if request.model:
            original_model = agent.config.llm.model
            agent.config.llm.model = request.model

        try:
            response = await agent.run(
                request.query,
                skills=request.skills,
            )

            return RunResponse(
                response=response,
                model=agent.config.llm.model,
                iterations=0,  # TODO: track iterations
            )

        finally:
            # Restore model
            if request.model:
                agent.config.llm.model = original_model

    @app.get("/skills", response_model=SkillListResponse)
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

        return SkillListResponse(skills=skills)

    @app.get("/tools", response_model=ToolListResponse)
    async def list_tools():
        """List available tools"""
        agent = get_agent()
        return ToolListResponse(tools=agent.list_tools())

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
        print("Error: FastAPI not available")
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
