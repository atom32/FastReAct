"""
Agent Session - Session-level business logic layer

This module contains the AgentSession class which encapsulates all session-level
business logic that was previously scattered across adapters.

Responsibilities:
- Conversation history management
- Follow-up query detection
- Session state tracking (running, interrupted)
- Message queue for concurrent inputs
- Query processing with event streaming

This class is CHANNEL-AGNOSTIC - it works with WebSocket, HTTP, CLI, etc.
"""

import asyncio
from datetime import datetime
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fastreact import Agent
    from fastreact.core.events import AgentEvent


class AgentSession:
    """
    Agent Session - Business Logic Layer

    Encapsulates all session-level business logic, independent of transport layer.

    Responsibilities:
    - Conversation history management with automatic pruning
    - Follow-up query detection (time-based context preservation)
    - Session state tracking (running, interrupted)
    - Message queue for handling concurrent inputs
    - Query processing with callback-based event streaming

    Architecture:
    Adapter (transport) → AgentSession (business logic) → Agent (orchestration) → Core (reasoning)
    """

    def __init__(
        self,
        session_id: str,
        agent: "Agent",
        max_history: int = 50,
        followup_window_seconds: int = 30,
        max_queue_size: int = 5,
    ):
        """
        Initialize Agent session

        Args:
            session_id: Unique session identifier
            agent: Agent instance for execution
            max_history: Maximum conversation turns to keep in memory
            followup_window_seconds: Time window for follow-up detection (default: 30s)
            max_queue_size: Maximum messages in queue (for flow control)
        """
        # Identity
        self.session_id = session_id
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

        # Agent reference (for execution)
        self._agent = agent

        # Conversation history
        self._history: list[dict] = []
        self._max_history = max_history

        # Follow-up detection
        self._last_response_time: Optional[datetime] = None
        self._followup_window_seconds = followup_window_seconds

        # Session state
        self._is_running = False
        self._interrupted = False

        # Message queue (for concurrent inputs)
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._max_queue_size = max_queue_size

    # === History Management ===

    def update_history(self, user_query: str, assistant_response: str):
        """
        Add conversation turn to history with automatic pruning

        Args:
            user_query: User's input message
            assistant_response: Agent's final response
        """
        # Add user message
        self._history.append({"role": "user", "content": user_query})

        # Add assistant message
        self._history.append({"role": "assistant", "content": assistant_response})

        # Prune history if too long (FIFO)
        if len(self._history) > self._max_history:
            import sys
            print(
                f"[INFO] Pruning history from {len(self._history)} to {self._max_history} messages",
                file=sys.stderr
            )
            self._history = self._history[-self._max_history:]

    def get_history(self) -> list[dict]:
        """
        Get conversation history

        Returns:
            Copy of conversation history in OpenAI-compatible format
        """
        return self._history.copy()

    # === Follow-up Detection ===

    def is_followup(self) -> bool:
        """
        Check if new query is within follow-up window

        Returns:
            True if within follow-up window, False otherwise
        """
        if not self._last_response_time:
            return False

        time_since_response = (
            datetime.utcnow() - self._last_response_time
        ).total_seconds()

        return time_since_response < self._followup_window_seconds

    def mark_response_sent(self):
        """
        Record response time for follow-up detection

        Should be called after sending final response to user
        """
        self._last_response_time = datetime.utcnow()

    # === Session State ===

    @property
    def is_running(self) -> bool:
        """Check if agent is currently running"""
        return self._is_running

    def set_running(self, running: bool):
        """
        Set agent running state

        Args:
            running: True if agent is running, False otherwise
        """
        self._is_running = running

    @property
    def is_interrupted(self) -> bool:
        """Check if session was interrupted"""
        return self._interrupted

    def interrupt(self):
        """Interrupt current execution"""
        self._interrupted = True

    def reset_interrupt(self):
        """Reset interrupt flag for new run"""
        self._interrupted = False

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()

    # === Message Queue ===

    async def enqueue_message(self, message: dict) -> bool:
        """
        Enqueue message for processing

        Control messages (type="control") bypass queue limit for priority handling.

        Args:
            message: Message dict with 'type' field

        Returns:
            True if message enqueued, False if queue is full
        """
        msg_type = message.get("type")

        # Control messages have priority (bypass queue limit)
        if msg_type == "control":
            await self._message_queue.put(message)
            return True

        # Check queue capacity for regular messages
        if self._message_queue.qsize() >= self._max_queue_size:
            return False

        await self._message_queue.put(message)
        return True

    async def process_queue(self, on_event: Callable):
        """
        Background task to process message queue

        Args:
            on_event: Callback function async def on_event(message_dict)
        """
        while True:
            message = await self._message_queue.get()
            await self.process_message(message, on_event)

    # === Message Processing ===

    async def process_message(self, message: dict, on_event: Callable):
        """
        Process individual message with event callback

        Args:
            message: Message dict from queue
            on_event: Callback function async def on_event(message_dict)
        """
        msg_type = message.get("type")

        if msg_type == "control":
            action = message.get("action")
            if action == "interrupt":
                self.interrupt()
                # Send via callback instead of direct WebSocket
                await on_event({
                    "type": "info",
                    "content": "Execution interrupted",
                })

        elif msg_type == "query":
            await self._handle_query(message, on_event)

    async def _handle_query(self, message: dict, on_event: Callable):
        """
        Handle query message with full event streaming

        Args:
            message: Query message dict with 'content' and optional 'skills'
            on_event: Callback function async def on_event(message_dict)
        """
        query = message.get("content", "")
        skills = message.get("skills")

        self.update_activity()

        # Check follow-up
        is_followup = self.is_followup()

        # Check if agent running
        if self._is_running:
            # Send user intervention signal
            from fastreact.core.messages import Message
            import sys

            print(
                f"[INFO] New query received while agent running, sending user intervention",
                file=sys.stderr
            )

            # Check if agent has session queue (backward compatibility)
            if hasattr(self._agent, '_session_queues') and self.session_id in self._agent._session_queues:
                self._agent._session_queues[self.session_id].push(
                    Message.steering(
                        query,
                        metadata={"source": "gateway", "user_intervention": True}
                    )
                )

            # Send notification via callback
            await on_event({
                "type": "info",
                "content": f"[USER INTERVENTION] {query[:50]}{'...' if len(query) > 50 else ''}",
            })
            return

        # Start new execution
        self.reset_interrupt()
        self._is_running = True

        # If follow-up query, log it
        if is_followup and len(self._history) > 0:
            import sys
            print(
                f"[INFO] Follow-up query will use conversation history (last {len(self._history)} messages)",
                file=sys.stderr
            )

        # Run agent with event streaming
        try:
            from fastreact.core.events import EventType

            final_response = None
            interrupted = False

            async for event in self._agent.run_event_stream(
                query,
                skills=skills,
                session_id=self.session_id,
                history=self._history if is_followup else [],
            ):
                # Check interrupt
                if self._interrupted:
                    break

                # Send event via callback
                await on_event({
                    "type": "event",
                    "event_type": event.type.value,
                    "content": event.content,
                    "tool_name": event.tool_name,
                    "tool_args": event.tool_args,
                    "session_id": event.session_id,
                    "metadata": event.metadata,
                })

                # Track final response
                if event.type == EventType.SESSION_END:
                    final_response = event.content
                    if "[INTERRUPTED]" in event.content or "User stopped" in event.content:
                        interrupted = True
                        break

            # Update history if not interrupted
            if not interrupted and final_response:
                self.update_history(query, final_response)
                self.mark_response_sent()

        except Exception as e:
            await on_event({
                "type": "error",
                "content": str(e),
            })

        finally:
            # Always reset running state when done
            self._is_running = False
