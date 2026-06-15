from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys


WORKER_PATH = Path(__file__).resolve().parents[2] / "scripts" / "pska_digest_worker.py"
SPEC = importlib.util.spec_from_file_location("pska_digest_worker", WORKER_PATH)
worker = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = worker
SPEC.loader.exec_module(worker)


class FakeHttp:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request_json(self, method, url, *, payload=None, headers=None):
        self.calls.append({"method": method, "url": url, "payload": payload, "headers": headers or {}})
        if not self.responses:
            raise AssertionError(f"unexpected request: {method} {url}")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_find_ready_digest_job_uses_priority_and_run_after():
    now = datetime.now(timezone.utc)
    http = FakeHttp(
        [
            {
                "jobs": [
                    {"job_id": "job_low", "job_type": "digest_via_fastreact", "status": "queued", "priority": 1, "run_after": now.isoformat()},
                    {
                        "job_id": "job_later",
                        "job_type": "digest_via_fastreact",
                        "status": "queued",
                        "priority": 99,
                        "run_after": (now + timedelta(hours=1)).isoformat(),
                    },
                    {"job_id": "job_high", "job_type": "digest_via_fastreact", "status": "queued", "priority": 10, "run_after": now.isoformat()},
                    {"job_id": "job_other", "job_type": "extract_via_fastreact", "status": "queued", "priority": 100, "run_after": now.isoformat()},
                ]
            }
        ]
    )

    job_id = worker.find_ready_digest_job(worker.DigestWorkerConfig(), http=http)

    assert job_id == "job_high"


def test_run_once_returns_noop_when_no_ready_digest_job():
    http = FakeHttp([{"jobs": []}])

    result = worker.run_once(worker.DigestWorkerConfig(), http=http)

    assert result == {"ok": True, "processed": 0, "reason": "no_ready_digest_job"}
    assert len(http.calls) == 1


def test_run_digest_job_leases_batches_runs_skill_and_completes():
    http = FakeHttp(
        [
            {"job": {"job_id": "job_digest", "status": "running"}},
            {
                "cursor": "0",
                "next_cursor": "1",
                "has_more": True,
                "source_items": [{"source_item_id": "src_1", "title": "One"}],
                "chunks": [{"chunk_id": "chk_1", "source_item_id": "src_1", "text": "one"}],
            },
            {"type": "run", "run_id": "run_1", "status": "queued"},
            {"type": "run", "run_id": "run_1", "status": "completed"},
            {
                "events": [
                    {
                        "schema": "fastreact.agent_event.v1",
                        "type": "tool_call",
                        "sequence": 1,
                        "run_id": "run_1",
                        "tool_name": "pska_pska_write_candidates",
                        "tool_call_id": "call_1",
                        "tool_args": {
                            "job_id": "job_digest",
                            "request_id": "batch-0",
                            "source_refs": [{"source_item_id": "src_1"}],
                            "entities": [{"entity_id": "ent_1"}],
                        },
                    },
                    {"type": "session_end", "content": "batch one"},
                ]
            },
            {
                "cursor": "1",
                "next_cursor": None,
                "has_more": False,
                "source_items": [{"source_item_id": "src_2", "title": "Two"}],
                "chunks": [{"chunk_id": "chk_2", "source_item_id": "src_2", "text": "two"}],
            },
            {"type": "run", "run_id": "run_2", "status": "queued"},
            {"type": "run", "run_id": "run_2", "status": "completed"},
            {"events": [{"type": "session_end", "content": "batch two"}]},
            {"job": {"job_id": "job_digest", "status": "succeeded"}},
        ]
    )
    config = worker.DigestWorkerConfig(
        pska_url="http://pska.test",
        fastreact_url="http://fastreact.test",
        pska_service_token="pska-token",
        fastreact_service_token="fr-token",
        worker_id="worker-test",
        batch_limit=1,
    )

    result = worker.run_digest_job(config, "job_digest", http=http)

    assert result["ok"] is True
    assert result["result"]["batch_count"] == 2
    run_calls = [call for call in http.calls if call["url"].endswith("/v1/runs") and call["method"] == "POST"]
    assert len(run_calls) == 2
    assert run_calls[0]["payload"]["skills"] == ["pska_digest"]
    assert run_calls[0]["payload"]["user_key"] == "pska:user_primary"
    assert run_calls[0]["payload"]["metadata"]["pska_job_id"] == "job_digest"
    assert "pska.candidates.v1" in run_calls[0]["payload"]["messages"][1]["content"]
    assert "Do not use built-in tools" in run_calls[0]["payload"]["messages"][1]["content"]
    assert "pska_pska_write_candidates <= 1" in run_calls[0]["payload"]["messages"][1]["content"]
    assert "Merge all summaries" in run_calls[0]["payload"]["messages"][1]["content"]
    assert "memory_candidates require kind='agent_memory' and text" in run_calls[0]["payload"]["messages"][1]["content"]
    assert "prefer exactly one memory_candidates item" in run_calls[0]["payload"]["messages"][1]["content"]
    complete_call = http.calls[-1]
    assert complete_call["url"] == "http://pska.test/jobs/job_digest/complete"
    first_run = complete_call["payload"]["result"]["fastreact_runs"][0]
    assert first_run["run_id"] == "run_1"
    assert first_run["write_call_count"] == 1
    assert first_run["job_context_call_count"] == 0
    assert first_run["tool_budget"]["pska_pska_write_candidates"] == 1
    assert first_run["tool_budget_exceeded"] is False
    tool_summary = first_run["tool_calls"][0]
    assert tool_summary["tool_name"] == "pska_pska_write_candidates"
    assert tool_summary["entity_count"] == 1
    assert "tool_args" not in tool_summary


