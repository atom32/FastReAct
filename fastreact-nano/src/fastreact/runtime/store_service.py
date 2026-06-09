"""Append-only JSONL store for product control-plane data."""

import json
import threading
from pathlib import Path
from typing import Any, Optional

from fastreact.core.time import utc_iso


SENSITIVE_KEYS = {"api_key", "apikey", "token", "pat", "password", "secret", "authorization"}


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
        record = self.sanitize(record)
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

    def latest_by_id(self, stream: str, id_field: str, value: str) -> Optional[dict[str, Any]]:
        records = self.read(stream, limit=0)
        for record in reversed(records):
            if record.get(id_field) == value:
                return record
        return None

    def upsert_snapshot(self, stream: str, id_field: str, record: dict[str, Any]) -> dict[str, Any]:
        """Append a snapshot record; readers use the latest record per id."""
        if id_field not in record:
            raise ValueError(f"Missing id field: {id_field}")
        return self.append(stream, record)

    @classmethod
    def sanitize(cls, value: Any) -> Any:
        if isinstance(value, dict):
            cleaned = {}
            for key, inner in value.items():
                if any(secret in str(key).lower() for secret in SENSITIVE_KEYS):
                    cleaned[key] = "***"
                else:
                    cleaned[key] = cls.sanitize(inner)
            return cleaned
        if isinstance(value, list):
            return [cls.sanitize(item) for item in value]
        if isinstance(value, str) and (value.startswith("sk-") or len(value) > 1200):
            return value[:600] + "\n[... truncated ...]" if len(value) > 1200 else "***"
        return value
