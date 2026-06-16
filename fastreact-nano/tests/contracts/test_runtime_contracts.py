import pytest

from fastreact import Agent, Config, LLMConfig, PolicyConfig, ReactConfig, ToolConfig
from fastreact.core.events import EventType
from fastreact.runtime.run_service import RunService
from fastreact.runtime.store_service import StoreService


def make_test_config(tmp_path):
    return Config(
        llm=LLMConfig(api_key="test-key", api_base="http://localhost:8000"),
        tools=ToolConfig(working_dir=tmp_path, protected_paths=[]),
        react=ReactConfig(
            max_iterations=3,
            enable_safety=False,
            enable_filesystem_memory=False,
        ),
    )


def test_session_service_create_list_close(tmp_path):
    agent = Agent(config=make_test_config(tmp_path), multitenant=False)

    session = agent.sessions.create(session_id="contract-session", user_key="web:test")

    assert session.session_id == "contract-session"
    assert agent.sessions.get("contract-session") is session
    assert agent.sessions.status("contract-session") == "idle"
    assert any(s["session_id"] == "contract-session" for s in agent.sessions.list())

    agent.sessions.close("contract-session")
    assert agent.sessions.get("contract-session") is None


@pytest.mark.asyncio
async def test_runtime_adds_timing_metadata(tmp_path, mock_llm_no_tools):
    agent = Agent(config=make_test_config(tmp_path), multitenant=False)

    events = []
    async for event in agent.run_event_stream("What is 2+2?", session_id="timing-contract"):
        events.append(event)

    assert [event.type for event in events][0] == EventType.SESSION_START
    assert events[-1].type == EventType.SESSION_END
    assert "time_to_first_event_ms" in events[0].metadata["timing"]
    assert "time_to_final_ms" in events[-1].metadata["timing"]
    assert events[-1].metadata["llm_usage_total"]["prompt_tokens"] == 10
    assert events[-1].metadata["llm_usage_total"]["completion_tokens"] == 5
    assert events[-1].metadata["llm_usage_total"]["total_tokens"] == 15

    traces = agent.store.read("traces", session_id="timing-contract")
    assert traces[-1]["llm_usage_total"]["total_tokens"] == 15


def test_store_task_service_jsonl_roundtrip(tmp_path):
    agent = Agent(config=make_test_config(tmp_path), multitenant=False)

    task = agent.tasks.create(
        title="Ship product control plane",
        priority="high",
        owner="web:test",
        dependencies=["task-seed"],
        session_id="session-a",
    )
    updated = agent.tasks.update(task["task_id"], status="in_progress")
    tasks = agent.tasks.list(session_id="session-a")

    assert updated["status"] == "in_progress"
    assert updated["started_at"]
    assert updated["status_changed_at"] == updated["started_at"]
    assert updated["status_history"][0]["to"] == "pending"
    assert updated["status_history"][-1]["from"] == "pending"
    assert updated["status_history"][-1]["to"] == "in_progress"
    assert tasks[0]["task_id"] == task["task_id"]
    assert "Current Task Board" in agent.tasks.prompt_context("session-a")


def test_store_service_reports_stream_stats(tmp_path):
    store = StoreService(tmp_path / ".fastreact")
    store.append("audit", {"session_id": "s1", "tool_name": "read_file"})
    store.append("traces", {"session_id": "s1", "time_to_final_ms": 42})

    stats = store.stats()

    assert stats["total_records"] == 2
    assert stats["streams"]["audit"]["records"] == 1
    assert stats["streams"]["traces"]["bytes"] > 0


def test_run_trace_records_pska_digest_tool_budget(tmp_path):
    store = StoreService(tmp_path / ".fastreact")
    runs = RunService(store)
    runs.create(
        run_id="run-pska-digest",
        session_id="session-pska",
        query="digest",
        user_key="pska:user_primary",
        metadata={"caller": "pska_digest_worker", "purpose": "digest"},
    )
    runs.mark_running("run-pska-digest", worker_id="worker-test")
    runs.append_event("run-pska-digest", {"type": "tool_call", "tool_name": "pska_pska_job_context", "sequence": 1})
    runs.append_event("run-pska-digest", {"type": "tool_call", "tool_name": "pska_pska_write_candidates", "sequence": 2})
    runs.append_event("run-pska-digest", {"type": "tool_call", "tool_name": "pska_pska_write_candidates", "sequence": 3})
    runs.append_event("run-pska-digest", {"type": "session_end", "content": "done", "sequence": 4})

    runs.complete("run-pska-digest")
    trace = store.latest_by_id("traces", "run_id", "run-pska-digest")

    assert trace["tool_name_counts"]["pska_pska_write_candidates"] == 2
    assert trace["tool_call_count"] == 3
    assert trace["pska_digest_tool_budget"]["write_call_count"] == 2
    assert trace["pska_digest_tool_budget"]["job_context_call_count"] == 1
    assert trace["pska_digest_tool_budget"]["tool_budget_exceeded"] is True


