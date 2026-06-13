from fastreact.adapters.http import (
    SERVICE_EVENT_SCHEMA_VERSION,
    configured_service_token,
    create_app,
    extract_history,
    extract_query,
    readiness_payload,
    service_event_payload,
    set_agent_for_testing,
    sse_frame,
    summarize_events,
)
from fastreact.core.events import AgentEvent


class FakeAgent:
    skills = {}

    async def run_event_stream(self, query, skills=None, session_id=None, history=None, user_key=None):
        yield AgentEvent.session_start(query, session_id, skills=skills)
        yield AgentEvent.tool_call("pska_search", {"query": query}, session_id, call_id="call-1")
        yield AgentEvent.tool_result("pska_search", "source evidence", session_id)
        yield AgentEvent.session_end(session_id, "final answer")

    async def run(self, query):
        return f"answer: {query}"

    def list_skills(self):
        return []

    def list_tools(self):
        return ["pska_search"]

    def list_mcp_tools(self):
        return ["pska_search"]

    def list_mcp_server_status(self):
        return [{"name": "pska", "alive": True}]

    async def ensure_mcp_loaded(self, required_skills=None):
        return {"loaded": True, "required_skills": required_skills}


class FakeApprovalExecutor:
    def __init__(self):
        self.records = {
            "approval-123": {
                "request_id": "approval-123",
                "session_id": "session-123",
                "tool_name": "exec",
                "tool_args": {"command": "rm test.txt"},
                "reason": "Dangerous command requires confirmation",
                "decision_level": "danger",
                "status": "pending",
                "approved": None,
                "expired": False,
            }
        }

    def list_approvals(self):
        return list(self.records.values())

    def resolve_approval(self, request_id, approved, reason=""):
        record = self.records.get(request_id)
        if not record or record["status"] != "pending":
            return False
        record["status"] = "approved" if approved else "denied"
        record["approved"] = approved
        record["resolution_reason"] = reason
        return True


class FakeApprovalAgent(FakeAgent):
    def __init__(self):
        self.tool_executor = FakeApprovalExecutor()


def test_extract_query_uses_last_user_message():
    messages = [
        {"role": "system", "content": "Use PSKA tools."},
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "second"},
    ]

    assert extract_query(messages) == "second"
    assert extract_history(messages) == messages[:-1]


def test_service_event_payload_has_stable_contract_fields():
    event = AgentEvent.tool_call(
        "pska_search",
        {"query": "Project Atlas"},
        "session-123",
        call_id="call-123",
    )

    payload = service_event_payload(event, run_id="run-123", sequence=7)

    assert payload["schema"] == SERVICE_EVENT_SCHEMA_VERSION
    assert payload["type"] == "tool_call"
    assert payload["event_id"] == "run-123:7"
    assert payload["run_id"] == "run-123"
    assert payload["session_id"] == "session-123"
    assert payload["tool_name"] == "pska_search"
    assert payload["tool_args"] == {"query": "Project Atlas"}
    assert payload["tool_call_id"] == "call-123"
    assert payload["cited_source_ids"] == []
    assert "metadata" in payload


def test_service_event_payload_exposes_headless_approval_id():
    event = AgentEvent.ask_user(
        "Dangerous command requires confirmation",
        "exec",
        {"command": "rm test.txt"},
        "session-123",
    )
    event.metadata.update(
        {
            "request_id": "approval-123",
            "decision_level": "danger",
        }
    )

    payload = service_event_payload(event, run_id="run-123", sequence=3)

    assert payload["type"] == "ask_user"
    assert payload["approval_request_id"] == "approval-123"
    assert payload["tool_name"] == "exec"
    assert payload["tool_args"] == {"command": "rm test.txt"}
    assert payload["metadata"]["request_id"] == "approval-123"
    assert payload["metadata"]["decision_level"] == "danger"


def test_sse_frame_names_event_and_serializes_data():
    frame = sse_frame(
        {
            "type": "final_answer",
            "content": "done",
        }
    )

    assert frame.startswith("event: final_answer\n")
    assert 'data: {"type": "final_answer", "content": "done"}' in frame
    assert frame.endswith("\n\n")


def test_summarize_events_returns_final_answer_and_tool_calls():
    events = [
        {
            "type": "tool_call",
            "event_id": "run-123:1",
            "tool_call_id": "call-123",
            "tool_name": "pska_search",
            "tool_args": {"query": "Atlas"},
        },
        {
            "type": "session_end",
            "event_id": "run-123:2",
            "content": "Final answer",
        },
    ]

    response = summarize_events(
        run_id="run-123",
        session_id="session-123",
        events=events,
        started_at=0,
    )

    assert response["type"] == "chat.completion"
    assert response["run_id"] == "run-123"
    assert response["session_id"] == "session-123"
    assert response["content"] == "Final answer"
    assert response["tool_calls"] == [
        {
            "event_id": "run-123:1",
            "tool_call_id": "call-123",
            "tool_name": "pska_search",
            "tool_args": {"query": "Atlas"},
        }
    ]


