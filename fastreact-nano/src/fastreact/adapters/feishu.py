"""
FastReAct Nano - Feishu (Lark) Channel Adapter

Provides Feishu bot integration with multi-tenant support.
"""

import asyncio
import hashlib
import hmac
import json
import time
import uuid
from typing import Optional
from pathlib import Path

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import JSONResponse
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from fastreact import Agent
from fastreact.core.config import FeishuConfig
from fastreact.core.multitenant import MultiTenantManager


class FeishuEvent:
    """Feishu event wrapper"""

    def __init__(
        self,
        event_type: str,
        sender_id: str,
        content: str,
        message_id: str = None,
        timestamp: int = None,
    ):
        self.type = event_type
        self.sender_id = sender_id
        self.content = content
        self.message_id = message_id or str(uuid.uuid4())
        self.timestamp = timestamp or 0


class FeishuChannel:
    """
    Feishu (Lark) channel adapter with multi-tenant support.

    Features:
    - Webhook event handling
    - Multi-tenant user isolation
    - Card-based interaction
    - Real-time thinking updates
    """

    def __init__(
        self,
        agent: Agent,
        config: FeishuConfig,
    ):
        """
        Initialize Feishu channel

        Args:
            agent: FastReAct agent instance
            config: Feishu configuration
        """
        if not FASTAPI_AVAILABLE:
            raise RuntimeError(
                "FastAPI is required for Feishu channel. "
                "Install with: pip install fastapi uvicorn"
            )

        self.agent = agent
        self.config = config

        # Initialize FastAPI app
        self.app = FastAPI(title="FastReAct Feishu Bot")

        # Multi-tenant manager
        self._multitenant: Optional[MultiTenantManager] = None
        if config.enable_multitenant:
            workspace = config.base_workspace or Path.cwd() / "workspace"
            self._multitenant = MultiTenantManager(workspace)

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup webhook routes"""

        @self.app.get("/")
        async def root():
            """Health check endpoint"""
            return {
                "service": "FastReAct Feishu Bot",
                "status": "running",
                "multi_tenant": self.config.enable_multitenant,
            }

        @self.app.post(self.config.webhook_path)
        async def handle_webhook(request: Request):
            """
            Handle Feishu webhook events

            Feishu sends POST requests with event data.
            We need to verify signature and process events asynchronously.
            """
            try:
                # SECURITY: Get raw body FIRST for signature verification
                body_bytes = await request.body()

                # Store raw body in request state for signature verification
                request.state.raw_body = body_bytes

                # Parse JSON
                body = json.loads(body_bytes.decode("utf-8"))

                # Verify signature (raises HTTPException if invalid)
                self._verify_signature(request, body)

                # Handle different event types
                event_type = body.get("type", "")

                if event_type == "url_verification":
                    # URL verification challenge
                    return self._handle_url_verification(body)

                elif event_type == "event_callback":
                    # Actual event
                    event_data = body.get("event", {})

                    # Process asynchronously (don't block webhook)
                    asyncio.create_task(self._process_event(event_data))

                    # Return immediately
                    return {"code": 0, "msg": "success"}

                else:
                    return {"code": 1, "msg": f"Unknown event type: {event_type}"}

            except HTTPException:
                # Re-raise HTTP exceptions (signature validation failures)
                raise
            except Exception as e:
                import sys
                print(f"[ERROR] Failed to handle webhook: {e}", file=sys.stderr)
                return {"code": 1, "msg": str(e)}

    def _verify_signature(self, request: Request, body: dict) -> bool:
        """
        Verify Feishu webhook signature using HMAC-SHA256

        Feishu signature verification algorithm:
        1. Get timestamp, nonce, and signature from headers
        2. Build sign string: timestamp + nonce + encrypt_key + body_bytes
        3. Calculate HMAC-SHA256 hash
        4. Compare with provided signature

        Args:
            request: FastAPI request
            body: Parsed request body

        Returns:
            True if signature is valid

        Raises:
            HTTPException: If signature verification fails
        """
        # If no encrypt_key configured, reject all requests (secure by default)
        if not self.config.encrypt_key:
            raise HTTPException(
                status_code=401,
                detail="Feishu encrypt_key not configured"
            )

        # Get signature headers
        timestamp = request.headers.get("X-Lark-Request-Timestamp", "")
        nonce = request.headers.get("X-Lark-Request-Nonce", "")
        signature = request.headers.get("X-Lark-Signature", "")

        if not timestamp or not nonce or not signature:
            raise HTTPException(
                status_code=401,
                detail="Missing signature headers"
            )

        # SECURITY: Check timestamp to prevent replay attacks
        # Reject requests older than 1 hour
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - request_time) > 3600:
                raise HTTPException(
                    status_code=401,
                    detail=f"Request timestamp too old: {timestamp}"
                )
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid timestamp format: {timestamp}"
            )

        # Rebuild the sign string
        # Note: We need the raw body bytes, not the parsed dict
        # This is handled in the webhook handler by passing raw_bytes

        # For now, extract from request state (set in webhook handler)
        raw_body = getattr(request.state, "raw_body", b"")
        if not raw_body:
            raise HTTPException(
                status_code=401,
                detail="Cannot access request body for signature verification"
            )

        # Build sign string: timestamp + nonce + encrypt_key + body
        sign_string = timestamp + nonce + self.config.encrypt_key
        sign_string += raw_body.decode("utf-8", errors="replace")

        # Calculate HMAC-SHA256
        expected_signature = hmac.new(
            self.config.encrypt_key.encode("utf-8"),
            sign_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(expected_signature, signature):
            raise HTTPException(
                status_code=401,
                detail="Invalid signature"
            )

        return True

    def _handle_url_verification(self, body: dict) -> dict:
        """
        Handle Feishu URL verification challenge

        Args:
            body: Request body with challenge

        Returns:
            Challenge response
        """
        challenge = body.get("challenge", "")
        return {
            "code": 0,
            "challenge": challenge,
        }

    async def _process_event(self, event_data: dict):
        """
        Process Feishu event

        Args:
            event_data: Event data from Feishu
        """
        try:
            event_type = event_data.get("type", "")

            if event_type == "message":
                await self._handle_message(event_data)

        except Exception as e:
            import sys
            print(f"[ERROR] Failed to process event: {e}", file=sys.stderr)

    async def _handle_message(self, event_data: dict):
        """
        Handle message event with multi-tenant support

        Args:
            event_data: Message event data
        """
        # Extract sender ID
        sender_id = event_data.get("sender", {}).get("sender_id", {}).get("open_id", "")

        if not sender_id:
            print("[ERROR] No sender_id in message event")
            return

        # Extract message content
        content = event_data.get("message", {}).get("content", "")

        # Parse content (Feishu uses JSON in content field)
        try:
            content_obj = json.loads(content)
            text = content_obj.get("text", "")
        except json.JSONDecodeError:
            # Content is plain text
            text = content

        # Create Feishu event
        event = FeishuEvent(
            event_type="message",
            sender_id=sender_id,
            content=text,
            message_id=event_data.get("message", {}).get("message_id", ""),
            timestamp=event_data.get("timestamp", 0),
        )

        # Send thinking card
        card_id = await self._send_thinking_card(sender_id, text)

        # Process with agent (with user context)
        await self._process_agent_stream(event, card_id)

    async def _send_thinking_card(
        self,
        user_id: str,
        query: str,
    ) -> str:
        """
        Send initial "thinking" card to user

        Args:
            user_id: Feishu user ID
            query: User's query

        Returns:
            Card ID for updating
        """
        card_id = str(uuid.uuid4())

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "[INFO] Processing...",
                    },
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**Query**: {query}\n\n[INFO] Agent is thinking...",
                        }
                    }
                ]
            }
        }

        # Send card via Feishu API
        # TODO: Implement actual Feishu message sending
        # await self._send_feishu_message(user_id, card)

        print(f"[FEISHU] Would send thinking card to {user_id}")
        print(f"[CARD] {json.dumps(card, ensure_ascii=False)}")

        return card_id

    async def _process_agent_stream(
        self,
        event: FeishuEvent,
        card_id: str,
    ):
        """
        Process query with Agent and stream results back to Feishu

        Args:
            event: Feishu event
            card_id: Card ID to update
        """
        # Extract user_key for multi-tenant
        user_key = f"feishu:{event.sender_id}"

        # Session ID with user prefix
        session_id = f"{user_key}:session-{uuid.uuid4()}"

        # Collect events for final card
        events_collected = []

        try:
            # Stream agent events
            async for agent_event in self.agent.run_event_stream(
                query=event.content,
                session_id=session_id,
                user_key=user_key if self._multitenant else None,
            ):
                events_collected.append(agent_event)

                # Update card in real-time
                await self._update_card(event.sender_id, card_id, agent_event)

        except Exception as e:
            import sys
            print(f"[ERROR] Agent processing failed: {e}", file=sys.stderr)

            # Send error card
            await self._send_error_card(event.sender_id, str(e))

    async def _update_card(
        self,
        user_id: str,
        card_id: str,
        agent_event,
    ):
        """
        Update Feishu card with agent event

        Args:
            user_id: Feishu user ID
            card_id: Card ID to update
            agent_event: Agent event
        """
        from fastreact.core.events import EventType

        # Build card content based on event type
        if agent_event.type == EventType.THINK:
            title = "[THINK] Agent is thinking"
            content = f"**Thinking**:\n{agent_event.content}"

        elif agent_event.type == EventType.TOOL_CALL:
            title = "[TOOL] Calling tool"
            content = f"**Tool**: {agent_event.tool_name}\n**Args**: {json.dumps(agent_event.tool_args, ensure_ascii=False)}"

        elif agent_event.type == EventType.TOOL_RESULT:
            title = "[RESULT] Tool completed"
            # Truncate result if too long
            result = agent_event.content
            if len(result) > 500:
                result = result[:500] + "\n... (truncated)"
            content = f"**Result**:\n```\n{result}\n```"

        elif agent_event.type == EventType.SESSION_END:
            title = "[DONE] Completed"
            content = f"**Answer**:\n{agent_event.content}"

        elif agent_event.type == EventType.ERROR:
            title = "[ERROR] Error occurred"
            content = f"**Error**:\n{agent_event.content}"

        else:
            title = "[INFO] Event"
            content = str(agent_event.content)

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title,
                    },
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": content,
                        }
                    }
                ]
            }
        }

        # Send card update via Feishu API
        # TODO: Implement actual Feishu card update
        print(f"[FEISHU] Would update card {card_id} for {user_id}")
        print(f"[CARD] {json.dumps(card, ensure_ascii=False)}")

    async def _send_error_card(
        self,
        user_id: str,
        error_message: str,
    ):
        """
        Send error card to user

        Args:
            user_id: Feishu user ID
            error_message: Error message
        """
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "[ERROR] Error occurred",
                    },
                    "template": "red",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**Error**:\n{error_message}",
                        }
                    }
                ]
            }
        }

        # Send card via Feishu API
        # TODO: Implement actual Feishu message sending
        print(f"[FEISHU] Would send error card to {user_id}")
        print(f"[CARD] {json.dumps(card, ensure_ascii=False)}")

    async def start(self):
        """
        Start Feishu webhook server

        Runs uvicorn server to listen for webhook events.
        """
        import uvicorn

        config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        await server.serve()

    def run_sync(self):
        """
        Run Feishu webhook server synchronously

        Convenience method for non-async contexts.
        """
        import uvicorn

        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
        )
