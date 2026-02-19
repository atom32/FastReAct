"""
FastReAct Nano - Feishu (Lark) Channel Adapter using Official SDK

Provides Feishu bot integration using lark-oapi SDK with WebSocket long connection.
This is the "ultimate form" - no webhook, no public network exposure needed.
"""

import asyncio
import json
import uuid
from typing import Optional, Callable
from pathlib import Path

from fastreact import Agent, EventType
from fastreact.core.config import FeishuConfig
from fastreact.core.multitenant import MultiTenantManager

try:
    from lark_oapi import Client as LarkClient
    from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
    from lark_oapi.api.im.v1.model.p2_im_message_receive_v1 import P2ImMessageReceiveV1
    from lark_oapi.core.enum import LogLevel
    from lark_oapi.event.dispatcher_handler import EventDispatcherHandlerBuilder
    from lark_oapi.ws.client import Client as WSClient
    from lark_oapi.core.model.config import Config as LarkConfig

    LARK_SDK_AVAILABLE = True
except ImportError:
    LARK_SDK_AVAILABLE = False

    # Type stubs for when SDK is not available
    LarkClient = None
    P2ImMessageReceiveV1 = None
    LogLevel = None
    EventDispatcherHandlerBuilder = None
    WSClient = None
    LarkConfig = None


