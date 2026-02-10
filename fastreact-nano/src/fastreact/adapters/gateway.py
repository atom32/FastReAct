"""
Gateway Adapter for FastReAct Nano

Provides WebSocket gateway with session management.
Install with: pip install fastreact-nano[gateway]
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Optional

try:
    from fastapi import WebSocket, WebSocketDisconnect, FastAPI
    from fastapi.responses import HTMLResponse
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

try:
    import websockets

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from fastreact import Agent, Config


class Session:
    """Gateway session"""

    def __init__(
        self,
        session_id: str,
        websocket: WebSocket,
    ):
        self.session_id = session_id
        self.websocket = websocket
        self.agent = Agent()
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

    async def send(self, message: dict):
        """Send message to client"""
        try:
            await self.websocket.send_json(message)
        except Exception:
            pass

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()


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

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time communication"""
        session = await _session_manager.connect(websocket)
        session_id = session.session_id

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle different message types
                if message.get("type") == "query":
                    # Update activity
                    session.update_activity()

                    # Send user message
                    await session.send({
                        "type": "user",
                        "content": message.get("content", ""),
                    })

                    # Run agent
                    try:
                        response = await session.agent.run(
                            message.get("content", ""),
                            skills=message.get("skills"),
                        )

                        # Send agent response
                        await session.send({
                            "type": "agent",
                            "content": response,
                        })

                    except Exception as e:
                        await session.send({
                            "type": "error",
                            "content": str(e),
                        })

                elif message.get("type") == "ping":
                    await session.send({"type": "pong"})

                elif message.get("type") == "list_skills":
                    skills = session.agent.list_skills()
                    await session.send({
                        "type": "skills",
                        "skills": skills,
                    })

        except WebSocketDisconnect:
            _session_manager.disconnect(session_id)


def run_gateway(
    host: str = "0.0.0.0",
    port: int = 9000,
    log_level: str = "info",
):
    """
    Run WebSocket gateway server

    Args:
        host: Host to bind to
        port: Port to bind to
        log_level: Log level
    """
    if not FASTAPI_AVAILABLE:
        print("Error: FastAPI not available")
        print("Install with: pip install fastreact-nano[gateway]")
        return

    app = create_gateway_app()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
    )


if __name__ == "__main__":
    run_gateway()
