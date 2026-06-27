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
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


DIGEST_JOB_TYPE = "digest_via_fastreact"
DEFAULT_PSKA_URL = "http://127.0.0.1:8765"
DEFAULT_FASTREACT_URL = "http://127.0.0.1:8000"
DEFAULT_KEY_FILE = Path.home() / "api_key.txt"
DEFAULT_TENANT_ID = "tenant_default"
PROMPT_SOURCE_ITEM_LIMIT = 3
PROMPT_DOCUMENT_LIMIT = 3
PROMPT_PASSAGE_LIMIT = 6
PROMPT_CHUNK_LIMIT = 6
PROMPT_SOURCE_TEXT_CHARS = 1200
PROMPT_DOCUMENT_TEXT_CHARS = 12000
PROMPT_PASSAGE_TEXT_CHARS = 8000
PROMPT_CHUNK_TEXT_CHARS = 900


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
    batch_limit: int = 1
    tenant_id: str = DEFAULT_TENANT_ID
    represented_user_id: str = "user_primary"
    timeout_seconds: float = 90.0
    run_timeout_seconds: float = 900.0
    run_poll_interval_seconds: float = 2.0


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
            tool_budget = _digest_tool_budget_summary(response)
            fastreact_runs.append(
                {
                    "run_id": response.get("run_id"),
                    "batch_cursor": batch.get("cursor"),
                    "next_cursor": batch.get("next_cursor"),
                    "content": response.get("content"),
                    "tool_calls": response.get("tool_calls") or [],
                    **tool_budget,
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
    compact_batch = _compact_batch_for_prompt(batch)
    prompt = (
        "Execute exactly one PSKA digest batch and then stop.\n"
        f"PSKA job_id: {job_id}\n"
        f"Batch cursor: {batch.get('cursor')}\n"
        "Allowed tools: pska_pska_job_context and pska_pska_write_candidates only. "
        "Do not use built-in tools such as exec, read_file, write_file, or edit_file. "
        "Do not inspect local code, local files, package modules, or environment state.\n"
        "Tool budget for this batch: pska_pska_write_candidates <= 1 and pska_pska_job_context <= 1. "
        "Required flow: first call pska_pska_job_context with job_id, max_document_chars=48000, "
        "max_passage_chars=24000, max_passage_windows=4, max_chunk_chars=1200, max_chunks=6. Use returned documents and "
        "passage_windows as the primary evidence; chunks are retrieval slices only. "
        "Then perform agentic offline processing in two phases: (1) Knowledge Extraction into readable "
        "knowledge_claims/facts with evidence, and (2) Digest synthesis into digest_notes, actions, risks, "
        "questions, memory suggestions, and relationship suggestions. "
        "If there is useful grounded knowledge, call pska_pska_write_candidates exactly once or not at all. "
        "When you need to write multiple candidate categories, combine them into that single pska_pska_write_candidates payload. "
        "The one payload may contain knowledge_claims, digest_notes, entities, memory_candidates, review_items, hyperedges, summaries, and source_refs together. "
        "Merge all digest_notes, knowledge_claims, summaries, memory_candidates, review_items, and action candidates into one pska_pska_write_candidates payload. "
        "Do not split write calls by candidate category, source, confidence, or citation group. "
        "A second pska_pska_write_candidates call is invalid even if it writes a different candidate type. "
        "Every candidate must include schema_version='pska.candidates.v1', job_id, source_refs, confidence, and producer='fastreact'. "
        "Prefer readable knowledge_claims first: each claim needs claim_type, statement, evidence_text, source_refs, and confidence. "
        "Use Chinese for user-facing statement/synopsis/summary fields by default. "
        "Every claim should cite the narrowest source_refs available, ideally passage_window_id or document_id. "
        "Do not write digest_notes, hyperedges, or relationship_suggestions unless the same payload also includes at least one knowledge_claim. "
        "Then write digest_notes with title, synopsis, key_points, actions, open_questions, risks, memory_suggestions, relationship_suggestions, and source_refs when useful. "
        "Use valid PSKA candidate fields: entities require entity_type and label; memory_candidates require kind='agent_memory' and text; "
        "review_items require review_type, title, and proposal; hyperedges require relation_type and at least two members with entity_type, label, and role. "
        "For simple single-fact digest batches, prefer one readable knowledge_claim and one digest_note; only add memory_candidates/entities/hyperedges if they are genuinely useful. "
        "If you write a hyperedge or relationship suggestion, also write at least one knowledge_claim that explains the source statement it formalizes. "
        "Do not use name/content/source/memory_id for memory candidates. "
        "Low-confidence, sensitive, or high-impact suggestions must be review_items, not direct memory writes. "
        "If there is no useful candidate, do not call tools; return a short final JSON summary. "
        "After the optional write call, return a short final JSON summary and stop.\n\n"
        f"Batch context JSON:\n{json.dumps(compact_batch, ensure_ascii=False)}"
    )
    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are FastReAct executing a constrained PSKA digest worker. "
                    "Use only PSKA MCP tools named in the user message. Never use local shell or file tools. "
                    "One digest batch may make at most one pska_pska_write_candidates call; all candidate categories must be merged into that one payload."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "skills": ["pska_digest"],
        "user_key": f"pska:{config.represented_user_id}",
        "metadata": {
            "caller": "pska_digest_worker",
            "purpose": "digest",
            "tenant_key": config.tenant_id,
            "pska_tenant_id": config.tenant_id,
            "pska_user_id": config.represented_user_id,
            "pska_job_id": job_id,
            "max_context_tokens": 128000,
            "scope": {"job_id": job_id, "cursor": batch.get("cursor")},
            "tool_budget": {
                "pska_pska_write_candidates": 1,
                "pska_pska_job_context": 1,
            },
        },
    }
    created = http.request_json(
        "POST",
        f"{config.fastreact_url.rstrip('/')}/v1/runs",
        payload=payload,
        headers=_fastreact_headers(config),
    )
    run_id = str(created.get("run_id") or "")
    if not run_id:
        raise WorkerError("FastReAct /v1/runs response missing run_id")
    snapshot = _wait_for_run(config, run_id, http=http)
    events_payload = http.request_json(
        "GET",
        f"{config.fastreact_url.rstrip('/')}/v1/runs/{run_id}/events",
        headers=_fastreact_headers(config),
    )
    events = events_payload.get("events") if isinstance(events_payload.get("events"), list) else []
    return {
        "type": "run",
        "run_id": run_id,
        "status": snapshot.get("status"),
        "content": _final_content(events),
        "events": events,
        "tool_calls": _summarize_tool_calls(events),
        "metadata": snapshot.get("metadata") or {},
    }


def _compact_batch_for_prompt(batch: dict[str, Any]) -> dict[str, Any]:
    """Keep the prompt focused so the agent writes grounded candidates instead of exploring."""
    compact = {
        "cursor": batch.get("cursor"),
        "next_cursor": batch.get("next_cursor"),
        "has_more": batch.get("has_more"),
        "job": batch.get("job"),
        "source_items": [],
        "documents": [],
        "passage_windows": [],
        "chunks": [],
        "limits": {
            "source_items": PROMPT_SOURCE_ITEM_LIMIT,
            "documents": PROMPT_DOCUMENT_LIMIT,
            "passage_windows": PROMPT_PASSAGE_LIMIT,
            "chunks": PROMPT_CHUNK_LIMIT,
            "source_text_chars": PROMPT_SOURCE_TEXT_CHARS,
            "document_text_chars": PROMPT_DOCUMENT_TEXT_CHARS,
            "passage_text_chars": PROMPT_PASSAGE_TEXT_CHARS,
            "chunk_text_chars": PROMPT_CHUNK_TEXT_CHARS,
        },
        "input_strategy": "document_first_agentic_digest",
    }
    source_items = [item for item in batch.get("source_items") or [] if isinstance(item, dict)]
    for item in source_items[:PROMPT_SOURCE_ITEM_LIMIT]:
        text = str(item.get("content_text") or item.get("text") or item.get("content") or "")
        compact["source_items"].append(
            {
                "source_item_id": item.get("source_item_id"),
                "source_channel": item.get("source_channel"),
                "record_type": item.get("record_type"),
                "source_id": item.get("source_id"),
                "title": item.get("title"),
                "url": item.get("url"),
                "path": _source_path(item),
                "created_at": item.get("created_at"),
                "content_text": _truncate(text, PROMPT_SOURCE_TEXT_CHARS),
                "content_chars": len(text),
            }
        )
    if len(source_items) > PROMPT_SOURCE_ITEM_LIMIT:
        compact["source_items_truncated"] = len(source_items) - PROMPT_SOURCE_ITEM_LIMIT
    documents = [document for document in batch.get("documents") or [] if isinstance(document, dict)]
    for document in documents[:PROMPT_DOCUMENT_LIMIT]:
        text = str(document.get("body") or document.get("text") or document.get("content") or "")
        compact["documents"].append(
            {
                "document_id": document.get("document_id"),
                "source_item_id": document.get("source_item_id"),
                "title": document.get("title"),
                "mime_type": document.get("mime_type"),
                "body": _truncate(text, PROMPT_DOCUMENT_TEXT_CHARS),
                "body_chars": len(text),
            }
        )
    if len(documents) > PROMPT_DOCUMENT_LIMIT:
        compact["documents_truncated"] = len(documents) - PROMPT_DOCUMENT_LIMIT
    passage_windows = [window for window in batch.get("passage_windows") or [] if isinstance(window, dict)]
    for window in passage_windows[:PROMPT_PASSAGE_LIMIT]:
        text = str(window.get("text") or window.get("content") or "")
        compact["passage_windows"].append(
            {
                "passage_window_id": window.get("passage_window_id"),
                "source_item_id": window.get("source_item_id"),
                "document_id": window.get("document_id"),
                "ordinal": window.get("ordinal"),
                "title": window.get("title"),
                "text": _truncate(text, PROMPT_PASSAGE_TEXT_CHARS),
                "text_chars": len(text),
                "token_estimate": window.get("token_estimate"),
            }
        )
    if len(passage_windows) > PROMPT_PASSAGE_LIMIT:
        compact["passage_windows_truncated"] = len(passage_windows) - PROMPT_PASSAGE_LIMIT
    chunks = [chunk for chunk in batch.get("chunks") or [] if isinstance(chunk, dict)]
    for chunk in chunks[:PROMPT_CHUNK_LIMIT]:
        if not isinstance(chunk, dict):
            continue
        text = str(chunk.get("text") or chunk.get("content") or "")
        compact["chunks"].append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "source_item_id": chunk.get("source_item_id"),
                "document_id": chunk.get("document_id"),
                "ordinal": chunk.get("ordinal"),
                "text": _truncate(text, PROMPT_CHUNK_TEXT_CHARS),
                "text_chars": len(text),
            }
        )
    if len(chunks) > PROMPT_CHUNK_LIMIT:
        compact["chunks_truncated"] = len(chunks) - PROMPT_CHUNK_LIMIT
    return compact


