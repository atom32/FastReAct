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
import inspect
import json
import os
from pathlib import Path
import time
from typing import Any, AsyncIterator, Optional
import uuid

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel, Field
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised in minimal installs.
    FASTAPI_AVAILABLE = False
    FastAPI = None  # type: ignore[assignment]
    CORSMiddleware = None  # type: ignore[assignment]
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
from fastreact.runtime.run_service import RunService, TERMINAL_RUN_STATUSES


SERVICE_EVENT_SCHEMA_VERSION = "fastreact.agent_event.v1"
MAX_PAGE_LIMIT = 1000

_agent: Optional[Agent] = None
_service_config = None
_run_tasks: dict[str, asyncio.Task] = {}
_run_wakeup_task: Optional[asyncio.Task] = None
_rate_limit_windows: dict[str, dict[str, float | int]] = {}


class ChatRequest(BaseModel):
    messages: list[dict[str, Any]]
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
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


class TaskCreateRequest(BaseModel):
    title: str
    description: str = ""
    priority: str = "normal"
    owner: str = ""
    dependencies: list[str] = Field(default_factory=list)
    session_id: str = ""


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    owner: Optional[str] = None
    dependencies: Optional[list[str]] = None
    session_id: Optional[str] = None
    status_reason: Optional[str] = None


class SetupConfigDraftRequest(BaseModel):
    model: str = "deepseek-v4-flash"
    api_base: Optional[str] = "https://api.deepseek.com"
    api_key_file: str = "~/api_key.txt"
    service_token: Optional[str] = None
    host: str = "127.0.0.1"
    port: int = 8000
    workspace: str = "~/fastreact-workspace"
    preset: str = "default"
    include_pska: bool = False
    pska_command: str = "/Users/xudawei/Documents/personal archive/scripts/pska"
    pska_http_url: Optional[str] = None


class WorkspaceProfileUpdateRequest(BaseModel):
    agents_md: Optional[str] = None
    soul_md: Optional[str] = None


class ExtensionReloadRequest(BaseModel):
    skills: bool = True
    mcp: bool = False
    dry_run: bool = False
    required_skills: Optional[list[str]] = None
    user_key: Optional[str] = None


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
    global _agent, _run_wakeup_task
    _agent = agent
    _run_tasks.clear()
    if _run_wakeup_task and not _run_wakeup_task.done():
        _run_wakeup_task.cancel()
    _run_wakeup_task = None
    _rate_limit_windows.clear()


def set_service_config(config: Any) -> None:
    global _service_config
    _service_config = config


def run_agent_event_stream(agent: Any, **kwargs: Any) -> AsyncIterator[AgentEvent]:
    """Call Agent.run_event_stream while tolerating older compatible facades."""
    try:
        signature = inspect.signature(agent.run_event_stream)
    except (TypeError, ValueError):
        return agent.run_event_stream(**kwargs)
    parameters = signature.parameters
    supports_var_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    for optional_kwarg in ("run_metadata", "llm_options"):
        if optional_kwarg not in parameters and not supports_var_kwargs:
            kwargs.pop(optional_kwarg, None)
    return agent.run_event_stream(**kwargs)


def generation_options_from_request(chat_request: ChatRequest) -> dict[str, Any]:
    options: dict[str, Any] = {}
    model = getattr(chat_request, "model", None)
    if isinstance(model, str) and model.strip():
        options["model"] = model.strip()
    for field_name in ("temperature", "top_p", "max_tokens"):
        value = getattr(chat_request, field_name, None)
        if value is not None:
            options[field_name] = value
    return options


def configured_service_token() -> str | None:
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


def require_rate_limit(user_key: Optional[str]) -> None:
    limit = int(getattr(_service_config, "rate_limit_per_hour", 0) or 0)
    if limit <= 0:
        return

    identity = user_key or "anonymous"
    now = time.time()
    window = _rate_limit_windows.get(identity)
    if not window or now - float(window["started_at"]) >= 3600:
        _rate_limit_windows[identity] = {"started_at": now, "count": 1}
        return

    count = int(window["count"])
    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for user '{identity}': {limit}/hour",
            headers={"Retry-After": str(max(1, int(3600 - (now - float(window["started_at"])))))},
        )
    window["count"] = count + 1


def require_user_access(user_key: Optional[str]) -> None:
    identity = user_key or "anonymous"
    blocked = set(getattr(_service_config, "blocked_user_keys", []) or [])
    if identity in blocked:
        raise HTTPException(status_code=403, detail=f"User '{identity}' is blocked")

    allowed = set(getattr(_service_config, "allowed_user_keys", []) or [])
    if allowed and identity not in allowed:
        raise HTTPException(status_code=403, detail=f"User '{identity}' is not allowed")


