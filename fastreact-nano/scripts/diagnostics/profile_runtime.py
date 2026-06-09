#!/usr/bin/env python3
"""Collect a local runtime performance baseline without real LLM calls."""

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastreact import Agent, Config, LLMConfig, ReactConfig, ToolConfig
from fastreact.providers.litellm import LLMResponse, ToolCall


REPORT = ROOT / "runtime_baseline.json"


class BaselineLLM:
    def __init__(self):
        self.calls = 0

    async def chat(self, messages, tools=None, **kwargs):
        self.calls += 1
        last = messages[-1].get("content", "") if messages else ""
        lower = last.lower()
        if "read" in lower and self.calls % 2 == 1:
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(id="baseline-read", name="read_file", params={"path": str(ROOT / "README.md")})],
            )
        if "task" in lower and self.calls % 2 == 1:
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(id="baseline-task", name="task_create", params={"title": "Baseline task"})],
            )
        return LLMResponse(content="baseline complete")


def make_agent(tmp: Path) -> Agent:
    config = Config(
        llm=LLMConfig(api_key="baseline", api_base="http://localhost.invalid", model="baseline"),
        tools=ToolConfig(working_dir=tmp, protected_paths=[]),
        react=ReactConfig(max_iterations=4, enable_safety=False, enable_filesystem_memory=False),
    )
    agent = Agent(config=config, multitenant=False)
    fake_llm = BaselineLLM()
    agent._llm = fake_llm
    agent._core._llm = fake_llm
    return agent


async def run_case(agent: Agent, name: str, query: str) -> dict:
    started = time.perf_counter()
    first_ms = None
    final_ms = None
    events = []
    async for event in agent.run_event_stream(query, session_id=f"baseline-{name}"):
        if first_ms is None:
            first_ms = (time.perf_counter() - started) * 1000
        events.append(event)
        if event.type.value in ("session_end", "error"):
            final_ms = (time.perf_counter() - started) * 1000
    spans = agent.store.read("runtime_spans", limit=200, session_id=f"baseline-{name}")
    return {
        "case": name,
        "time_to_first_event_ms": round(first_ms or 0, 2),
        "time_to_final_ms": round(final_ms or 0, 2),
        "event_count": len(events),
        "span_totals_ms": _span_totals(spans),
    }


def _span_totals(spans: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for span in spans:
        name = span.get("name", "unknown")
        totals[name] = round(totals.get(name, 0) + float(span.get("duration_ms") or 0), 2)
    return totals


async def main() -> int:
    tmp = ROOT / "workspace" / "baseline"
    tmp.mkdir(parents=True, exist_ok=True)
    agent = make_agent(tmp)
    cases = [
        ("chat", "Say hello"),
        ("tool_read", "Read the project README"),
        ("task_tool", "Create a task for baseline"),
        ("mcp_lazy", "Say hello after MCP bootstrap"),
    ]
    results = [await run_case(agent, name, query) for name, query in cases]
    REPORT.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
    print("Runtime Baseline")
    for result in results:
        print(
            f"{result['case']:10} first={result['time_to_first_event_ms']:7.2f}ms "
            f"final={result['time_to_final_ms']:7.2f}ms events={result['event_count']}"
        )
    print(f"wrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
