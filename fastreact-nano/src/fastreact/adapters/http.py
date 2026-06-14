"""
HTTP adapter for FastReAct Nano.

This is the headless service API surface for systems that use FastReAct as an
agentic runtime. The primary contract is OpenAI-style chat input with either
SSE AgentEvent streaming or a summarized non-streaming response.
"""

from __future__ import annotations

import argparse
import asyncio
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
MAX_PAGE_LIMIT = 1000

_agent: Optional[Agent] = None
_service_config = None
_runs: dict[str, dict[str, Any]] = {}


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


class ApprovalDecisionRequest(BaseModel):
    reason: Optional[str] = None


class PolicyCheckRequest(BaseModel):
    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    user_key: Optional[str] = None
    tenant_key: Optional[str] = None


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
    approval_request_id = metadata.get("approval_request_id") or metadata.get("request_id")
    event_id = f"{run_id}:{sequence}"
    payload = {
        "schema": SERVICE_EVENT_SCHEMA_VERSION,
        "type": event.type.value,
        "event_id": event_id,
        "sequence": sequence,
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
        "approval_request_id": approval_request_id,
        "metadata": metadata,
    }
    return payload


def bounded_limit(limit: int, *, default: int = 200, maximum: int = MAX_PAGE_LIMIT) -> int:
    if limit is None:
        return default
    if limit < 0:
        raise HTTPException(status_code=400, detail="limit must be >= 0")
    if limit == 0:
        return 0
    return min(limit, maximum)


def event_sequence(event: dict[str, Any]) -> int:
    sequence = event.get("sequence")
    if isinstance(sequence, int):
        return sequence
    event_id = str(event.get("event_id") or "")
    try:
        return int(event_id.rsplit(":", 1)[-1])
    except ValueError:
        return 0


def page_event_list(
    events: list[dict[str, Any]],
    *,
    limit: int = 200,
    after_sequence: Optional[int] = None,
) -> dict[str, Any]:
    bounded = bounded_limit(limit)
    ordered = sorted(events, key=event_sequence)
    if after_sequence is not None:
        ordered = [event for event in ordered if event_sequence(event) > after_sequence]
    total_after_cursor = len(ordered)
    page = ordered if bounded == 0 else ordered[:bounded]
    has_more = bounded != 0 and total_after_cursor > len(page)
    next_after_sequence = event_sequence(page[-1]) if page else after_sequence
    return {
        "events": page,
        "count": len(page),
        "event_count": len(events),
        "total_event_count": len(events),
        "after_sequence": after_sequence,
        "next_after_sequence": next_after_sequence,
        "has_more": has_more,
    }


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


def run_snapshot(record: dict[str, Any], include_events: bool = False) -> dict[str, Any]:
    snapshot = {
        "run_id": record["run_id"],
        "session_id": record["session_id"],
        "status": record["status"],
        "created_at": record["created_at"],
        "started_at": record.get("started_at"),
        "completed_at": record.get("completed_at"),
        "cancelled_at": record.get("cancelled_at"),
        "duration_ms": record.get("duration_ms"),
        "event_count": len(record.get("events", [])),
        "error": record.get("error"),
        "metadata": record.get("metadata", {}),
    }
    if include_events:
        snapshot["events"] = list(record.get("events", []))
    return snapshot


def persist_run_trace(record: dict[str, Any]) -> None:
    agent = get_agent()
    store = getattr(agent, "store", None)
    if not store:
        return
    events = list(record.get("events", []))
    final_event = next((event for event in reversed(events) if event.get("type") == "session_end"), None)
    tool_calls = [event for event in events if event.get("type") == "tool_call"]
    store.append(
        "traces",
        {
            "trace_type": "background_run",
            "run_id": record["run_id"],
            "session_id": record["session_id"],
            "status": record["status"],
            "created_at": record["created_at"],
            "started_at": record.get("started_at"),
            "completed_at": record.get("completed_at"),
            "duration_ms": record.get("duration_ms"),
            "event_count": len(events),
            "tool_call_count": len(tool_calls),
            "final_content": final_event.get("content") if final_event else "",
            "error": record.get("error"),
            "metadata": record.get("metadata", {}),
        },
    )


def persist_run_event(record: dict[str, Any], event: dict[str, Any]) -> None:
    agent = get_agent()
    store = getattr(agent, "store", None)
    if not store:
        return
    store.append(
        "events",
        {
            **event,
            "trace_type": "background_run",
            "run_id": record["run_id"],
            "session_id": record["session_id"],
        },
    )