def get_run_service(agent: Any | None = None) -> RunService:
    agent = agent or get_agent()
    service = getattr(agent, "runs", None)
    if service:
        return service
    store = getattr(agent, "store", None)
    if not store:
        raise HTTPException(status_code=503, detail="Durable run store not available")
    service_config = getattr(getattr(agent, "_config", None), "service", None) or _service_config
    service = RunService(
        store,
        lease_seconds=float(getattr(service_config, "run_lease_seconds", 300.0) or 300.0),
        max_attempts=int(getattr(service_config, "run_max_attempts", 3) or 3),
        retry_base_seconds=float(getattr(service_config, "run_retry_base_seconds", 5.0) or 5.0),
        retry_max_seconds=float(getattr(service_config, "run_retry_max_seconds", 300.0) or 300.0),
        event_schema=SERVICE_EVENT_SCHEMA_VERSION,
    )
    setattr(agent, "runs", service)
    return service


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
        "event_count": record.get("event_count", len(record.get("events", []))),
        "error": record.get("error"),
        "metadata": record.get("metadata", {}),
        "generation_options": record.get("generation_options", {}),
        "attempts": record.get("attempts", 0),
        "lease_expires_at": record.get("lease_expires_at"),
        "retry_after": record.get("retry_after"),
        "worker_id": record.get("worker_id"),
        "last_error": record.get("last_error"),
    }
    if include_events:
        snapshot["events"] = list(record.get("events", []))
    return snapshot


def task_runs_and_traces(agent: Any, task_id: str, session_id: str | None = None) -> dict[str, Any]:
    run_service = get_run_service(agent)
    runs = [
        run_service.snapshot(run["run_id"]) or run_snapshot(run)
        for run in run_service.list(limit=0)
        if run.get("metadata", {}).get("task_id") == task_id or (session_id and run.get("session_id") == session_id)
    ]
    store = getattr(agent, "store", None)
    traces = store.read("traces", limit=0) if store else []
    traces = [
        trace
        for trace in traces
        if trace.get("metadata", {}).get("task_id") == task_id or (session_id and trace.get("session_id") == session_id)
    ]
    runs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    traces.sort(key=lambda item: item.get("completed_at") or item.get("created_at") or "", reverse=True)
    return {"runs": runs, "traces": traces}


async def execute_background_run(run_id: str) -> None:
    agent = get_agent()
    runs = get_run_service(agent)
    record = runs.mark_running(run_id)
    started_at = time.perf_counter()
    parent_event_id = None
    sequence = runs.next_sequence(run_id)
    try:
        async for event in run_agent_event_stream(
            agent,
            query=record["query"],
            skills=record.get("skills"),
            session_id=record["session_id"],
            history=record.get("history"),
            user_key=record.get("user_key"),
            run_metadata=record.get("metadata") or {},
            llm_options=record.get("generation_options") or {},
        ):
            payload = service_event_payload(
                event,
                run_id=run_id,
                sequence=sequence,
                parent_event_id=parent_event_id,
            )
            sequence += 1
            parent_event_id = payload["event_id"]
            runs.append_event(run_id, payload)
        latest = runs.get(run_id) or {}
        if latest.get("status") != "cancelled":
            runs.complete(run_id)
    except asyncio.CancelledError:
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
        runs.append_event(run_id, payload)
        runs.cancel(run_id)
        raise
    except Exception as exc:  # noqa: BLE001 - background run should record errors.
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
        runs.append_event(run_id, payload)
        runs.fail(run_id, str(exc), retryable=True)
    finally:
        _run_tasks.pop(run_id, None)
        schedule_queued_runs(agent)


def configured_run_concurrency(agent: Any) -> int:
    service_config = getattr(getattr(agent, "_config", None), "service", None) or _service_config
    return max(0, int(getattr(service_config, "run_concurrency", 4) or 0))


def active_background_run_count() -> int:
    return sum(1 for task in _run_tasks.values() if not task.done())


def schedule_queued_runs(agent: Any | None = None) -> int:
    global _run_wakeup_task
    agent = agent or get_agent()
    runs = get_run_service(agent)
    limit = configured_run_concurrency(agent)
    available = max(0, limit - active_background_run_count()) if limit else len(runs.queued_for_recovery())
    scheduled = 0
    for record in runs.queued_for_recovery():
        run_id = str(record.get("run_id") or "")
        if not run_id or run_id in _run_tasks:
            continue
        if available <= 0:
            break
        task = asyncio.create_task(execute_background_run(run_id))
        _run_tasks[run_id] = task
        scheduled += 1
        available -= 1
    if scheduled == 0 and available > 0:
        delay = next_queued_retry_delay_seconds(runs)
        if delay is not None and (_run_wakeup_task is None or _run_wakeup_task.done()):
            _run_wakeup_task = asyncio.create_task(wake_queued_runs_after(delay))
    return scheduled


async def wake_queued_runs_after(delay_seconds: float) -> None:
    await asyncio.sleep(max(0.0, delay_seconds))
    schedule_queued_runs()


def next_queued_retry_delay_seconds(runs: RunService) -> float | None:
    delays: list[float] = []
    now = datetime.now(timezone.utc)
    for run in runs.list(status="queued", limit=0):
        retry_after = run.get("retry_after")
        if not retry_after:
            return 0.0
        try:
            parsed = datetime.fromisoformat(str(retry_after))
        except ValueError:
            return 0.0
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        delays.append(max(0.0, (parsed - now).total_seconds()))
    return min(delays) if delays else None


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


def workspace_profile_root(agent: Any) -> Path:
    config = getattr(agent, "_config", None)
    paths = getattr(config, "paths", None)
    workspace = getattr(paths, "gateway_workspace", None) or getattr(paths, "workspace", None)
    return Path(workspace) if workspace else Path.cwd() / "workspaces" / "default"


