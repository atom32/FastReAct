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
            {"type": "chat.completion", "run_id": "run_1", "content": "batch one", "events": [], "tool_calls": []},
            {
                "cursor": "1",
                "next_cursor": None,
                "has_more": False,
                "source_items": [{"source_item_id": "src_2", "title": "Two"}],
                "chunks": [{"chunk_id": "chk_2", "source_item_id": "src_2", "text": "two"}],
            },
            {"type": "chat.completion", "run_id": "run_2", "content": "batch two", "events": [], "tool_calls": []},
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
    chat_calls = [call for call in http.calls if call["url"].endswith("/v1/chat/completions")]
    assert len(chat_calls) == 2
    assert chat_calls[0]["payload"]["skills"] == ["pska_digest"]
    assert chat_calls[0]["payload"]["metadata"]["pska_job_id"] == "job_digest"
    assert "pska.candidates.v1" in chat_calls[0]["payload"]["messages"][1]["content"]
    complete_call = http.calls[-1]
    assert complete_call["url"] == "http://pska.test/jobs/job_digest/complete"
    assert complete_call["payload"]["result"]["fastreact_runs"][0]["run_id"] == "run_1"


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
            {"type": "chat.completion", "run_id": "run_bad", "content": "", "events": [{"type": "error", "content": "boom"}]},
            {"job": {"job_id": "job_digest", "status": "queued", "error": "boom"}},
        ]
    )

    result = worker.run_digest_job(worker.DigestWorkerConfig(pska_url="http://pska.test", fastreact_url="http://fastreact.test"), "job_digest", http=http)

    assert result["ok"] is False
    assert http.calls[-1]["url"] == "http://pska.test/jobs/job_digest/fail"
    assert http.calls[-1]["payload"]["retryable"] is True
    assert "boom" in http.calls[-1]["payload"]["error"]
