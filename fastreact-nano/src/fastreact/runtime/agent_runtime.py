"""Agent runtime facade for the ReAct execution loop."""

from typing import AsyncIterator, Optional, TYPE_CHECKING

from fastreact.runtime.timing import TimingSpan

if TYPE_CHECKING:
    from fastreact.agent import Agent
    from fastreact.core.events import AgentEvent


class AgentRuntime:
    """
    Runtime boundary for Agent execution.

    The first refactor phase delegates to the legacy loop implementation while
    centralizing timing and adapter-facing execution in one place. Follow-up
    work can move the loop body here without changing the public Agent API.
    """

    def __init__(self, agent: "Agent"):
        self._agent = agent

    async def run_event_stream(
        self,
        query: str,
        skills: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        history: Optional[list[dict]] = None,
        user_key: Optional[str] = None,
    ) -> AsyncIterator["AgentEvent"]:
        span = TimingSpan("agent.run_event_stream")
        first_event_seen = False
        event_count = 0
        time_to_first_event_ms = None
        final_answer_length = 0
        effective_session_id = session_id or ""

        async for event in self._agent._run_event_stream_impl(
            query=query,
            skills=skills,
            session_id=session_id,
            history=history,
            user_key=user_key,
        ):
            event_count += 1
            effective_session_id = event.session_id or effective_session_id
            if not first_event_seen:
                first_event_seen = True
                event.metadata.setdefault("timing", {})
                time_to_first_event_ms = round(span.elapsed_ms, 2)
                event.metadata["timing"]["time_to_first_event_ms"] = time_to_first_event_ms

            if event.type.value in ("session_end", "error"):
                span.finish(event_type=event.type.value)
                event.metadata.setdefault("timing", {})
                event.metadata["timing"]["time_to_final_ms"] = round(span.elapsed_ms, 2)
                final_answer_length = len(event.content or "")
                if hasattr(self._agent, "store"):
                    self._agent.store.append("traces", {
                        "session_id": event.session_id,
                        "query": query,
                        "skills": skills or event.metadata.get("skills", []),
                        "event_type": event.type.value,
                        "time_to_first_event_ms": time_to_first_event_ms,
                        "time_to_final_ms": round(span.elapsed_ms, 2),
                        "event_count": event_count,
                        "final_answer_length": final_answer_length,
                    })

            if hasattr(self._agent, "store"):
                self._agent.store.append("events", event.to_dict())
                if event.type.value == "session_start":
                    self._agent.store.upsert_snapshot("sessions", "session_id", {
                        "session_id": event.session_id,
                        "user_key": user_key,
                        "status": "running",
                        "query": query,
                        "skills": event.metadata.get("skills", []),
                        "last_event_type": event.type.value,
                    })
                elif event.type.value in ("session_end", "error"):
                    self._agent.store.upsert_snapshot("sessions", "session_id", {
                        "session_id": event.session_id,
                        "user_key": user_key,
                        "status": "idle" if event.type.value == "session_end" else "error",
                        "query": query,
                        "skills": skills or [],
                        "last_event_type": event.type.value,
                        "final_answer_length": final_answer_length,
                    })

            yield event