async def execute_background_run(run_id: str) -> None:
    record = _runs[run_id]
    agent = get_agent()
    record["status"] = "running"
    record["started_at"] = utc_now()
    started_at = time.perf_counter()
    parent_event_id = None
    sequence = 0
    try:
        async for event in agent.run_event_stream(
            record["query"],
            skills=record.get("skills"),
            session_id=record["session_id"],
            history=record.get("history"),
            user_key=record.get("user_key"),
        ):
            payload = service_event_payload(
                event,
                run_id=run_id,
                sequence=sequence,
                parent_event_id=parent_event_id,
            )
            sequence += 1
            parent_event_id = payload["event_id"]
            record["events"].append(payload)
            persist_run_event(record, payload)
        if record["status"] != "cancelled":
            record["status"] = "completed"
    except asyncio.CancelledError:
        record["status"] = "cancelled"
        record["cancelled_at"] = utc_now()
        payload = {
            "schema": SERVICE_EVENT_SCHEMA_VERSION,
            "type": "error",
            "event_id": f"{run_id}:{sequence}",
            "sequence": sequence,
            "parent_event_id": parent_event_id,
            "run_id": run_id,
            "session_id": record["session_id"],
            "timestamp": utc_now(),
            "content": "Run cancelled",
            "tool_name": None,
            "tool_args": None,
            "tool_call_id": None,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            "approval_request_id": None,
            "cited_source_ids": [],
            "metadata": {"error_type": "CancelledError"},
        }
        record["events"].append(payload)
        persist_run_event(record, payload)
        raise
    except Exception as exc:  # noqa: BLE001 - background run should record errors.
        record["status"] = "failed"
        record["error"] = str(exc)
        payload = {
            "schema": SERVICE_EVENT_SCHEMA_VERSION,
            "type": "error",
            "event_id": f"{run_id}:{sequence}",
            "sequence": sequence,
            "parent_event_id": parent_event_id,
            "run_id": run_id,
            "session_id": record["session_id"],
            "timestamp": utc_now(),
            "content": str(exc),
            "tool_name": None,
            "tool_args": None,
            "tool_call_id": None,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            "approval_request_id": None,
            "cited_source_ids": [],
            "metadata": {"error_type": type(exc).__name__},
        }
        record["events"].append(payload)
        persist_run_event(record, payload)
    finally:
        record["completed_at"] = utc_now()
        record["duration_ms"] = round((time.perf_counter() - started_at) * 1000, 2)
        persist_run_trace(record)
        record.pop("task", None)


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


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _duration_between_ms(start: Any, end: Any) -> float | None:
    if not start or not end:
        return None
    try:
        started = datetime.fromisoformat(str(start))
        ended = datetime.fromisoformat(str(end))
    except ValueError:
        return None
    return round((ended - started).total_seconds() * 1000, 2)


