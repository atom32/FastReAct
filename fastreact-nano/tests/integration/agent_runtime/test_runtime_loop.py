import pytest

from fastreact import Agent, Config, LLMConfig, ReactConfig, ToolConfig
from fastreact.core.events import EventType
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