def _source_path(item: dict[str, Any]) -> str | None:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    raw_paths = metadata.get("raw_paths") if isinstance(metadata.get("raw_paths"), dict) else {}
    path = raw_paths.get("markdown") or raw_paths.get("original") or item.get("path")
    return str(path) if path else None


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 24)].rstrip() + "\n...[truncated]"


def _raise_on_fastreact_error(response: dict[str, Any]) -> None:
    if response.get("status") in {"failed", "cancelled", "expired"}:
        raise WorkerError(f"FastReAct run ended with status {response.get('status')}")
    errors = [event for event in response.get("events") or [] if isinstance(event, dict) and event.get("type") == "error"]
    if errors:
        raise WorkerError(str(errors[-1].get("content") or "FastReAct digest run failed"))
    forbidden = [
        str(event.get("tool_name"))
        for event in response.get("events") or []
        if isinstance(event, dict)
        and event.get("type") == "tool_call"
        and str(event.get("tool_name") or "") in {"exec", "read_file", "write_file", "edit_file"}
    ]
    if forbidden:
        raise WorkerError(f"FastReAct digest used forbidden tools: {', '.join(forbidden)}")
    budget = _digest_tool_budget_summary(response)
    if budget["tool_budget_exceeded"]:
        raise WorkerError(
            "FastReAct digest exceeded tool budget: "
            f"pska_pska_write_candidates={budget['write_call_count']} "
            f"(max {budget['tool_budget']['pska_pska_write_candidates']}), "
            f"pska_pska_job_context={budget['job_context_call_count']} "
            f"(max {budget['tool_budget']['pska_pska_job_context']})"
        )
    if _validation_rejected_call_ids(response) and not budget["write_call_count"]:
        raise WorkerError("FastReAct candidate payload failed validation and was not repaired")
    if budget["job_context_call_count"] and not budget["write_call_count"] and _looks_like_unresolved_context_failure(response):
        raise WorkerError("FastReAct could not obtain usable PSKA job context and wrote no candidates")
    if budget["write_call_count"] and _candidate_count(response) == 0:
        raise WorkerError("FastReAct called pska_write_candidates without any candidates")
    if _wrote_digest_or_relationship_without_claims(response):
        raise WorkerError("FastReAct wrote digest or relationship candidates without knowledge_claims")


