"""Durable background run service backed by JSONL snapshots and events."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import uuid
from typing import Any, Optional

from fastreact.core.time import utc_iso


TERMINAL_RUN_STATUSES = {"completed", "failed", "cancelled", "expired"}
ACTIVE_RUN_STATUSES = {"queued", "running"}


def _parse_iso(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_after(seconds: float) -> str:
    return (_utc_now() + timedelta(seconds=seconds)).isoformat()


class RunService:
    """Owns durable run lifecycle, replay events, and trace summaries."""

    def __init__(
        self,
        store,
        *,
        lease_seconds: float = 300.0,
        max_attempts: int = 3,
        retry_base_seconds: float = 5.0,
        retry_max_seconds: float = 300.0,
        event_schema: str = "fastreact.agent_event.v1",
    ):
        self._store = store
        self.lease_seconds = float(lease_seconds)
        self.max_attempts = int(max_attempts)
        self.retry_base_seconds = float(retry_base_seconds)
        self.retry_max_seconds = float(retry_max_seconds)
        self.event_schema = event_schema

    def create(
        self,
        *,
        run_id: str,
        session_id: str,
        query: str,
        skills: Optional[list[str]] = None,
        history: Optional[list[dict[str, Any]]] = None,
        user_key: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        generation_options: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if self.get(run_id):
            raise ValueError(f"Run already exists: {run_id}")
        now = utc_iso()
        record = {
            "run_id": run_id,
            "session_id": session_id,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "completed_at": None,
            "cancelled_at": None,
            "duration_ms": None,
            "query": query,
            "skills": skills,
            "history": history or [],
            "user_key": user_key,
            "metadata": metadata or {},
            "generation_options": generation_options or {},
            "event_count": 0,
            "error": None,
            "last_error": None,
            "attempts": 0,
            "lease_owner": None,
            "lease_expires_at": None,
            "retry_after": None,
            "worker_id": None,
        }
        return self._save(record)

    def get(self, run_id: str) -> Optional[dict[str, Any]]:
        return self._store.latest_by_id("runs", "run_id", run_id)

    def list(self, *, status: Optional[str] = None, limit: int = 200) -> list[dict[str, Any]]:
        runs = list(self._store.latest_snapshots("runs", "run_id").values())
        if status:
            runs = [run for run in runs if run.get("status") == status]
        runs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return runs if limit == 0 else runs[:limit]

    def snapshot(self, run_id: str, *, include_events: bool = False) -> Optional[dict[str, Any]]:
        record = self.get(run_id)
        if not record:
            return None
        snapshot = {
            "run_id": record["run_id"],
            "session_id": record["session_id"],
            "status": record["status"],
            "created_at": record["created_at"],
            "started_at": record.get("started_at"),
            "completed_at": record.get("completed_at"),
            "cancelled_at": record.get("cancelled_at"),
            "duration_ms": record.get("duration_ms"),
            "event_count": self.event_count(run_id),
            "error": record.get("error"),
            "metadata": record.get("metadata", {}),
            "generation_options": record.get("generation_options", {}),
            "attempts": record.get("attempts", 0),
            "lease_expires_at": record.get("lease_expires_at"),
            "retry_after": record.get("retry_after"),
            "worker_id": record.get("worker_id"),
            "last_error": record.get("last_error"),
        }
        if include_events:
            snapshot["events"] = self.events(run_id)
        return snapshot

    def mark_running(self, run_id: str, *, worker_id: Optional[str] = None) -> dict[str, Any]:
        record = self._require(run_id)
        worker_id = worker_id or f"worker-{uuid.uuid4().hex[:10]}"
        now = utc_iso()
        record.update({
            "status": "running",
            "started_at": record.get("started_at") or now,
            "updated_at": now,
            "attempts": int(record.get("attempts") or 0) + 1,
            "worker_id": worker_id,
            "lease_owner": worker_id,
            "lease_expires_at": _utc_after(self.lease_seconds),
            "error": None,
        })
        return self._save(record)

    def heartbeat(self, run_id: str) -> dict[str, Any]:
        record = self._require(run_id)
        record["updated_at"] = utc_iso()
        record["lease_expires_at"] = _utc_after(self.lease_seconds)
        return self._save(record)

    def cancel(self, run_id: str) -> dict[str, Any]:
        record = self._require(run_id)
        if record.get("status") in TERMINAL_RUN_STATUSES:
            return record
        now = utc_iso()
        record.update({
            "status": "cancelled",
            "cancelled_at": now,
            "completed_at": now,
            "updated_at": now,
            "lease_owner": None,
            "lease_expires_at": None,
        })
        record["duration_ms"] = record.get("duration_ms") or self._duration_ms(record)
        return self._save(record)

    def complete(self, run_id: str) -> dict[str, Any]:
        record = self._require(run_id)
        if record.get("status") == "cancelled":
            return record
        now = utc_iso()
        record.update({
            "status": "completed",
            "completed_at": now,
            "updated_at": now,
            "lease_owner": None,
            "lease_expires_at": None,
            "event_count": self.event_count(run_id),
        })
        record["duration_ms"] = self._duration_ms(record)
        saved = self._save(record)
        self.persist_trace(run_id)
        return saved

    def fail(self, run_id: str, error: str, *, status: str = "failed", retryable: bool = False) -> dict[str, Any]:
        record = self._require(run_id)
        now = utc_iso()
        attempts = int(record.get("attempts") or 0)
        if retryable and attempts < self.max_attempts:
            retry_seconds = self.retry_delay_seconds(attempts)
            record.update({
                "status": "queued",
                "error": None,
                "last_error": error,
                "retry_after": _utc_after(retry_seconds),
                "updated_at": now,
                "lease_owner": None,
                "lease_expires_at": None,
                "worker_id": None,
                "event_count": self.event_count(run_id),
            })
            return self._save(record)
        record.update({
            "status": status,
            "error": error,
            "last_error": error,
            "completed_at": now,
            "updated_at": now,
            "lease_owner": None,
            "lease_expires_at": None,
            "retry_after": None,
            "event_count": self.event_count(run_id),
        })
        record["duration_ms"] = self._duration_ms(record)
        saved = self._save(record)
        self.persist_trace(run_id)
        return saved

    def recover_stale(self) -> dict[str, int]:
        recovered = 0
        failed = 0
        now = _utc_now()
        for record in self.list(limit=0):
            status = record.get("status")
            if status == "queued":
                recovered += 1
                continue
            if status != "running":
                continue
            lease_expires_at = _parse_iso(record.get("lease_expires_at"))
            if lease_expires_at and lease_expires_at > now:
                continue
            if int(record.get("attempts") or 0) < self.max_attempts:
                record.update({
                    "status": "queued",
                    "updated_at": utc_iso(),
                    "retry_after": _utc_after(self.retry_delay_seconds(int(record.get("attempts") or 0))),
                    "last_error": "Recovered stale running lease",
                    "lease_owner": None,
                    "lease_expires_at": None,
                    "worker_id": None,
                })
                self._save(record)
                recovered += 1
            else:
                record.update({
                    "status": "failed",
                    "updated_at": utc_iso(),
                    "completed_at": utc_iso(),
                    "error": "Run exceeded retry attempts during daemon recovery",
                    "last_error": "Stale running lease exceeded retry attempts",
                    "lease_owner": None,
                    "lease_expires_at": None,
                })
                self._save(record)
                self.persist_trace(record["run_id"])
                failed += 1
        return {"recovered": recovered, "failed": failed}

    def queued_for_recovery(self) -> list[dict[str, Any]]:
        return [run for run in self.list(limit=0) if run.get("status") == "queued" and self.is_retry_ready(run)]

    def is_retry_ready(self, record: dict[str, Any]) -> bool:
        retry_after = _parse_iso(record.get("retry_after"))
        return retry_after is None or retry_after <= _utc_now()

    def append_event(self, run_id: str, event: dict[str, Any]) -> dict[str, Any]:
        record = self._require(run_id)
        event = {
            **event,
            "trace_type": "background_run",
            "run_id": run_id,
            "session_id": record["session_id"],
        }
        saved = self._store.append("run_events", event)
        # Compatibility stream for existing admin/session readers.
        self._store.append("events", saved)
        record["event_count"] = self.event_count(run_id)
        record["updated_at"] = utc_iso()
        self._save(record)
        return saved

    def events(self, run_id: str) -> list[dict[str, Any]]:
        events = self._store.read("run_events", limit=0, run_id=run_id)
        events.sort(key=self.event_sequence)
        return events

    def event_count(self, run_id: str) -> int:
        return len(self.events(run_id))

    def next_sequence(self, run_id: str) -> int:
        events = self.events(run_id)
        return self.event_sequence(events[-1]) + 1 if events else 0

    def persist_trace(self, run_id: str) -> Optional[dict[str, Any]]:
        record = self.get(run_id)
        if not record:
            return None
        events = self.events(run_id)
        final_event = next((event for event in reversed(events) if event.get("type") == "session_end"), None)
        error_event = next((event for event in reversed(events) if event.get("type") == "error"), None)
        tool_calls = [event for event in events if event.get("type") == "tool_call"]
        tool_name_counts = self.tool_name_counts(tool_calls)
        approvals = [event for event in events if event.get("type") == "ask_user" or event.get("approval_request_id")]
        compression_count = sum(
            1
            for event in events
            if event.get("metadata", {}).get("compression") or event.get("metadata", {}).get("compression_event")
        )
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for event in events:
            usage = event.get("metadata", {}).get("llm_usage") or event.get("metadata", {}).get("llm_usage_total")
            if not isinstance(usage, dict):
                continue
            for key in usage_total:
                value = usage.get(key)
                if isinstance(value, (int, float)):
                    usage_total[key] += int(value)
        usage_total = {key: value for key, value in usage_total.items() if value}
        trace = {
            "trace_type": "background_run",
            "run_id": run_id,
            "session_id": record["session_id"],
            "status": record["status"],
            "created_at": record.get("created_at"),
            "started_at": record.get("started_at"),
            "completed_at": record.get("completed_at"),
            "duration_ms": record.get("duration_ms"),
            "event_count": len(events),
            "tool_call_count": len(tool_calls),
            "tool_name_counts": tool_name_counts,
            "approval_count": len(approvals),
            "compression_count": compression_count,
            "llm_usage_total": usage_total,
            "final_content": final_event.get("content") if final_event else "",
            "error": record.get("error") or (error_event.get("content") if error_event else None),
            "metadata": record.get("metadata", {}),
            "generation_options": record.get("generation_options", {}),
            "policy_snapshot_hash": self.policy_snapshot_hash(record.get("metadata", {})),
        }
        digest_budget = self.pska_digest_tool_budget(record.get("metadata", {}), tool_name_counts)
        if digest_budget:
            trace["pska_digest_tool_budget"] = digest_budget
        return self._store.upsert_snapshot("traces", "run_id", trace)

    def stats(self) -> dict[str, Any]:
        runs = self.list(limit=0)
        status_counts: dict[str, int] = {}
        stale_lease_count = 0
        now = _utc_now()
        for run in runs:
            status = str(run.get("status") or "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            if status == "running":
                lease_expires_at = _parse_iso(run.get("lease_expires_at"))
                if lease_expires_at and lease_expires_at <= now:
                    stale_lease_count += 1
        return {
            "total_count": len(runs),
            "status_counts": status_counts,
            "queued_count": status_counts.get("queued", 0),
            "ready_queued_count": sum(1 for run in runs if run.get("status") == "queued" and self.is_retry_ready(run)),
            "delayed_queued_count": sum(1 for run in runs if run.get("status") == "queued" and not self.is_retry_ready(run)),
            "running_count": status_counts.get("running", 0),
            "stale_lease_count": stale_lease_count,
            "replay_event_count": len(self._store.read("run_events", limit=0)),
        }

    @staticmethod
    def event_sequence(event: dict[str, Any]) -> int:
        sequence = event.get("sequence")
        if isinstance(sequence, int):
            return sequence
        event_id = str(event.get("event_id") or "")
        try:
            return int(event_id.rsplit(":", 1)[-1])
        except ValueError:
            return 0

    @staticmethod
    def tool_name_counts(tool_calls: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in tool_calls:
            tool_name = event.get("tool_name")
            if not tool_name:
                continue
            key = str(tool_name)
            counts[key] = counts.get(key, 0) + 1
        return counts

    @staticmethod
    def pska_digest_tool_budget(metadata: dict[str, Any], tool_name_counts: dict[str, int]) -> Optional[dict[str, Any]]:
        if metadata.get("caller") != "pska_digest_worker" and metadata.get("purpose") != "digest":
            return None
        write_count = int(tool_name_counts.get("pska_pska_write_candidates", 0))
        job_context_count = int(tool_name_counts.get("pska_pska_job_context", 0))
        tool_budget = {
            "pska_pska_write_candidates": 1,
            "pska_pska_job_context": 1,
        }
        return {
            "write_call_count": write_count,
            "job_context_call_count": job_context_count,
            "tool_budget": tool_budget,
            "tool_budget_exceeded": write_count > tool_budget["pska_pska_write_candidates"]
            or job_context_count > tool_budget["pska_pska_job_context"],
        }

    @staticmethod
    def policy_snapshot_hash(policy_snapshot: Any) -> str | None:
        if not policy_snapshot:
            return None
        encoded = repr(policy_snapshot).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:16]

    def retry_delay_seconds(self, attempts: int) -> float:
        exponent = max(0, int(attempts) - 1)
        delay = self.retry_base_seconds * (2**exponent)
        return min(self.retry_max_seconds, max(0.0, delay))

    def _duration_ms(self, record: dict[str, Any]) -> float | None:
        started = _parse_iso(record.get("started_at") or record.get("created_at"))
        completed = _parse_iso(record.get("completed_at")) or _utc_now()
        if not started:
            return None
        return round((completed - started).total_seconds() * 1000, 2)

    def _save(self, record: dict[str, Any]) -> dict[str, Any]:
        record["updated_at"] = record.get("updated_at") or utc_iso()
        return self._store.upsert_snapshot("runs", "run_id", record)

    def _require(self, run_id: str) -> dict[str, Any]:
        record = self.get(run_id)
        if not record:
            raise KeyError(f"Run not found: {run_id}")
        return dict(record)
