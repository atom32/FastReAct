from fastreact.adapters.http import (
    SERVICE_EVENT_SCHEMA_VERSION,
    configured_service_token,
    create_app,
    extract_history,
    extract_query,
    get_agent,
    metrics_payload,
    readiness_payload,
    service_event_payload,
    set_agent_for_testing,
    set_service_config,
    sse_frame,
    summarize_events,
)
from fastreact.core.config import ServiceConfig
from fastreact.core.events import AgentEvent
from fastreact.runtime.run_service import RunService


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


class FakeSkillMetadata:
    version = "1.0.0"
    tags = ["demo"]
    dependencies = ["base"]
    mcp_servers = ["pska"]
    recommended_tools = ["pska_search"]


class FakeSkill:
    name = "pska_demo"
    description = "Use PSKA demo tools."
    metadata = FakeSkillMetadata()

    def list_files(self):
        return ["SKILL.md"]


class FakeSkillAgent(FakeAgent):
    skills = {"pska_demo": FakeSkill()}

    def list_skills(self):
        return ["pska_demo"]

    def get_skill(self, skill_name):
        return self.skills.get(skill_name)


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
                "timeout_seconds": 300.0,
                "created_at": "2026-01-01T00:00:00+00:00",
                "expires_at": "2026-01-01T00:05:00+00:00",
                "resolved_at": None,
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


class FakeWorkspaceAgent(FakeAgent):
    def __init__(self, workspace):
        from types import SimpleNamespace

        self._config = SimpleNamespace(
            paths=SimpleNamespace(
                gateway_workspace=workspace,
                global_skills_dir=workspace / "skills" / "builtin",
                user_skills_dir=None,
            ),
            service=SimpleNamespace(
                host="127.0.0.1",
                port=9000,
                approval_timeout_seconds=300,
                run_lease_seconds=600,
                run_max_attempts=3,
                run_retry_base_seconds=5,
                run_retry_max_seconds=300,
                run_concurrency=4,
                recover_queued_runs=True,
            ),
            mcp=SimpleNamespace(servers=[]),
            llm=SimpleNamespace(model="test-model", api_base=None, api_key=None),
        )


class FakeTaskAgent(FakeWorkspaceAgent):
    def __init__(self, workspace):
        super().__init__(workspace)
        from fastreact.runtime.store_service import StoreService
        from fastreact.runtime.task_service import TaskService

        self.store = StoreService(workspace / "store")
        self.runs = RunService(self.store)
        self.tasks = TaskService(self.store)


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


def test_chat_completions_rate_limit_returns_429():
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")

    set_agent_for_testing(FakeAgent())
    set_service_config(ServiceConfig(rate_limit_per_hour=1))
    try:
        client = testclient.TestClient(create_app())
        body = {
            "messages": [{"role": "user", "content": "search Atlas"}],
            "stream": False,
            "user_key": "web:alice",
        }
        first = client.post("/v1/chat/completions", json=body)
        second = client.post("/v1/chat/completions", json=body)
    finally:
        set_agent_for_testing(None)
        set_service_config(ServiceConfig())

    assert first.status_code == 200
    assert second.status_code == 429
    assert "Rate limit exceeded" in second.json()["detail"]


def test_chat_completions_blocks_configured_user():
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")

    set_agent_for_testing(FakeAgent())
    set_service_config(ServiceConfig(blocked_user_keys=["web:blocked"]))
    try:
        client = testclient.TestClient(create_app())
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "search Atlas"}],
                "stream": False,
                "user_key": "web:blocked",
            },
        )
    finally:
        set_agent_for_testing(None)
        set_service_config(ServiceConfig())

    assert response.status_code == 403
    assert "blocked" in response.json()["detail"]


def test_chat_completions_allowed_user_list_rejects_others():
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")

    set_agent_for_testing(FakeAgent())
    set_service_config(ServiceConfig(allowed_user_keys=["web:alice"]))
    try:
        client = testclient.TestClient(create_app())
        denied = client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "search Atlas"}],
                "stream": False,
                "user_key": "web:bob",
            },
        )
        allowed = client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "search Atlas"}],
                "stream": False,
                "user_key": "web:alice",
            },
        )
    finally:
        set_agent_for_testing(None)
        set_service_config(ServiceConfig())

    assert denied.status_code == 403
    assert "not allowed" in denied.json()["detail"]
    assert allowed.status_code == 200


