"""
Gateway Adapter for FastReAct Nano

Provides WebSocket gateway with session management.
Install with: pip install fastreact-nano[gateway]
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

try:
    from fastapi import WebSocket, WebSocketDisconnect, FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    Request = None  # Placeholder for type hints

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import websockets

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from fastreact import Agent, Config
from fastreact import __version__  # Import version for consistency
from fastreact.core.multitenant import (
    get_global_agent,
    generate_temp_user_key,
    validate_user_key,
    MultiTenantManager,
)

logger = logging.getLogger(__name__)


class Session:
    """
    Gateway Session - Transport Layer Only

    Responsibilities:
    - WebSocket connection management
    - Event sending to client
    - Delegating business logic to AgentSession

    This class is now a THIN wrapper around AgentSession.
    All business logic (history, follow-ups, state) is in AgentSession.

    Multi-tenant Support (Unified Architecture):
    - All sessions share a global Agent instance
    - User identification via user_key parameter
    - Workspace isolation per user (handled by Agent)
    - Lightweight sessions with user context

    Architecture Pattern: Shared Agent + user_key (same as Feishu SDK)
    """

    def __init__(
        self,
        session_id: str,
        websocket: WebSocket,
        user_key: str,
        agent: "Agent",  # ✅ Shared Agent instance (required)
        multitenant_enabled: bool = True,
        max_history: int = 50,
        max_queue_size: int = 5,
    ):
        self.session_id = session_id
        self.websocket = websocket
        self.user_key = user_key
        self.multitenant_enabled = multitenant_enabled
        self.max_queue_size = max_queue_size
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)

        # Background task reference
        self._processing_task: Optional[asyncio.Task] = None

        # ✅ Use shared Agent instance (passed from outside)
        self.agent = agent

        # Create AgentSession for business logic (all business logic here)
        # Pass user_key for multi-tenant session tracking
        self.agent_session = self.agent.sessions.create(
            session_id=session_id,
            user_key=user_key if multitenant_enabled else None,
            max_history=max_history,
            followup_window_seconds=30,
            max_queue_size=max_queue_size,
        )

    async def send(self, message: dict):
        """
        Send message to client (transport layer only)

        Args:
            message: Message dict to send as JSON
        """
        try:
            await self.websocket.send_json(message)
        except Exception:
            pass

    def update_activity(self):
        """Update last activity timestamp (delegated to AgentSession)"""
        self.last_activity = datetime.now(timezone.utc)
        self.agent_session.update_activity()

    def interrupt(self):
        """Interrupt current execution (delegated to AgentSession)"""
        self.agent_session.interrupt()

    async def enqueue_message(self, message: dict) -> bool:
        """
        Enqueue message for processing (delegated to AgentSession)

        Args:
            message: Message dict with 'type' field

        Returns:
            True if message enqueued, False if queue full
        """
        return await self.agent_session.enqueue_message(message)

    async def process_queue(self):
        """
        Background task to process message queue (simplified)

        Delegates to AgentSession.process_queue() with callback for sending events.
        """
        while True:
            message = await self.agent_session._message_queue.get()

            # Process with callback (self.send) to send events to WebSocket client
            await self.agent_session.process_message(
                message,
                on_event=self.send,  # Callback: send events to WebSocket
            )


class SessionManager:
    """Manage gateway sessions"""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_key: str,
        agent: "Agent",  # ✅ Shared Agent instance
        multitenant_enabled: bool = True,
    ) -> Session:
        """
        Accept connection and create session

        Args:
            websocket: WebSocket connection
            user_key: User identifier (format: "channel:user_id")
            agent: Shared Agent instance
            multitenant_enabled: Enable multi-tenant mode

        Returns:
            Session instance
        """
        await websocket.accept()

        session_id = str(uuid.uuid4())
        session = Session(
            session_id,
            websocket,
            user_key=user_key,
            agent=agent,  # ✅ Pass shared Agent
            multitenant_enabled=multitenant_enabled,
        )
        self._sessions[session_id] = session

        mode = "multi-tenant" if multitenant_enabled else "single-tenant"
        await session.send({
            "type": "connected",
            "session_id": session_id,
            "user_key": user_key,
            "mode": mode,  # NEW: Include mode in connection message
            "message": f"Connected to FastReAct Nano Gateway ({mode} mode)",
        })

        return session

    def disconnect(self, session_id: str):
        """Remove session"""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def get(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self._sessions.get(session_id)

    def list_all(self) -> list[str]:
        """List all session IDs"""
        return list(self._sessions.keys())

    @property
    def count(self) -> int:
        """Get session count"""
        return len(self._sessions)


# Global session manager
_session_manager = SessionManager()

# Global agent (unified architecture - simplified)
_global_agent_cached: Optional[Agent] = None

# Global metrics
_gateway_start_time = datetime.now(timezone.utc)
_total_events_counter = 0

# Admin authentication (loaded from config at runtime)
ADMIN_API_KEY = None


def get_gateway_agent(
    config: Optional["Config"] = None,
) -> Agent:
    """
    Get or create global agent for gateway (simplified)

    Args:
        config: Configuration object

    Returns:
        Global Agent instance
    """
    global _global_agent_cached

    if _global_agent_cached is None:
        # Load config if not provided
        if config is None:
            config = Config.load()

        # Determine workspace
        workspace_path = Path.cwd() / "workspace"

        # Create global agent (always multi-tenant mode)
        _global_agent_cached = get_global_agent(
            base_workspace=workspace_path,
            config=config,
        )

        logger.info("Using global shared Agent (multi-tenant=True)")

    return _global_agent_cached


def get_admin_api_key() -> str:
    """Get admin API key from configuration or environment"""
    global ADMIN_API_KEY

    if ADMIN_API_KEY is None:
        # Try environment variable first (backward compatibility)
        ADMIN_API_KEY = os.getenv("GATEWAY_ADMIN_KEY")

        if ADMIN_API_KEY is None:
            # Try loading from config file
            try:
                config = Config.load()
                ADMIN_API_KEY = config.gateway.admin_api_key
            except Exception:
                # Fallback to default
                ADMIN_API_KEY = "admin-secret-key-change-in-production"

    return ADMIN_API_KEY


def verify_admin(request) -> bool:
    """
    Verify admin access

    Args:
        request: FastAPI request object

    Returns:
        True if authenticated, False otherwise
    """
    expected_key = get_admin_api_key()

    # Check API key in header
    api_key = request.headers.get("X-Admin-Key")
    if api_key:
        return api_key == expected_key

    # For GET requests, check query params
    if hasattr(request, "query_params"):
        api_key = request.query_params.get("admin_key")
        if api_key:
            return api_key == expected_key

    return False


def admin_api_auth_enabled() -> bool:
    """Return whether REST control-plane APIs require admin authentication."""
    env_value = os.getenv("FASTREACT_ADMIN_API_AUTH")
    if env_value is not None:
        return env_value.lower() in ("1", "true", "yes", "on")
    try:
        return Config.load().gateway.admin_only
    except Exception:
        return False


def require_admin_api(request: Request) -> Optional[JSONResponse]:
    """Return a 401 response when protected admin API access is unauthorized."""
    if admin_api_auth_enabled() and not verify_admin(request):
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized. Valid admin API key required."},
        )
    return None


def create_gateway_app() -> FastAPI:
    """Create FastAPI gateway application"""
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI not available. "
            "Install with: pip install fastreact-nano[gateway]"
        )

    app = FastAPI(
        title="FastReAct Nano Gateway",
        description="WebSocket gateway for FastReAct Nano",
        version=__version__,  # Use version from __init__.py for consistency
    )

    configured_origins = [
        origin.strip()
        for origin in os.getenv("FASTREACT_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Next.js frontend
            "http://127.0.0.1:3000",  # Next.js frontend
            "http://localhost:5173",  # Vue 3 frontend (dev)
            "http://localhost:9000",  # Gateway self
            "http://127.0.0.1:9000",  # Gateway self
            *configured_origins,
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        """Gateway homepage"""
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>FastReAct Nano Gateway</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; }
                #messages { border: 1px solid #ccc; height: 400px; overflow-y: scroll; padding: 10px; }
                .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
                .user { background: #e3f2fd; }
                .agent { background: #f1f8e9; }
                input { width: 70%; padding: 10px; }
                button { padding: 10px 20px; }
            </style>
        </head>
        <body>
            <h1>FastReAct Nano Gateway</h1>
            <div id="messages"></div>
            <input type="text" id="query" placeholder="输入问题...">
            <button onclick="send()">发送</button>

            <script>
                const ws = new WebSocket("ws://localhost:9000/ws");

                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    const messages = document.getElementById("messages");
                    const div = document.createElement("div");
                    div.className = "message " + data.type;
                    div.textContent = data.content;
                    messages.appendChild(div);
                    messages.scrollTop = messages.scrollHeight;
                };

                function send() {
                    const query = document.getElementById("query").value;
                    ws.send(JSON.stringify({ type: "query", content: query }));
                    document.getElementById("query").value = "";
                }
            </script>
        </body>
        </html>
        """)

    @app.get("/sessions")
    async def list_sessions():
        """List active sessions"""
        return {
            "count": _session_manager.count,
            "sessions": _session_manager.list_all(),
        }

    @app.get("/api/sessions")
    async def list_sessions_api(request: Request):
        """List all active sessions (REST API)"""
        denied = require_admin_api(request)
        if denied:
            return denied
        agent = get_gateway_agent()
        sessions = agent.sessions.list()
        return {"sessions": sessions, "count": len(sessions)}

    @app.get("/api/sessions/{session_id}")
    async def get_session_api(session_id: str, request: Request):
        """Get live or persisted session detail with event replay."""
        denied = require_admin_api(request)
        if denied:
            return denied
        agent = get_gateway_agent()
        detail = agent.sessions.detail(session_id)
        if not detail:
            return JSONResponse(status_code=404, content={"message": f"Session {session_id} not found"})
        detail["traces"] = agent.store.read("traces", limit=50, session_id=session_id)
        detail["audit"] = agent.store.read("audit", limit=50, session_id=session_id)
        detail["tasks"] = agent.tasks.list(session_id=session_id)
        return detail

    @app.post("/api/sessions/{session_id}/resume")
    async def resume_session_api(session_id: str, request: Request):
        """Mark a persisted session as resumable for clients."""
        denied = require_admin_api(request)
        if denied:
            return denied
        agent = get_gateway_agent()
        detail = agent.sessions.detail(session_id)
        if not detail:
            return JSONResponse(status_code=404, content={"message": f"Session {session_id} not found"})
        agent.store.append("sessions", {
            "session_id": session_id,
            "status": "idle",
            "resume_requested": True,
            "user_key": detail.get("user_key"),
        })
        return {"message": "Session ready to resume", "session_id": session_id}

    @app.delete("/api/sessions/{session_id}")
    async def terminate_session(session_id: str, request: Request):
        """Terminate a session by ID"""
        denied = require_admin_api(request)
        if denied:
            return denied
        session = _session_manager.get(session_id)
        if session:
            # Close WebSocket connection
            try:
                await session.websocket.close()
            except Exception:
                pass
            # Remove from session manager
            _session_manager.disconnect(session_id)
            return {"message": f"Session {session_id} terminated"}
        else:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=404,
                content={"message": f"Session {session_id} not found"}
            )

    @app.get("/api/tasks")
    async def list_tasks(request: Request, status: Optional[str] = None, owner: Optional[str] = None, session_id: Optional[str] = None):
        """List durable tasks."""
        denied = require_admin_api(request)
        if denied:
            return denied
        agent = get_gateway_agent()
        tasks = agent.tasks.list(status=status, owner=owner, session_id=session_id)
        return {"tasks": tasks, "count": len(tasks)}

    @app.post("/api/tasks")
    async def create_task(request_data: dict, request: Request):
        """Create a durable task."""
        denied = require_admin_api(request)
        if denied:
            return denied
        agent = get_gateway_agent()
        task = agent.tasks.create(
            title=request_data.get("title", ""),
            description=request_data.get("description", ""),
            priority=request_data.get("priority", "normal"),
            owner=request_data.get("owner", ""),
            dependencies=request_data.get("dependencies") or [],
            session_id=request_data.get("session_id", ""),
        )
        return task

    @app.patch("/api/tasks/{task_id}")
    async def update_task(task_id: str, request_data: dict, request: Request):
        """Update a durable task."""
        denied = require_admin_api(request)
        if denied:
            return denied
        agent = get_gateway_agent()
        try:
            return agent.tasks.update(task_id, **request_data)
        except ValueError as exc:
            return JSONResponse(status_code=404, content={"message": str(exc)})

    @app.get("/api/audit")
    async def list_audit(request: Request, limit: int = 200, session_id: Optional[str] = None):
        """List tool permission and execution audit records."""
        denied = require_admin_api(request)
        if denied:
            return denied
        agent = get_gateway_agent()
        records = agent.store.read("audit", limit=limit, session_id=session_id)
        return {"audit": records, "count": len(records)}

    @app.get("/api/traces")
    async def list_traces(request: Request, limit: int = 200, session_id: Optional[str] = None):
        """List runtime timing traces."""
        denied = require_admin_api(request)
        if denied:
            return denied
        agent = get_gateway_agent()
        records = agent.store.read("traces", limit=limit, session_id=session_id)
        return {"traces": records, "count": len(records)}

    @app.post("/api/control/tool-approval")
    async def tool_approval(request_data: dict, request: Request):
        """Resolve a pending tool approval request."""
        denied = require_admin_api(request)
        if denied:
            return denied
        agent = get_gateway_agent()
        request_id = request_data.get("request_id", "")
        approved = bool(request_data.get("approved"))
        ok = agent.tool_executor.resolve_approval(
            request_id,
            approved,
            reason=request_data.get("reason", ""),
        )
        return {"ok": ok, "request_id": request_id, "approved": approved}

    @app.get("/api/control/pending-approvals")
    async def pending_approvals(request: Request):
        """List pending and recently resolved tool approval requests."""
        denied = require_admin_api(request)
        if denied:
            return denied
        agent = get_gateway_agent()
        approvals = agent.tool_executor.list_approvals()
        return {"approvals": approvals, "count": len(approvals)}

    @app.get("/api/config")
    async def get_config(request: Request):
        """Get current configuration (hide sensitive fields)"""
        denied = require_admin_api(request)
        if denied:
            return denied
        from fastreact.core.config import Config

        config = Config.load()

        # Derive provider from model name
        model = config.llm.model or ""
        if "/" in model:
            provider = model.split("/")[0]
        elif "gpt" in model:
            provider = "openai"
        elif "claude" in model:
            provider = "anthropic"
        else:
            provider = "custom"

        return {
            "llm": {
                "provider": provider,
                "model": config.llm.model,
                "api_key": "***",  # Hidden for security
                "base_url": config.llm.api_base or "https://api.openai.com/v1",
                "temperature": config.llm.temperature,
                "max_tokens": config.llm.max_tokens,
            },
            "mcp_servers": [
                {
                    "name": s.name,
                    "command": s.command,
                    "args": s.args,
                    "description": s.description if hasattr(s, 'description') else None,
                    "isolation": s.isolation if hasattr(s, 'isolation') else "shared",
                    "associated_skill": s.associated_skill if hasattr(s, 'associated_skill') else None,
                }
                for s in config.mcp.servers
            ],
            "tools": [],  # Tools list (empty for now)
            "system_prompt": "",  # System prompt (empty for now)
            "max_iterations": config.react.max_iterations,
        }

    @app.put("/api/config")
    async def update_config(request_data: dict, request: Request):
        """Update configuration"""
        denied = require_admin_api(request)
        if denied:
            return denied
        from fastreact.core.config import Config
        from pathlib import Path as LibPath
        import json

        config = Config.load()

        # Update LLM config
        if "llm" in request_data:
            llm_data = request_data["llm"]
            if llm_data.get("api_key") != "***":
                config.llm.api_key = llm_data.get("api_key")
            config.llm.model = llm_data.get("model", config.llm.model)
            config.llm.api_base = llm_data.get("base_url", config.llm.api_base)
            config.llm.temperature = llm_data.get("temperature", config.llm.temperature)
            config.llm.max_tokens = llm_data.get("max_tokens", config.llm.max_tokens)

        # Update React config
        if "max_iterations" in request_data:
            config.react.max_iterations = request_data["max_iterations"]

        # Save to config file
        config_path = LibPath.home() / ".fastreact" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config.save(config_path)

        return {"message": "Configuration saved successfully", "path": str(config_path)}

    @app.get("/api/skills")
    async def list_skills():
        """List all available skills (global and user-specific)"""
        # ✅ Use shared agent from global agent cache
        agent = get_gateway_agent()

        # Get all available skills through the runtime boundary
        skill_names = agent.skill_resolver.list_available()

        skills = []
        for skill_name in skill_names:
            skill = agent.get_skill(skill_name)
            if skill:
                skill_info = {
                    "name": skill.name,
                    "description": skill.description,
                    "version": skill.version if hasattr(skill, 'version') else "1.0.0",
                    "author": skill.author if hasattr(skill, 'author') else "Unknown",
                    "mcp_servers": skill.metadata.mcp_servers if hasattr(skill, 'metadata') and hasattr(skill.metadata, 'mcp_servers') else [],
                }
                skills.append(skill_info)

        return {
            "skills": skills,
            "global_skills_dir": str(agent.config.paths.global_skills_dir),
            "total_count": len(skills)
        }

    @app.get("/api/status")
    async def get_status():
        """Get system status including SKILL and MCP information"""
        import asyncio

        # ✅ Use shared agent from global agent cache
        agent = get_gateway_agent()
        config = agent.config

        # Determine multi-tenant mode from configuration
        multitenant_enabled = config.gateway.enable_multitenant

        # Load MCP servers to get status
        mcp_loaded = False
        mcp_servers_info = []

        try:
            asyncio.get_event_loop()
            await agent.ensure_mcp_loaded()
            mcp_loaded = True

            # Get MCP server status
            for server_status in agent.list_mcp_server_status():
                server_name = server_status["name"]
                isolation = "unknown"
                for server_config in config.mcp.servers:
                    if server_config.name == server_name:
                        isolation = server_config.isolation if hasattr(server_config, 'isolation') else server_config.get("isolation", "shared")
                        break
                mcp_servers_info.append({
                    "name": server_name,
                    "status": "running" if server_status["alive"] else "stopped",
                    "isolation": isolation
                })
        except RuntimeError:
            pass

        # Get skills
        skill_names = agent.list_skills()

        # Get temp user stats if multi-tenant
        temp_user_stats = agent.get_temp_user_stats() if multitenant_enabled else {}

        return {
            "status": "healthy",
            "version": "2.4.2",
            "features": {
                "skill_system": {
                    "enabled": True,
                    "total_skills": len(skill_names),
                    "global_skills_dir": str(config.paths.global_skills_dir),
                    "skills": skill_names
                },
                "mcp_system": {
                    "enabled": True,
                    "loaded": mcp_loaded,
                    "total_servers": len(config.mcp.servers),
                    "servers": mcp_servers_info
                },
                "multi_tenant": {
                    "enabled": multitenant_enabled,
                    "mode": "multi-tenant (per-user workspace isolation)" if multitenant_enabled else "single-tenant (shared workspace)",
                    "temp_users": temp_user_stats if multitenant_enabled else {}
                }
            }
        }

    @app.get("/api/health/dependencies")
    async def dependency_health(request: Request):
        """Return deploy-time dependency health without exposing secrets."""
        denied = require_admin_api(request)
        if denied:
            return denied

        agent = get_gateway_agent()
        config = agent.config
        store_stats = agent.store.stats()

        llm_configured = bool(config.llm.model) and bool(config.llm.api_key or os.getenv("OPENAI_API_KEY"))
        store_writable = False
        try:
            agent.store.root.mkdir(parents=True, exist_ok=True)
            store_writable = os.access(agent.store.root, os.W_OK)
        except Exception:
            store_writable = False

        mcp_servers = agent.list_mcp_server_status()
        checks = {
            "llm": {
                "status": "configured" if llm_configured else "missing_key",
                "model": config.llm.model,
                "api_base_configured": bool(config.llm.api_base),
            },
            "store": {
                "status": "writable" if store_writable else "not_writable",
                "root": store_stats["root"],
                "streams": len(store_stats["streams"]),
                "records": store_stats["total_records"],
                "bytes": store_stats["total_bytes"],
            },
            "mcp": {
                "status": "configured" if config.mcp.servers else "not_configured",
                "configured_servers": len(config.mcp.servers),
                "known_servers": mcp_servers,
            },
            "gateway": {
                "status": "healthy",
                "active_sessions": _session_manager.count,
                "admin_api_auth": admin_api_auth_enabled(),
                "multitenant": config.gateway.enable_multitenant,
            },
            "frontend": {
                "status": "external",
                "expected_http_env": "NEXT_PUBLIC_FASTREACT_GATEWAY_HTTP_URL",
                "expected_ws_env": "NEXT_PUBLIC_FASTREACT_GATEWAY_WS_URL",
            },
        }

        overall = "healthy"
        if checks["store"]["status"] != "writable":
            overall = "degraded"
        if checks["llm"]["status"] != "configured":
            overall = "degraded"

        return {
            "status": overall,
            "version": __version__,
            "checks": checks,
        }

    @app.get("/api/tools")
    async def list_tools(request: Request):
        """List all available tools (including MCP tools)"""
        denied = require_admin_api(request)
        if denied:
            return denied
        # ✅ Use shared agent from global agent cache
        agent = get_gateway_agent()

        # Load MCP servers to populate tool registry
        import asyncio
        try:
            asyncio.get_event_loop()
            # If we're in an async context, load MCP servers
            await agent.ensure_mcp_loaded()
        except RuntimeError:
            # No event loop, skip MCP loading
            pass

        # Get all registered tools
        tools = agent.list_tools()
        return {
            "tools": tools,
            "mcp_tools": agent.list_mcp_tools(),
            "schemas": agent.list_tool_schema_summary(),
            "mcp_servers": agent.list_mcp_server_status(),
        }

    @app.get("/api/mcp/servers")
    async def list_mcp_servers(request: Request):
        """List all MCP servers from configuration"""
        denied = require_admin_api(request)
        if denied:
            return denied
        from fastreact.core.config import Config

        config = Config.load()

        servers = []
        for server in config.mcp.servers:
            server_info = {
                "name": server.name,
                "command": server.command,
                "args": server.args,
                "description": server.description if hasattr(server, 'description') else None,
                "isolation": server.isolation if hasattr(server, 'isolation') else "shared",
                "associated_skill": server.associated_skill if hasattr(server, 'associated_skill') else None,
            }
            servers.append(server_info)

        return {"servers": servers, "count": len(servers)}

    @app.get("/api/metrics")
    async def get_metrics(request: Request):
        """Get system metrics"""
        denied = require_admin_api(request)
        if denied:
            return denied
        global _total_events_counter

        # Calculate uptime in seconds
        uptime_seconds = int((datetime.now(timezone.utc) - _gateway_start_time).total_seconds())

        # Get memory and CPU usage (if psutil available)
        memory_usage = 0
        cpu_usage = 0

        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                memory_usage = memory_info.rss  # Resident Set Size in bytes
                cpu_usage = process.cpu_percent(interval=0.1)
            except Exception:
                pass

        return {
            "active_sessions": _session_manager.count,
            "total_events": _total_events_counter,
            "uptime": uptime_seconds,
            "memory_usage": memory_usage,
            "cpu_usage": cpu_usage,
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "version": __version__,  # Use version from __init__.py for consistency
            "active_sessions": _session_manager.count,
        }

    # ===== Admin Monitoring Endpoints =====

    @app.get("/admin/sessions")
    async def admin_list_sessions(request: Request):
        """
        Admin endpoint: List all active sessions

        Requires admin authentication via X-Admin-Key header or admin_key query param
        """
        if not verify_admin(request):
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized. Valid admin API key required."}
            )

        agent = get_gateway_agent()
        sessions = agent.sessions.list()

        return {
            "total": len(sessions),
            "sessions": sessions,
        }

    @app.get("/admin/users")
    async def admin_list_users(request: Request):
        """
        Admin endpoint: List all users with active sessions

        Requires admin authentication via X-Admin-Key header or admin_key query param
        """
        if not verify_admin(request):
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized. Valid admin API key required."}
            )

        # Aggregate sessions by user from Agent session state
        agent = get_gateway_agent()
        users = {}
        for session in agent.sessions.list():
            user_key = session.get("user_key") or "unknown"
            if user_key not in users:
                users[user_key] = {
                    "user_key": user_key,
                    "active_sessions": 0,
                    "total_sessions": 0,
                }
            users[user_key]["active_sessions"] += 1
            users[user_key]["total_sessions"] += 1

        return {
            "total_users": len(users),
            "users": list(users.values()),
        }

    @app.get("/admin/metrics")
    async def admin_metrics(request: Request):
        """
        Admin endpoint: System performance metrics

        Requires admin authentication via X-Admin-Key header or admin_key query param
        """
        if not verify_admin(request):
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized. Valid admin API key required."}
            )

        # System metrics
        cpu_usage = 0
        memory_info = {"percent": 0, "available": 0, "total": 0}

        if PSUTIL_AVAILABLE:
            try:
                cpu_usage = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                memory_info = {
                    "percent": memory.percent,
                    "available": memory.available,
                    "total": memory.total,
                }
            except Exception:
                pass

        # Gateway metrics
        active_sessions = _session_manager.count
        uptime_seconds = int((datetime.now(timezone.utc) - _gateway_start_time).total_seconds())

        return {
            "system": {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_info["percent"],
                "memory_available": memory_info["available"],
                "memory_total": memory_info["total"],
            },
            "gateway": {
                "active_sessions": active_sessions,
                "uptime": uptime_seconds,
                "total_events": _total_events_counter,
            },
        }

    @app.get("/admin/user/{user_key}")
    async def admin_get_user_info(user_key: str, request: Request):
        """
        Admin endpoint: Get user information (read-only)

        Requires admin authentication via X-Admin-Key header or admin_key query param

        NOTE: Only shows metadata, NOT user data (privacy protection)
        """
        if not verify_admin(request):
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized. Valid admin API key required."}
            )

        # Get user workspace path (if multi-tenant)
        try:
            from fastreact.core.multitenant import MultiTenantManager

            # Use default workspace path
            from pathlib import Path as LibPath
            workspace_path = LibPath.cwd() / "workspaces"
            manager = MultiTenantManager(workspace_path)

            try:
                workspace = manager.get_user_workspace(user_key)

                # Get workspace metadata (not content)
                import os
                stat = workspace.stat()

                # Calculate workspace size
                workspace_size = sum(
                    f.stat().st_size for f in workspace.rglob('*') if f.is_file()
                )

                return {
                    "user_key": user_key,
                    "workspace_path": str(workspace),
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_bytes": workspace_size,
                    "size_human": f"{workspace_size / 1024:.2f} KB" if workspace_size < 1024 * 1024 else f"{workspace_size / (1024 * 1024):.2f} MB",
                    # NOTE: Does NOT expose user data (privacy)
                }
            except ValueError as e:
                return JSONResponse(
                    status_code=404,
                    content={"error": f"User not found: {user_key}", "detail": str(e)}
                )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to get user info", "detail": str(e)}
            )

    @app.get("/admin")
    async def admin_dashboard():
        """
        Admin dashboard (HTML)

        Requires admin authentication via API key prompt
        """
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>FastReAct Nano - Admin Dashboard</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; background: #f5f5f5; padding: 20px; }
                .container { max-width: 1400px; margin: 0 auto; }
                h1 { color: #333; margin-bottom: 20px; }
                h2 { color: #555; margin-top: 30px; margin-bottom: 15px; font-size: 18px; }
                .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
                .metric { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .metric-label { color: #666; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
                .metric-value { font-size: 32px; font-weight: bold; color: #333; margin-top: 10px; }
                table { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); width: 100%; }
                th { background: #4CAF50; color: white; padding: 12px; text-align: left; font-weight: 500; }
                td { padding: 12px; border-bottom: 1px solid #eee; }
                tr:last-child td { border-bottom: none; }
                .login-form { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 400px; margin: 100px auto; }
                .login-form input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
                .login-form button { width: 100%; padding: 12px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
                .login-form button:hover { background: #45a049; }
                .error { color: #f44336; margin-top: 10px; }
                .badge { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; }
                .badge-web { background: #2196F3; color: white; }
                .badge-mobile { background: #FF9800; color: white; }
                .badge-api { background: #9C27B0; color: white; }
                .badge-default { background: #9E9E9E; color: white; }
            </style>
        </head>
        <body>
            <div id="login" class="login-form">
                <h1 style="text-align: center; margin-bottom: 20px;">Admin Login</h1>
                <input type="password" id="adminKey" placeholder="Enter Admin API Key">
                <button onclick="login()">Login</button>
                <div id="loginError" class="error"></div>
            </div>

            <div id="dashboard" class="container" style="display: none;">
                <h1>FastReAct Nano - Admin Dashboard</h1>

                <div id="metrics"></div>

                <h2>Users</h2>
                <div id="users"></div>

                <h2>Active Sessions</h2>
                <div id="sessions"></div>
            </div>

            <script>
                let ADMIN_KEY = '';

                function login() {
                    ADMIN_KEY = document.getElementById('adminKey').value;
                    loadDashboard();
                }

                async function loadDashboard() {
                    try {
                        // Test authentication with metrics endpoint
                        await loadMetrics();
                        document.getElementById('login').style.display = 'none';
                        document.getElementById('dashboard').style.display = 'block';
                        document.getElementById('loginError').textContent = '';
                    } catch (error) {
                        document.getElementById('loginError').textContent = 'Invalid admin API key';
                    }
                }

                async function loadMetrics() {
                    const res = await fetch(`/admin/metrics?admin_key=${ADMIN_KEY}`);
                    if (!res.ok) throw new Error('Unauthorized');
                    const data = await res.json();

                    document.getElementById('metrics').innerHTML = `
                        <div class="metrics">
                            <div class="metric">
                                <div class="metric-label">CPU Usage</div>
                                <div class="metric-value">${data.system.cpu_usage.toFixed(1)}%</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Memory Usage</div>
                                <div class="metric-value">${data.system.memory_usage.toFixed(1)}%</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Active Sessions</div>
                                <div class="metric-value">${data.gateway.active_sessions}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Uptime</div>
                                <div class="metric-value">${Math.floor(data.gateway.uptime / 60)} min</div>
                            </div>
                        </div>
                    `;
                }

                async function loadUsers() {
                    const res = await fetch(`/admin/users?admin_key=${ADMIN_KEY}`);
                    if (!res.ok) throw new Error('Unauthorized');
                    const data = await res.json();

                    if (data.users.length === 0) {
                        document.getElementById('users').innerHTML = '<p style="color: #666;">No active users</p>';
                        return;
                    }

                    let html = '<table><thead><tr><th>User</th><th>Active Sessions</th></tr></thead><tbody>';
                    data.users.forEach(user => {
                        const channel = user.user_key.split(':')[0];
                        const badgeClass = `badge-${channel}`;
                        html += `<tr>
                            <td><span class="badge ${badgeClass}">${user.user_key}</span></td>
                            <td>${user.active_sessions}</td>
                        </tr>`;
                    });
                    html += '</tbody></table>';

                    document.getElementById('users').innerHTML = html;
                }

                async function loadSessions() {
                    const res = await fetch(`/admin/sessions?admin_key=${ADMIN_KEY}`);
                    if (!res.ok) throw new Error('Unauthorized');
                    const data = await res.json();

                    if (data.sessions.length === 0) {
                        document.getElementById('sessions').innerHTML = '<p style="color: #666;">No active sessions</p>';
                        return;
                    }

                    let html = '<table><thead><tr><th>Session ID</th><th>User</th><th>Created At</th><th>Last Activity</th></tr></thead><tbody>';
                    data.sessions.forEach(session => {
                        const channel = session.user_key.split(':')[0];
                        const badgeClass = `badge-${channel}`;
                        html += `<tr>
                            <td style="font-family: monospace; font-size: 12px;">${session.session_id.substring(0, 8)}...</td>
                            <td><span class="badge ${badgeClass}">${session.user_key}</span></td>
                            <td>${new Date(session.created_at).toLocaleString()}</td>
                            <td>${new Date(session.last_activity).toLocaleString()}</td>
                        </tr>`;
                    });
                    html += '</tbody></table>';

                    document.getElementById('sessions').innerHTML = html;
                }

                // Load dashboard data on login
                function loadDashboard() {
                    loadMetrics().then(() => {
                        loadUsers();
                        loadSessions();
                    }).catch(() => {
                        document.getElementById('loginError').textContent = 'Invalid admin API key';
                    });
                }

                // Auto-refresh every 5 seconds
                setInterval(() => {
                    if (ADMIN_KEY) {
                        loadMetrics();
                        loadUsers();
                        loadSessions();
                    }
                }, 5000);

                // Handle Enter key on password field
                document.getElementById('adminKey').addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') login();
                });
            </script>
        </body>
        </html>
        """)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint for real-time communication

        Unified Architecture (Phase 0):
        - All sessions share a global Agent instance
        - User identification via user_key query parameter
        - Temporary user_key auto-generation if not provided
        - Workspace isolation per user (handled by Agent)

        Multi-tenant Mode (default):
        - Extract user_key from query parameters (format: ?user_key=web:user@example.com)
        - Auto-generate temporary user_key if not provided (web:temp_xxx)
        - Each user gets isolated workspace

        Single-tenant Fallback:
        - If gateway.multitenant=false in config, all users share same workspace
        - Recommended for Admin-only deployments

        Examples:
        - ws://localhost:9000/ws (auto-generates temp user_key)
        - ws://localhost:9000/ws?user_key=web:user@example.com
        - ws://localhost:9000/ws?user_key=mobile:user123
        """
        # Load configuration
        config = Config.load()

        # Check multi-tenant mode from configuration
        multitenant_enabled = config.gateway.enable_multitenant

        if not multitenant_enabled:
            logger.info("Running in single-tenant mode (all users share workspace)")
        else:
            logger.info("Running in multi-tenant mode (per-user workspace isolation)")

        # ✅ Get shared Agent from global agent cache
        shared_agent = get_gateway_agent(config)

        # ✅ Extract or generate user_key
        user_key = websocket.query_params.get("user_key")

        if multitenant_enabled:
            # Multi-tenant mode: require valid user_key
            if not user_key:
                # Auto-generate temporary user_key
                user_key = generate_temp_user_key()
                logger.debug("No user_key provided, using temporary: %s", user_key)
            else:
                # Validate user_key format
                is_valid, error = validate_user_key(user_key)
                if not is_valid:
                    await websocket.accept()
                    await websocket.send_json({
                        "type": "error",
                        "content": error,
                    })
                    await websocket.close(code=1008)  # Policy violation
                    return

            # ✅ Register temporary user if applicable
            shared_agent.register_temp_user_if_needed(user_key)
        else:
            # Single-tenant mode: use default user_key
            if not user_key:
                user_key = "web:default"

        logger.info(
            "WebSocket connection user_key=%s mode=%s",
            user_key,
            "multi-tenant" if multitenant_enabled else "single-tenant",
        )

        # ✅ Create session with shared Agent
        session = await _session_manager.connect(
            websocket,
            user_key=user_key,
            agent=shared_agent,  # ✅ Pass shared Agent
            multitenant_enabled=multitenant_enabled,
        )
        session_id = session.session_id

        # Start background queue processing task
        session._processing_task = asyncio.create_task(
            session.process_queue()
        )

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Enqueue message (control messages bypass queue limit)
                success = await session.enqueue_message(message)

                if not success:
                    await session.send({
                        "type": "warning",
                        "content": f"Queue full (max {session.max_queue_size}), please wait",
                    })

                # Handle immediate responses (ping, list_skills)
                if message.get("type") == "ping":
                    await session.send({"type": "pong"})

                elif message.get("type") == "list_skills":
                    skills = session.agent.list_skills()
                    await session.send({
                        "type": "skills",
                        "skills": skills,
                    })

        except WebSocketDisconnect:
            _session_manager.disconnect(session_id)
        except RuntimeError as exc:
            if "WebSocket is not connected" not in str(exc):
                raise
            _session_manager.disconnect(session_id)

        finally:
            # Cancel background task
            if session._processing_task:
                session._processing_task.cancel()
                try:
                    await session._processing_task
                except asyncio.CancelledError:
                    pass

    return app


def run_gateway(
    host: Optional[str] = None,
    port: Optional[int] = None,
    log_level: Optional[str] = None,
    base_workspace: Optional[Path] = None,
):
    """
    Run WebSocket gateway server

    Args:
        host: Host to bind to (default: from config or 0.0.0.0)
        port: Port to bind to (default: from config or 9000)
        log_level: Log level (default: from config or info)
        base_workspace: Base directory for user workspaces (default: from config or ./workspace)
    """
    if not FASTAPI_AVAILABLE:
        print("[ERROR] FastAPI not available")
        print("Install with: pip install fastreact-nano[gateway]")
        return

    from pathlib import Path as LibPath
    from fastreact.core.config import Config

    # Load configuration first
    config = Config.load()

    # Use config values or fallback to parameters
    host = host or config.gateway.host
    port = port or config.gateway.port
    log_level = log_level or config.gateway.log_level

    # Create workspace directory using configured path
    workspace_path = base_workspace or config.paths.gateway_workspace
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Log configuration
    logger.info(
        "Gateway configuration: multi_tenant=%s admin_only=%s host=%s port=%s workspace=%s",
        config.gateway.enable_multitenant,
        config.gateway.admin_only,
        host,
        port,
        workspace_path,
    )

    # Log MCP server configuration
    if config.mcp.servers:
        logger.info("Loaded %s MCP servers", len(config.mcp.servers))
        for server in config.mcp.servers:
            isolation = server.isolation if hasattr(server, 'isolation') else server.get("isolation", "shared")
            logger.debug("MCP server %s isolation=%s", server.name, isolation)
    else:
        logger.warning("No MCP servers configured")

    app = create_gateway_app()

    logger.info("Gateway starting on %s:%s", host, port)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
    )


if __name__ == "__main__":
    run_gateway()