def test_run_service_retry_backoff_and_ready_queue(tmp_path):
    store = StoreService(tmp_path / ".fastreact")
    runs = RunService(store, max_attempts=2, retry_base_seconds=60, retry_max_seconds=120)
    runs.create(run_id="run-retry", session_id="session-retry", query="retry")
    runs.mark_running("run-retry", worker_id="worker-a")

    retry = runs.fail("run-retry", "temporary boom", retryable=True)

    assert retry["status"] == "queued"
    assert retry["last_error"] == "temporary boom"
    assert retry["retry_after"]
    assert runs.queued_for_recovery() == []
    assert runs.stats()["delayed_queued_count"] == 1

    retry["retry_after"] = "2000-01-01T00:00:00+00:00"
    store.upsert_snapshot("runs", "run_id", retry)
    assert [run["run_id"] for run in runs.queued_for_recovery()] == ["run-retry"]

    runs.mark_running("run-retry", worker_id="worker-b")
    failed = runs.fail("run-retry", "still broken", retryable=True)

    assert failed["status"] == "failed"
    assert failed["error"] == "still broken"


def test_store_service_sanitizes_sensitive_nested_fields(tmp_path):
    store = StoreService(tmp_path / ".fastreact")

    store.append(
        "run_events",
        {
            "run_id": "run-secret",
            "metadata": {
                "authorization": "Bearer secret-token",
                "nested": {
                    "api_key": "sk-test-secret",
                    "long_text": "x" * 1300,
                },
            },
            "tool_args": {
                "password": "plain-secret",
                "query": "safe",
            },
        },
    )

    record = store.read("run_events", limit=0)[0]
    assert record["metadata"]["authorization"] == "***"
    assert record["metadata"]["nested"]["api_key"] == "***"
    assert record["tool_args"]["password"] == "***"
    assert record["tool_args"]["query"] == "safe"
    assert record["metadata"]["nested"]["long_text"].endswith("[... truncated ...]")


def test_workspace_profile_context_loads_agents_and_soul_files(tmp_path):
    config = make_test_config(tmp_path)
    config.paths.gateway_workspace = tmp_path
    (tmp_path / "AGENTS.md").write_text("Project convention: cite sources.", encoding="utf-8")
    (tmp_path / ".fastreact").mkdir()
    (tmp_path / ".fastreact" / "SOUL.md").write_text("Agent profile: calm and precise.", encoding="utf-8")
    agent = Agent(config=config, multitenant=False)

    _base_prompt, variable_content = agent.skill_resolver.build_prompt(skills=None)

    assert "# Workspace Profile" in variable_content
    assert "Project convention: cite sources." in variable_content
    assert "Agent profile: calm and precise." in variable_content


@pytest.mark.asyncio
async def test_tool_execution_audits_safe_tool(tmp_path):
    agent = Agent(config=make_test_config(tmp_path), multitenant=False)

    execution, event = await agent.tool_executor.execute(
        tool_name="read_file",
        tool_params={"path": str(tmp_path / "missing.txt")},
        session_id="audit-session",
    )

    audit = agent.store.read("audit", session_id="audit-session")
    assert execution.tool_name == "read_file"
    assert event.type == EventType.TOOL_RESULT
    assert audit[-1]["tool_name"] == "read_file"
    assert audit[-1]["decision_level"] in ("none", "safe")


@pytest.mark.asyncio
async def test_tool_approval_contract(tmp_path):
    config = make_test_config(tmp_path)
    config.react.enable_safety = True
    agent = Agent(config=config, multitenant=False)

    decision, event = agent.tool_executor.assess(
        tool_name="exec",
        tool_params={"command": "rm test.txt"},
        session_id="approval-session",
    )

    assert decision is not None
    assert event is not None
    assert event.type == EventType.ASK_USER
    request_id = event.metadata["request_id"]
    assert event.metadata["timeout_seconds"] == 300.0
    assert event.metadata["expires_at"]
    assert agent.tool_executor.resolve_approval(request_id, approved=True)


@pytest.mark.asyncio
async def test_tool_approval_timeout_marks_record_expired(tmp_path):
    config = make_test_config(tmp_path)
    config.react.enable_safety = True
    agent = Agent(config=config, multitenant=False)

    decision, event = agent.tool_executor.assess(
        tool_name="exec",
        tool_params={"command": "rm test.txt"},
        session_id="approval-timeout-session",
    )

    assert decision is not None
    assert event is not None
    request_id = event.metadata["request_id"]

    approved = await agent.tool_executor.wait_for_approval(request_id, timeout_seconds=0.01)

    assert approved is False
    record = agent.tool_executor.list_approvals()[0]
    assert record["request_id"] == request_id
    assert record["status"] == "expired"
    assert record["approved"] is False
    assert record["expired"] is True
    assert record["resolution_reason"] == "approval_timeout"
    assert record["timeout_seconds"] == 0.01
    assert record["resolved_at"]
    assert agent.tool_executor.resolve_approval(request_id, approved=True) is False


