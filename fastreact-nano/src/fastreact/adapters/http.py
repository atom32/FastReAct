"""
HTTP adapter for FastReAct Nano.

This is the headless service API surface for systems that use FastReAct as an
agentic runtime. The primary contract is OpenAI-style chat input with either
SSE AgentEvent streaming or a summarized non-streaming response.
"""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any, AsyncIterator, Optional
import uuid

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel, Field
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised in minimal installs.
    FASTAPI_AVAILABLE = False
    FastAPI = None  # type: ignore[assignment]
    HTTPException = Exception  # type: ignore[assignment]
    Request = None  # type: ignore[assignment]
    StreamingResponse = None  # type: ignore[assignment]
    uvicorn = None  # type: ignore[assignment]

    class BaseModel:  # type: ignore[no-redef]
        pass

    def Field(default: Any = None, **_: Any) -> Any:
        return default

from fastreact import Agent, Config
from fastreact.core.events import AgentEvent


SERVICE_EVENT_SCHEMA_VERSION = "fastreact.agent_event.v1"
SERVICE_AUTH_ENV = "FASTREACT_SERVICE_TOKEN"

_agent: Optional[Agent] = None
_service_config = None


class ChatRequest(BaseModel):
    messages: list[dict[str, Any]]
    model: Optional[str] = None
    stream: bool = True
    session_id: Optional[str] = None
    skills: Optional[list[str]] = None
    user_key: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatCompletionResponse(BaseModel):
    type: str
    run_id: str
    session_id: str
    content: str
    events: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    duration_ms: float
    metadata: dict[str, Any] = Field(default_factory=dict)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        config = Config.load()
        set_service_config(config.service)
        _agent = Agent(config)
    return _agent


def set_agent_for_testing(agent: Optional[Agent]) -> None:
    global _agent
    _agent = agent


def set_service_config(config: Any) -> None:
    global _service_config
    _service_config = config


def configured_service_token() -> str | None:
    token = os.getenv(SERVICE_AUTH_ENV)
    if token and token.strip():
        return token.strip()
    config_token = getattr(_service_config, "service_token", None)
    return config_token.strip() if isinstance(config_token, str) and config_token.strip() else None


def require_service_auth(request: Request) -> None:  # type: ignore[valid-type]
    expected = configured_service_token()
    if not expected:
        return

    authorization = request.headers.get("authorization", "")
    bearer_prefix = "Bearer "
    bearer_token = authorization[len(bearer_prefix) :].strip() if authorization.startswith(bearer_prefix) else ""
    header_token = request.headers.get("x-fastreact-service-token", "").strip()
    if bearer_token == expected or header_token == expected:
        return
    raise HTTPException(status_code=401, detail="FastReAct service token required")


