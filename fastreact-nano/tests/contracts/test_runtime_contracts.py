import pytest

from fastreact import Agent, Config, LLMConfig, ReactConfig, ToolConfig
from fastreact.core.events import EventType


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
async def test_session_detail_replays_persisted_events(tmp_path, mock_llm_no_tools):
    agent = Agent(config=make_test_config(tmp_path), multitenant=False)

    async for _event in agent.run_event_stream("hello", session_id="replay-session"):
        pass

    detail = agent.sessions.detail("replay-session")
    assert detail is not None
    assert detail["session_id"] == "replay-session"
    assert any(event["type"] == "session_start" for event in detail["events"])
