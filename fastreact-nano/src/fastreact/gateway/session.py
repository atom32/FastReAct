"""
Session management for FastReAct Gateway

Handles user sessions across channels with context persistence.
"""

import asyncio
from uuid import uuid4
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Any, Callable

from fastreact.core.bus import MessageBus, InboundMessage, OutboundMessage
from fastreact.core.context import ContextManager, FileContextStore
from fastreact.core.react import ReActCore, Phase
from fastreact.utils.config import Paths, get_paths


@dataclass
class SessionConfig:
    """Session configuration"""
    channel: str
    user_id: str
    max_iterations: int = 20
    timeout_seconds: int = 300
    enable_streaming: bool = False


@dataclass
class SessionState:
    """Session state"""
    session_id: str
    channel: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class Session:
    """
    User session - manages conversation state and processing

    Each session represents a user's conversation with the agent.
    """

    def __init__(
        self,
        config: SessionConfig,
        react_core: ReActCore,
        context_manager: ContextManager,
        message_bus: MessageBus,
    ):
        """
        Initialize session

        Args:
            config: Session configuration
            react_core: ReAct core for processing
            context_manager: Context manager
            message_bus: Message bus for communication
        """
        self._config = config
        self._react_core = react_core
        self._context_manager = context_manager
        self._message_bus = message_bus

        # Session state
        session_id = f"{config.channel}:{config.user_id}"
        self._state = SessionState(
            session_id=session_id,
            channel=config.channel,
            user_id=config.user_id,
        )

        # Processing lock
        self._lock = asyncio.Lock()
        self._processing = False

    @property
    def session_id(self) -> str:
        return self._state.session_id

    @property
    def channel(self) -> str:
        return self._state.channel

    @property
    def user_id(self) -> str:
        return self._state.user_id

    @property
    def state(self) -> SessionState:
        return self._state

    async def handle_message(self, message: InboundMessage) -> OutboundMessage:
        """
        Handle incoming message

        Args:
            message: Inbound message

        Returns:
            Outbound message response
        """
        async with self._lock:
            self._processing = True
            try:
                # Update activity
                self._state.last_activity = datetime.utcnow()
                self._state.message_count += 1

                # Get or create context
                context = await self._context_manager.get_context(
                    self._state.session_id,
                    self._state.user_id,
                )

                # Add user message
                context.add_message(
                    role="user",
                    content=message.content,
                )

                # Build messages for LLM
                messages = context.messages.copy()

                # Stream callback if enabled
                stream_callback = None
                if self._config.enable_streaming:
                    async def send_chunk(chunk: str):
                        await self._message_bus.publish_outbound(
                            OutboundMessage(
                                channel=self._state.channel,
                                user_id=self._state.user_id,
                                content=chunk,
                                is_stream=True,
                                is_final=False,
                            )
                        )
                    stream_callback = send_chunk

                # Run ReAct loop
                response_content = await self._react_core.run(
                    messages=messages,
                    stream_callback=stream_callback,
                )

                # Add assistant response to context
                if response_content:
                    context.add_message(
                        role="assistant",
                        content=response_content,
                    )

                # Save context
                await self._context_manager.save_context(context)

                # Send final response
                return OutboundMessage(
                    channel=self._state.channel,
                    user_id=self._state.user_id,
                    content=response_content,
                    is_final=True,
                )

            finally:
                self._processing = False

    async def stream_response(self) -> None:
        """
        Stream response to message bus

        This method publishes OutboundMessage objects to the message bus.
        Subscribers (channels) consume these messages.
        """
        # The actual streaming is handled by handle_message
        # This method is a placeholder for future streaming optimizations
        pass

    def is_processing(self) -> bool:
        """Check if session is currently processing a message"""
        return self._processing

    def is_expired(self, timeout_seconds: Optional[int] = None) -> bool:
        """
        Check if session is expired

        Args:
            timeout_seconds: Timeout in seconds (default from config)

        Returns:
            True if expired
        """
        timeout = timeout_seconds or self._config.timeout_seconds
        if timeout <= 0:
            return False

        elapsed = (datetime.utcnow() - self._state.last_activity).total_seconds()
        return elapsed > timeout


class SessionManager:
    """
    Manage multiple user sessions

    Provides session creation, lookup, and cleanup.
    """

    def __init__(
        self,
        react_core: ReActCore,
        context_manager: ContextManager,
        message_bus: MessageBus,
        paths: Optional[Paths] = None,
    ):
        """
        Initialize session manager

        Args:
            react_core: ReAct core for processing
            context_manager: Context manager
            message_bus: Message bus
            paths: Path configuration
        """
        self._react_core = react_core
        self._context_manager = context_manager
        self._message_bus = message_bus
        self._paths = paths or get_paths()

        # Session storage
        self._sessions: dict[str, Session] = {}

        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def get_or_create_session(
        self,
        channel: str,
        user_id: str,
        **config_kwargs,
    ) -> Session:
        """
        Get existing session or create new one

        Args:
            channel: Channel name
            user_id: User identifier
            **config_kwargs: Additional session config

        Returns:
            Session object
        """
        session_id = f"{channel}:{user_id}"

        if session_id in self._sessions:
            return self._sessions[session_id]

        # Create session config
        config = SessionConfig(
            channel=channel,
            user_id=user_id,
            **config_kwargs,
        )

        # Create session
        session = Session(
            config=config,
            react_core=self._react_core,
            context_manager=self._context_manager,
            message_bus=self._message_bus,
        )

        # Store session
        self._sessions[session_id] = session

        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self._sessions.get(session_id)

    async def remove_session(self, session_id: str):
        """Remove session"""
        if session_id in self._sessions:
            # Clear context cache
            await self._context_manager.clear_cache(session_id)
            del self._sessions[session_id]

    async def cleanup_expired(self):
        """Remove expired sessions"""
        expired = []

        for session_id, session in self._sessions.items():
            if session.is_expired():
                expired.append(session_id)

        for session_id in expired:
            await self.remove_session(session_id)

    async def start_cleanup_task(self, interval_seconds: int = 60):
        """Start background cleanup task"""
        if self._cleanup_task and not self._cleanup_task.done():
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop(interval_seconds))

    async def stop_cleanup_task(self):
        """Stop background cleanup task"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self, interval_seconds: int):
        """Cleanup loop"""
        while self._running:
            try:
                await asyncio.sleep(interval_seconds)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue
                pass

    def get_stats(self) -> dict[str, Any]:
        """Get session statistics"""
        return {
            "total_sessions": len(self._sessions),
            "processing": sum(
                1 for s in self._sessions.values() if s.is_processing()
            ),
            "channels": {
                channel: len([
                    s for s in self._sessions.values()
                    if s.channel == channel
                ])
                for channel in set(s.channel for s in self._sessions.values())
            },
        }