def test_chat_completions_non_streaming_endpoint():
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")

    set_agent_for_testing(FakeAgent())
    try:
        client = testclient.TestClient(create_app())
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "search Atlas"}],
                "stream": False,
                "session_id": "session-123",
                "metadata": {"run_id": "run-123"},
            },
        )
    finally:
        set_agent_for_testing(None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "chat.completion"
    assert payload["run_id"] == "run-123"
    assert payload["session_id"] == "session-123"
    assert payload["content"] == "final answer"
    assert [event["type"] for event in payload["events"]] == [
        "session_start",
        "tool_call",
        "tool_result",
        "session_end",
    ]


def test_chat_completions_streaming_endpoint_emits_sse_frames():
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")

    set_agent_for_testing(FakeAgent())
    try:
        client = testclient.TestClient(create_app())
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "search Atlas"}],
                "session_id": "session-123",
                "metadata": {"run_id": "run-123"},
            },
        )
    finally:
        set_agent_for_testing(None)

    assert response.status_code == 200
    assert response.headers["x-fastreact-run-id"] == "run-123"
    assert response.headers["x-fastreact-event-schema"] == SERVICE_EVENT_SCHEMA_VERSION
    text = response.text
    assert "event: session_start" in text
    assert "event: tool_call" in text
    assert "event: done" in text


def test_readiness_payload_has_deployment_contract_fields(monkeypatch):
    monkeypatch.setenv("FASTREACT_SERVICE_TOKEN", "service-secret")
    payload = readiness_payload(FakeAgent())

    assert payload["service_contract"] == SERVICE_EVENT_SCHEMA_VERSION
    assert payload["auth"]["required"] is True
    assert payload["auth"]["header"] == "Authorization: Bearer <token>"
    assert payload["mcp"]["ready"] is True
    assert payload["mcp"]["servers"] == [{"name": "pska", "alive": True}]
    assert payload["mcp"]["tools"] == ["pska_search"]
    assert "model" in payload
    assert configured_service_token() == "service-secret"


def test_service_auth_blocks_chat_and_readiness_when_configured(monkeypatch):
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")
    monkeypatch.setenv("FASTREACT_SERVICE_TOKEN", "service-secret")
    set_agent_for_testing(FakeAgent())
    try:
        client = testclient.TestClient(create_app())
        unauthenticated = client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "search Atlas"}]},
        )
        assert unauthenticated.status_code == 401
        assert client.get("/ready").status_code == 401

        ready = client.get("/ready", headers={"Authorization": "Bearer service-secret"})
        assert ready.status_code == 200
        assert ready.json()["auth"]["required"] is True

        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "search Atlas"}],
                "stream": False,
                "metadata": {"run_id": "run-auth"},
            },
            headers={"X-FastReAct-Service-Token": "service-secret"},
        )
        assert response.status_code == 200
        assert response.json()["run_id"] == "run-auth"
    finally:
        set_agent_for_testing(None)


