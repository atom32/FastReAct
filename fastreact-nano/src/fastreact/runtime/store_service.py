"""Append-only JSONL store for product control-plane data."""

import json
import os
import threading
from pathlib import Path
from typing import Any, Optional

from fastreact.core.time import utc_iso


SENSITIVE_KEYS = {"api_key", "apikey", "token", "pat", "password", "secret", "authorization"}
SAFE_TOKEN_USAGE_KEYS = {
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "max_tokens",
    "max_context_tokens",
    "completion_buffer_tokens",
    "compression_budget_tokens",
}
LONG_STRING_LIMIT = 1200
PREVIEW_CHARS = 600
TRUNCATION_MARKER = "\n[... truncated ...]"


class StoreService:
    """Small JSONL persistence layer for sessions, events, tasks, audit, and traces."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    @classmethod
    def from_agent(cls, agent: Any) -> "StoreService":
        paths = getattr(getattr(agent, "config", None), "paths", None)
        workspace = getattr(paths, "gateway_workspace", None) or getattr(paths, "workspace", None)
        root = Path(workspace) if workspace else Path.cwd() / "workspaces" / "default"
        return cls(root / ".fastreact")

    def append(self, stream: str, record: dict[str, Any]) -> dict[str, Any]:
        record = dict(record)
        record.setdefault("created_at", utc_iso())
        record = self.sanitize_for_stream(stream, record)
        path = self.root / f"{stream}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return record

    def read(self, stream: str, limit: int = 200, **filters: Any) -> list[dict[str, Any]]:
        path = self.root / f"{stream}.jsonl"
        if not path.exists():
            return []

        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if all(record.get(key) == value for key, value in filters.items() if value is not None):
                    records.append(record)

        if limit and len(records) > limit:
            records = records[-limit:]
        return records

    def stream_path(self, stream: str) -> Path:
        """Return the JSONL path for a stream without creating it."""
        return self.root / f"{stream}.jsonl"

    def streams(self) -> list[str]:
        """List known JSONL stream names."""
        if not self.root.exists():
            return []
        return sorted(path.stem for path in self.root.glob("*.jsonl") if path.is_file())

    def stats(self) -> dict[str, Any]:
        """Return lightweight store statistics for health checks and diagnostics."""
        streams: dict[str, dict[str, Any]] = {}
        total_bytes = 0
        total_records = 0

        for stream in self.streams():
            path = self.stream_path(stream)
            size = path.stat().st_size
            records = 0
            last_created_at = None
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    records += 1
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    last_created_at = record.get("created_at") or last_created_at

            streams[stream] = {
                "records": records,
                "bytes": size,
                "last_created_at": last_created_at,
            }
            total_bytes += size
            total_records += records

        return {
            "root": str(self.root),
            "exists": self.root.exists(),
            "streams": streams,
            "total_records": total_records,
            "total_bytes": total_bytes,
        }

    def latest_by_id(self, stream: str, id_field: str, value: str) -> Optional[dict[str, Any]]:
        records = self.read(stream, limit=0)
        for record in reversed(records):
            if record.get(id_field) == value:
                return record
        return None

    def latest_snapshots(self, stream: str, id_field: str, **filters: Any) -> dict[str, dict[str, Any]]:
        """Return the latest snapshot per id from an append-only snapshot stream."""
        latest: dict[str, dict[str, Any]] = {}
        for record in self.read(stream, limit=0):
            if not all(record.get(key) == value for key, value in filters.items() if value is not None):
                continue
            record_id = record.get(id_field)
            if record_id:
                latest[str(record_id)] = record
        return latest

    def upsert_snapshot(self, stream: str, id_field: str, record: dict[str, Any]) -> dict[str, Any]:
        """Append a snapshot record; readers use the latest record per id."""
        if id_field not in record:
            raise ValueError(f"Missing id field: {id_field}")
        return self.append(stream, record)

    def compact_snapshots(self, stream: str, id_field: str) -> dict[str, Any]:
        """
        Compact a snapshot stream to one latest record per id.

        Event streams should remain append-only; this helper is for streams such
        as runs, sessions, tasks, and approvals where latest-snapshot semantics
        are expected.
        """
        latest = self.latest_snapshots(stream, id_field)
        path = self.stream_path(stream)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with self._lock:
            with tmp_path.open("w", encoding="utf-8") as handle:
                for record in latest.values():
                    handle.write(
                        json.dumps(self.sanitize_for_stream(stream, record), ensure_ascii=False, default=str) + "\n"
                    )
            os.replace(tmp_path, path)
        return {
            "stream": stream,
            "records": len(latest),
            "path": str(path),
        }

    @classmethod
    def preview_text(cls, value: str) -> str:
        return value[:PREVIEW_CHARS] + TRUNCATION_MARKER if len(value) > LONG_STRING_LIMIT else value

    @classmethod
    def preview_metadata(cls, field_name: str, value: str) -> dict[str, Any]:
        return {
            f"{field_name}_preview": cls.preview_text(value),
            f"{field_name}_truncated": len(value) > LONG_STRING_LIMIT,
            f"{field_name}_length": len(value),
        }

    @classmethod
    def sanitize_for_stream(cls, stream: str, record: dict[str, Any]) -> dict[str, Any]:
        # Durable runs are execution inputs, not just observability events. Long
        # queries/history must survive round-trip so background workers and
        # recovery runs execute the same request that was submitted.
        cleaned = cls.sanitize(record, preserve_long_text=(stream == "runs"))
        if not isinstance(cleaned, dict):
            return cleaned

        if stream in {"run_events", "events"} and record.get("type") == "session_end":
            content = record.get("content")
            if isinstance(content, str):
                cleaned["content"] = content
                cleaned.update(cls.preview_metadata("content", content))

        if stream == "traces":
            final_content = record.get("final_content")
            if isinstance(final_content, str):
                cleaned["final_content"] = final_content
                cleaned.update(cls.preview_metadata("final_content", final_content))

        return cleaned

    @classmethod
    def sanitize(cls, value: Any, *, preserve_long_text: bool = False) -> Any:
        if isinstance(value, dict):
            cleaned = {}
            for key, inner in value.items():
                key_lower = str(key).lower()
                if key_lower in SAFE_TOKEN_USAGE_KEYS:
                    cleaned[key] = cls.sanitize(inner, preserve_long_text=preserve_long_text)
                elif any(secret in key_lower for secret in SENSITIVE_KEYS):
                    cleaned[key] = "***"
                else:
                    cleaned[key] = cls.sanitize(inner, preserve_long_text=preserve_long_text)
            return cleaned
        if isinstance(value, list):
            return [cls.sanitize(item, preserve_long_text=preserve_long_text) for item in value]
        if isinstance(value, str) and value.startswith("sk-"):
            return "***"
        if isinstance(value, str) and len(value) > LONG_STRING_LIMIT:
            return value if preserve_long_text else cls.preview_text(value)
        return value
