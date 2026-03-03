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
    from lark_oapi.api.im.v1.model.p2_im_message_message_read_v1 import P2ImMessageMessageReadV1
    from lark_oapi.core.enum import LogLevel
    from lark_oapi.event.dispatcher_handler import EventDispatcherHandlerBuilder
    from lark_oapi.ws.client import Client as WSClient
    from lark_oapi.core.model.config import Config as LarkConfig
    import httpx

    LARK_SDK_AVAILABLE = True
except ImportError:
    LARK_SDK_AVAILABLE = False

    # Type stubs for when SDK is not available
    LarkClient = None
    P2ImMessageReceiveV1 = None
    P2ImMessageMessageReadV1 = None
    LogLevel = None
    EventDispatcherHandlerBuilder = None
    WSClient = None
    LarkConfig = None
    httpx = None


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

        # HTTP client for direct API calls
        self._http_client: Optional[httpx.AsyncClient] = None

        # Access token cache
        self._access_token: Optional[str] = None
        self._token_expire_time: Optional[float] = None

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

        # Register message read event handler (to suppress warnings)
        builder.register_p2_im_message_message_read_v1(self._handle_message_read_event_v2)

        return builder.build()

    def _handle_message_read_event_v2(self, event: P2ImMessageMessageReadV1) -> None:
        """
        Handle message read event from Feishu (V2 API)

        This is a no-op handler to suppress "processor not found" warnings.

        Args:
            event: Message read event (P2ImMessageMessageReadV1)
        """
        # Silently ignore message read events
        pass

    async def _get_access_token(self) -> str:
        """
        Get tenant access token for API calls

        Returns:
            Access token string
        """
        import time

        # Check if token is still valid
        if self._access_token and self._token_expire_time:
            if time.time() < self._token_expire_time:
                return self._access_token

        # Fetch new token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.config.app_id,
            "app_secret": self.config.app_secret
        }

        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=30.0)

        response = await self._http_client.post(url, json=payload)
        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"Failed to get access token: {data.get('msg')}")

        self._access_token = data.get("tenant_access_token")
        # Token expires in 2 hours, use 1.5 hours to be safe
        self._token_expire_time = time.time() + 5400

        return self._access_token

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
        message = f"收到你的消息：「{query}」\n\n正在思考..."

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
        try:
            # Get access token
            access_token = await self._get_access_token()

            # Send message via HTTP API
            url = "https://open.feishu.cn/open-apis/im/v1/messages"

            # Build content - must be a JSON string
            content_json = json.dumps({"text": text})

            # Payload
            payload = {
                "receive_id": chat_id,
                "msg_type": "text",
                "content": content_json
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            params = {
                "receive_id_type": "chat_id"
            }

            if not self._http_client:
                self._http_client = httpx.AsyncClient(timeout=30.0)

            # Send with receive_id_type as query parameter
            response = await self._http_client.post(
                url,
                headers=headers,
                params=params,
                json=payload
            )
            data = response.json()

            if data.get("code") != 0:
                print(f"[ERROR] Failed to send message: {data.get('msg')}")

        except Exception as e:
            import sys
            print(f"[ERROR] Failed to send message: {e}", file=sys.stderr)

    def _format_execution_summary(self, skills: list, tool_calls: list) -> str:
        """
        Format execution summary for user

        Args:
            skills: List of selected skills
            tool_calls: List of tool calls made

        Returns:
            Formatted summary string
        """
        lines = []

        # Skills section
        if skills and skills != ["None"]:
            lines.append("📚 使用技能:")
            for skill in skills:
                lines.append(f"  • {skill}")

        # Tools section
        if tool_calls:
            lines.append("\n🔧 调用工具:")

            # Group by MCP vs builtin
            mcp_tools = []
            builtin_tools = []

            for tool in tool_calls:
                tool_name = tool["name"]
                # MCP tools have "_" prefix with server name (e.g., "graphrag_search_graph")
                # Builtin tools are simple names (e.g., "read_file", "exec")
                if "_" in tool_name and tool_name.split("_")[0] in ["graphrag", "filesystem", "fetch", "rss"]:
                    mcp_tools.append(tool)
                else:
                    builtin_tools.append(tool)

            # Builtin tools
            if builtin_tools:
                lines.append("  系统工具:")
                for tool in builtin_tools:
                    tool_name = tool["name"]
                    # Simplify tool name
                    if tool_name == "read_file":
                        tool_name = "📄 读取文件"
                    elif tool_name == "write_file":
                        tool_name = "✏️ 写入文件"
                    elif tool_name == "edit_file":
                        tool_name = "🔄 编辑文件"
                    elif tool_name == "exec":
                        tool_name = "⚡ 执行命令"

                    args = tool["args"]
                    # Format args concisely
                    if tool_name == "⚡ 执行命令":
                        cmd = args.get("command", "unknown")[:50]
                        lines.append(f"    {tool_name}: {cmd}...")
                    elif tool_name == "📄 读取文件":
                        file_path = args.get("path", "unknown")[:40]
                        lines.append(f"    {tool_name}: {file_path}")
                    else:
                        lines.append(f"    {tool_name}")

            # MCP tools
            if mcp_tools:
                lines.append("  MCP 工具:")
                for tool in mcp_tools:
                    tool_name = tool["name"]
                    # Extract MCP server name and tool name
                    if ":" in tool_name:
                        server, tool_func = tool_name.split(":", 1)
                        lines.append(f"    [{server}] {tool_func}")

        return "\n".join(lines) if lines else ""

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
        selected_skills_list = [None]  # Use list to allow modification in nested scope

        print(f"[INFO] Starting agent processing for user: {user_key}")
        print(f"[INFO] Query: {query}")
        print(f"[INFO] Session ID: {session_id}")

        try:
            # Check MCP manager status before processing
            print(f"[DEBUG] MCP Manager status: {type(self.agent._mcp_manager)}")
            if self.agent._mcp_manager:
                servers = self.agent._mcp_manager.list_servers()
                print(f"[DEBUG] MCP Servers: {servers}")
                mcp_tools = self.agent._mcp_manager.list_mcp_tools()
                print(f"[DEBUG] MCP Tools: {mcp_tools}")
            else:
                print(f"[DEBUG] MCP Manager is None (will load on first run)")

            # Check total tool count
            all_tools = self.agent._tools.list_all()
            print(f"[DEBUG] Total tools available: {len(all_tools)}")
            print(f"[DEBUG] Tool names: {all_tools[:10]}")

            # Stream agent events
            async for agent_event in self.agent.run_event_stream(
                query=query,
                session_id=session_id,
                user_key=user_key if self._multitenant else None,
            ):
                # Handle different event types
                if agent_event.type == EventType.SESSION_START:
                    print(f"[INFO] Session started")
                    selected_skills_list[0] = agent_event.metadata.get("skills", [])
                    if selected_skills_list[0]:
                        print(f"[INFO] Selected skills: {selected_skills_list[0]}")

                elif agent_event.type == EventType.THINK:
                    thinking_steps.append(agent_event.content)
                    # Log to console
                    print(f"[THINK] {agent_event.content[:100]}...")

                    # Send thinking update (truncated for readability)
                    await self._send_text_message(
                        chat_id,
                        f"💭 {agent_event.content[:100]}..."
                    )

                elif agent_event.type == EventType.TOOL_CALL:
                    tool_calls.append({
                        "name": agent_event.tool_name,
                        "args": agent_event.tool_args,
                    })
                    # Log to console
                    print(f"[TOOL] Calling {agent_event.tool_name}")
                    print(f"[TOOL] Args: {str(agent_event.tool_args)[:100]}...")

                    await self._send_text_message(
                        chat_id,
                        f"🔧 正在调用工具: {agent_event.tool_name}"
                    )

                elif agent_event.type == EventType.TOOL_RESULT:
                    result = agent_event.content
                    # Log to console
                    print(f"[RESULT] {result[:100]}...")

                    if len(result) > 200:
                        result = result[:200] + "..."
                    await self._send_text_message(
                        chat_id,
                        f"📊 工具结果: {result}"
                    )

                elif agent_event.type == EventType.SESSION_END:
                    # Log final answer to console
                    print(f"[FINAL ANSWER] {agent_event.content}")
                    print(f"[INFO] Agent processing completed")

                    # Generate execution summary
                    selected_skills = selected_skills_list[0] or []
                    summary = self._format_execution_summary(selected_skills, tool_calls)
                    if summary:
                        print(f"[INFO] Execution Summary:\n{summary}")

                    # Send message with execution summary
                    if summary:
                        message = f"✅ **执行完成**\n\n{summary}\n\n---\n\n**回答:**\n\n{agent_event.content}"
                    else:
                        message = agent_event.content

                    # Send final answer to Feishu
                    await self._send_text_message(
                        chat_id,
                        message
                    )

                elif agent_event.type == EventType.ERROR:
                    print(f"[ERROR] {agent_event.content}")
                    await self._send_text_message(
                        chat_id,
                        f"❌ 错误: {agent_event.content}"
                    )

        except Exception as e:
            import sys
            print(f"[ERROR] Agent processing failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            await self._send_text_message(
                chat_id,
                f"❌ 处理失败: {e}"
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
            "warn": LogLevel.WARNING,
            "warning": LogLevel.WARNING,
            "error": LogLevel.ERROR,
        }
        log_level = log_level_map.get(self.config.log_level.lower(), LogLevel.INFO)

        # Initialize HTTP client
        self._http_client = httpx.AsyncClient(timeout=30.0)

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

        # Log MCP configuration
        if self.agent._mcp_manager:
            print(f"[INFO] MCP Manager initialized")
        else:
            print(f"[INFO] MCP Manager: Will load on first request (lazy initialization)")

        # Log Skills configuration
        if hasattr(self.agent, '_skills'):
            skills = self.agent._skills.list_skills()
            print(f"[INFO] Loaded {len(skills)} skills")
            if skills:
                # skills is a list, not a dict
                skill_names = list(skills) if isinstance(skills, dict) else skills[:5]
                print(f"[INFO] Available skills: {', '.join(skill_names)}")

        # Start WebSocket client (blocking)
        self._ws_client.start()