def test_headless_approval_endpoints_list_get_and_resolve(monkeypatch):
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")
    monkeypatch.setenv("FASTREACT_SERVICE_TOKEN", "service-secret")
    set_agent_for_testing(FakeApprovalAgent())
    headers = {"X-FastReAct-Service-Token": "service-secret"}
    try:
        client = testclient.TestClient(create_app())
        assert client.get("/v1/approvals").status_code == 401

        listed = client.get("/v1/approvals", headers=headers)
        assert listed.status_code == 200
        listed_payload = listed.json()
        assert listed_payload["count"] == 1
        assert listed_payload["pending_count"] == 1
        assert listed_payload["approvals"][0]["request_id"] == "approval-123"

        fetched = client.get("/v1/approvals/approval-123", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["approval"]["tool_name"] == "exec"

        approved = client.post(
            "/v1/approvals/approval-123/approve",
            headers=headers,
            json={"reason": "operator approved"},
        )
        assert approved.status_code == 200
        assert approved.json() == {
            "request_id": "approval-123",
            "status": "approved",
            "approved": True,
        }

        fetched_after = client.get("/v1/approvals/approval-123", headers=headers)
        assert fetched_after.json()["approval"]["status"] == "approved"
        assert fetched_after.json()["approval"]["resolution_reason"] == "operator approved"

        second_resolution = client.post(
            "/v1/approvals/approval-123/deny",
            headers=headers,
            json={"reason": "too late"},
        )
        assert second_resolution.status_code == 404
    finally:
        set_agent_for_testing(None)


def test_background_run_endpoints_create_query_events_cancel_and_trace(monkeypatch, tmp_path):
    import time

    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")
    from fastreact.runtime.store_service import StoreService

    monkeypatch.setenv("FASTREACT_SERVICE_TOKEN", "service-secret")
    fake_agent = FakeAgent()
    fake_agent.store = StoreService(tmp_path / "store")
    set_agent_for_testing(fake_agent)
    headers = {"X-FastReAct-Service-Token": "service-secret"}
    run_id = f"run-background-contract-{time.time_ns()}"
    try:
        client = testclient.TestClient(create_app())
        created = client.post(
            "/v1/runs",
            headers=headers,
            json={
                "messages": [{"role": "user", "content": "search Atlas"}],
                "metadata": {"run_id": run_id},
            },
        )
        assert created.status_code == 200
        created_payload = created.json()
        assert created_payload["type"] == "run"
        assert created_payload["run_id"] == run_id
        assert created_payload["status"] in {"queued", "running", "completed"}

        final_payload = None
        for _ in range(20):
            response = client.get(f"/v1/runs/{run_id}", headers=headers)
            assert response.status_code == 200
            final_payload = response.json()
            if final_payload["status"] == "completed":
                break
            time.sleep(0.01)
        assert final_payload is not None
        assert final_payload["status"] == "completed"
        assert final_payload["event_count"] == 4

        events = client.get(f"/v1/runs/{run_id}/events", headers=headers)
        assert events.status_code == 200
        events_payload = events.json()
        assert events_payload["run_id"] == run_id
        assert [event["type"] for event in events_payload["events"]] == [
            "session_start",
            "tool_call",
            "tool_result",
            "session_end",
        ]
        assert [event["sequence"] for event in events_payload["events"]] == [0, 1, 2, 3]
        assert events_payload["count"] == 4
        assert events_payload["total_event_count"] == 4
        assert events_payload["next_after_sequence"] == 3
        assert events_payload["has_more"] is False

        first_page = client.get(f"/v1/runs/{run_id}/events?limit=2", headers=headers)
        assert first_page.status_code == 200
        first_page_payload = first_page.json()
        assert [event["sequence"] for event in first_page_payload["events"]] == [0, 1]
        assert first_page_payload["count"] == 2
        assert first_page_payload["event_count"] == 4
        assert first_page_payload["total_event_count"] == 4
        assert first_page_payload["next_after_sequence"] == 1
        assert first_page_payload["has_more"] is True

        second_page = client.get(
            f"/v1/runs/{run_id}/events?limit=2&after_sequence={first_page_payload['next_after_sequence']}",
            headers=headers,
        )
        assert second_page.status_code == 200
        second_page_payload = second_page.json()
        assert [event["sequence"] for event in second_page_payload["events"]] == [2, 3]
        assert second_page_payload["has_more"] is False

        listed = client.get("/v1/runs", headers=headers)
        assert listed.status_code == 200
        assert any(run["run_id"] == run_id for run in listed.json()["runs"])
        listed_limited = client.get("/v1/runs?limit=1&status=completed", headers=headers)
        assert listed_limited.status_code == 200
        assert listed_limited.json()["count"] <= 1
        assert listed_limited.json()["limit"] == 1

        traces = client.get("/v1/traces", headers=headers)
        assert traces.status_code == 200
        assert any(trace["run_id"] == run_id for trace in traces.json()["traces"])
        traces_limited = client.get("/v1/traces?limit=1", headers=headers)
        assert traces_limited.status_code == 200
        assert traces_limited.json()["count"] <= 1
        assert traces_limited.json()["limit"] == 1

        trace = client.get(f"/v1/traces/{run_id}", headers=headers)
        assert trace.status_code == 200
        assert trace.json()["trace"]["status"] == "completed"
        assert trace.json()["trace"]["event_count"] == 4

        trace_events = client.get(f"/v1/traces/{run_id}/events", headers=headers)
        assert trace_events.status_code == 200
        assert trace_events.json()["event_count"] == 4
        trace_events_page = client.get(f"/v1/traces/{run_id}/events?limit=2&after_sequence=1", headers=headers)
        assert trace_events_page.status_code == 200
        assert [event["sequence"] for event in trace_events_page.json()["events"]] == [2, 3]
        assert len(fake_agent.store.read("events", limit=0, run_id=run_id)) == 4

        cancelled_completed = client.post(
            f"/v1/runs/{run_id}/cancel",
            headers=headers,
        )
        assert cancelled_completed.status_code == 200
        assert cancelled_completed.json()["status"] == "completed"
    finally:
        set_agent_for_testing(None)
