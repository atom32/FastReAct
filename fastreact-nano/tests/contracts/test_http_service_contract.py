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