class FeishuSDKAdapter:
    """
    Feishu (Lark) channel adapter using official lark-oapi SDK with WebSocket long connection.

    This is the recommended "ultimate form" of Feishu integration:
    - No webhook server needed
    - No public network exposure
    - Automatic reconnection
    - Multi-tenant user isolation

    Features:
    - WebSocket long connection for event receiving
    - Multi-tenant user isolation (feishu:user_id)
    - Card-based interaction
    - Real-time thinking updates
    """

    def __init__(
        self,
        agent: Agent,
        config: FeishuConfig,
    ):
        """
        Initialize Feishu SDK adapter

        Args:
            agent: FastReAct agent instance
            config: Feishu configuration
        """
        if not LARK_SDK_AVAILABLE:
            raise RuntimeError(
                "lark-oapi SDK is required for Feishu SDK adapter. "
                "Install with: pip install lark-oapi>=1.5.0"
            )

        if not config.app_id or not config.app_secret:
            raise ValueError(
                "FEISHU_APP_ID and FEISHU_APP_SECRET are required for SDK mode"
            )

        self.agent = agent
        self.config = config

        # Multi-tenant manager
        self._multitenant: Optional[MultiTenantManager] = None
        if config.enable_multitenant:
            # Use Feishu-specific workspace from config or paths config
            workspace = config.base_workspace or agent._config.paths.feishu_workspace_base
            self._multitenant = MultiTenantManager(workspace)

        # Build event handler with builder pattern
        self._event_handler = self._build_event_handler()

        # API client for sending messages
        self._api_client: Optional[LarkClient] = None

        # WebSocket client (initialized in start())
        self._ws_client: Optional[WSClient] = None

    def _build_event_handler(self):
        """
        Build event handler for receiving Feishu events

        Returns:
            EventDispatcherHandler instance
        """
        builder = EventDispatcherHandlerBuilder(
            encrypt_key=self.config.encrypt_key,
            verification_token=self.config.verification_token
        )

        # Register message received event handler (p2 = version 2 API)
        builder.register_p2_im_message_receive_v1(self._handle_message_event_v2)

        return builder.build()

    def _handle_message_event_v2(self, event: P2ImMessageReceiveV1) -> None:
        """
        Handle message received event from Feishu (V2 API)

        Args:
            event: Message receive event (P2ImMessageReceiveV1)
        """
        try:
            # Extract data from event
            event_data = event.event

            # Extract sender ID
            sender_id = event_data.sender.sender_id.open_id

            if not sender_id:
                print("[ERROR] No sender_id in message event")
                return

            # Extract message content
            content = event_data.message.content

            # Parse content (Feishu uses JSON in content field)
            try:
                content_obj = json.loads(content)
                text = content_obj.get("text", "")
            except json.JSONDecodeError:
                # Content is plain text
                text = content

            # Extract message ID and chat ID
            message_id = event_data.message.message_id
            chat_id = event_data.message.chat_id

            # Create event wrapper
            feishu_event = {
                "type": "message",
                "sender_id": sender_id,
                "chat_id": chat_id,
                "content": text,
                "message_id": message_id,
            }

            print(f"[FEISHU] Received message from {sender_id}: {text}")

            # Process asynchronously (don't block event loop)
            loop = asyncio.get_event_loop()
            loop.create_task(self._process_message_async(feishu_event))

        except Exception as e:
            import sys
            print(f"[ERROR] Failed to handle message event: {e}", file=sys.stderr)

    async def _process_message_async(self, event: dict):
        """
        Process message event asynchronously

        Args:
            event: Feishu event dict
        """
        try:
            sender_id = event["sender_id"]
            chat_id = event["chat_id"]
            content = event["content"]

            # Extract user_key for multi-tenant
            user_key = f"feishu:{sender_id}"

            # Send initial message
            await self._send_thinking_message(chat_id, content)

            # Process with agent (with user context)
            await self._process_agent_stream(user_key, content, chat_id)

        except Exception as e:
            import sys
            print(f"[ERROR] Failed to process message: {e}", file=sys.stderr)

    async def _send_thinking_message(
        self,
        chat_id: str,
        query: str,
    ):
        """
        Send initial "thinking" message to user

        Args:
            chat_id: Feishu chat ID
            query: User's query
        """
        message = f"[INFO] Processing your query: {query}\n\nAgent is thinking..."

        await self._send_text_message(chat_id, message)

    async def _send_text_message(
        self,
        chat_id: str,
        text: str,
    ):
        """
        Send text message to Feishu chat

        Args:
            chat_id: Feishu chat ID
            text: Message text
        """
        if not self._api_client:
            print(f"[FEISHU] Would send to {chat_id}: {text}")
            return

        try:
            request = CreateMessageRequest()
            request.body = CreateMessageRequestBody()
            request.body.receive_id_type = "chat_id"
            request.body.receive_id = chat_id
            request.body.msg_type = "text"
            request.body.content = json.dumps({"text": text})

            response = await self._api_client.im.message.acreate(request)

            if not response.success():
                print(f"[ERROR] Failed to send message: {response.code} - {response.msg}")
            else:
                print(f"[FEISHU] Message sent to {chat_id}")

        except Exception as e:
            import sys
            print(f"[ERROR] Failed to send message: {e}", file=sys.stderr)

    async def _process_agent_stream(
        self,
        user_key: str,
        query: str,
        chat_id: str,
    ):
        """
        Process query with Agent and stream results back to Feishu

        Args:
            user_key: User key for multi-tenant (e.g., "feishu:ou_xxx")
            query: User's query
            chat_id: Feishu chat ID
        """
        # Session ID with user prefix
        session_id = f"{user_key}:session-{uuid.uuid4()}"

        # Collect thinking and tool calls
        thinking_steps = []
        tool_calls = []

        try:
            # Stream agent events
            async for agent_event in self.agent.run_event_stream(
                query=query,
                session_id=session_id,
                user_key=user_key if self._multitenant else None,
            ):
                # Handle different event types
                if agent_event.type == EventType.THINK:
                    thinking_steps.append(agent_event.content)
                    # Send thinking update
                    await self._send_text_message(
                        chat_id,
                        f"[THINK] {agent_event.content[:100]}..."
                    )

                elif agent_event.type == EventType.TOOL_CALL:
                    tool_calls.append({
                        "name": agent_event.tool_name,
                        "args": agent_event.tool_args,
                    })
                    await self._send_text_message(
                        chat_id,
                        f"[TOOL] Calling {agent_event.tool_name}"
                    )

                elif agent_event.type == EventType.TOOL_RESULT:
                    result = agent_event.content
                    if len(result) > 200:
                        result = result[:200] + "..."
                    await self._send_text_message(
                        chat_id,
                        f"[RESULT] {result}"
                    )

                elif agent_event.type == EventType.SESSION_END:
                    # Send final answer
                    await self._send_text_message(
                        chat_id,
                        f"[DONE]\n\n{agent_event.content}"
                    )

                elif agent_event.type == EventType.ERROR:
                    await self._send_text_message(
                        chat_id,
                        f"[ERROR] {agent_event.content}"
                    )

        except Exception as e:
            import sys
            print(f"[ERROR] Agent processing failed: {e}", file=sys.stderr)
            await self._send_text_message(
                chat_id,
                f"[ERROR] Processing failed: {e}"
            )

    def start(self):
        """
        Start Feishu WebSocket connection (blocking)

        Runs the WebSocket client to listen for events from Feishu.
        This is a blocking call that runs forever.
        """
        # Map log level string to LogLevel enum
        log_level_map = {
            "debug": LogLevel.DEBUG,
            "info": LogLevel.INFO,
            "warn": LogLevel.WARN,
            "error": LogLevel.ERROR,
        }
        log_level = log_level_map.get(self.config.log_level.lower(), LogLevel.INFO)

        # Initialize API client
        lark_config = LarkConfig.new_config_with_app_id_and_app_secret(
            self.config.app_id,
            self.config.app_secret
        )
        self._api_client = LarkClient(config=lark_config)

        # Create WebSocket client
        self._ws_client = WSClient(
            app_id=self.config.app_id,
            app_secret=self.config.app_secret,
            event_handler=self._event_handler,
            auto_reconnect=self.config.auto_reconnect,
            log_level=log_level,
        )

        print(f"[INFO] Starting Feishu SDK adapter (WebSocket long connection)")
        print(f"[INFO] App ID: {self.config.app_id}")
        print(f"[INFO] Multi-tenant: {self.config.enable_multitenant}")
        print(f"[INFO] Auto-reconnect: {self.config.auto_reconnect}")

        # Start WebSocket client (blocking)
        self._ws_client.start()
