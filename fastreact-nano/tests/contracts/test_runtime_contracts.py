import pytest

from fastreact import Agent, Config, LLMConfig, PolicyConfig, ReactConfig, ToolConfig
from fastreact.core.events import EventType
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
    assert agent.tool_executor.resolve_approval(request_id, approved=True)


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
