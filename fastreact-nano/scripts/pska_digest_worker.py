#!/usr/bin/env python3
"""Lease and execute PSKA digest jobs through FastReAct.

This worker is intentionally outside PSKA. PSKA owns durable jobs, ACL,
source refs, and candidate persistence. FastReAct owns the agentic digest loop.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


DIGEST_JOB_TYPE = "digest_via_fastreact"
DEFAULT_PSKA_URL = "http://127.0.0.1:8765"
DEFAULT_FASTREACT_URL = "http://127.0.0.1:8000"
DEFAULT_KEY_FILE = Path.home() / "api_key.txt"


class WorkerError(RuntimeError):
    """Raised when a PSKA digest worker step fails."""


@dataclass(slots=True)
class DigestWorkerConfig:
    pska_url: str = DEFAULT_PSKA_URL
    fastreact_url: str = DEFAULT_FASTREACT_URL
    pska_service_token: str | None = None
    fastreact_service_token: str | None = None
    worker_id: str = "fastreact-pska-digest-worker"
    lease_seconds: int = 300
    batch_limit: int = 20
    represented_user_id: str = "user_primary"
    timeout_seconds: float = 90.0


class JsonHttpClient:
    def __init__(self, *, timeout_seconds: float = 90.0) -> None:
        self.timeout_seconds = timeout_seconds

    def request_json(
        self,
        method: str,
        url: str,
        *,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers = {"accept": "application/json", **(headers or {})}
        if data is not None:
            request_headers["content-type"] = "application/json; charset=utf-8"
        request = Request(url, data=data, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise WorkerError(f"{method} {url} failed with HTTP {exc.code}: {detail}") from exc
        except (TimeoutError, URLError) as exc:
            raise WorkerError(f"{method} {url} unavailable: {exc}") from exc
        try:
            parsed = json.loads(body or "{}")
        except json.JSONDecodeError as exc:
            raise WorkerError(f"{method} {url} returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise WorkerError(f"{method} {url} returned non-object JSON")
        return parsed


def run_once(config: DigestWorkerConfig, *, job_id: str | None = None, http: JsonHttpClient | None = None) -> dict[str, Any]:
    http = http or JsonHttpClient(timeout_seconds=config.timeout_seconds)
    if job_id is None:
        job_id = find_ready_digest_job(config, http=http)
    if job_id is None:
        return {"ok": True, "processed": 0, "reason": "no_ready_digest_job"}
    return run_digest_job(config, job_id, http=http)


def find_ready_digest_job(config: DigestWorkerConfig, *, http: JsonHttpClient) -> str | None:
    payload = http.request_json("GET", f"{config.pska_url.rstrip('/')}/jobs", headers=_pska_headers(config))
    jobs = payload.get("jobs") if isinstance(payload.get("jobs"), list) else []
    ready = [job for job in jobs if _is_ready_digest_job(job)]
    if not ready:
        return None
    ready.sort(key=lambda job: (-int(job.get("priority") or 0), str(job.get("run_after") or ""), str(job.get("created_at") or "")))
    return str(ready[0]["job_id"])


def run_digest_job(config: DigestWorkerConfig, job_id: str, *, http: JsonHttpClient) -> dict[str, Any]:
    leased = _lease_job(config, job_id, http=http)
    fastreact_runs: list[dict[str, Any]] = []
    cursor: str | None = "0"
    batch_count = 0
    try:
        while True:
            batch = _get_digest_batch(config, job_id, cursor=cursor, http=http)
            if not batch.get("source_items"):
                break
            batch_count += 1
            response = _run_fastreact_digest(config, job_id, batch, http=http)
            _raise_on_fastreact_error(response)
            fastreact_runs.append(
                {
                    "run_id": response.get("run_id"),
                    "batch_cursor": batch.get("cursor"),
                    "next_cursor": batch.get("next_cursor"),
                    "content": response.get("content"),
                    "tool_calls": response.get("tool_calls") or [],
                }
            )
            if not batch.get("has_more"):
                break
            cursor = str(batch.get("next_cursor") or "")
        result = {
            "ok": True,
            "worker_id": config.worker_id,
            "leased_job": leased.get("job", {}),
            "batch_count": batch_count,
            "fastreact_runs": fastreact_runs,
        }
        completed = http.request_json(
            "POST",
            f"{config.pska_url.rstrip('/')}/jobs/{job_id}/complete",
            payload={"result": result},
            headers=_pska_headers(config),
        )
        return {"ok": True, "processed": 1, "job": completed.get("job"), "result": result}
    except Exception as exc:
        failure = http.request_json(
            "POST",
            f"{config.pska_url.rstrip('/')}/jobs/{job_id}/fail",
            payload={"error": f"{type(exc).__name__}: {exc}", "retryable": True},
            headers=_pska_headers(config),
        )
        return {"ok": False, "processed": 1, "job": failure.get("job"), "error": str(exc)}


def read_service_token(path: Path) -> str | None:
    if not path.expanduser().exists():
        return None
    text = path.expanduser().read_text(encoding="utf-8").strip()
    if not text:
        return None
    if text.startswith("{"):
        data = json.loads(text)
        return str(data.get("service_token") or data.get("fastreact_service_token") or "").strip() or None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[3] if len(lines) > 3 else None


def _lease_job(config: DigestWorkerConfig, job_id: str, *, http: JsonHttpClient) -> dict[str, Any]:
    return http.request_json(
        "POST",
        f"{config.pska_url.rstrip('/')}/jobs/{job_id}/lease",
        payload={"worker_id": config.worker_id, "lease_seconds": config.lease_seconds},
        headers=_pska_headers(config),
    )


def _get_digest_batch(config: DigestWorkerConfig, job_id: str, *, cursor: str | None, http: JsonHttpClient) -> dict[str, Any]:
    query = urlencode({"cursor": cursor or "0", "limit": str(config.batch_limit)})
    return http.request_json(
        "GET",
        f"{config.pska_url.rstrip('/')}/digest/batches/{job_id}?{query}",
        headers=_pska_headers(config),
    )


def _run_fastreact_digest(
    config: DigestWorkerConfig,
    job_id: str,
    batch: dict[str, Any],
    *,
    http: JsonHttpClient,
) -> dict[str, Any]:
    prompt = (
        "Execute one PSKA digest batch.\n"
        f"PSKA job_id: {job_id}\n"
        f"Batch cursor: {batch.get('cursor')}\n"
        "Use PSKA MCP tools only. Prefer pska_pska_job_context for context verification and "
        "pska_pska_write_candidates for grounded writes. Any write must include "
        "schema_version='pska.candidates.v1', job_id, source_refs, confidence, and producer='fastreact'. "
        "Low-confidence, sensitive, or high-impact suggestions must be review_items, not direct memory writes.\n\n"
        f"Batch context JSON:\n{json.dumps(batch, ensure_ascii=False)}"
    )
    return http.request_json(
        "POST",
        f"{config.fastreact_url.rstrip('/')}/v1/chat/completions",
        payload={
            "messages": [
                {"role": "system", "content": "You are FastReAct executing a PSKA digest worker loop."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "skills": ["pska_digest"],
            "user_key": f"pska:{config.represented_user_id}",
            "metadata": {
                "caller": "pska_digest_worker",
                "purpose": "digest",
                "pska_user_id": config.represented_user_id,
                "pska_job_id": job_id,
                "scope": {"job_id": job_id, "cursor": batch.get("cursor")},
            },
        },
        headers=_fastreact_headers(config),
    )


def _raise_on_fastreact_error(response: dict[str, Any]) -> None:
    errors = [event for event in response.get("events") or [] if isinstance(event, dict) and event.get("type") == "error"]
    if errors:
        raise WorkerError(str(errors[-1].get("content") or "FastReAct digest run failed"))


def _is_ready_digest_job(job: Any) -> bool:
    if not isinstance(job, dict):
        return False
    if job.get("job_type") != DIGEST_JOB_TYPE or job.get("status") != "queued":
        return False
    run_after = _parse_time(job.get("run_after"))
    return run_after is None or run_after <= datetime.now(timezone.utc)


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _pska_headers(config: DigestWorkerConfig) -> dict[str, str]:
    headers: dict[str, str] = {"X-PSKA-Caller": "agent_service", "X-PSKA-Represented-User-Id": config.represented_user_id}
    if config.pska_service_token:
        headers["X-PSKA-Service-Token"] = config.pska_service_token
    return headers


def _fastreact_headers(config: DigestWorkerConfig) -> dict[str, str]:
    return {"X-FastReAct-Service-Token": config.fastreact_service_token} if config.fastreact_service_token else {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pska-url", default=DEFAULT_PSKA_URL)
    parser.add_argument("--fastreact-url", default=DEFAULT_FASTREACT_URL)
    parser.add_argument("--job-id")
    parser.add_argument("--worker-id", default=f"fastreact-pska-digest-{uuid4().hex[:8]}")
    parser.add_argument("--represented-user-id", default="user_primary")
    parser.add_argument("--lease-seconds", type=int, default=300)
    parser.add_argument("--batch-limit", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=float, default=90)
    parser.add_argument("--service-token")
    parser.add_argument("--pska-service-token")
    parser.add_argument("--fastreact-service-token")
    parser.add_argument("--api-key-file", type=Path, default=DEFAULT_KEY_FILE)
    args = parser.parse_args()

    token = args.service_token or read_service_token(args.api_key_file)
    config = DigestWorkerConfig(
        pska_url=args.pska_url,
        fastreact_url=args.fastreact_url,
        pska_service_token=args.pska_service_token or os.getenv("PSKA_SERVICE_TOKEN") or token,
        fastreact_service_token=args.fastreact_service_token or os.getenv("FASTREACT_SERVICE_TOKEN") or token,
        worker_id=args.worker_id,
        lease_seconds=args.lease_seconds,
        batch_limit=args.batch_limit,
        represented_user_id=args.represented_user_id,
        timeout_seconds=args.timeout_seconds,
    )
    result = run_once(config, job_id=args.job_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