def extract_query(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content
    raise ValueError("At least one user message with non-empty content is required")


def extract_history(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(messages) <= 1:
        return []
    return messages[:-1]


def service_event_payload(
    event: AgentEvent,
    *,
    run_id: str,
    sequence: int,
    parent_event_id: str | None = None,
) -> dict[str, Any]:
    metadata = dict(event.metadata or {})
    event_id = f"{run_id}:{sequence}"
    payload = {
        "schema": SERVICE_EVENT_SCHEMA_VERSION,
        "type": event.type.value,
        "event_id": event_id,
        "parent_event_id": parent_event_id,
        "run_id": run_id,
        "session_id": event.session_id,
        "timestamp": event.timestamp,
        "content": event.content,
        "tool_name": event.tool_name,
        "tool_args": event.tool_args,
        "tool_call_id": metadata.get("call_id") or metadata.get("tool_call_id"),
        "duration_ms": metadata.get("duration_ms"),
        "cited_source_ids": metadata.get("cited_source_ids") or metadata.get("source_ids") or [],
        "metadata": metadata,
    }
    return payload


def sse_frame(payload: dict[str, Any]) -> str:
    event_type = payload.get("type") or "agent_event"
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def summarize_events(
    *,
    run_id: str,
    session_id: str,
    events: list[dict[str, Any]],
    started_at: float,
) -> dict[str, Any]:
    final_answer = ""
    error = None
    for event in events:
        if event["type"] == "session_end":
            final_answer = event.get("content") or ""
        elif event["type"] == "error":
            error = event.get("content") or "Unknown error"

    tool_calls = [
        {
            "event_id": event["event_id"],
            "tool_call_id": event.get("tool_call_id"),
            "tool_name": event.get("tool_name"),
            "tool_args": event.get("tool_args"),
        }
        for event in events
        if event["type"] == "tool_call"
    ]

    response = {
        "type": "chat.completion",
        "run_id": run_id,
        "session_id": session_id,
        "content": final_answer,
        "events": events,
        "tool_calls": tool_calls,
        "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
        "metadata": {
            "schema": SERVICE_EVENT_SCHEMA_VERSION,
            "event_count": len(events),
        },
    }
    if error:
        response["type"] = "error"
        response["error"] = error
    return response


def readiness_payload(agent: Agent) -> dict[str, Any]:
    config = getattr(agent, "_config", None)
    mcp_servers = []
    mcp_tools = []
    try:
        mcp_servers = agent.list_mcp_server_status()
    except Exception as exc:  # noqa: BLE001 - readiness reports dependency failures.
        mcp_servers = [{"name": "unknown", "alive": False, "error": str(exc)}]
    try:
        mcp_tools = agent.list_mcp_tools() if hasattr(agent, "list_mcp_tools") else []
    except Exception as exc:  # noqa: BLE001 - readiness reports dependency failures.
        mcp_tools = []
        mcp_servers.append({"name": "tools", "alive": False, "error": str(exc)})

    mcp_ready = bool(mcp_tools) or all(server.get("alive") for server in mcp_servers) if mcp_servers else False
    return {
        "status": "ready" if agent is not None and mcp_ready else "degraded",
        "agent_ready": agent is not None,
        "service_contract": SERVICE_EVENT_SCHEMA_VERSION,
        "auth": {
            "required": configured_service_token() is not None,
            "header": "Authorization: Bearer <token>",
            "alternate_header": "X-FastReAct-Service-Token",
        },
        "model": {
            "name": getattr(getattr(config, "llm", None), "model", None),
            "api_base_configured": bool(getattr(getattr(config, "llm", None), "api_base", None)),
            "api_key_configured": bool(getattr(getattr(config, "llm", None), "api_key", None)),
        },
        "mcp": {
            "ready": mcp_ready,
            "servers": mcp_servers,
            "tools": mcp_tools,
        },
        "timestamp": utc_now(),
    }


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:  # type: ignore[valid-type]
    get_agent()
    yield


def create_app() -> FastAPI:  # type: ignore[valid-type]
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI not available. Install with: pip install fastreact-nano[http]")

    app = FastAPI(
        title="FastReAct Nano API",
        description="Headless agentic service API for FastReAct Nano",
        version="2.4.2",
        lifespan=lifespan,
    )

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "name": "FastReAct Nano",
            "version": "2.4.2",
            "service_contract": SERVICE_EVENT_SCHEMA_VERSION,
            "endpoints": {
                "chat_completions": "POST /v1/chat/completions",
                "health": "GET /health",
                "skills": "GET /v1/skills",
                "tools": "GET /v1/tools",
            },
        }

    @app.get("/health")
    async def health() -> dict[str, Any]:
        agent = get_agent()
        readiness = readiness_payload(agent)
        return {
            "status": "healthy",
            "agent_ready": readiness["agent_ready"],
            "service_contract": readiness["service_contract"],
            "timestamp": readiness["timestamp"],
        }

    @app.get("/ready")
    async def ready(request: Request) -> dict[str, Any]:  # type: ignore[valid-type]
        require_service_auth(request)
        agent = get_agent()
        if hasattr(agent, "ensure_mcp_loaded"):
            await agent.ensure_mcp_loaded()
        return readiness_payload(agent)

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request, chat_request: ChatRequest) -> Any:  # type: ignore[valid-type]
        require_service_auth(request)
        if not chat_request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        try:
            query = extract_query(chat_request.messages)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        agent = get_agent()
        run_id = str(chat_request.metadata.get("run_id") or uuid.uuid4())
        session_id = chat_request.session_id or str(uuid.uuid4())
        history = extract_history(chat_request.messages)
        started_at = time.perf_counter()

        async def event_generator() -> AsyncIterator[str]:
            parent_event_id = None
            try:
                async for event in agent.run_event_stream(
                    query,
                    skills=chat_request.skills,
                    session_id=session_id,
                    history=history,
                    user_key=chat_request.user_key,
                ):
                    payload = service_event_payload(
                        event,
                        run_id=run_id,
                        sequence=event_generator.sequence,
                        parent_event_id=parent_event_id,
                    )
                    event_generator.sequence += 1
                    parent_event_id = payload["event_id"]
                    yield sse_frame(payload)
            except Exception as exc:  # noqa: BLE001 - transport must serialize errors.
                payload = {
                    "schema": SERVICE_EVENT_SCHEMA_VERSION,
                    "type": "error",
                    "event_id": f"{run_id}:{event_generator.sequence}",
                    "parent_event_id": parent_event_id,
                    "run_id": run_id,
                    "session_id": session_id,
                    "timestamp": utc_now(),
                    "content": str(exc),
                    "tool_name": None,
                    "tool_args": None,
                    "tool_call_id": None,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                    "cited_source_ids": [],
                    "metadata": {"error_type": type(exc).__name__},
                }
                yield sse_frame(payload)
            finally:
                yield "event: done\ndata: [DONE]\n\n"

        event_generator.sequence = 0  # type: ignore[attr-defined]

        if chat_request.stream:
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-FastReAct-Run-ID": run_id,
                    "X-FastReAct-Session-ID": session_id,
                    "X-FastReAct-Event-Schema": SERVICE_EVENT_SCHEMA_VERSION,
                },
            )

        events = []
        parent_event_id = None
        sequence = 0
        try:
            async for event in agent.run_event_stream(
                query,
                skills=chat_request.skills,
                session_id=session_id,
                history=history,
                user_key=chat_request.user_key,
            ):
                payload = service_event_payload(
                    event,
                    run_id=run_id,
                    sequence=sequence,
                    parent_event_id=parent_event_id,
                )
                sequence += 1
                parent_event_id = payload["event_id"]
                events.append(payload)
        except Exception as exc:  # noqa: BLE001 - service response should carry errors.
            events.append(
                {
                    "schema": SERVICE_EVENT_SCHEMA_VERSION,
                    "type": "error",
                    "event_id": f"{run_id}:{sequence}",
                    "parent_event_id": parent_event_id,
                    "run_id": run_id,
                    "session_id": session_id,
                    "timestamp": utc_now(),
                    "content": str(exc),
                    "tool_name": None,
                    "tool_args": None,
                    "tool_call_id": None,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                    "cited_source_ids": [],
                    "metadata": {"error_type": type(exc).__name__},
                }
            )

        return summarize_events(
            run_id=run_id,
            session_id=session_id,
            events=events,
            started_at=started_at,
        )

    @app.post("/run")
    async def run_legacy(request: dict[str, Any]) -> dict[str, str]:
        query = request.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Query required")
        response = await get_agent().run(query)
        return {"response": response}

    @app.get("/v1/skills")
    async def list_skills() -> dict[str, Any]:
        agent = get_agent()
        skills = []
        for name in agent.list_skills():
            skill = agent.skills.get(name)
            if skill:
                skills.append(
                    {
                        "name": skill.name,
                        "description": skill.description,
                        "version": skill.metadata.version,
                    }
                )
        return {"skills": skills}

    @app.get("/v1/tools")
    async def list_tools() -> dict[str, Any]:
        agent = get_agent()
        return {
            "tools": agent.list_tools(),
            "mcp_tools": agent.list_mcp_tools() if hasattr(agent, "list_mcp_tools") else [],
        }

    return app


def run_server(
    host: str | None = None,
    port: int | None = None,
    log_level: str | None = None,
    config_path: str | None = None,
) -> None:
    if not FASTAPI_AVAILABLE:
        print("[ERROR] FastAPI not available")
        print("Install with: pip install fastreact-nano[http]")
        return

    config = Config.load(Path(config_path).expanduser() if config_path else None)
    set_service_config(config.service)
    set_agent_for_testing(Agent(config))
    app = create_app()
    service = config.service
    uvicorn.run(
        app,
        host=host or service.host,
        port=port if port is not None else service.port,
        log_level=log_level or service.log_level,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FastReAct HTTP service")
    parser.add_argument("--config", help="Path to FastReAct JSON config")
    parser.add_argument("--host", help="Override service.host from config")
    parser.add_argument("--port", type=int, help="Override service.port from config")
    parser.add_argument("--log-level", help="Override service.log_level from config")
    args = parser.parse_args()
    run_server(
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()
