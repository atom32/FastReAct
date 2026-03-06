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
- Memory consolidation (dual-layer memory system)

This class is CHANNEL-AGNOSTIC - it works with WebSocket, HTTP, CLI, etc.
"""

import asyncio
from datetime import datetime
from pathlib import Path
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
        enable_memory: bool = True,
        workspace_path: Optional[Path] = None,
    ):
        """
        Initialize Agent session

        Args:
            session_id: Unique session identifier
            agent: Agent instance for execution
            max_history: Maximum conversation turns to keep in memory
            followup_window_seconds: Time window for follow-up detection (default: 30s)
            max_queue_size: Maximum messages in queue (for flow control)
            enable_memory: Enable dual-layer memory system (MEMORY.md consolidation)
            workspace_path: Path to workspace for memory files (auto-detected if None)
        """
        # Identity
        self.session_id = session_id
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.user_key: Optional[str] = None  # User identifier for multi-tenant
        self.status: str = "idle"  # Session status: idle | running | closed

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

        # Memory management
        self._enable_memory = enable_memory
        self._memory_manager = None

        if enable_memory:
            # Auto-detect workspace path if not provided
            if workspace_path is None:
                workspace_path = self._detect_workspace_path()

            if workspace_path:
                from fastreact.core.memory import MemoryManager
                self._memory_manager = MemoryManager(
                    workspace_path=workspace_path,
                    agent=agent,
                    consolidation_threshold=max_history,
                )
                import sys
                print(
                    f"[MEMORY] MemoryManager initialized for session {session_id}",
                    file=sys.stderr
                )

    def _detect_workspace_path(self) -> Optional[Path]:
        """
        Auto-detect workspace path from agent config

        Returns:
            Path to workspace directory or None if not found
        """
        try:
            # Try to get workspace from agent config
            if hasattr(self._agent, 'config') and hasattr(self._agent.config, 'paths'):
                paths = self._agent.config.paths

                # Check for gateway_workspace (single-tenant mode)
                if hasattr(paths, 'gateway_workspace'):
                    return Path(paths.gateway_workspace)

                # Check for workspace (general)
                if hasattr(paths, 'workspace'):
                    return Path(paths.workspace)

            # Fallback: check default locations
            default_candidates = [
                Path.cwd() / "workspaces" / "default",
                Path.home() / ".fastreact" / "workspaces" / "default",
            ]

            for candidate in default_candidates:
                if candidate.exists():
                    return candidate

            # Last resort: create workspaces/default
            default_workspace = Path.cwd() / "workspaces" / "default"
            default_workspace.mkdir(parents=True, exist_ok=True)
            return default_workspace

        except Exception as e:
            import sys
            print(
                f"[WARNING] Failed to detect workspace path: {e}",
                file=sys.stderr
            )
            return None

    # === History Management ===

    async def update_history(self, user_query: str, assistant_response: str):
        """
        Add conversation turn to history with automatic pruning

        Triggers memory consolidation if history exceeds threshold.

        Args:
            user_query: User's input message
            assistant_response: Agent's final response
        """
        # Add user message
        self._history.append({"role": "user", "content": user_query})

        # Add assistant message
        self._history.append({"role": "assistant", "content": assistant_response})

        # Check if consolidation is needed (only when EXCEEDING threshold)
        if len(self._history) > self._max_history and self._memory_manager:
            import sys
            print(
                f"[MEMORY] History threshold exceeded ({len(self._history)} > {self._max_history}), "
                f"triggering consolidation",
                file=sys.stderr
            )

            # Try to consolidate to long-term memory
            new_history = await self._memory_manager.consolidate(
                self._history,
                self.session_id
            )

            # If consolidation succeeded, use new history (empty)
            # If consolidation failed, fallback to FIFO pruning
            if len(new_history) == 0:
                # Success: history was cleared
                self._history = new_history
            else:
                # Failure: fallback to FIFO pruning
                print(
                    f"[WARNING] Memory consolidation failed, falling back to FIFO pruning",
                    file=sys.stderr
                )
                self._history = self._history[-self._max_history:]

        # Fallback: prune history if consolidation is disabled or not triggered
        elif len(self._history) > self._max_history:
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
        self.status = "running" if running else "idle"  # Sync status

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

        # Run agent with event streaming (using new API with queue support)
        try:
            from fastreact.core.events import EventType

            final_response = None
            interrupted = False

            # ✅ Use new API (run_or_inject) for queue support and fast user intervention
            # This matches Feishu SDK behavior: checks queue after each tool execution
            async for event in self._agent.run_or_inject(
                query=query,
                user_key=self.user_key,
                skills=skills,
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
                await self.update_history(query, final_response)
                self.mark_response_sent()

        except Exception as e:
            await on_event({
                "type": "error",
                "content": str(e),
            })

        finally:
            # Always reset running state when done
            self._is_running = False

    # === Session Metadata ===

    def get_status(self) -> str:
        """
        Get session status

        Returns:
            Current status string: "idle", "running", or "closed"
        """
        return self.status

    def set_status(self, status: str):
        """
        Set session status with validation

        Args:
            status: New status ("idle", "running", or "closed")

        Raises:
            ValueError: If status is not valid
        """
        valid_statuses = ["idle", "running", "closed"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        self.status = status

    def get_metadata(self) -> dict:
        """
        Get session metadata for query APIs

        Returns:
            Dictionary containing session metadata
        """
        return {
            "session_id": self.session_id,
            "user_key": self.user_key,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_running": self._is_running,
            "is_interrupted": self._interrupted,
        }
