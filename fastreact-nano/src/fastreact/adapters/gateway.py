"""
Gateway Adapter for FastReAct Nano

Provides WebSocket gateway with session management.
Install with: pip install fastreact-nano[gateway]
"""

import asyncio
import json
import os
import psutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    from fastapi import WebSocket, WebSocketDisconnect, FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

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


class Session:
    """
    Gateway Session - Transport Layer Only

    Responsibilities:
    - WebSocket connection management
    - Event sending to client
    - Delegating business logic to AgentSession

    This class is now a THIN wrapper around AgentSession.
    All business logic (history, follow-ups, state) is in AgentSession.
    """

    def __init__(
        self,
        session_id: str,
        websocket: WebSocket,
        config: Optional["Config"] = None,
        max_queue_size: int = 5,
        base_workspace: Optional[Path] = None,
        max_history: int = 50,
    ):
        self.session_id = session_id
        self.websocket = websocket
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

        # Background task reference
        self._processing_task: Optional[asyncio.Task] = None

        # NOTE: Gateway runs in single-tenant mode (no user authentication)
        # If you need multi-tenant support, implement user auth first
        self.agent = Agent(
            config=config,
            multitenant=False,  # Single-tenant mode (cannot distinguish users)
        )

        # Create AgentSession for business logic (NEW: all business logic here)
        self.agent_session = self.agent.create_session(
            session_id=session_id,
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
        self.last_activity = datetime.utcnow()
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

    async def connect(self, websocket: WebSocket) -> Session:
        """Accept connection and create session"""
        await websocket.accept()

        session_id = str(uuid.uuid4())
        session = Session(session_id, websocket)
        self._sessions[session_id] = session

        await session.send({
            "type": "connected",
            "session_id": session_id,
            "message": "Connected to FastReAct Nano Gateway",
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

# Global metrics
_gateway_start_time = datetime.utcnow()
_total_events_counter = 0


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
        version="2.0.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Next.js frontend
            "http://localhost:5173",  # Vue 3 frontend (dev)
            "http://localhost:9000",  # Gateway self
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
    async def list_sessions_api():
        """List all active sessions (REST API)"""
        sessions = []
        for session_id in _session_manager.list_all():
            session = _session_manager.get(session_id)
            if session:
                sessions.append({
                    "session_id": session.session_id,
                    "created_at": session.created_at.isoformat(),
                    "last_active": session.last_activity.isoformat(),
                    "status": "active",
                })
        return {"sessions": sessions, "count": len(sessions)}

    @app.delete("/api/sessions/{session_id}")
    async def terminate_session(session_id: str):
        """Terminate a session by ID"""
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

    @app.get("/api/config")
    async def get_config():
        """Get current configuration (hide sensitive fields)"""
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
    async def update_config(request_data: dict):
        """Update configuration"""
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
        from fastreact.core.config import Config

        config = Config.load()
        agent = Agent(config=config)

        # Get all available skills
        skill_names = agent._skills.list_available()

        skills = []
        for skill_name in skill_names:
            skill = agent._skills.get(skill_name)
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
            "global_skills_dir": str(config.paths.global_skills_dir),
            "total_count": len(skills)
        }

    @app.get("/api/status")
    async def get_status():
        """Get system status including SKILL and MCP information"""
        from fastreact.core.config import Config
        import asyncio

        config = Config.load()
        agent = Agent(config=config)

        # Load MCP servers to get status
        mcp_loaded = False
        mcp_servers_info = []

        try:
            asyncio.get_event_loop()
            await agent._load_mcp_servers()
            mcp_loaded = True

            # Get MCP server status
            if agent._mcp_manager:
                for server_name in agent._mcp_manager._servers.keys():
                    is_alive = agent._mcp_manager.is_server_alive(server_name)

                    # Get isolation mode from config
                    isolation = "unknown"
                    for server_config in config.mcp.servers:
                        if server_config.name == server_name:
                            isolation = server_config.isolation if hasattr(server_config, 'isolation') else server_config.get("isolation", "shared")
                            break

                    mcp_servers_info.append({
                        "name": server_name,
                        "status": "running" if is_alive else "stopped",
                        "isolation": isolation
                    })
        except RuntimeError:
            pass

        # Get skills
        skill_names = agent._skills.list_available()

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
                    "enabled": False,
                    "mode": "single-tenant (Gateway)"
                }
            }
        }

    @app.get("/api/tools")
    async def list_tools():
        """List all available tools (including MCP tools)"""
        # Create a temporary agent to discover tools
        from fastreact.core.config import Config

        config = Config.load()
        agent = Agent(config=config)

        # Load MCP servers to populate tool registry
        import asyncio
        try:
            asyncio.get_event_loop()
            # If we're in an async context, load MCP servers
            await agent._load_mcp_servers()
        except RuntimeError:
            # No event loop, skip MCP loading
            pass

        # Get all registered tools
        tools = agent._tools.list_all()

        return {
            "tools": tools,
            "mcp_tools": agent._mcp_manager.list_mcp_tools() if agent._mcp_manager else [],
        }

    @app.get("/api/mcp/servers")
    async def list_mcp_servers():
        """List all MCP servers from configuration"""
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
    async def get_metrics():
        """Get system metrics"""
        global _total_events_counter

        # Calculate uptime in seconds
        uptime_seconds = int((datetime.utcnow() - _gateway_start_time).total_seconds())

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
            "version": "2.0.0",
            "active_sessions": _session_manager.count,
        }

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time communication"""
        session = await _session_manager.connect(websocket)
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
    host: str = "0.0.0.0",
    port: int = 9000,
    log_level: str = "info",
    base_workspace: Optional[Path] = None,
):
    """
    Run WebSocket gateway server

    Args:
        host: Host to bind to
        port: Port to bind to
        log_level: Log level
        base_workspace: Base directory for user workspaces (default: ./workspace)
    """
    if not FASTAPI_AVAILABLE:
        print("[ERROR] FastAPI not available")
        print("Install with: pip install fastreact-nano[gateway]")
        return

    from pathlib import Path as LibPath
    from fastreact.core.config import Config

    # Load configuration first
    config = Config.load()

    # Create workspace directory using configured path
    workspace_path = base_workspace or config.paths.gateway_workspace
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Log MCP server configuration
    if config.mcp.servers:
        print(f"[INFO] Loaded {len(config.mcp.servers)} MCP servers:")
        for server in config.mcp.servers:
            isolation = server.isolation if hasattr(server, 'isolation') else server.get("isolation", "shared")
            print(f"  - {server.name} (isolation: {isolation})")
    else:
        print("[WARNING] No MCP servers configured")

    app = create_gateway_app()

    print(f"[INFO] Gateway starting on {host}:{port}")
    print(f"[INFO] Workspace: {workspace_path}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
    )


if __name__ == "__main__":
    run_gateway()
