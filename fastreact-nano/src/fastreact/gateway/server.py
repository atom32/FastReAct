"""
WebSocket Gateway server for FastReAct Nano

Based on Moltbot's Gateway pattern with FastAPI + WebSocket.
Provides real-time bi-directional communication with channels.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from fastreact.core.bus import MessageBus, InboundMessage, OutboundMessage
from fastreact.core.react import ReActCore
from fastreact.core.tools import ToolRegistry
from fastreact.core.context import ContextManager, FileContextStore
from fastreact.providers.litellm import LiteLLMProvider
from fastreact.gateway.session import SessionManager, Session
from fastreact.utils.config import Config, Paths, get_config, get_paths


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class GatewayServer:
    """
    FastReAct WebSocket Gateway server

    Provides real-time communication between channels and the agent.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        config: Optional[Config] = None,
    ):
        """
        Initialize gateway server

        Args:
            host: Host to bind to
            port: Port to bind to
            config: Configuration object
        """
        self._host = host
        self._port = port
        self._config = config or get_config()
        self._paths = get_paths()

        # Ensure directories exist
        self._paths.ensure_directories()

        # Core components
        self._message_bus = MessageBus()
        self._llm = self._create_llm()
        self._tools = self._create_tools()
        self._react_core = self._create_react_core()
        self._context_manager = self._create_context_manager()
        self._session_manager = self._create_session_manager()

        # WebSocket connections
        self._connections: Dict[str, WebSocket] = {}

        # Running state
        self._running = False
        self._server: Optional[uvicorn.Server] = None

    def _create_llm(self) -> LiteLLMProvider:
        """Create LLM provider"""
        model = self._config.get("llm.model", "gpt-4o")
        api_base = self._config.get("llm.api_base")
        api_key = self._config.get("llm.api_key")
        temperature = self._config.get_float("llm.temperature", 0.7)
        max_tokens = self._config.get_int("llm.max_tokens", 4096)

        return LiteLLMProvider(
            model=model,
            api_base=api_base,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _create_tools(self) -> ToolRegistry:
        """Create tool registry"""
        registry = ToolRegistry()

        # Register tools from config if specified
        # For now, just create empty registry
        # Tools will be registered by plugins

        return registry

    def _create_react_core(self) -> ReActCore:
        """Create ReAct core"""
        max_iterations = self._config.get_int("agent.max_iterations", 20)
        streaming = self._config.get_bool("agent.streaming", False)

        return ReActCore(
            llm=self._llm,
            tools=self._tools,
            max_iterations=max_iterations,
            streaming=streaming,
        )

    def _create_context_manager(self) -> ContextManager:
        """Create context manager"""
        max_tokens = self._config.get_int("context.max_tokens", 8000)
        reserve_tokens = self._config.get_int("context.reserve_tokens", 2000)
        max_history = self._config.get_int("context.max_history", 50)

        store = FileContextStore(self._paths.sessions_dir)

        return ContextManager(
            store=store,
            max_tokens=max_tokens,
            reserve_tokens=reserve_tokens,
            max_history=max_history,
        )

    def _create_session_manager(self) -> SessionManager:
        """Create session manager"""
        return SessionManager(
            react_core=self._react_core,
            context_manager=self._context_manager,
            message_bus=self._message_bus,
            paths=self._paths,
        )

    async def start(self):
        """Start gateway server"""
        if self._running:
            logger.warning("[Gateway] Already running")
            return

        self._running = True
        logger.info(f"[Gateway] Starting on {self._host}:{self._port}")

        # Start cleanup task
        await self._session_manager.start_cleanup_task()

        # Start outbound message handler
        asyncio.create_task(self._handle_outbound_messages())

        # Create FastAPI app
        app = self._create_app()

        # Configure uvicorn
        config = uvicorn.Config(
            app=app,
            host=self._host,
            port=self._port,
            log_level="info",
        )
        self._server = uvicorn.Server(config)

        # Run server
        await self._server.serve()

    async def stop(self):
        """Stop gateway server"""
        if not self._running:
            return

        logger.info("[Gateway] Stopping...")
        self._running = False

        # Stop cleanup task
        await self._session_manager.stop_cleanup_task()

        # Close all WebSocket connections
        for conn_id, ws in self._connections.items():
            try:
                await ws.close()
            except Exception:
                pass
        self._connections.clear()

        # Stop server
        if self._server:
            self._server.should_exit = True
            await self._server.shutdown()

        logger.info("[Gateway] Stopped")

    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Lifespan context"""
            logger.info("[Gateway] Application startup")
            yield
            logger.info("[Gateway] Application shutdown")

        app = FastAPI(
            title="FastReAct Nano Gateway",
            description="Lightweight multi-channel ReAct agent gateway",
            version="2.0.0-alpha",
            lifespan=lifespan,
        )

        # Health check endpoint
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "ok",
                "running": self._running,
                "sessions": self._session_manager.get_stats(),
            }

        # Stats endpoint
        @app.get("/stats")
        async def get_stats():
            """Get gateway statistics"""
            return {
                "sessions": self._session_manager.get_stats(),
                "message_bus": {
                    "inbound_size": self._message_bus.inbound_size(),
                    "outbound_size": self._message_bus.outbound_size(),
                },
                "connections": len(self._connections),
            }

        # WebSocket endpoint
        @app.websocket("/ws/{channel}/{user_id}")
        async def websocket_endpoint(
            websocket: WebSocket,
            channel: str,
            user_id: str,
        ):
            """WebSocket endpoint for channels"""
            await self._handle_websocket(websocket, channel, user_id)

        return app

    async def _handle_websocket(
        self,
        websocket: WebSocket,
        channel: str,
        user_id: str,
    ):
        """Handle WebSocket connection"""
        conn_id = f"{channel}:{user_id}"

        # Accept connection
        await websocket.accept()
        self._connections[conn_id] = websocket
        logger.info(f"[WebSocket] Connected: {conn_id}")

        try:
            # Send connection confirmation
            await websocket.send_json({
                "type": "connected",
                "channel": channel,
                "user_id": user_id,
            })

            # Message loop
            while True:
                # Receive message
                data = await websocket.receive_json()

                # Process message
                await self._process_message(channel, user_id, data)

        except WebSocketDisconnect:
            logger.info(f"[WebSocket] Disconnected: {conn_id}")
        except Exception as e:
            logger.error(f"[WebSocket] Error for {conn_id}: {e}")
        finally:
            # Remove connection
            self._connections.pop(conn_id, None)

    async def _process_message(
        self,
        channel: str,
        user_id: str,
        data: Dict[str, Any],
    ):
        """Process incoming message"""
        try:
            # Extract message content
            content = data.get("content", "")
            if not content:
                return

            # Create inbound message
            inbound = InboundMessage(
                channel=channel,
                user_id=user_id,
                content=content,
                message_id=data.get("message_id"),
                metadata=data.get("metadata", {}),
            )

            # Publish to message bus
            await self._message_bus.publish_inbound(inbound)

            # Get or create session
            session = await self._session_manager.get_or_create_session(
                channel=channel,
                user_id=user_id,
            )

            # Handle message
            outbound = await session.handle_message(inbound)

            # Send response
            conn_id = f"{channel}:{user_id}"
            websocket = self._connections.get(conn_id)
            if websocket:
                await websocket.send_json(outbound.to_dict())

        except Exception as e:
            logger.error(f"[Gateway] Error processing message: {e}")

    async def _handle_outbound_messages(self):
        """Handle outbound messages from message bus"""
        while self._running:
            try:
                # Get outbound message
                outbound = await self._message_bus.consume_outbound()

                # Send to appropriate WebSocket
                conn_id = f"{outbound.channel}:{outbound.user_id}"
                websocket = self._connections.get(conn_id)

                if websocket:
                    try:
                        await websocket.send_json(outbound.to_dict())
                    except Exception as e:
                        logger.error(f"[Gateway] Error sending to {conn_id}: {e}")
                else:
                    logger.warning(f"[Gateway] No connection for {conn_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Gateway] Error in outbound handler: {e}")


# Convenience function


async def run_gateway(
    host: str = "0.0.0.0",
    port: int = 8765,
    config: Optional[Config] = None,
):
    """
    Run gateway server

    Args:
        host: Host to bind to
        port: Port to bind to
        config: Configuration object
    """
    server = GatewayServer(host=host, port=port, config=config)
    await server.start()


# CLI entry point


def main():
    """Main entry point for running gateway"""
    import argparse

    parser = argparse.ArgumentParser(description="FastReAct Nano Gateway")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to bind to (default: 8765)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file",
    )

    args = parser.parse_args()

    # Load config
    config = Config(args.config) if args.config else get_config()

    # Run server
    server = GatewayServer(host=args.host, port=args.port, config=config)

    # Run with uvicorn
    uvicorn.run(
        server._create_app(),
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