def _wait_for_run(config: DigestWorkerConfig, run_id: str, *, http: JsonHttpClient) -> dict[str, Any]:
    deadline = time.monotonic() + config.run_timeout_seconds
    while time.monotonic() < deadline:
        snapshot = http.request_json(
            "GET",
            f"{config.fastreact_url.rstrip('/')}/v1/runs/{run_id}",
            headers=_fastreact_headers(config),
        )
        status = snapshot.get("status")
        if status in {"completed", "failed", "cancelled", "expired"}:
            return snapshot
        time.sleep(config.run_poll_interval_seconds)
    raise WorkerError(f"FastReAct run {run_id} timed out after {config.run_timeout_seconds:g}s")


def _final_content(events: list[Any]) -> str:
    for event in reversed(events):
        if not isinstance(event, dict):
            continue
        if event.get("type") in {"session_end", "step_end"} and event.get("content"):
            return str(event["content"])
    return ""


def _summarize_tool_calls(events: list[Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict) or event.get("type") != "tool_call":
            continue
        args = event.get("tool_args") if isinstance(event.get("tool_args"), dict) else {}
        summaries.append(
            {
                "sequence": event.get("sequence"),
                "tool_name": event.get("tool_name"),
                "tool_call_id": event.get("tool_call_id"),
                "schema": event.get("schema"),
                "run_id": event.get("run_id"),
                "request_id": args.get("request_id"),
                "job_id": args.get("job_id"),
                "source_ref_count": len(args.get("source_refs") or []) if isinstance(args.get("source_refs"), list) else 0,
                "knowledge_claim_count": len(args.get("knowledge_claims") or [])
                if isinstance(args.get("knowledge_claims"), list)
                else 0,
                "digest_note_count": len(args.get("digest_notes") or [])
                if isinstance(args.get("digest_notes"), list)
                else 0,
                "entity_count": len(args.get("entities") or []) if isinstance(args.get("entities"), list) else 0,
                "hyperedge_count": len(args.get("hyperedges") or []) if isinstance(args.get("hyperedges"), list) else 0,
                "review_item_count": len(args.get("review_items") or []) if isinstance(args.get("review_items"), list) else 0,
                "memory_candidate_count": len(args.get("memory_candidates") or [])
                if isinstance(args.get("memory_candidates"), list)
                else 0,
            }
        )
    return summaries


def _digest_tool_budget_summary(response: dict[str, Any]) -> dict[str, Any]:
    write_count = _count_effective_tool_calls(response, "pska_pska_write_candidates")
    job_context_count = _count_tool_calls(response, "pska_pska_job_context")
    return {
        "write_call_count": write_count,
        "job_context_call_count": job_context_count,
        "tool_budget": {
            "pska_pska_write_candidates": 1,
            "pska_pska_job_context": 1,
        },
        "tool_budget_exceeded": write_count > 1 or job_context_count > 1,
    }


def _candidate_count(response: dict[str, Any]) -> int:
    total = 0
    for call in response.get("tool_calls") or []:
        if not isinstance(call, dict) or call.get("tool_name") != "pska_pska_write_candidates":
            continue
        for key in [
            "knowledge_claim_count",
            "digest_note_count",
            "entity_count",
            "hyperedge_count",
            "review_item_count",
            "memory_candidate_count",
        ]:
            total += int(call.get(key) or 0)
    return total


def _wrote_digest_or_relationship_without_claims(response: dict[str, Any]) -> bool:
    claim_count = 0
    digest_or_relationship_count = 0
    for call in response.get("tool_calls") or []:
        if not isinstance(call, dict) or call.get("tool_name") != "pska_pska_write_candidates":
            continue
        claim_count += int(call.get("knowledge_claim_count") or 0)
        digest_or_relationship_count += int(call.get("digest_note_count") or 0)
        digest_or_relationship_count += int(call.get("hyperedge_count") or 0)
    return digest_or_relationship_count > 0 and claim_count == 0


def _looks_like_unresolved_context_failure(response: dict[str, Any]) -> bool:
    text_parts = [str(response.get("content") or "")]
    for event in response.get("events") or []:
        if not isinstance(event, dict):
            continue
        if event.get("type") in {"tool_result", "error", "session_end", "step_end"}:
            text_parts.append(str(event.get("content") or event.get("result") or ""))
    text = "\n".join(part for part in text_parts if part).lower()
    if not text:
        return False
    failure_terms = [
        "pska_job_context",
        "context",
        "chunk",
        "chunk size",
        "separator",
        "limit",
        "retry",
        "failed",
        "failure",
        "error",
        "上下文",
        "分块",
        "块分割",
        "失败",
        "错误",
        "重试",
        "回退",
    ]
    return any(term in text for term in failure_terms)


def _count_tool_calls(response: dict[str, Any], tool_name: str) -> int:
    return sum(1 for call in response.get("tool_calls") or [] if isinstance(call, dict) and call.get("tool_name") == tool_name)


def _count_effective_tool_calls(response: dict[str, Any], tool_name: str) -> int:
    validation_rejected_call_ids = _validation_rejected_call_ids(response)
    count = 0
    for call in response.get("tool_calls") or []:
        if not isinstance(call, dict) or call.get("tool_name") != tool_name:
            continue
        call_id = str(call.get("tool_call_id") or "")
        if call_id and call_id in validation_rejected_call_ids:
            continue
        count += 1
    return count


def _validation_rejected_call_ids(response: dict[str, Any]) -> set[str]:
    rejected: set[str] = set()
    for event in response.get("events") or []:
        if not isinstance(event, dict) or event.get("type") != "tool_result":
            continue
        if not event.get("digest_validation_error"):
            metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
            if not metadata.get("digest_validation_error"):
                continue
        request_id = event.get("request_id")
        if request_id is None:
            metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
            request_id = metadata.get("request_id")
        if request_id:
            rejected.add(str(request_id))
    return rejected


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
    headers: dict[str, str] = {
        "X-PSKA-Caller": "agent_service",
        "X-PSKA-Tenant-Id": config.tenant_id,
        "X-PSKA-User-Id": config.represented_user_id,
        "X-PSKA-Represented-User-Id": config.represented_user_id,
    }
    if config.pska_service_token:
        headers["X-PSKA-Service-Token"] = config.pska_service_token
    return headers


def _fastreact_headers(config: DigestWorkerConfig) -> dict[str, str]:
    headers = {
        "X-FastReAct-Tenant-Key": config.tenant_id,
        "X-FastReAct-User-Key": f"pska:{config.represented_user_id}",
    }
    if config.fastreact_service_token:
        headers["X-FastReAct-Service-Token"] = config.fastreact_service_token
    return headers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pska-url", default=DEFAULT_PSKA_URL)
    parser.add_argument("--fastreact-url", default=DEFAULT_FASTREACT_URL)
    parser.add_argument("--job-id")
    parser.add_argument("--worker-id", default=f"fastreact-pska-digest-{uuid4().hex[:8]}")
    parser.add_argument("--tenant-id", default=os.getenv("PSKA_TENANT_ID") or DEFAULT_TENANT_ID)
    parser.add_argument("--represented-user-id", default="user_primary")
    parser.add_argument("--lease-seconds", type=int, default=300)
    parser.add_argument("--batch-limit", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=float, default=90)
    parser.add_argument("--run-timeout-seconds", type=float, default=900)
    parser.add_argument("--run-poll-interval-seconds", type=float, default=2)
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
        tenant_id=args.tenant_id,
        represented_user_id=args.represented_user_id,
        timeout_seconds=args.timeout_seconds,
        run_timeout_seconds=args.run_timeout_seconds,
        run_poll_interval_seconds=args.run_poll_interval_seconds,
    )
    result = run_once(config, job_id=args.job_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
