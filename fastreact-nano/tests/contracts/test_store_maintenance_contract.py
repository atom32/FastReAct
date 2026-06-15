from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys

from fastreact.runtime.store_service import StoreService


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "store_maintenance.py"
SPEC = importlib.util.spec_from_file_location("store_maintenance", SCRIPT_PATH)
maintenance = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = maintenance
SPEC.loader.exec_module(maintenance)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_compact_store_applies_snapshot_and_time_retention(tmp_path):
    store = StoreService(tmp_path / ".fastreact")
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    recent = datetime.now(timezone.utc).isoformat()
    store.append("runs", {"run_id": "run-1", "status": "queued", "created_at": old})
    store.append("runs", {"run_id": "run-1", "status": "completed", "created_at": recent})
    store.append("run_events", {"run_id": "run-old", "type": "session_end", "created_at": old})
    store.append("run_events", {"run_id": "run-new", "type": "session_end", "created_at": recent})

    result = maintenance.compact_store(store, keep_last=5000, make_backup=False, retain_days=7)

    assert result["streams"]["runs"] == {"before": 2, "after": 1, "removed": 1}
    assert result["streams"]["run_events"] == {"before": 2, "after": 1, "removed": 1}
    assert read_jsonl(store.stream_path("runs"))[0]["status"] == "completed"
    assert read_jsonl(store.stream_path("run_events"))[0]["run_id"] == "run-new"


def test_compact_store_dry_run_reports_without_writing(tmp_path):
    store = StoreService(tmp_path / ".fastreact")
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    store.append("run_events", {"run_id": "run-old", "type": "session_end", "created_at": old})

    result = maintenance.compact_store(store, keep_last=5000, make_backup=False, retain_days=7, dry_run=True)

    assert result["dry_run"] is True
    assert result["streams"]["run_events"]["removed"] == 1
    assert len(read_jsonl(store.stream_path("run_events"))) == 1
