"""Session lifecycle service for AgentRuntime and adapters."""

import uuid
from typing import Optional, TYPE_CHECKING

from fastreact.core.messages import Message

if TYPE_CHECKING:
    from fastreact.agent import Agent
    from fastreact.core.session import AgentSession


class SessionService:
    """
    Single owner for Agent session lifecycle.

    This intentionally wraps the legacy Agent methods during the first
    refactor phase so adapters can stop touching private fields immediately.
    """

    def __init__(self, agent: "Agent"):
        self._agent = agent

    def create(
        self,
        session_id: Optional[str] = None,
        user_key: Optional[str] = None,
        max_history: int = 50,
        followup_window_seconds: int = 30,
        max_queue_size: int = 5,
    ) -> "AgentSession":
        session_id = session_id or self.new_session_id(user_key)
        return self._agent._create_session_impl(
            session_id=session_id,
            user_key=user_key,
            max_history=max_history,
            followup_window_seconds=followup_window_seconds,
            max_queue_size=max_queue_size,
        )

    def new_session_id(self, user_key: Optional[str] = None) -> str:
        suffix = f"session-{uuid.uuid4()}"
        return f"{user_key}:{suffix}" if user_key else suffix

    def get(self, session_id: str) -> Optional["AgentSession"]:
        return self._agent._sessions.get(session_id)

    def close(self, session_id: str) -> None:
        self._agent._close_session_impl(session_id)

    def find_active(self, user_key: str) -> Optional["AgentSession"]:
        return self._agent._find_active_session_impl(user_key)

    def list(self, user_key: Optional[str] = None) -> list[dict]:
        live = self._agent._list_sessions_impl(user_key=user_key)
        by_id = {item.get("session_id"): item for item in live}
        if hasattr(self._agent, "store"):
            for record in self._agent.store.read("sessions", limit=0):
                session_id = record.get("session_id")
                if not session_id:
                    continue
                if user_key and record.get("user_key") != user_key:
                    continue
                by_id.setdefault(session_id, record)
        sessions = list(by_id.values())
        sessions.sort(key=lambda item: item.get("last_activity") or item.get("updated_at") or item.get("created_at") or "", reverse=True)
        return sessions

    def status(self, session_id: str) -> Optional[str]:
        session = self.get(session_id)
        if session:
            return session.get_status()
        if hasattr(self._agent, "store"):
            record = self._agent.store.latest_by_id("sessions", "session_id", session_id)
            return record.get("status") if record else None
        return None

    def inject(self, session_id: str, message: Message) -> None:
        self._agent._inject_message_impl(session_id, message)

    async def enqueue(self, session_id: str, message: dict) -> bool:
        session = self.get(session_id)
        if not session:
            return False
        return await session.enqueue_message(message)

    def detail(self, session_id: str) -> Optional[dict]:
        live = self.get(session_id)
        record = live.get_metadata() if live else None
        if hasattr(self._agent, "store"):
            stored = self._agent.store.latest_by_id("sessions", "session_id", session_id)
            if stored:
                record = {**stored, **(record or {})}
            events = self._agent.store.read("events", limit=500, session_id=session_id)
        else:
            events = []
        if not record:
            return None
        record["events"] = events
        return record