def read_workspace_profile(agent: Any) -> dict[str, Any]:
    root = workspace_profile_root(agent).expanduser().resolve()
    files = {
        "AGENTS.md": root / "AGENTS.md",
        "SOUL.md": root / "SOUL.md",
        ".fastreact/AGENT.md": root / ".fastreact" / "AGENT.md",
        ".fastreact/SOUL.md": root / ".fastreact" / "SOUL.md",
    }
    profile_files = []
    for name, path in files.items():
        exists = path.exists()
        content = ""
        error = None
        if exists:
            try:
                content = path.read_text(encoding="utf-8")
            except OSError as exc:
                error = str(exc)
        profile_files.append(
            {
                "name": name,
                "path": str(path),
                "exists": exists,
                "size_bytes": path.stat().st_size if exists and path.is_file() else 0,
                "content": content,
                "error": error,
            }
        )
    return {
        "schema": "fastreact.workspace_profile.v1",
        "workspace": str(root),
        "files": profile_files,
        "editable_files": ["AGENTS.md", "SOUL.md"],
    }


def write_workspace_profile(agent: Any, update: WorkspaceProfileUpdateRequest) -> dict[str, Any]:
    root = workspace_profile_root(agent).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    updates = {
        "AGENTS.md": update.agents_md,
        "SOUL.md": update.soul_md,
    }
    written = []
    for name, content in updates.items():
        if content is None:
            continue
        path = root / name
        path.write_text(content, encoding="utf-8")
        written.append({"name": name, "path": str(path), "size_bytes": path.stat().st_size})
    profile = read_workspace_profile(agent)
    profile["written"] = written
    return profile