def test_background_run_create_rate_limit_returns_429(tmp_path):
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")

    set_agent_for_testing(FakeTaskAgent(tmp_path / "rate-limit-agent"))
    set_service_config(ServiceConfig(rate_limit_per_hour=1))
    try:
        client = testclient.TestClient(create_app())
        first = client.post(
            "/v1/runs",
            json={
                "messages": [{"role": "user", "content": "search Atlas"}],
                "user_key": "web:bob",
                "metadata": {"run_id": "rate-limit-run-1"},
            },
        )
        second = client.post(
            "/v1/runs",
            json={
                "messages": [{"role": "user", "content": "search Atlas"}],
                "user_key": "web:bob",
                "metadata": {"run_id": "rate-limit-run-2"},
            },
        )
    finally:
        set_agent_for_testing(None)
        set_service_config(ServiceConfig())

    assert first.status_code == 200
    assert second.status_code == 429


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


def test_metrics_payload_summarizes_headless_service_state(tmp_path):
    from fastreact.runtime.store_service import StoreService

    fake_agent = FakeApprovalAgent()
    fake_agent.store = StoreService(tmp_path / "metrics-store")
    fake_agent.runs = RunService(fake_agent.store)
    fake_agent.runs.create(run_id="run-queued", session_id="session-queued", query="queued")
    fake_agent.store.append(
        "traces",
        {
            "run_id": "run-ok",
            "session_id": "session-ok",
            "status": "completed",
            "duration_ms": 120.0,
            "llm_usage_total": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    )
    fake_agent.store.append(
        "traces",
        {
            "run_id": "run-failed",
            "session_id": "session-failed",
            "status": "failed",
            "duration_ms": 80.0,
            "error": "boom",
            "llm_usage_total": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
        },
    )
    fake_agent.store.append(
        "traces",
        {
            "run_id": "run-pska-digest",
            "session_id": "session-pska-digest",
            "status": "completed",
            "metadata": {"caller": "pska_digest_worker", "purpose": "digest", "pska_job_id": "job-digest"},
            "tool_name_counts": {"pska_pska_job_context": 1, "pska_pska_write_candidates": 2},
            "pska_digest_tool_budget": {
                "write_call_count": 2,
                "job_context_call_count": 1,
                "tool_budget": {"pska_pska_write_candidates": 1, "pska_pska_job_context": 1},
                "tool_budget_exceeded": True,
            },
        },
    )
    fake_agent.store.append(
        "events",
        {
            "run_id": "run-failed",
            "session_id": "session-failed",
            "type": "error",
            "content": "boom",
            "timestamp": "2026-01-01T00:00:00+00:00",
        },
    )
    fake_agent.store.append(
        "audit",
        {
            "session_id": "session-ok",
            "tool_name": "pska_search",
            "duration_ms": 20.0,
        },
    )
    fake_agent.tool_executor.records["approval-123"]["status"] = "approved"
    fake_agent.tool_executor.records["approval-123"]["approved"] = True
    fake_agent.tool_executor.records["approval-123"]["resolved_at"] = "2026-01-01T00:00:03+00:00"

    payload = metrics_payload(fake_agent)

    assert payload["schema"] == "fastreact.metrics.v1"
    assert payload["runs"]["durable"]["queued_count"] == 1
    assert payload["runs"]["durable"]["replay_event_count"] == 0
    assert payload["runs"]["trace_count"] == 3
    assert payload["runs"]["status_counts"]["completed"] == 2
    assert payload["runs"]["status_counts"]["failed"] == 1
    assert payload["runs"]["avg_duration_ms"] == 100.0
    assert payload["events"]["error_count"] == 1
    assert payload["tools"]["audit_count"] == 1
    assert payload["tools"]["avg_duration_ms"] == 20.0
    assert payload["llm"]["usage_total"] == {
        "prompt_tokens": 13,
        "completion_tokens": 7,
        "total_tokens": 20,
    }
    assert payload["integrations"]["pska_digest"]["run_count"] == 1
    assert payload["integrations"]["pska_digest"]["write_call_count"] == 2
    assert payload["integrations"]["pska_digest"]["job_context_call_count"] == 1
    assert payload["integrations"]["pska_digest"]["tool_budget_exceeded_count"] == 1
    assert payload["integrations"]["pska_digest"]["recent_budget_exceeded"][0]["pska_job_id"] == "job-digest"
    assert payload["tasks"]["count"] == 0
    assert payload["tasks"]["active_count"] == 0
    assert payload["approvals"]["count"] == 1
    assert payload["approvals"]["status_counts"]["approved"] == 1
    assert payload["approvals"]["avg_resolution_ms"] == 3000.0
    assert payload["errors"]["count"] == 2
    assert payload["store"]["total_records"] == 6


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
        assert client.get("/v1/metrics").status_code == 401

        ready = client.get("/ready", headers={"Authorization": "Bearer service-secret"})
        assert ready.status_code == 200
        assert ready.json()["auth"]["required"] is True

        set_agent_for_testing(FakeApprovalAgent())
        metrics = client.get("/v1/metrics", headers={"Authorization": "Bearer service-secret"})
        assert metrics.status_code == 200
        assert metrics.json()["schema"] == "fastreact.metrics.v1"

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
        assert listed_payload["schema"] == "fastreact.approvals.v1"
        assert listed_payload["count"] == 1
        assert listed_payload["total_count"] == 1
        assert listed_payload["offset"] == 0
        assert listed_payload["order"] == "desc"
        assert listed_payload["pending_count"] == 1
        assert listed_payload["summary"]["status_counts"]["pending"] == 1
        assert listed_payload["summary"]["policy_action_counts"]["none"] == 1
        assert listed_payload["approvals"][0]["request_id"] == "approval-123"
        assert listed_payload["approvals"][0]["timeout_seconds"] == 300.0
        assert listed_payload["approvals"][0]["expires_at"] == "2026-01-01T00:05:00+00:00"

        filtered = client.get("/v1/approvals?status=approved", headers=headers)
        assert filtered.status_code == 200
        assert filtered.json()["count"] == 0
        assert filtered.json()["filters"]["status"] == "approved"

        agent = get_agent()
        agent.tool_executor.records["approval-older"] = {
            **agent.tool_executor.records["approval-123"],
            "request_id": "approval-older",
            "created_at": "2025-12-31T00:00:00+00:00",
        }
        agent.tool_executor.records["approval-newer"] = {
            **agent.tool_executor.records["approval-123"],
            "request_id": "approval-newer",
            "created_at": "2026-01-02T00:00:00+00:00",
        }

        desc_page = client.get("/v1/approvals?limit=2&offset=1&order=desc", headers=headers)
        assert desc_page.status_code == 200
        assert [item["request_id"] for item in desc_page.json()["approvals"]] == ["approval-123", "approval-older"]
        assert desc_page.json()["next_offset"] is None

        asc_page = client.get("/v1/approvals?limit=2&order=asc", headers=headers)
        assert asc_page.status_code == 200
        assert [item["request_id"] for item in asc_page.json()["approvals"]] == ["approval-older", "approval-123"]
        assert asc_page.json()["next_offset"] == 2

        bad_order = client.get("/v1/approvals?order=sideways", headers=headers)
        assert bad_order.status_code == 400

        fetched = client.get("/v1/approvals/approval-123", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["approval"]["tool_name"] == "exec"
        assert fetched.json()["approval"]["expires_at"] == "2026-01-01T00:05:00+00:00"

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


def test_skill_diagnostics_endpoint_reports_dependencies(monkeypatch):
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")
    monkeypatch.setenv("FASTREACT_SERVICE_TOKEN", "service-secret")
    set_agent_for_testing(FakeSkillAgent())
    try:
        client = testclient.TestClient(create_app())
        response = client.get(
            "/v1/skills/diagnostics",
            headers={"X-FastReAct-Service-Token": "service-secret"},
        )
    finally:
        set_agent_for_testing(None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "fastreact.skill_diagnostics.v1"
    assert payload["skills"][0]["name"] == "pska_demo"
    assert payload["skills"][0]["status"] == "ready"
    assert payload["skills"][0]["mcp_servers"] == ["pska"]


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


def test_background_run_events_replay_from_durable_store(monkeypatch, tmp_path):
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")
    from fastreact.runtime.store_service import StoreService

    monkeypatch.setenv("FASTREACT_SERVICE_TOKEN", "service-secret")
    fake_agent = FakeAgent()
    fake_agent.store = StoreService(tmp_path / "durable-store")
    fake_agent.runs = RunService(fake_agent.store)
    run_id = "run-durable-replay"
    fake_agent.runs.create(
        run_id=run_id,
        session_id="session-durable",
        query="search Atlas",
        metadata={"run_id": run_id},
    )
    fake_agent.runs.mark_running(run_id, worker_id="test-worker")
    for sequence, event_type in enumerate(["session_start", "tool_call", "tool_result", "session_end"]):
        fake_agent.runs.append_event(
            run_id,
            {
                "schema": SERVICE_EVENT_SCHEMA_VERSION,
                "type": event_type,
                "event_id": f"{run_id}:{sequence}",
                "sequence": sequence,
                "run_id": run_id,
                "session_id": "session-durable",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "content": "done" if event_type == "session_end" else "",
                "tool_name": "pska_search" if "tool" in event_type else None,
                "tool_args": {"query": "Atlas"} if event_type == "tool_call" else None,
                "tool_call_id": "call-1" if "tool" in event_type else None,
                "approval_request_id": None,
                "cited_source_ids": [],
                "metadata": {},
            },
        )
    fake_agent.runs.complete(run_id)

    set_agent_for_testing(fake_agent)
    try:
        client = testclient.TestClient(create_app())
        headers = {"X-FastReAct-Service-Token": "service-secret"}
        events = client.get(f"/v1/runs/{run_id}/events?limit=2", headers=headers)
        assert events.status_code == 200
        payload = events.json()
        assert [event["sequence"] for event in payload["events"]] == [0, 1]
        assert payload["has_more"] is True

        trace_events = client.get(f"/v1/traces/{run_id}/events?after_sequence=1", headers=headers)
        assert trace_events.status_code == 200
        assert [event["sequence"] for event in trace_events.json()["events"]] == [2, 3]
        assert fake_agent.runs.snapshot(run_id)["event_count"] == 4
    finally:
        set_agent_for_testing(None)


def test_run_service_recovers_stale_running_run(tmp_path):
    import time
    from fastreact.runtime.store_service import StoreService

    service = RunService(StoreService(tmp_path / "run-recovery"), lease_seconds=0.01)
    service.create(run_id="run-stale", session_id="session-stale", query="recover me")
    service.mark_running("run-stale", worker_id="old-worker")
    time.sleep(0.02)

    recovered = service.recover_stale()

    assert recovered["recovered"] == 1
    snapshot = service.snapshot("run-stale")
    assert snapshot["status"] == "queued"
    assert snapshot["last_error"] == "Recovered stale running lease"


def test_lifespan_recovers_queued_run_from_durable_store(monkeypatch, tmp_path):
    import time

    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")
    from fastreact.runtime.store_service import StoreService

    monkeypatch.setenv("FASTREACT_SERVICE_TOKEN", "service-secret")
    fake_agent = FakeAgent()
    fake_agent.store = StoreService(tmp_path / "lifespan-recovery")
    fake_agent.runs = RunService(fake_agent.store)
    fake_agent._config = type(
        "FakeConfig",
        (),
        {
            "service": type(
                "FakeService",
                (),
                {"recover_queued_runs": True},
            )()
        },
    )()
    run_id = "run-lifespan-recovery"
    fake_agent.runs.create(
        run_id=run_id,
        session_id="session-lifespan",
        query="search Atlas",
        metadata={"run_id": run_id},
    )

    set_agent_for_testing(fake_agent)
    try:
        headers = {"X-FastReAct-Service-Token": "service-secret"}
        with testclient.TestClient(create_app()) as client:
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
            events = client.get(f"/v1/runs/{run_id}/events", headers=headers)
            assert [event["type"] for event in events.json()["events"]] == [
                "session_start",
                "tool_call",
                "tool_result",
                "session_end",
            ]
    finally:
        set_agent_for_testing(None)


def test_workspace_profile_endpoint_reads_and_updates_profile(monkeypatch, tmp_path):
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")

    monkeypatch.setenv("FASTREACT_SERVICE_TOKEN", "service-secret")
    workspace = tmp_path / "workspace-profile"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("Use project rules.", encoding="utf-8")
    fake_agent = FakeWorkspaceAgent(workspace)

    set_agent_for_testing(fake_agent)
    try:
        client = testclient.TestClient(create_app())
        headers = {"X-FastReAct-Service-Token": "service-secret"}

        response = client.get("/v1/workspace/profile", headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["schema"] == "fastreact.workspace_profile.v1"
        assert payload["workspace"] == str(workspace.resolve())
        agents_file = next(item for item in payload["files"] if item["name"] == "AGENTS.md")
        assert agents_file["content"] == "Use project rules."

        updated = client.put(
            "/v1/workspace/profile",
            headers=headers,
            json={"agents_md": "New agent rules.", "soul_md": "Project voice."},
        )
        assert updated.status_code == 200
        assert (workspace / "AGENTS.md").read_text(encoding="utf-8") == "New agent rules."
        assert (workspace / "SOUL.md").read_text(encoding="utf-8") == "Project voice."
        assert [item["name"] for item in updated.json()["written"]] == ["AGENTS.md", "SOUL.md"]
    finally:
        set_agent_for_testing(None)


def test_setup_status_summarizes_service_workspace_and_pska_preset(monkeypatch, tmp_path):
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")

    monkeypatch.setenv("FASTREACT_SERVICE_TOKEN", "service-secret")
    fake_agent = FakeWorkspaceAgent(tmp_path / "setup-workspace")

    set_agent_for_testing(fake_agent)
    try:
        client = testclient.TestClient(create_app())
        response = client.get("/v1/setup", headers={"X-FastReAct-Service-Token": "service-secret"})
    finally:
        set_agent_for_testing(None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "fastreact.setup_status.v1"
    assert payload["service"]["auth_required"] is True
    assert payload["workspace"]["path"].endswith("setup-workspace")
    assert payload["presets"]["pska"]["protocol_only"] is True


def test_setup_presets_and_config_draft_are_safe_and_pska_aware(monkeypatch, tmp_path):
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")

    monkeypatch.setenv("FASTREACT_SERVICE_TOKEN", "service-secret")
    fake_agent = FakeWorkspaceAgent(tmp_path / "setup-draft-workspace")

    set_agent_for_testing(fake_agent)
    try:
        client = testclient.TestClient(create_app())
        headers = {"X-FastReAct-Service-Token": "service-secret"}
        presets = client.get("/v1/setup/presets", headers=headers)
        assert presets.status_code == 200
        assert presets.json()["write_supported"] is False
        assert [item["id"] for item in presets.json()["presets"]] == ["default", "pska"]

        draft = client.post(
            "/v1/setup/config-draft",
            headers=headers,
            json={
                "preset": "pska",
                "include_pska": True,
                "model": "deepseek-v4-flash",
                "api_base": "https://api.deepseek.com",
                "service_token": "local-token",
                "workspace": "~/fastreact-pska-workspace",
            },
        )
    finally:
        set_agent_for_testing(None)

    assert draft.status_code == 200
    payload = draft.json()
    assert payload["schema"] == "fastreact.setup_config_draft.v1"
    assert payload["write_supported"] is False
    assert payload["service_token"] == "local-token"
    assert payload["config"]["llm"]["api_key_file"] == "~/api_key.txt"
    assert "api_key" not in payload["config"]["llm"]
    assert payload["config"]["service"]["run_concurrency"] == 4
    assert payload["config"]["service"]["run_retry_base_seconds"] == 5
    assert payload["config"]["mcp"]["servers"][0]["name"] == "pska"
    assert payload["config"]["policy"]["tenant_rules"]["pska"]["tools"]["exec"] == "require_approval"


def test_task_endpoints_create_update_list_and_include_related_runs(monkeypatch, tmp_path):
    pytest = __import__("pytest")
    testclient = pytest.importorskip("fastapi.testclient")

    monkeypatch.setenv("FASTREACT_SERVICE_TOKEN", "service-secret")
    fake_agent = FakeTaskAgent(tmp_path / "task-workspace")

    set_agent_for_testing(fake_agent)
    try:
        client = testclient.TestClient(create_app())
        headers = {"X-FastReAct-Service-Token": "service-secret"}
        created = client.post(
            "/v1/tasks",
            headers=headers,
            json={
                "title": "Review PSKA citations",
                "description": "Inspect evidence fields",
                "priority": "high",
                "owner": "pska",
                "session_id": "session-task",
            },
        )
        assert created.status_code == 200
        task = created.json()["task"]
        assert task["status"] == "pending"
        assert task["priority"] == "high"

        fake_agent.runs.create(
            run_id="run-task-1",
            session_id="session-task",
            query="review citations",
            metadata={"task_id": task["task_id"]},
        )
        fake_agent.runs.complete("run-task-1")

        listed = client.get("/v1/tasks?owner=pska", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["schema"] == "fastreact.tasks.v1"
        assert listed.json()["tasks"][0]["task_id"] == task["task_id"]

        updated = client.patch(
            f"/v1/tasks/{task['task_id']}",
            headers=headers,
            json={"status": "in_progress", "status_reason": "operator started"},
        )
        assert updated.status_code == 200
        payload = updated.json()
        assert payload["task"]["status"] == "in_progress"
        assert payload["task"]["started_at"]
        assert payload["task"]["status_history"][-1]["reason"] == "operator started"
        assert payload["runs"][0]["run_id"] == "run-task-1"

        detail = client.get(f"/v1/tasks/{task['task_id']}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["task"]["title"] == "Review PSKA citations"
        assert detail.json()["runs"][0]["status"] == "completed"

        metrics = client.get("/v1/metrics", headers=headers)
        assert metrics.status_code == 200
        assert metrics.json()["tasks"]["count"] == 1
        assert metrics.json()["tasks"]["active_count"] == 1
        assert metrics.json()["tasks"]["status_counts"]["in_progress"] == 1
    finally:
        set_agent_for_testing(None)
