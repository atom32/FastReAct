import pytest

from fastreact import Agent, Config, LLMConfig, ReactConfig, ToolConfig
from fastreact.core.events import EventType
from fastreact.core.tools import Tool
from fastreact.providers.litellm import LLMResponse, ToolCall


class ToolThenAnswerLLM:
    def __init__(self):
        self.calls = 0

    async def chat(self, messages, tools=None, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        id="runtime-task",
                        name="task_create",
                        params={"title": "Runtime integration task"},
                    )
                ],
            )
        return LLMResponse(content="Task created and ready.")


class DuplicateDigestWriteLLM:
    def __init__(self):
        self.calls = 0

    async def chat(self, messages, tools=None, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        id="digest-write-1",
                        name="pska_pska_write_candidates",
                        params={
                            "schema_version": "pska.candidates.v1",
                            "job_id": "job-digest",
                            "request_id": "batch-0",
                            "producer": "fastreact",
                            "source_refs": [{"source_item_id": "src_1", "chunk_id": "chk_1"}],
                            "memory_candidates": [{"kind": "agent_memory", "text": "One memory", "confidence": 0.8}],
                        },
                    ),
                    ToolCall(
                        id="digest-write-2",
                        name="pska_pska_write_candidates",
                        params={
                            "schema_version": "pska.candidates.v1",
                            "job_id": "job-digest",
                            "request_id": "batch-0-extra",
                            "producer": "fastreact",
                            "source_refs": [{"source_item_id": "src_1", "chunk_id": "chk_1"}],
                            "review_items": [{"review_type": "quality", "title": "Review", "proposal": {"note": "Second write"}}],
                        },
                    ),
                ],
            )
        return LLMResponse(content='{"ok": true, "write_calls": 1}')


class FakePskAWriteCandidatesTool(Tool):
    def __init__(self):
        self.calls = []

    @property
    def name(self) -> str:
        return "pska_pska_write_candidates"

    @property
    def description(self) -> str:
        return "Fake PSKA candidate writer."

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, user_context=None, **kwargs) -> str:
        self.calls.append(kwargs)
        return '{"ok": true}'


def make_config(tmp_path):
    return Config(
        llm=LLMConfig(api_key="test-key", api_base="http://localhost.invalid", model="test"),
        tools=ToolConfig(working_dir=tmp_path, protected_paths=[]),
        react=ReactConfig(
            max_iterations=4,
            enable_safety=False,
            enable_filesystem_memory=False,
        ),
    )


async def collect(agent, query, session_id):
    events = []
    async for event in agent.run_event_stream(query, session_id=session_id):
        events.append(event)
    return events


@pytest.mark.asyncio
async def test_runtime_loop_executes_task_tool_and_records_spans(tmp_path):
    agent = Agent(config=make_config(tmp_path), multitenant=False)
    fake_llm = ToolThenAnswerLLM()
    agent._llm = fake_llm
    agent._core._llm = fake_llm

    events = await collect(agent, "Create a task", "runtime-loop-session")
    event_types = [event.type for event in events]

    assert event_types[0] == EventType.SESSION_START
    assert EventType.TOOL_CALL in event_types
    assert EventType.TOOL_RESULT in event_types
    assert events[-1].type == EventType.SESSION_END
    assert events[-1].content == "Task created and ready."

    tasks = agent.tasks.list(session_id="")
    assert any(task["title"] == "Runtime integration task" for task in tasks)

    span_names = {
        span["name"]
        for span in agent.store.read("runtime_spans", session_id="runtime-loop-session")
    }
    assert {"context.assembly", "llm.step", "tool.execution"}.issubset(span_names)


@pytest.mark.asyncio
async def test_pska_digest_runtime_budget_suppresses_duplicate_write_calls(tmp_path):
    agent = Agent(config=make_config(tmp_path), multitenant=False)
    fake_llm = DuplicateDigestWriteLLM()
    write_tool = FakePskAWriteCandidatesTool()
    agent._llm = fake_llm
    agent._core._llm = fake_llm
    agent._tools.register(write_tool)

    events = []
    async for event in agent.run_event_stream(
        "Digest this PSKA batch",
        skills=["pska_digest"],
        session_id="digest-budget-session",
        user_key="pska:user_primary",
        run_metadata={
            "caller": "pska_digest_worker",
            "purpose": "digest",
            "pska_job_id": "job-digest",
            "tool_budget": {
                "pska_pska_write_candidates": 1,
                "pska_pska_job_context": 1,
            },
        },
    ):
        events.append(event)

    write_call_events = [
        event
        for event in events
        if event.type == EventType.TOOL_CALL and event.tool_name == "pska_pska_write_candidates"
    ]
    denied_events = [
        event
        for event in events
        if event.type == EventType.THINK and event.metadata.get("tool_budget_denied")
    ]

    assert len(write_call_events) == 1
    assert write_call_events[0].metadata["call_id"] == "digest-write-1"
    assert len(write_tool.calls) == 1
    assert write_tool.calls[0]["memory_candidates"][0]["text"] == "One memory"
    assert denied_events
    assert denied_events[0].metadata["tool_name"] == "pska_pska_write_candidates"
    assert events[-1].type == EventType.SESSION_END