def setup_config_draft(request: SetupConfigDraftRequest) -> dict[str, Any]:
    token = request.service_token.strip() if request.service_token else f"fr-{uuid.uuid4().hex}"
    mcp_servers = []
    if request.include_pska:
        if request.pska_http_url:
            mcp_servers.append(
                {
                    "name": "pska",
                    "transport": "http",
                    "url": request.pska_http_url,
                    "isolation": "shared",
                    "description": "PSKA HTTP MCP endpoint.",
                }
            )
        else:
            mcp_servers.append(
                {
                    "name": "pska",
                    "transport": "stdio",
                    "command": request.pska_command,
                    "args": ["mcp-server"],
                    "isolation": "shared",
                    "description": "PSKA personal knowledge store tools.",
                }
            )
    policy = {"default_action": "caution"}
    if request.include_pska:
        policy["tenant_rules"] = {
            "pska": {
                "tools": {
                    "exec": "require_approval",
                    "write_file": "require_approval",
                    "edit_file": "require_approval",
                    "pska_pska_search": "allow",
                    "pska_pska_agentic_search": "allow",
                    "pska_pska_index_status": "allow",
                }
            }
        }
    config = {
        "llm": {
            "model": request.model,
            "api_base": request.api_base,
            "api_key_file": request.api_key_file,
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        "service": {
            "host": request.host,
            "port": request.port,
            "log_level": "info",
            "service_token": token,
            "approval_timeout_seconds": 300,
            "run_lease_seconds": 300,
            "run_max_attempts": 3,
            "run_retry_base_seconds": 5,
            "run_retry_max_seconds": 300,
            "run_concurrency": 4,
            "recover_queued_runs": True,
        },
        "paths": {
            "gateway_workspace": request.workspace,
        },
        "react": {
            "max_iterations": 20,
            "max_context_tokens": 128000,
            "sliding_window_size": 15,
            "max_tool_output_chars": 5000,
            "enable_safety": True,
            "auto_approve_safe": True,
            "enable_filesystem_memory": True,
        },
        "mcp": {
            "servers": mcp_servers,
        },
        "policy": policy,
    }
    return {
        "schema": "fastreact.setup_config_draft.v1",
        "preset": request.preset,
        "write_supported": False,
        "recommended_path": "~/.fastreact/config.json",
        "service_token": token,
        "config": config,
        "warnings": [
            "This endpoint returns a draft only and does not write ~/.fastreact/config.json.",
            "The draft uses api_key_file and never includes a raw LLM API key.",
            "Review MCP commands and policy before using the draft in production.",
        ],
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


def _sum_llm_usage(records: list[dict[str, Any]]) -> dict[str, int]:
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for record in records:
        usage = record.get("llm_usage_total") or record.get("metadata", {}).get("llm_usage_total")
        if not isinstance(usage, dict):
            continue
        for key in totals:
            value = usage.get(key)
            if isinstance(value, (int, float)):
                totals[key] += int(value)
    return {key: value for key, value in totals.items() if value}


def _pska_digest_metrics(traces: list[dict[str, Any]]) -> dict[str, Any]:
    digest_traces = [
        trace
        for trace in traces
        if isinstance(trace.get("pska_digest_tool_budget"), dict)
        or trace.get("metadata", {}).get("caller") == "pska_digest_worker"
        or trace.get("metadata", {}).get("purpose") == "digest"
    ]
    exceeded = []
    write_calls = 0
    job_context_calls = 0
    for trace in digest_traces:
        budget = trace.get("pska_digest_tool_budget")
        if not isinstance(budget, dict):
            counts = trace.get("tool_name_counts") if isinstance(trace.get("tool_name_counts"), dict) else {}
            write_count = int(counts.get("pska_pska_write_candidates", 0) or 0)
            job_context_count = int(counts.get("pska_pska_job_context", 0) or 0)
            budget = {
                "write_call_count": write_count,
                "job_context_call_count": job_context_count,
                "tool_budget_exceeded": write_count > 1 or job_context_count > 1,
            }
        write_calls += int(budget.get("write_call_count") or 0)
        job_context_calls += int(budget.get("job_context_call_count") or 0)
        if budget.get("tool_budget_exceeded"):
            exceeded.append(
                {
                    "run_id": trace.get("run_id"),
                    "session_id": trace.get("session_id"),
                    "pska_job_id": trace.get("metadata", {}).get("pska_job_id"),
                    "write_call_count": budget.get("write_call_count"),
                    "job_context_call_count": budget.get("job_context_call_count"),
                    "completed_at": trace.get("completed_at"),
                }
            )
    return {
        "run_count": len(digest_traces),
        "write_call_count": write_calls,
        "job_context_call_count": job_context_calls,
        "tool_budget_exceeded_count": len(exceeded),
        "recent_budget_exceeded": exceeded[-5:],
    }


def _task_metrics(agent: Agent) -> dict[str, Any]:
    tasks_service = getattr(agent, "tasks", None)
    if not tasks_service:
        return {"count": 0, "status_counts": {}, "active_count": 0, "terminal_count": 0}
    tasks = tasks_service.list(limit=0)
    if isinstance(tasks, dict):
        task_list = list(tasks.values())
    else:
        task_list = list(tasks)
    status_counts: dict[str, int] = {}
    for task in task_list:
        status = str(task.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    terminal_count = status_counts.get("completed", 0) + status_counts.get("cancelled", 0)
    return {
        "count": len(task_list),
        "status_counts": status_counts,
        "active_count": sum(status_counts.get(status, 0) for status in ("pending", "in_progress", "blocked")),
        "terminal_count": terminal_count,
        "blocked_count": status_counts.get("blocked", 0),
    }


def policy_payload_for_agent(agent: Any) -> dict[str, Any]:
    config = getattr(agent, "_config", None)
    policy = getattr(config, "policy", None)
    payload = policy.to_safety_policy() if policy else {}
    return payload


def approval_resolution_ms(record: dict[str, Any]) -> float | None:
    return _duration_between_ms(record.get("created_at"), record.get("resolved_at"))


def approval_summary(approvals: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    policy_action_counts: dict[str, int] = {}
    durations = []
    for record in approvals:
        status = str(record.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        action = str(record.get("policy_action") or "none")
        policy_action_counts[action] = policy_action_counts.get(action, 0) + 1
        duration = approval_resolution_ms(record)
        if duration is not None:
            durations.append(duration)
    return {
        "count": len(approvals),
        "pending_count": sum(1 for item in approvals if item.get("status") == "pending"),
        "expired_count": sum(1 for item in approvals if item.get("expired") is True),
        "status_counts": status_counts,
        "policy_action_counts": policy_action_counts,
        "avg_resolution_ms": _avg(durations),
    }


def filter_approvals(
    approvals: list[dict[str, Any]],
    *,
    status: str | None = None,
    session_id: str | None = None,
    tool_name: str | None = None,
    policy_action: str | None = None,
    policy_scope: str | None = None,
    run_id: str | None = None,
    task_id: str | None = None,
    agent: Any | None = None,
    order: str = "desc",
) -> list[dict[str, Any]]:
    if status:
        approvals = [item for item in approvals if item.get("status") == status]
    if session_id:
        approvals = [item for item in approvals if item.get("session_id") == session_id]
    if tool_name:
        approvals = [item for item in approvals if item.get("tool_name") == tool_name]
    if policy_action:
        approvals = [item for item in approvals if item.get("policy_action") == policy_action]
    if policy_scope:
        approvals = [item for item in approvals if item.get("policy_scope") == policy_scope]
    if run_id and agent:
        run = get_run_service(agent).get(run_id) or {}
        run_session_id = run.get("session_id")
        approvals = [
            item
            for item in approvals
            if item.get("run_id") == run_id or (run_session_id and item.get("session_id") == run_session_id)
        ]
    if task_id and agent:
        task = getattr(agent, "tasks", None).get(task_id) if getattr(agent, "tasks", None) else None
        task_session_id = task.get("session_id") if task else None
        related = task_runs_and_traces(agent, task_id, task_session_id)
        session_ids = {run.get("session_id") for run in related.get("runs", []) if run.get("session_id")}
        if task_session_id:
            session_ids.add(task_session_id)
        approvals = [
            item
            for item in approvals
            if item.get("task_id") == task_id or (item.get("session_id") in session_ids if session_ids else False)
        ]
    approvals.sort(key=lambda item: item.get("created_at", ""), reverse=order != "asc")
    return approvals


def metrics_payload(agent: Agent) -> dict[str, Any]:
    """Return lightweight headless-service observability metrics."""
    store = getattr(agent, "store", None)
    store_stats = store.stats() if store else {}
    traces = store.read("traces", limit=0) if store else []
    events = store.read("events", limit=0) if store else []
    audit = store.read("audit", limit=0) if store else []
    approvals = agent.tool_executor.list_approvals() if hasattr(agent, "tool_executor") else []

    run_service = get_run_service(agent) if store else None
    durable_run_stats = run_service.stats() if run_service else {}
    durable_runs = run_service.list(limit=0) if run_service else []
    all_run_statuses: dict[str, int] = {}
    for item in [*traces, *durable_runs]:
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
            "live_count": sum(1 for run in durable_runs if run.get("status") in {"queued", "running"}),
            "trace_count": len(traces),
            "status_counts": all_run_statuses,
            "avg_duration_ms": _avg(trace_durations),
            "durable": durable_run_stats,
        },
        "events": {
            "total_count": len(events),
            "error_count": len(error_events),
        },
        "tools": {
            "audit_count": len(audit),
            "avg_duration_ms": _avg(tool_durations),
        },
        "llm": {
            "usage_total": _sum_llm_usage(traces),
        },
        "integrations": {
            "pska_digest": _pska_digest_metrics(traces),
        },
        "approvals": {
            "count": len(approvals),
            "pending_count": sum(1 for record in approvals if record.get("status") == "pending"),
            "expired_count": sum(1 for record in approvals if record.get("expired") is True),
            "status_counts": approval_statuses,
            "avg_resolution_ms": _avg(approval_durations),
        },
        "tasks": _task_metrics(agent),
        "errors": {
            "count": len(error_events) + len(failed_traces),
            "recent": recent_errors,
        },
        "store": store_stats,
    }


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:  # type: ignore[valid-type]
    agent = get_agent()
    try:
        runs = get_run_service(agent)
        runs.recover_stale()
        service_config = getattr(getattr(agent, "_config", None), "service", None)
        if getattr(service_config, "recover_queued_runs", True):
            schedule_queued_runs(agent)
    except Exception:
        # Readiness and metrics will report degraded dependency state.
        pass
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
    configured_origins = list(getattr(_service_config, "cors_origins", []) or [])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:13000",
            "http://127.0.0.1:13000",
            "http://localhost:13001",
            "http://127.0.0.1:13001",
            *configured_origins,
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
                "tasks": "GET/POST /v1/tasks",
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

    @app.get("/v1/setup")
    async def setup_status(request: Request) -> dict[str, Any]:  # type: ignore[valid-type]
        require_service_auth(request)
        agent = get_agent()
        readiness = readiness_payload(agent)
        metrics = metrics_payload(agent)
        config = getattr(agent, "_config", None)
        service = getattr(config, "service", None)
        paths = getattr(config, "paths", None)
        mcp_config = getattr(config, "mcp", None)
        return {
            "schema": "fastreact.setup_status.v1",
            "timestamp": utc_now(),
            "readiness": readiness,
            "service": {
                "host": getattr(service, "host", None),
                "port": getattr(service, "port", None),
                "auth_required": configured_service_token() is not None,
                "approval_timeout_seconds": getattr(service, "approval_timeout_seconds", None),
                "run_lease_seconds": getattr(service, "run_lease_seconds", None),
                "run_max_attempts": getattr(service, "run_max_attempts", None),
                "run_retry_base_seconds": getattr(service, "run_retry_base_seconds", None),
                "run_retry_max_seconds": getattr(service, "run_retry_max_seconds", None),
                "run_concurrency": getattr(service, "run_concurrency", None),
                "recover_queued_runs": getattr(service, "recover_queued_runs", None),
                "rate_limit_per_hour": getattr(service, "rate_limit_per_hour", 0),
                "blocked_user_count": len(getattr(service, "blocked_user_keys", []) or []),
                "allowed_user_count": len(getattr(service, "allowed_user_keys", []) or []),
            },
            "workspace": {
                "path": str(workspace_profile_root(agent)),
                "profile_files": read_workspace_profile(agent)["files"],
            },
            "mcp": {
                "configured_servers": len(getattr(mcp_config, "servers", []) or []),
                "servers": readiness.get("mcp", {}).get("servers", []),
                "tools": readiness.get("mcp", {}).get("tools", []),
            },
            "paths": {
                "global_skills_dir": str(getattr(paths, "global_skills_dir", "")),
                "user_skills_dir": str(getattr(paths, "user_skills_dir", "") or ""),
                "gateway_workspace": str(getattr(paths, "gateway_workspace", "")),
            },
            "metrics": metrics,
            "presets": {
                "pska": {
                    "config_file": "config.pska.example.json",
                    "protocol_only": True,
                    "notes": "Use HTTP/SSE plus MCP/HTTP MCP. FastReAct should not import PSKA internals or access the PSKA DB.",
                }
            },
        }

    @app.get("/v1/setup/presets")
    async def setup_presets(request: Request) -> dict[str, Any]:  # type: ignore[valid-type]
        require_service_auth(request)
        return {
            "schema": "fastreact.setup_presets.v1",
            "presets": [
                {
                    "id": "default",
                    "label": "Generic single-agent daemon",
                    "description": "HTTP/SSE daemon with durable runs, approvals, JSONL store, and local workspace profile.",
                },
                {
                    "id": "pska",
                    "label": "PSKA protocol-only integration",
                    "description": "Adds PSKA MCP server and tenant-safe policy defaults without importing PSKA internals.",
                },
            ],
            "write_supported": False,
        }

    @app.post("/v1/setup/config-draft")
    async def create_setup_config_draft(
        request: Request,
        draft_request: SetupConfigDraftRequest,
    ) -> dict[str, Any]:
        require_service_auth(request)
        return setup_config_draft(draft_request)

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request, chat_request: ChatRequest) -> Any:  # type: ignore[valid-type]
        require_service_auth(request)
        require_user_access(chat_request.user_key)
        require_rate_limit(chat_request.user_key)
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
        generation_options = generation_options_from_request(chat_request)
        started_at = time.perf_counter()

        async def event_generator() -> AsyncIterator[str]:
            parent_event_id = None
            try:
                async for event in run_agent_event_stream(
                    agent,
                    query=query,
                    skills=chat_request.skills,
                    session_id=session_id,
                    history=history,
                    user_key=chat_request.user_key,
                    run_metadata=dict(chat_request.metadata or {}),
                    llm_options=generation_options,
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
            async for event in run_agent_event_stream(
                agent,
                query=query,
                skills=chat_request.skills,
                session_id=session_id,
                history=history,
                user_key=chat_request.user_key,
                run_metadata=dict(chat_request.metadata or {}),
                llm_options=generation_options,
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
        require_user_access(chat_request.user_key)
        require_rate_limit(chat_request.user_key)
        if not chat_request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        try:
            query = extract_query(chat_request.messages)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        run_id = str(chat_request.metadata.get("run_id") or uuid.uuid4())
        generation_options = generation_options_from_request(chat_request)
        runs = get_run_service()
        if runs.get(run_id):
            raise HTTPException(status_code=409, detail="Run already exists")
        session_id = chat_request.session_id or str(uuid.uuid4())
        record = runs.create(
            run_id=run_id,
            session_id=session_id,
            query=query,
            skills=chat_request.skills,
            history=extract_history(chat_request.messages),
            user_key=chat_request.user_key,
            metadata=dict(chat_request.metadata or {}),
            generation_options=generation_options,
        )
        schedule_queued_runs(get_agent())
        return {"type": "run", **(runs.snapshot(run_id) or run_snapshot(record))}

    @app.get("/v1/runs")
    async def list_runs(request: Request, limit: int = 200, status: Optional[str] = None) -> dict[str, Any]:
        require_service_auth(request)
        run_service = get_run_service()
        runs = [run_service.snapshot(run["run_id"]) or run_snapshot(run) for run in run_service.list(status=status, limit=0)]
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
        run_service = get_run_service()
        snapshot = run_service.snapshot(run_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail="Run not found")
        return {"type": "run", **snapshot}

    @app.get("/v1/runs/{run_id}/events")
    async def get_run_events(
        run_id: str,
        request: Request,
        limit: int = 200,
        after_sequence: Optional[int] = None,
    ) -> dict[str, Any]:
        require_service_auth(request)
        run_service = get_run_service()
        record = run_service.get(run_id)
        if not record:
            raise HTTPException(status_code=404, detail="Run not found")
        events = run_service.events(run_id)
        page = page_event_list(events, limit=limit, after_sequence=after_sequence)
        return {
            "run_id": run_id,
            "session_id": record["session_id"],
            "status": record["status"],
            **page,
        }

    @app.post("/v1/runs/{run_id}/cancel")
    async def cancel_run(run_id: str, request: Request) -> dict[str, Any]:
        require_service_auth(request)
        run_service = get_run_service()
        record = run_service.get(run_id)
        if not record:
            raise HTTPException(status_code=404, detail="Run not found")
        if record["status"] in TERMINAL_RUN_STATUSES:
            return {"type": "run", **(run_service.snapshot(run_id) or run_snapshot(record))}
        record = run_service.cancel(run_id)
        task = _run_tasks.get(run_id)
        if task and not task.done():
            task.cancel()
        return {"type": "run", **(run_service.snapshot(run_id) or run_snapshot(record))}

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
        run_service = get_run_service(agent)
        snapshot = run_service.snapshot(run_id, include_events=False)
        if snapshot:
            return {"trace": snapshot}
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
        run_service = get_run_service(agent)
        events = run_service.events(run_id)
        if not events and store:
            events = store.read("events", limit=0, run_id=run_id)
        if not events:
            raise HTTPException(status_code=404, detail="Trace events not found")
        page = page_event_list(events, limit=limit, after_sequence=after_sequence)
        return {"run_id": run_id, **page}

    @app.get("/v1/tasks")
    async def list_tasks(
        request: Request,
        limit: int = 200,
        status: Optional[str] = None,
        owner: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        tasks_service = getattr(agent, "tasks", None)
        if not tasks_service:
            raise HTTPException(status_code=503, detail="Task service not available")
        bounded = bounded_limit(limit)
        tasks = tasks_service.list(status=status, owner=owner, session_id=session_id, limit=0)
        if isinstance(tasks, dict):
            tasks = list(tasks.values())
            tasks.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        page = tasks if bounded == 0 else tasks[:bounded]
        return {
            "schema": "fastreact.tasks.v1",
            "tasks": page,
            "count": len(page),
            "total_count": len(tasks),
            "limit": bounded,
            "has_more": bounded != 0 and len(tasks) > len(page),
        }

    @app.post("/v1/tasks")
    async def create_task(request: Request, task_request: TaskCreateRequest) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        tasks_service = getattr(agent, "tasks", None)
        if not tasks_service:
            raise HTTPException(status_code=503, detail="Task service not available")
        if not task_request.title.strip():
            raise HTTPException(status_code=400, detail="Task title is required")
        task = tasks_service.create(
            title=task_request.title.strip(),
            description=task_request.description,
            priority=task_request.priority,
            owner=task_request.owner,
            dependencies=task_request.dependencies,
            session_id=task_request.session_id,
        )
        return {"schema": "fastreact.tasks.v1", "task": task}

    @app.get("/v1/tasks/{task_id}")
    async def get_task(task_id: str, request: Request) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        tasks_service = getattr(agent, "tasks", None)
        if not tasks_service:
            raise HTTPException(status_code=503, detail="Task service not available")
        task = tasks_service.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        related = task_runs_and_traces(agent, task_id, task.get("session_id") or None)
        return {"schema": "fastreact.tasks.v1", "task": task, **related}

    @app.patch("/v1/tasks/{task_id}")
    async def update_task(task_id: str, request: Request, task_request: TaskUpdateRequest) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        tasks_service = getattr(agent, "tasks", None)
        if not tasks_service:
            raise HTTPException(status_code=503, detail="Task service not available")
        changes = task_request.model_dump(exclude_unset=True) if hasattr(task_request, "model_dump") else task_request.dict(exclude_unset=True)
        try:
            task = tasks_service.update(task_id, **changes)
        except ValueError as exc:
            message = str(exc)
            status_code = 404 if "not found" in message.lower() else 400
            raise HTTPException(status_code=status_code, detail=message) from exc
        related = task_runs_and_traces(agent, task_id, task.get("session_id") or None)
        return {"schema": "fastreact.tasks.v1", "task": task, **related}

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
            skill = agent.get_skill(name) if hasattr(agent, "get_skill") else getattr(agent, "skills", {}).get(name)
            if skill:
                locations = agent.get_skill_locations(name) if hasattr(agent, "get_skill_locations") else []
                source_path = next((item.get("path") for item in locations if item.get("active")), None)
                skills.append(
                    {
                        "name": skill.name,
                        "description": skill.description,
                        "version": skill.metadata.version,
                        "source_path": source_path,
                        "duplicate_count": max(0, len(locations) - 1),
                    }
                )
        return {"skills": skills}

    @app.get("/v1/skills/diagnostics")
    async def skill_diagnostics(request: Request) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        diagnostics = []
        available_tools = set(agent.list_tools())
        mcp_status = agent.list_mcp_server_status() if hasattr(agent, "list_mcp_server_status") else []
        mcp_by_name = {item.get("name"): item for item in mcp_status if isinstance(item, dict)}
        for name in agent.list_skills():
            skill = agent.get_skill(name) if hasattr(agent, "get_skill") else getattr(agent, "skills", {}).get(name)
            if not skill:
                continue
            metadata = skill.metadata
            locations = agent.get_skill_locations(name) if hasattr(agent, "get_skill_locations") else []
            active_source = next((item for item in locations if item.get("active")), None)
            duplicate_sources = [item for item in locations if not item.get("active")]
            missing_tools = [tool for tool in metadata.recommended_tools if tool not in available_tools]
            missing_mcp_servers = [
                server_name
                for server_name in metadata.mcp_servers
                if not mcp_by_name.get(server_name, {}).get("alive", False)
            ]
            diagnostics.append(
                {
                    "name": skill.name,
                    "description": skill.description,
                    "version": metadata.version,
                    "tags": metadata.tags,
                    "dependencies": metadata.dependencies,
                    "mcp_servers": metadata.mcp_servers,
                    "recommended_tools": metadata.recommended_tools,
                    "missing_tools": missing_tools,
                    "missing_mcp_servers": missing_mcp_servers,
                    "files": skill.list_files(),
                    "source_path": active_source.get("path") if active_source else None,
                    "source_root": active_source.get("root") if active_source else None,
                    "duplicate_sources": duplicate_sources,
                    "status": "ready" if not missing_tools and not missing_mcp_servers else "degraded",
                }
            )
        return {
            "schema": "fastreact.skill_diagnostics.v1",
            "skills": diagnostics,
            "count": len(diagnostics),
            "tools": sorted(available_tools),
            "mcp_servers": mcp_status,
        }

    @app.get("/v1/tools")
    async def list_tools() -> dict[str, Any]:
        agent = get_agent()
        return {
            "tools": agent.list_tools(),
            "mcp_tools": agent.list_mcp_tools() if hasattr(agent, "list_mcp_tools") else [],
            "tool_summaries": agent.list_tool_schema_summary() if hasattr(agent, "list_tool_schema_summary") else [],
            "mcp_servers": agent.list_mcp_server_status() if hasattr(agent, "list_mcp_server_status") else [],
        }

    @app.post("/v1/extensions/reload")
    async def reload_extensions(
        request: Request,
        reload_request: ExtensionReloadRequest,
    ) -> dict[str, Any]:
        require_service_auth(request)
        require_user_access(reload_request.user_key)
        agent = get_agent()
        config = getattr(agent, "config", getattr(agent, "_config", None))
        extensions = getattr(config, "extensions", None)

        if not getattr(extensions, "runtime_reload_enabled", False):
            raise HTTPException(status_code=403, detail="Runtime extension reload is disabled")
        if reload_request.mcp and not getattr(extensions, "mcp_reload_enabled", False):
            raise HTTPException(status_code=403, detail="Runtime MCP reload is disabled")

        response: dict[str, Any] = {
            "schema": "fastreact.extension_reload.v1",
            "timestamp": utc_now(),
            "dry_run": reload_request.dry_run,
            "requested": {
                "skills": reload_request.skills,
                "mcp": reload_request.mcp,
                "required_skills": reload_request.required_skills or [],
                "user_key": reload_request.user_key,
            },
        }

        if reload_request.dry_run:
            response["skills"] = {
                "would_reload": reload_request.skills,
                "current_count": len(agent.list_skills()) if hasattr(agent, "list_skills") else None,
                "search_paths": [str(path) for path in agent._skill_search_paths()] if hasattr(agent, "_skill_search_paths") else [],
            }
            response["mcp"] = {
                "would_reload": reload_request.mcp,
                "current_tools": agent.list_mcp_tools() if hasattr(agent, "list_mcp_tools") else [],
                "servers": agent.list_mcp_server_status() if hasattr(agent, "list_mcp_server_status") else [],
            }
            return response

        if reload_request.skills:
            if not hasattr(agent, "reload_skills"):
                raise HTTPException(status_code=503, detail="Skill reload is not available")
            response["skills"] = agent.reload_skills()
        else:
            response["skills"] = {"reloaded": False}

        if reload_request.mcp:
            if not hasattr(agent, "reload_mcp_servers"):
                raise HTTPException(status_code=503, detail="MCP reload is not available")
            response["mcp"] = await agent.reload_mcp_servers(
                required_skills=reload_request.required_skills,
                user_key=reload_request.user_key,
            )
        else:
            response["mcp"] = {"reloaded": False}

        return response

    @app.get("/v1/workspace/profile")
    async def get_workspace_profile(request: Request) -> dict[str, Any]:
        require_service_auth(request)
        return read_workspace_profile(get_agent())

    @app.put("/v1/workspace/profile")
    async def update_workspace_profile(
        request: Request,
        update: WorkspaceProfileUpdateRequest,
    ) -> dict[str, Any]:
        require_service_auth(request)
        return write_workspace_profile(get_agent(), update)

    @app.get("/v1/policy")
    async def get_policy(request: Request) -> dict[str, Any]:
        require_service_auth(request)
        agent = get_agent()
        policy_payload = policy_payload_for_agent(agent)
        return {
            "schema": "fastreact.policy.v1",
            "policy": policy_payload,
            "policy_snapshot_hash": RunService.policy_snapshot_hash(policy_payload),
            "policy_version": RunService.policy_snapshot_hash(policy_payload),
            "reload_supported": False,
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
    async def list_approvals(
        request: Request,
        limit: int = 200,
        offset: int = 0,
        order: str = "desc",
        status: Optional[str] = None,
        session_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        policy_action: Optional[str] = None,
        policy_scope: Optional[str] = None,
        run_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> dict[str, Any]:
        require_service_auth(request)
        if order not in {"asc", "desc"}:
            raise HTTPException(status_code=400, detail="order must be 'asc' or 'desc'")
        agent = get_agent()
        executor = getattr(agent, "tool_executor", None)
        approvals = executor.list_approvals() if executor and hasattr(executor, "list_approvals") else []
        filtered = filter_approvals(
            approvals,
            status=status,
            session_id=session_id,
            tool_name=tool_name,
            policy_action=policy_action,
            policy_scope=policy_scope,
            run_id=run_id,
            task_id=task_id,
            agent=agent,
            order=order,
        )
        bounded = bounded_limit(limit)
        safe_offset = max(0, int(offset or 0))
        page = filtered[safe_offset:] if bounded == 0 else filtered[safe_offset : safe_offset + bounded]
        summary = approval_summary(filtered)
        return {
            "schema": "fastreact.approvals.v1",
            "approvals": page,
            "count": len(page),
            "total_count": len(filtered),
            "limit": bounded,
            "offset": safe_offset,
            "order": order,
            "next_offset": safe_offset + len(page) if bounded != 0 and safe_offset + len(page) < len(filtered) else None,
            "has_more": bounded != 0 and safe_offset + len(page) < len(filtered),
            "pending_count": summary["pending_count"],
            "summary": summary,
            "filters": {
                "order": order,
                "status": status,
                "session_id": session_id,
                "tool_name": tool_name,
                "policy_action": policy_action,
                "policy_scope": policy_scope,
                "run_id": run_id,
                "task_id": task_id,
            },
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
