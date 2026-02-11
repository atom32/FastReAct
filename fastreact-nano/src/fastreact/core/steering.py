"""
Steering System for FastReAct Nano

Allows real-time intervention into agent execution:
- User correction: "不对，先看 README"
- Admin override: "STOP: 禁止删除"
- Testing injection: "TEST: 模拟拒绝"

Architecture:
- Core: Exposes inject_message() interface
- Agent: Wrapper with convenient steer() method
- Adapter: Manages steering sources (WebSocket, HTTP, CLI)
"""

import asyncio
from typing import Optional, Callable, Awaitable
from collections import defaultdict
from dataclasses import dataclass

from fastreact.core.messages import Message, MessageQueue
from fastreact.core.events import AgentEvent, EventType


@dataclass
class SteeringSource:
    """
    Source of steering messages

    Examples:
    - WebSocket connection from web UI
    - HTTP endpoint from monitoring system
    - CLI input from terminal
    - Test harness
    """
    name: str
    queue: asyncio.Queue
    priority: int = 0  # Higher priority messages processed first


class SteeringManager:
    """
    Manages multiple steering sources and merges them

    Usage:
        manager = SteeringManager()

        # Register sources
        ws_source = manager.register_source("websocket", priority=10)
        http_source = manager.register_source("http", priority=5)

        # Inject messages
        ws_source.put_nowait("STOP: 禁止删除")

        # Check for messages (called by core)
        messages = await manager.get_messages(session_id)
    """

    def __init__(self):
        self._sources: dict[str, SteeringSource] = {}
        self._session_queues: dict[str, dict[str, asyncio.Queue]] = defaultdict(
            lambda: defaultdict(asyncio.Queue)
        )

    def register_source(
        self,
        name: str,
        priority: int = 0,
    ) -> asyncio.Queue:
        """
        Register a steering source

        Args:
            name: Source name (e.g., "websocket", "http")
            priority: Higher priority sources processed first

        Returns:
            Queue for injecting messages into this source
        """
        source = SteeringSource(
            name=name,
            queue=asyncio.Queue(),
            priority=priority,
        )
        self._sources[name] = source
        return source.queue

    def unregister_source(self, name: str):
        """Unregister a steering source"""
        if name in self._sources:
            del self._sources[name]

    async def inject(
        self,
        session_id: str,
        source_name: str,
        content: str,
        metadata: Optional[dict] = None,
    ):
        """
        Inject steering message from a source

        Args:
            session_id: Target session
            source_name: Source name (must be registered)
            content: Message content
            metadata: Optional metadata
        """
        if source_name not in self._sources:
            raise ValueError(f"Unknown source: {source_name}")

        queue = self._session_queues[session_id][source_name]
        await queue.put((content, metadata or {}))

    def inject_nowait(
        self,
        session_id: str,
        source_name: str,
        content: str,
        metadata: Optional[dict] = None,
    ):
        """Non-blocking version of inject()"""
        if source_name not in self._sources:
            raise ValueError(f"Unknown source: {source_name}")

        queue = self._session_queues[session_id][source_name]
        queue.put_nowait((content, metadata or {}))

    async def get_messages(self, session_id: str) -> list[Message]:
        """
        Get all pending steering messages for a session

        Args:
            session_id: Session ID

        Returns:
            List of steering messages, sorted by priority
        """
        if session_id not in self._session_queues:
            return []

        messages = []

        # Collect messages from all sources
        for source_name, source in self._sources.items():
            queue = self._session_queues[session_id][source_name]

            # Drain all messages from this source
            while not queue.empty():
                try:
                    content, metadata = queue.get_nowait()
                    messages.append(
                        Message.steering(
                            content,
                            **{
                                **metadata,
                                "source": source_name,
                                "priority": source.priority,
                            }
                        )
                    )
                except asyncio.QueueEmpty:
                    break

        # Sort by priority (higher first)
        messages.sort(key=lambda m: m.metadata.get("priority", 0), reverse=True)

        # Clean up empty session
        if not messages and session_id in self._session_queues:
            # Check if any queue has messages
            has_messages = any(
                not q.empty()
                for q in self._session_queues[session_id].values()
            )
            if not has_messages:
                del self._session_queues[session_id]

        return messages


class SteerableEventStream:
    """
    Wrapper around agent event stream with steering support

    Usage:
        agent = Agent()
        stream = SteerableEventStream(agent)

        # Start streaming in background
        task = asyncio.create_task(stream.run("分析代码", "session-123"))

        # Inject steering from anywhere
        stream.steer("session-123", "不对，先看 README")

        # Wait for completion
        result = await task
    """

    def __init__(self, agent, steering_manager: Optional[SteeringManager] = None):
        """
        Initialize steerable event stream

        Args:
            agent: FastReAct Agent instance
            steering_manager: Optional steering manager (creates new if None)
        """
        self._agent = agent
        self._steering_manager = steering_manager or SteeringManager()
        self._active_sessions: dict[str, asyncio.Task] = {}

    def register_source(self, name: str, priority: int = 0) -> asyncio.Queue:
        """Register a steering source"""
        return self._steering_manager.register_source(name, priority)

    async def steer(
        self,
        session_id: str,
        message: str,
        source: str = "default",
    ):
        """
        Inject steering message into active session

        Args:
            session_id: Target session
            message: Steering message content
            source: Source name (registers if not exists)
        """
        await self._steering_manager.inject(session_id, source, message)

    def steer_nowait(
        self,
        session_id: str,
        message: str,
        source: str = "default",
    ):
        """Non-blocking version of steer()"""
        self._steering_manager.inject_nowait(session_id, source, message)

    async def run(
        self,
        query: str,
        session_id: str,
        skills: Optional[list[str]] = None,
    ):
        """
        Run agent with steering support

        Args:
            query: User query
            session_id: Session ID
            skills: Optional skills

        Yields:
            AgentEvent objects
        """
        # Create message callback for core
        async def message_callback(sid: str):
            """Called by core to check for steering messages"""
            if sid != session_id:
                return None
            return await self._steering_manager.get_messages(sid)

        # Inject callback into core (needs core modification)
        # For now, we'll poll in the adapter layer
        try:
            async for event in self._agent.run_event_stream(
                query,
                skills=skills,
                session_id=session_id,
            ):
                yield event

                # Check for steering after each event
                steering_messages = await self._steering_manager.get_messages(session_id)
                if steering_messages:
                    # Create a follow-up event with steering
                    yield AgentEvent.think(
                        f"[干预] {steering_messages[0].content}",
                        session_id,
                        metadata={"steering": True},
                    )


__all__ = [
    "SteeringSource",
    "SteeringManager",
    "SteerableEventStream",
]