def test_run_digest_job_fails_pska_when_fastreact_errors():
    http = FakeHttp(
        [
            {"job": {"job_id": "job_digest", "status": "running"}},
            {
                "cursor": "0",
                "next_cursor": None,
                "has_more": False,
                "source_items": [{"source_item_id": "src_1"}],
                "chunks": [],
            },
            {"type": "run", "run_id": "run_bad", "status": "queued"},
            {"type": "run", "run_id": "run_bad", "status": "completed"},
            {"events": [{"type": "error", "content": "boom"}]},
            {"job": {"job_id": "job_digest", "status": "queued", "error": "boom"}},
        ]
    )

    result = worker.run_digest_job(worker.DigestWorkerConfig(pska_url="http://pska.test", fastreact_url="http://fastreact.test"), "job_digest", http=http)

    assert result["ok"] is False
    assert http.calls[-1]["url"] == "http://pska.test/jobs/job_digest/fail"
    assert http.calls[-1]["payload"]["retryable"] is True
    assert "boom" in http.calls[-1]["payload"]["error"]


def test_run_digest_job_fails_pska_when_fastreact_uses_forbidden_tool():
    http = FakeHttp(
        [
            {"job": {"job_id": "job_digest", "status": "running"}},
            {
                "cursor": "0",
                "next_cursor": None,
                "has_more": False,
                "source_items": [{"source_item_id": "src_1"}],
                "chunks": [],
            },
            {"type": "run", "run_id": "run_bad", "status": "queued"},
            {"type": "run", "run_id": "run_bad", "status": "completed"},
            {"events": [{"type": "tool_call", "tool_name": "exec", "tool_args": {"command": "pwd"}}]},
            {"job": {"job_id": "job_digest", "status": "queued", "error": "forbidden"}},
        ]
    )

    result = worker.run_digest_job(worker.DigestWorkerConfig(pska_url="http://pska.test", fastreact_url="http://fastreact.test"), "job_digest", http=http)

    assert result["ok"] is False
    assert http.calls[-1]["url"] == "http://pska.test/jobs/job_digest/fail"
    assert "forbidden tools: exec" in http.calls[-1]["payload"]["error"]


def test_run_digest_job_fails_pska_when_fastreact_exceeds_tool_budget():
    http = FakeHttp(
        [
            {"job": {"job_id": "job_digest", "status": "running"}},
            {
                "cursor": "0",
                "next_cursor": None,
                "has_more": False,
                "source_items": [{"source_item_id": "src_1"}],
                "chunks": [],
            },
            {"type": "run", "run_id": "run_noisy", "status": "queued"},
            {"type": "run", "run_id": "run_noisy", "status": "completed"},
            {
                "events": [
                    {"type": "tool_call", "tool_name": "pska_pska_write_candidates", "tool_args": {"job_id": "job_digest"}},
                    {"type": "tool_call", "tool_name": "pska_pska_write_candidates", "tool_args": {"job_id": "job_digest"}},
                ]
            },
            {"job": {"job_id": "job_digest", "status": "queued", "error": "tool budget"}},
        ]
    )

    result = worker.run_digest_job(worker.DigestWorkerConfig(pska_url="http://pska.test", fastreact_url="http://fastreact.test"), "job_digest", http=http)

    assert result["ok"] is False
    assert http.calls[-1]["url"] == "http://pska.test/jobs/job_digest/fail"
    assert http.calls[-1]["payload"]["retryable"] is True
    assert "exceeded tool budget" in http.calls[-1]["payload"]["error"]
    assert "pska_pska_write_candidates=2" in http.calls[-1]["payload"]["error"]


def test_digest_tool_budget_summary_marks_duplicate_writes():
    summary = worker._digest_tool_budget_summary(
        {
            "tool_calls": [
                {"tool_name": "pska_pska_job_context"},
                {"tool_name": "pska_pska_write_candidates"},
                {"tool_name": "pska_pska_write_candidates"},
            ]
        }
    )

    assert summary["write_call_count"] == 2
    assert summary["job_context_call_count"] == 1
    assert summary["tool_budget"] == {
        "pska_pska_write_candidates": 1,
        "pska_pska_job_context": 1,
    }
    assert summary["tool_budget_exceeded"] is True
