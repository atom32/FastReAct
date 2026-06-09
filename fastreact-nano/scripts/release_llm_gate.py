#!/usr/bin/env python3
"""
Release LLM efficiency gate.

This script is intentionally outside pytest's default collection. It reads
provider credentials from ~/api_key.txt, runs a small real-LLM smoke suite,
records latency, asks an LLM judge to validate answer usefulness, and exits
non-zero if any release gate fails.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from time import perf_counter
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from fastreact import Agent, Config  # noqa: E402
from fastreact.core.events import EventType  # noqa: E402
from fastreact.providers.litellm import LiteLLMProvider  # noqa: E402


FIRST_EVENT_LIMIT_MS = 3000
FINAL_LIMIT_MS = 30000
API_KEY_FILE = Path.home() / "api_key.txt"
REPORT_FILE = PROJECT_ROOT / "release_llm_report.json"


@dataclass
class GateCase:
    name: str
    query: str
    expected: list[str]
    require_tool: bool = False
    followup_query: str | None = None


@dataclass
class GateResult:
    name: str
    passed: bool
    time_to_first_event_ms: float
    time_to_final_ms: float
    event_count: int
    final_answer_chars: int
    judge_passed: bool
    reason: str = ""


def load_api_env(path: Path = API_KEY_FILE) -> None:
    """Load credentials from JSON or KEY=VALUE lines without printing secrets."""
    if not path.exists():
        raise FileNotFoundError(f"Missing API key file: {path}")

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError(f"API key file is empty: {path}")

    data: dict[str, Any]
    if raw.startswith("{"):
        data = json.loads(raw)
    else:
        data = {}
        bare_values = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip().strip('"').strip("'")
            else:
                bare_values.append(line)

        for value in bare_values:
            if value.startswith(("http://", "https://")):
                data.setdefault("api_base", value)
            elif value.startswith(("sk-", "sess-")):
                data.setdefault("api_key", value)
            elif "model" not in data:
                data["model"] = value

    aliases = {
        "api_key": "FASTRACT_API_KEY",
        "api_base": "FASTRACT_API_BASE",
        "base_url": "FASTRACT_API_BASE",
        "model": "FASTRACT_MODEL",
    }

    for key, value in data.items():
        if value is None:
            continue
        env_key = aliases.get(key, key)
        os.environ[env_key] = str(value)

    if not (os.getenv("FASTRACT_API_KEY") or os.getenv("OPENAI_API_KEY")):
        raise ValueError("No API key found in ~/api_key.txt")


async def collect_agent_run(agent: Agent, case: GateCase) -> tuple[list, str, float, float]:
    start = perf_counter()
    first_event_ms = -1.0
    events = []
    final_answer = ""

    async def run_once(query: str, history: list[dict] | None = None):
        nonlocal first_event_ms, final_answer
        async for event in agent.run_event_stream(query, history=history):
            if first_event_ms < 0:
                first_event_ms = (perf_counter() - start) * 1000
            events.append(event)
            if event.type == EventType.SESSION_END:
                final_answer = event.content

    await asyncio.wait_for(run_once(case.query), timeout=FINAL_LIMIT_MS / 1000)

    if case.followup_query:
        history = [
            {"role": "user", "content": case.query},
            {"role": "assistant", "content": final_answer},
        ]
        await asyncio.wait_for(run_once(case.followup_query, history), timeout=FINAL_LIMIT_MS / 1000)

    final_ms = (perf_counter() - start) * 1000
    return events, final_answer, first_event_ms, final_ms


async def judge_answer(
    config: Config,
    case: GateCase,
    final_answer: str,
    events: list,
) -> tuple[bool, str]:
    judge = LiteLLMProvider(
        model=config.llm.model,
        api_base=config.llm.api_base,
        api_key=config.llm.api_key,
        temperature=0,
        max_tokens=512,
    )
    event_summary = [
        {
            "type": event.type.value,
            "tool_name": event.tool_name,
            "content_chars": len(event.content or ""),
        }
        for event in events
    ]
    prompt = {
        "task": "Judge whether the assistant answer is useful and satisfies the expected points. Return compact JSON only.",
        "case": case.name,
        "question": case.query,
        "expected_points": case.expected,
        "final_answer": final_answer,
        "event_summary": event_summary,
        "schema": {"pass": "boolean", "reason": "short string"},
    }
    response = await asyncio.wait_for(
        judge.chat([
            {"role": "system", "content": "You are a strict release-gate judge. Return JSON only."},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ]),
        timeout=20,
    )
    content = (response.content or "").strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return False, "judge returned non-JSON"
    return bool(parsed.get("pass")), str(parsed.get("reason", ""))


async def run_case(config: Config, case: GateCase) -> GateResult:
    agent = Agent(config=config)
    try:
        events, final_answer, first_ms, final_ms = await collect_agent_run(agent, case)
        event_types = [event.type for event in events]

        if first_ms < 0:
            return GateResult(case.name, False, -1, final_ms, len(events), 0, False, "no events")
        if first_ms > FIRST_EVENT_LIMIT_MS:
            return GateResult(case.name, False, first_ms, final_ms, len(events), len(final_answer), False, "first event timeout")
        if final_ms > FINAL_LIMIT_MS:
            return GateResult(case.name, False, first_ms, final_ms, len(events), len(final_answer), False, "final timeout")
        if EventType.SESSION_START not in event_types or EventType.SESSION_END not in event_types:
            return GateResult(case.name, False, first_ms, final_ms, len(events), len(final_answer), False, "missing lifecycle events")
        if case.require_tool and (EventType.TOOL_CALL not in event_types or EventType.TOOL_RESULT not in event_types):
            return GateResult(case.name, False, first_ms, final_ms, len(events), len(final_answer), False, "missing tool events")
        if not final_answer.strip():
            return GateResult(case.name, False, first_ms, final_ms, len(events), 0, False, "empty final answer")

        judge_passed, reason = await judge_answer(config, case, final_answer, events)
        return GateResult(
            name=case.name,
            passed=judge_passed,
            time_to_first_event_ms=round(first_ms, 2),
            time_to_final_ms=round(final_ms, 2),
            event_count=len(events),
            final_answer_chars=len(final_answer),
            judge_passed=judge_passed,
            reason=reason,
        )
    finally:
        await agent.close_mcp_servers()


async def main_async() -> int:
    load_api_env()
    config = Config.from_env()

    cases = [
        GateCase(
            name="provider-basic",
            query="Reply with one concise sentence explaining what FastReAct is.",
            expected=["concise", "FastReAct", "agent"],
        ),
        GateCase(
            name="agent-event-stream",
            query="Answer briefly: what is 2 + 2?",
            expected=["4"],
        ),
        GateCase(
            name="tool-call-read",
            query="Use the read_file tool to read README.md, then summarize the project in one sentence.",
            expected=["used file content", "summary"],
            require_tool=True,
        ),
        GateCase(
            name="multi-turn-followup",
            query="Remember this release keyword: blue-lantern.",
            followup_query="What release keyword did I ask you to remember?",
            expected=["blue-lantern"],
        ),
    ]

    results = []
    for case in cases:
        print(f"[release-llm] running {case.name}...")
        results.append(await run_case(config, case))

    print("\nRelease LLM Gate Summary")
    print("case                 pass  first_ms  final_ms  events  chars  reason")
    print("-" * 78)
    for result in results:
        print(
            f"{result.name:<20} {str(result.passed):<5} "
            f"{result.time_to_first_event_ms:>8.2f} "
            f"{result.time_to_final_ms:>8.2f} "
            f"{result.event_count:>6} "
            f"{result.final_answer_chars:>5} "
            f"{result.reason[:48]}"
        )

    REPORT_FILE.write_text(
        json.dumps([asdict(result) for result in results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n[release-llm] wrote non-sensitive report: {REPORT_FILE}")

    return 0 if all(result.passed for result in results) else 1


def main() -> int:
    try:
        return asyncio.run(main_async())
    except Exception as exc:
        print(f"[release-llm] failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