@pytest.mark.asyncio
async def test_dangerous_tool_has_no_side_effect_without_approval(tmp_path):
    config = make_test_config(tmp_path)
    config.react.enable_safety = True
    config.service.approval_timeout_seconds = 0.01
    agent = Agent(config=config, multitenant=False)
    target = tmp_path / "danger-target.txt"
    target.write_text("keep me\n", encoding="utf-8")

    decision, event = agent.tool_executor.assess(
        tool_name="exec",
        tool_params={"command": "rm danger-target.txt"},
        session_id="danger-no-side-effect-session",
    )

    assert decision is not None
    assert event is not None
    request_id = event.metadata["request_id"]

    approved = await agent.tool_executor.wait_for_approval(request_id)
    execution, result_event = await agent.tool_executor.execute(
        tool_name="exec",
        tool_params={"command": "rm danger-target.txt"},
        session_id="danger-no-side-effect-session",
        decision=decision,
        approved=approved,
        request_id=request_id,
    )

    assert approved is False
    assert execution.blocked is True
    assert execution.result.startswith("[SAFETY_DENIED]")
    assert result_event.type == EventType.TOOL_RESULT
    assert target.exists()
    record = agent.tool_executor.list_approvals()[0]
    assert record["request_id"] == request_id
    assert record["status"] == "expired"
    assert record["resolution_reason"] == "approval_timeout"
    audit = agent.store.read("audit", session_id="danger-no-side-effect-session")
    assert audit[-1]["approved"] is False
    assert audit[-1]["request_id"] == request_id


@pytest.mark.asyncio
async def test_tool_approval_uses_configured_timeout_and_persists_record(tmp_path):
    config = make_test_config(tmp_path)
    config.react.enable_safety = True
    config.service.approval_timeout_seconds = 0.02
    agent = Agent(config=config, multitenant=False)

    _decision, event = agent.tool_executor.assess(
        tool_name="exec",
        tool_params={"command": "rm test.txt"},
        session_id="approval-config-session",
    )

    request_id = event.metadata["request_id"]
    assert event.metadata["timeout_seconds"] == 0.02

    approved = await agent.tool_executor.wait_for_approval(request_id)

    assert approved is False
    record = agent.store.latest_by_id("approvals", "request_id", request_id)
    assert record["status"] == "expired"
    assert record["timeout_seconds"] == 0.02
    assert record["resolution_reason"] == "approval_timeout"


@pytest.mark.asyncio
async def test_tool_policy_approval_metadata_and_audit_contract(tmp_path):
    config = make_test_config(tmp_path)
    config.react.enable_safety = True
    config.policy = PolicyConfig(tool_rules={"exec": "require_approval"})
    agent = Agent(config=config, multitenant=False)

    decision, event = agent.tool_executor.assess(
        tool_name="exec",
        tool_params={"command": "ls"},
        session_id="policy-approval-session",
    )

    assert decision is not None
    assert event is not None
    assert event.metadata["policy_scope"] == "tool:exec"
    assert event.metadata["policy_action"] == "require_approval"
    assert event.metadata["policy_matched"] is True

    request_id = event.metadata["request_id"]
    approvals = agent.tool_executor.list_approvals()
    assert approvals[0]["request_id"] == request_id
    assert approvals[0]["policy_scope"] == "tool:exec"
    assert approvals[0]["policy_action"] == "require_approval"
    assert approvals[0]["policy_matched"] is True

    audit = agent.store.read("audit", session_id="policy-approval-session")
    assert audit[-1]["request_id"] == request_id
    assert audit[-1]["policy_scope"] == "tool:exec"
    assert audit[-1]["policy_action"] == "require_approval"
    assert audit[-1]["policy_matched"] is True


@pytest.mark.asyncio
async def test_session_detail_replays_persisted_events(tmp_path, mock_llm_no_tools):
    agent = Agent(config=make_test_config(tmp_path), multitenant=False)

    async for _event in agent.run_event_stream("hello", session_id="replay-session"):
        pass

    detail = agent.sessions.detail("replay-session")
    assert detail is not None
    assert detail["session_id"] == "replay-session"
    assert any(event["type"] == "session_start" for event in detail["events"])


@pytest.mark.asyncio
async def test_context_compression_emits_auditable_event(tmp_path, mock_llm_no_tools):
    config = make_test_config(tmp_path)
    agent = Agent(config=config, multitenant=False)
    agent._config.react.sliding_window_size = 1
    history = [
        {"role": "user", "content": "initial question " + ("x" * 30000)},
        {"role": "assistant", "content": "older answer " + ("y" * 30000)},
        {"role": "user", "content": "follow up " + ("z" * 30000)},
    ]

    events = []
    async for event in agent.run_event_stream(
        "compress now " + ("q" * 30000),
        session_id="compression-session",
        history=history,
    ):
        events.append(event)

    compression_events = [
        event for event in events
        if event.metadata.get("compression_event") is True
    ]
    assert compression_events
    metadata = compression_events[0].metadata["compression"]
    assert metadata["compressed"] is True
    assert metadata["dropped_count"] > 0
