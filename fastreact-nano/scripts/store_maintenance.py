#!/usr/bin/env python3
"""Maintain FastReAct JSONL control-plane stores."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastreact.core.config import Config  # noqa: E402
from fastreact.core.time import utc_iso  # noqa: E402
from fastreact.runtime.store_service import StoreService  # noqa: E402

SNAPSHOT_ID_FIELDS = {
    "sessions": "session_id",
    "tasks": "task_id",
    "runs": "run_id",
    "traces": "run_id",
    "approvals": "request_id",
}

APPEND_ONLY_STREAMS = {
    "events",
    "run_events",
    "audit",
    "runtime_spans",
}

TIME_FIELDS = ("created_at", "timestamp", "completed_at", "updated_at")


def default_store_root() -> Path:
    config = Config.load()
    return Path(config.paths.gateway_workspace) / ".fastreact"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"_invalid_jsonl": line[:200]})
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    temp_path.replace(path)


def latest_snapshots(records: list[dict[str, Any]], id_field: str) -> list[dict[str, Any]]:
    latest: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for record in records:
        record_id = record.get(id_field)
        if not record_id:
            continue
        if record_id in latest:
            del latest[record_id]
        latest[str(record_id)] = record
    return list(latest.values())


def parse_record_time(record: dict[str, Any]) -> datetime | None:
    for field in TIME_FIELDS:
        value = record.get(field)
        if not value:
            continue
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def apply_time_retention(records: list[dict[str, Any]], retain_days: int, *, now: datetime | None = None) -> list[dict[str, Any]]:
    if retain_days <= 0:
        return records
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retain_days)
    retained: list[dict[str, Any]] = []
    for record in records:
        record_time = parse_record_time(record)
        if record_time is None or record_time >= cutoff:
            retained.append(record)
    return retained


def backup_store(store_root: Path, backup_dir: Path | None = None) -> Path:
    timestamp = utc_iso().replace(":", "").replace("-", "").replace(".", "")
    target = backup_dir or store_root.parent / "backups" / f"store-{timestamp}"
    target.mkdir(parents=True, exist_ok=False)
    for path in sorted(store_root.glob("*.jsonl")):
        shutil.copy2(path, target / path.name)
    return target


def export_store(store: StoreService, output: Path) -> None:
    payload = {
        "exported_at": utc_iso(),
        "store": store.stats(),
        "streams": {
            stream: read_jsonl(store.stream_path(stream))
            for stream in store.streams()
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def compact_store(store: StoreService, keep_last: int, make_backup: bool, retain_days: int = 0, dry_run: bool = False) -> dict[str, Any]:
    backup_path = backup_store(store.root) if make_backup and not dry_run else None
    before = store.stats()
    changed: dict[str, dict[str, int]] = {}

    for stream in store.streams():
        path = store.stream_path(stream)
        records = read_jsonl(path)
        original_count = len(records)
        if stream in SNAPSHOT_ID_FIELDS:
            records = latest_snapshots(records, SNAPSHOT_ID_FIELDS[stream])
        elif stream in APPEND_ONLY_STREAMS:
            records = apply_time_retention(records, retain_days)
        elif keep_last > 0 and len(records) > keep_last:
            records = records[-keep_last:]
        if not dry_run:
            write_jsonl(path, records)
        changed[stream] = {
            "before": original_count,
            "after": len(records),
            "removed": max(0, original_count - len(records)),
        }

    return {
        "backup": str(backup_path) if backup_path else None,
        "dry_run": dry_run,
        "retain_days": retain_days,
        "before": before,
        "after": before if dry_run else store.stats(),
        "streams": changed,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FastReAct JSONL store maintenance")
    parser.add_argument("--store-root", type=Path, default=None, help="Path to .fastreact JSONL store root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("stats", help="Print store statistics")

    backup = subparsers.add_parser("backup", help="Copy JSONL streams to a timestamped backup directory")
    backup.add_argument("--backup-dir", type=Path, default=None, help="Explicit backup directory")

    export = subparsers.add_parser("export", help="Export all streams as one JSON document")
    export.add_argument("--output", type=Path, required=True, help="Output JSON path")

    compact = subparsers.add_parser("compact", help="Compact snapshots and trim append-only streams")
    compact.add_argument("--keep-last", type=int, default=5000, help="Records to keep for non-snapshot streams")
    compact.add_argument("--retain-days", type=int, default=0, help="Drop append-only stream records older than this many days")
    compact.add_argument("--dry-run", action="store_true", help="Report compaction and retention changes without writing")
    compact.add_argument("--no-backup", action="store_true", help="Skip pre-compaction backup")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = StoreService(args.store_root or default_store_root())

    if args.command == "stats":
        print(json.dumps(store.stats(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "backup":
        target = backup_store(store.root, args.backup_dir)
        print(json.dumps({"backup": str(target)}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "export":
        export_store(store, args.output)
        print(json.dumps({"export": str(args.output)}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "compact":
        result = compact_store(store, keep_last=args.keep_last, make_backup=not args.no_backup, retain_days=args.retain_days, dry_run=args.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
