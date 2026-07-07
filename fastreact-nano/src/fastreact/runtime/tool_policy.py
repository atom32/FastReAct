"""Run-scoped tool visibility and execution policy."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from fastreact.core.tools import ToolRegistry

SCOPED_READ_TOOL_NAMES = frozenset({
    "pska_pska_search",
    "pska_pska_read_evidence_context",
    "pska_pska_graph_context",
    "pska_pska_digest_context",
})


@dataclass(frozen=True)
class RunToolPolicy:
    mode: str = "default"
    allowed_tools: frozenset[str] = field(default_factory=frozenset)
    scope: dict[str, Any] = field(default_factory=dict)

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
        if self.scope:
            payload["scope"] = deepcopy(self.scope)
        return payload


def normalize_tool_policy(value: Any) -> RunToolPolicy:
    if not isinstance(value, dict):
        return RunToolPolicy()
    mode = str(value.get("mode") or "default").strip().lower()
    scope = _normalize_policy_scope(value.get("scope"))
    if mode in {"none", "off", "disabled", "no_tools"}:
        return RunToolPolicy(mode="none", scope=scope)
    if mode in {"allowlist", "allowed_tools", "allow"}:
        allowed = {
            str(item).strip()
            for item in value.get("allowed_tools", []) or []
            if str(item).strip()
        }
        return RunToolPolicy(mode="allowlist", allowed_tools=frozenset(allowed), scope=scope)
    return RunToolPolicy(scope=scope)


def apply_tool_policy_scope(tool_name: str, tool_params: dict[str, Any], policy: RunToolPolicy) -> tuple[dict[str, Any], bool]:
    """Inject run-scoped PSKA corpus bounds into MCP read-tool arguments.

    The LLM may choose query terms and tool-specific limits, but it must not
    widen the knowledge/source scope selected by the caller.
    """
    params = dict(tool_params or {})
    if not policy.scope or not tool_policy_scope_applies(tool_name):
        return params, False

    policy_scope = policy.scope
    nested_scope = dict(params.get("scope") or {}) if isinstance(params.get("scope"), dict) else {}
    injected = False
    scope_mode = str(policy_scope.get("scope_mode") or policy_scope.get("mode") or "").strip().lower()
    hard_scope = scope_mode == "hard"

    knowledge_base_ids = _string_list(policy_scope.get("knowledge_base_ids"))
    if knowledge_base_ids:
        params["knowledge_base_ids"] = knowledge_base_ids
        nested_scope["knowledge_base_ids"] = knowledge_base_ids
        injected = True

    policy_source_ids = _string_list(policy_scope.get("source_item_ids"))
    if policy_source_ids:
        policy_source_set = set(policy_source_ids)
        requested_source_ids = _string_list(params.get("source_item_ids")) or _string_list(
            nested_scope.get("source_item_ids")
        )
        if hard_scope:
            source_item_ids = policy_source_ids
        elif requested_source_ids:
            source_item_ids = [source_id for source_id in requested_source_ids if source_id in policy_source_set]
        else:
            source_item_ids = policy_source_ids
        params["source_item_ids"] = source_item_ids
        nested_scope["source_item_ids"] = source_item_ids
        if hard_scope and "source_refs" in params:
            params["source_refs"] = _filter_source_refs(params.get("source_refs"), policy_source_set)
        injected = True

    if scope_mode:
        params["scope_mode"] = scope_mode
        nested_scope["scope_mode"] = scope_mode
        nested_scope["mode"] = scope_mode
        injected = True

    if nested_scope:
        params["scope"] = nested_scope

    return params, injected


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


def tool_policy_scope_applies(tool_name: str) -> bool:
    return str(tool_name or "") in SCOPED_READ_TOOL_NAMES


def _normalize_policy_scope(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    scope: dict[str, Any] = {}
    knowledge_base_ids = _string_list(value.get("knowledge_base_ids"))
    source_item_ids = _string_list(value.get("source_item_ids"))
    mode = str(value.get("mode") or value.get("scope_mode") or "").strip().lower()
    if mode:
        scope["mode"] = mode
        scope["scope_mode"] = mode
    if knowledge_base_ids:
        scope["knowledge_base_ids"] = knowledge_base_ids
    if source_item_ids:
        scope["source_item_ids"] = source_item_ids
    return scope


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = list(value)
    else:
        values = [value]
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _filter_source_refs(value: Any, allowed_source_ids: set[str]) -> Any:
    if isinstance(value, list):
        filtered = []
        for item in value:
            item_source_id = _source_ref_id(item)
            if item_source_id and item_source_id not in allowed_source_ids:
                continue
            filtered.append(item)
        return filtered
    item_source_id = _source_ref_id(value)
    if item_source_id and item_source_id not in allowed_source_ids:
        return []
    return value


def _source_ref_id(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if not isinstance(value, dict):
        return None
    for key in ("source_item_id", "source_ref"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None