def metrics_payload(agent: Agent) -> dict[str, Any]:
    """Return lightweight headless-service observability metrics."""
    store = getattr(agent, "store", None)
    store_stats = store.stats() if store else {}
    traces = store.read("traces", limit=0) if store else []
    events = store.read("events", limit=0) if store else []
    audit = store.read("audit", limit=0) if store else []
    approvals = agent.tool_executor.list_approvals() if hasattr(agent, "tool_executor") else []

    live_runs = [run_snapshot(record) for record in _runs.values()]
    all_run_statuses: dict[str, int] = {}
    for item in [*traces, *live_runs]:
        status = str(item.get("status") or "unknown")
        all_run_statuses[status] = all_run_statuses.get(status, 0) + 1

    trace_durations = [float(record["duration_ms"]) for record in traces if isinstance(record.get("duration_ms"), (int, float))]
    tool_durations = [float(record["duration_ms"]) for record in audit if isinstance(record.get("duration_ms"), (int, float))]
    approval_durations = [
        duration
        for duration in (_duration_between_ms(record.get("created_at"), record.get("resolved_at")) for record in approvals)
        if duration is not None
    ]

    approval_statuses: dict[str, int] = {}
    for record in approvals:
        status = str(record.get("status") or "unknown")
        approval_statuses[status] = approval_statuses.get(status, 0) + 1

    error_events = [event for event in events if event.get("type") == "error"]
    failed_traces = [trace for trace in traces if trace.get("error") or trace.get("status") == "failed"]
    recent_errors = [
        {
            "run_id": item.get("run_id"),
            "session_id": item.get("session_id"),
            "type": item.get("type") or "trace_error",
            "content": item.get("content") or item.get("error") or "",
            "timestamp": item.get("timestamp") or item.get("completed_at") or item.get("created_at"),
        }
        for item in [*error_events[-5:], *failed_traces[-5:]]
    ][-5:]

    return {
        "schema": "fastreact.metrics.v1",
        "service_contract": SERVICE_EVENT_SCHEMA_VERSION,
        "timestamp": utc_now(),
        "runs": {
            "live_count": len(live_runs),
            "trace_count": len(traces),
            "status_counts": all_run_statuses,
            "avg_duration_ms": _avg(trace_durations),
        },
        "events": {
            "total_count": len(events),
            "error_count": len(error_events),
        },
        "tools": {
            "audit_count": len(audit),
            "avg_duration_ms": _avg(tool_durations),
        },
        "approvals": {
            "count": len(approvals),
            "pending_count": sum(1 for record in approvals if record.get("status") == "pending"),
            "expired_count": sum(1 for record in approvals if record.get("expired") is True),
            "status_counts": approval_statuses,
            "avg_resolution_ms": _avg(approval_durations),
        },
        "errors": {
            "count": len(error_events) + len(failed_traces),
            "recent": recent_errors,
        },
        "store": store_stats,
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
                "policy": "GET /v1/policy",
                "approvals": "GET /v1/approvals",
                "metrics": "GET /v1/metrics",
                "runs": "POST /v1/runs",
                "traces": "GET /v1/traces",
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

    @app.get("/v1/metrics")
    async def metrics(request: Request) -> dict[str, Any]:  # type: ignore[valid-type]
        require_service_auth(request)
        return metrics_payload(get_agent())

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

    @app.post("/v1/runs")
    async def create_run(request: Request, chat_request: ChatRequest) -> dict[str, Any]:
        require_service_auth(request)
        if not chat_request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        try:
            query = extract_query(chat_request.messages)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        run_id = str(chat_request.metadata.get("run_id") or uuid.uuid4())
        if run_id in _runs:
            raise HTTPException(status_code=409, detail="Run already exists")
        session_id = chat_request.session_id or str(uuid.uuid4())
        record = {
            "run_id": run_id,
            "session_id": session_id,
            "status": "queued",
            "created_at": utc_now(),
            "started_at": None,
            "completed_at": None,
            "cancelled_at": None,
            "duration_ms": None,
            "query": query,
            "skills": chat_request.skills,
            "history": extract_history(chat_request.messages),
            "user_key": chat_request.user_key,
            "metadata": dict(chat_request.metadata or {}),
            "events": [],
            "error": None,
        }
        _runs[run_id] = record
        task = asyncio.create_task(execute_background_run(run_id))
        record["task"] = task
        return {"type": "run", **run_snapshot(record)}

    @app.get("/v1/runs")
    async def list_runs(request: Request, limit: int = 200, status: Optional[str] = None) -> dict[str, Any]:
        require_service_auth(request)
        runs = [run_snapshot(record) for record in _runs.values()]
        if status:
            runs = [run for run in runs if run["status"] == status]
        runs.sort(key=lambda item: item["created_at"], reverse=True)
        bounded = bounded_limit(limit)
        page = runs if bounded == 0 else runs[:bounded]
        return {
            "runs": page,
            "count": len(page),
            "total_count": len(runs),
            "limit": bounded,
            "has_more": bounded != 0 and len(runs) > len(page),
        }

    @app.get("/v1/runs/{run_id}")
    async def get_run(run_id: str, request: Request) -> dict[str, Any]:
        require_service_auth(request)
        record = _runs.get(run_id)
        if not record:
            raise HTTPException(status_code=404, detail="Run not found")
        return {"type": "run", **run_snapshot(record)}

    @app.get("/v1/runs/{run_id}/events")
    async def get_run_events(
        run_id: str,
        request: Request,
        limit: int = 200,
        after_sequence: Optional[int] = None,
    ) -> dict[str, Any]:
        require_service_auth(request)
        record = _runs.get(run_id)
        if not record:
            raise HTTPException(status_code=404, detail="Run not found")
        page = page_event_list(record["events"], limit=limit, after_sequence=after_sequence)
        return {
            "run_id": run_id,
            "session_id": record["session_id"],
            "status": record["status"],
            **page,
        }

    @app.post("/v1/runs/{run_id}/cancel")
    async def cancel_run(run_id: str, request: Request) -> dict[str, Any]:
        require_service_auth(request)
        record = _runs.get(run_id)
        if not record:
            raise HTTPException(status_code=404, detail="Run not found")
        if record["status"] in {"completed", "failed", "cancelled"}:
            return {"type": "run", **run_snapshot(record)}
        record["status"] = "cancelled"
        record["cancelled_at"] = utc_now()
        task = record.get("task")
        if task and not task.done():
            task.cancel()
        return {"type": "run", **run_snapshot(record)}

    @app.get("/v1/traces")
    async def list_traces(request: Request, limit: int = 200, session_id: Optional[str] = None) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        store = getattr(agent, "store", None)
        records = store.read("traces", limit=0, session_id=session_id) if store else []
        records.sort(key=lambda item: item.get("completed_at") or item.get("created_at") or "", reverse=True)
        bounded = bounded_limit(limit)
        page = records if bounded == 0 else records[:bounded]
        return {
            "traces": page,
            "count": len(page),
            "total_count": len(records),
            "limit": bounded,
            "has_more": bounded != 0 and len(records) > len(page),
        }

    @app.get("/v1/traces/{run_id}")
    async def get_trace(run_id: str, request: Request) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        store = getattr(agent, "store", None)
        records = store.read("traces", limit=0, run_id=run_id) if store else []
        if records:
            return {"trace": records[-1]}
        record = _runs.get(run_id)
        if record:
            return {"trace": run_snapshot(record, include_events=False)}
        raise HTTPException(status_code=404, detail="Trace not found")

    @app.get("/v1/traces/{run_id}/events")
    async def get_trace_events(
        run_id: str,
        request: Request,
        limit: int = 200,
        after_sequence: Optional[int] = None,
    ) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        store = getattr(agent, "store", None)
        record = _runs.get(run_id)
        events = store.read("events", limit=0, run_id=run_id) if store else []
        if not events and record:
            events = list(record.get("events", []))
        if not events:
            raise HTTPException(status_code=404, detail="Trace events not found")
        page = page_event_list(events, limit=limit, after_sequence=after_sequence)
        return {"run_id": run_id, **page}

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

    @app.get("/v1/policy")
    async def get_policy(request: Request) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        config = getattr(agent, "_config", None)
        policy = getattr(config, "policy", None)
        return {
            "policy": policy.to_safety_policy() if policy else {},
            "actions": ["allow", "caution", "require_approval", "deny"],
            "priority": ["user_rules", "tenant_rules", "tool_rules", "default_action", "built_in_safety"],
            "tenant_inference": "prefix_before_colon_in_user_key",
        }

    @app.post("/v1/policy/check")
    async def check_policy(request: Request, policy_request: PolicyCheckRequest) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        safety_policy = getattr(agent, "_safety_policy", None)
        if not safety_policy:
            return {
                "tool_name": policy_request.tool_name,
                "level": "safe",
                "reason": "Safety policy disabled",
                "policy_scope": None,
                "policy_action": None,
                "policy_matched": False,
                "requires_confirmation": False,
                "should_allow": True,
            }
        decision = safety_policy.check(
            tool_name=policy_request.tool_name,
            args=policy_request.tool_args,
            user_key=policy_request.user_key,
            tenant_key=policy_request.tenant_key,
        )
        return {
            "tool_name": policy_request.tool_name,
            "user_key": policy_request.user_key,
            "tenant_key": policy_request.tenant_key,
            "level": decision.level.value,
            "reason": decision.reason,
            "pattern_matched": decision.pattern_matched,
            "policy_scope": decision.policy_scope,
            "policy_action": decision.policy_action,
            "policy_matched": decision.policy_matched,
            "requires_confirmation": decision.requires_confirmation,
            "should_allow": decision.should_allow,
        }

    @app.get("/v1/approvals")
    async def list_approvals(request: Request) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        executor = getattr(agent, "tool_executor", None)
        approvals = executor.list_approvals() if executor and hasattr(executor, "list_approvals") else []
        return {
            "approvals": approvals,
            "count": len(approvals),
            "pending_count": len([item for item in approvals if item.get("status") == "pending"]),
        }

    @app.get("/v1/approvals/{request_id}")
    async def get_approval(request_id: str, request: Request) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        executor = getattr(agent, "tool_executor", None)
        approvals = executor.list_approvals() if executor and hasattr(executor, "list_approvals") else []
        for approval in approvals:
            if approval.get("request_id") == request_id:
                return {"approval": approval}
        raise HTTPException(status_code=404, detail="Approval request not found")

    @app.post("/v1/approvals/{request_id}/approve")
    async def approve_tool_request(
        request_id: str,
        request: Request,
        decision: ApprovalDecisionRequest | None = None,
    ) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        executor = getattr(agent, "tool_executor", None)
        if not executor or not hasattr(executor, "resolve_approval"):
            raise HTTPException(status_code=404, detail="Approval request not found")
        resolved = executor.resolve_approval(request_id, approved=True, reason=(decision.reason if decision else "") or "")
        if not resolved:
            raise HTTPException(status_code=404, detail="Approval request not found or already resolved")
        return {"request_id": request_id, "status": "approved", "approved": True}

    @app.post("/v1/approvals/{request_id}/deny")
    async def deny_tool_request(
        request_id: str,
        request: Request,
        decision: ApprovalDecisionRequest | None = None,
    ) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        executor = getattr(agent, "tool_executor", None)
        if not executor or not hasattr(executor, "resolve_approval"):
            raise HTTPException(status_code=404, detail="Approval request not found")
        resolved = executor.resolve_approval(request_id, approved=False, reason=(decision.reason if decision else "") or "")
        if not resolved:
            raise HTTPException(status_code=404, detail="Approval request not found or already resolved")
        return {"request_id": request_id, "status": "denied", "approved": False}

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
