"""Run-scoped tool visibility and execution policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastreact.core.tools import ToolRegistry


@dataclass(frozen=True)
class RunToolPolicy:
    mode: str = "default"
    allowed_tools: frozenset[str] = field(default_factory=frozenset)

    @property
    def active(self) -> bool:
        return self.mode in {"none", "allowlist"}

    def allows(self, tool_name: str) -> bool:
        if self.mode == "none":
            return False
        if self.mode == "allowlist":
            return tool_name in self.allowed_tools
        return True

    def to_metadata(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"mode": self.mode}
        if self.mode == "allowlist":
            payload["allowed_tools"] = sorted(self.allowed_tools)
        if self.mode == "none":
            payload["allowed_tools"] = []
        return payload


def normalize_tool_policy(value: Any) -> RunToolPolicy:
    if not isinstance(value, dict):
        return RunToolPolicy()
    mode = str(value.get("mode") or "default").strip().lower()
    if mode in {"none", "off", "disabled", "no_tools"}:
        return RunToolPolicy(mode="none")
    if mode in {"allowlist", "allowed_tools", "allow"}:
        allowed = {
            str(item).strip()
            for item in value.get("allowed_tools", []) or []
            if str(item).strip()
        }
        return RunToolPolicy(mode="allowlist", allowed_tools=frozenset(allowed))
    return RunToolPolicy()


def filter_tool_registry(registry: ToolRegistry, policy: RunToolPolicy) -> ToolRegistry:
    if not policy.active:
        return registry
    filtered = ToolRegistry()
    for name in registry.list_all():
        if not policy.allows(name):
            continue
        tool = registry.get(name)
        if tool is not None:
            filtered.register(tool)
    return filtered


def tool_policy_denial(tool_name: str, policy: RunToolPolicy) -> str | None:
    if policy.allows(tool_name):
        return None
    if policy.mode == "none":
        return "run tool_policy mode=none disables all tools"
    if policy.mode == "allowlist":
        return f"tool '{tool_name}' is not in run tool_policy allowed_tools"
    return None
