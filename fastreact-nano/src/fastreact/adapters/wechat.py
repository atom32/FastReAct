"""
WeChat Work adapter for FastReAct Nano

Supports WeChat Work (企业微信) webhook integration for enterprise deployments.

This adapter enables FastReAct agents to interact with users through WeChat Work,
providing multi-tenant user isolation and real-time message processing.

Configuration:
    Add to config.json or .env:
    {
      "wechat_token": "your_token",
      "encoding_aes_key": "your_aes_key",  # Optional
      "corp_id": "your_corp_id",
      "base_workspace": "/var/fastreact/tenants/wechat"
    }

Dependencies:
    pip install werobot werkzeug

Usage:
    python3 -m fastreact.adapters.wechat

Author: FastReAct Team
Version: 1.0.0
"""

import asyncio
import logging
import uuid
from typing import Optional, Any

from fastreact.adapters.base import BaseAdapter
from fastreact.core.multitenant import MultiTenantManager, UserContext

try:
    from werobot import WeRoBot
    from werobot.contrib.werkzeug import make_view
    WECHAT_AVAILABLE = True
except ImportError:
    WECHAT_AVAILABLE = False

logger = logging.getLogger(__name__)


class WeChatWorkAdapter(BaseAdapter):
    """
    WeChat Work (企业微信) adapter for FastReAct Nano

    Supports:
    - Webhook message reception
    - Multi-tenant user isolation
    - Text message handling
    - Event handling (subscribe, unsubscribe, etc.)

    Architecture:
        WeChat Server → Webhook → WeRoBot → WeChatWorkAdapter → Agent → Response
    """

    name = "wechat"

    def __init__(self, config: Any):
        """
        Initialize WeChat Work adapter

        Args:
            config: Configuration object or dict containing:
                - wechat_token: WeChat verification token
                - encoding_aes_key: Optional AES key for message encryption
                - corp_id: WeChat Work corporation ID
                - base_workspace: Base path for user workspaces
                - host: Server host (default: 0.0.0.0)
                - port: Server port (default: 5000)
        """
        if not WECHAT_AVAILABLE:
            raise ImportError(
                "WeChat SDK not installed. "
                "Install with: pip install werobot werkzeug"
            )

        super().__init__(config)

        # WeChat Work configuration
        self.token = config.get("wechat_token") or config.get("WECHAT_TOKEN")
        self.encoding_aes_key = (
            config.get("encoding_aes_key") or
            config.get("WECHAT_ENCODING_AES_KEY")
        )
        self.corp_id = config.get("corp_id") or config.get("WECHAT_CORP_ID")

        if not self.token:
            raise ValueError("wechat_token is required")

        # Multi-tenant support
        base_workspace = config.get(
            "base_workspace",
            "/var/fastreact/tenants/wechat"
        )
        self.multitenant = MultiTenantManager(base_workspace)

        # Agent will be created per user context
        self._agents: dict[str, Any] = {}
        self._agent_config = config

        # WeChat robot
        if self.encoding_aes_key:
            self.robot = WeRoBot(
                token=self.token,
                encoding_aes_key=self.encoding_aes_key
            )
        else:
            self.robot = WeRoBot(token=self.token)

        # Server config
        self.host = config.get("host", "0.0.0.0")
        self.port = config.get("port", 5000)

        # Message handlers
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup WeChat message handlers"""
        from werobot.messages import texts, events

        @self.robot.handler
        async def handle_text_message(message: texts.TextMessage):
            """Handle text messages from WeChat"""
            user_id = message.source  # WeChat User ID
            content = message.content

            logger.info(f"[WeChat] Received message from {user_id}: {content[:50]}...")

            # Create user key for multi-tenant
            user_key = f"wechat:{user_id}"

            try:
                # Get or create agent for this user
                agent = await self._get_agent_for_user(user_key)

                # Create session ID
                session_id = f"{user_key}:session-{uuid.uuid4()}"

                # Process with Agent and collect response
                response_text = ""
                async for event in agent.run_event_stream(
                    query=content,
                    session_id=session_id,
                    user_key=user_key,
                ):
                    # Collect final response
                    if event.type == "SESSION_END":
                        response_text = event.content

                return response_text or "I'm processing your request."

            except Exception as e:
                logger.error(f"[WeChat] Error processing message: {e}")
                return f"Sorry, an error occurred: {str(e)}"

        @self.robot.handler
        async def handle_event(message: events.Event):
            """Handle WeChat events"""
            event_type = message.type

            if event_type == "subscribe_event":
                return (
                    "欢迎使用FastReAct智能助手！\n\n"
                    "I'm an AI assistant powered by FastReAct. "
                    "Send me any message and I'll do my best to help!"
                )
            elif event_type == "unsubscribe_event":
                logger.info(f"[WeChat] User {message.source} unsubscribed")
                return "SUCCESS"
            else:
                return "SUCCESS"

    async def _get_agent_for_user(self, user_key: str):
        """Get or create agent for a specific user"""
        # Check if we already have an agent for this user
        if user_key in self._agents:
            return self._agents[user_key]

        # Import Agent here to avoid circular imports
        from fastreact import Agent

        # Get user context
        user_context = self.multitenant.get_user_context(user_key)

        # Create new agent for this user
        agent = Agent(
            config=self._agent_config,
            multitenant=True,
            base_workspace=self.multitenant._base_workspace,
        )

        # Cache the agent
        self._agents[user_key] = agent

        return agent

    async def start(self):
        """Start WeChat adapter server"""
        if self._running:
            logger.warning("[WeChat] Adapter already running")
            return

        self._running = True
        logger.info(f"[WeChat] Starting adapter on {self.host}:{self.port}")

        # Create WSGI application
        from werkzeug.serving import run_simple
        from threading import Thread

        # Run in a separate thread to avoid blocking
        def run_server():
            app = make_view(self.robot)
            run_simple(self.host, self.port, app, threaded=True)

        server_thread = Thread(target=run_server, daemon=True)
        server_thread.start()

        logger.info(f"[WeChat] Adapter started and listening")

        # Keep the adapter running
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("[WeChat] Adapter stopped")
            self._running = False

    async def stop(self):
        """Stop WeChat adapter"""
        logger.info("[WeChat] Stopping adapter")
        self._running = False

        # Clear agent cache
        self._agents.clear()


class WeChatCLIAdapter(BaseAdapter):
    """
    Simplified WeChat adapter for CLI/testing

    This is a lightweight version for development and testing
    without the full webhook server setup.
    """

    name = "wechat_cli"

    def __init__(self, config: Any):
        """
        Initialize WeChat CLI adapter

        Args:
            config: Configuration object
        """
        super().__init__(config)

        self.multitenant = MultiTenantManager(
            config.get("base_workspace", "/tmp/wechat_test")
        )

        from fastreact import Agent
        self._agent_template = Agent(
            config=config,
            multitenant=True,
            base_workspace=self.multitenant._base_workspace,
        )

    async def handle_message(self, user_id: str, content: str) -> str:
        """
        Handle a message from a WeChat user

        Args:
            user_id: WeChat user ID
            content: Message content

        Returns:
            Agent response
        """
        user_key = f"wechat:{user_id}"
        session_id = f"{user_key}:session-{uuid.uuid4()}"

        response_text = ""
        async for event in self._agent_template.run_event_stream(
            query=content,
            session_id=session_id,
            user_key=user_key,
        ):
            if event.type == "SESSION_END":
                response_text = event.content

        return response_text

    async def start(self):
        """Start CLI adapter (no-op)"""
        logger.info("[WeChat CLI] Adapter ready")
        self._running = True

    async def stop(self):
        """Stop CLI adapter"""
        logger.info("[WeChat CLI] Adapter stopped")
        self._running = False


def main():
    """Main entry point for running WeChat adapter"""
    import sys
    from fastreact.core.config import Config

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
    )

    # Load configuration
    config = Config.load()

    # WeChat-specific config from config dict
    wechat_config = {
        "wechat_token": config.__dict__.get("wechat_token") or
                        config.__dict__.get("WECHAT_TOKEN"),
        "encoding_aes_key": config.__dict__.get("encoding_aes_key") or
                            config.__dict__.get("WECHAT_ENCODING_AES_KEY"),
        "corp_id": config.__dict__.get("corp_id") or
                  config.__dict__.get("WECHAT_CORP_ID"),
        "base_workspace": config.__dict__.get("base_workspace",
                                                "/var/fastreact/tenants/wechat"),
        "host": config.__dict__.get("host", "0.0.0.0"),
        "port": config.__dict__.get("port", 5000),
    }

    # Create and start adapter
    adapter = WeChatWorkAdapter(wechat_config)

    try:
        asyncio.run(adapter.start())
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        asyncio.run(adapter.stop())
        sys.exit(0)


if __name__ == "__main__":
    main()
