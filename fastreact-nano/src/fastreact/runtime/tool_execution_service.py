"""Tool execution boundary for safety, approvals, audit, and result shaping."""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any, Optional, TYPE_CHECKING

from fastreact.core.events import AgentEvent
from fastreact.core.safety import SafetyDecision, SafetyLevel
from fastreact.core.tools import ValidationError
from fastreact.runtime.tool_output_governance import (
    GovernedToolOutput,
    govern_mcp_tool_output,
    is_mcp_tool,
    retry_params_for_tool,
)
from fastreact.runtime.tool_policy import tool_policy_scope_applies

if TYPE_CHECKING:
    from fastreact.agent import Agent
    from fastreact.core.multitenant import UserContext


@dataclass
class ToolExecutionResult:
    tool_name: str
    result: str
    context_result: Optional[str] = None
    allowed: bool = True
    blocked: bool = False
    error: Optional[str] = None
    request_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolArgumentResolution:
    tool_name: str
    original_params: dict[str, Any]
    params: dict[str, Any]
    validation_error: Optional[str] = None
    missing_required: list[str] = field(default_factory=list)
    repaired: bool = False
    invalid: bool = False
    repair_reason: Optional[str] = None

    def to_metadata(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "tool_name": self.tool_name,
            "original_tool_args": self.original_params,
            "effective_tool_args": self.params,
            "validation_error": self.validation_error,
            "missing_required": self.missing_required,
            "tool_args_repaired": self.repaired,
            "invalid_tool_args": self.invalid,
        }
        if self.repair_reason:
            metadata["repair_reason"] = self.repair_reason
        return metadata


class ToolExecutionService:
    """Centralized tool execution with safety policy integration."""

    DEFAULT_APPROVAL_TIMEOUT_SECONDS = 300.0

    def __init__(self, agent: "Agent"):
        self._agent = agent
        self._pending_approvals: dict[str, asyncio.Future] = {}
        self._approval_records: dict[str, dict[str, Any]] = {}

    @property
    def approval_timeout_seconds(self) -> float:
        config = getattr(self._agent, "_config", None)
        service = getattr(config, "service", None)
        return float(getattr(service, "approval_timeout_seconds", self.DEFAULT_APPROVAL_TIMEOUT_SECONDS))

    def assess(
        self,
        tool_name: str,
        tool_params: dict[str, Any],
        session_id: str,
        user_key: Optional[str] = None,
        tenant_key: Optional[str] = None,
    ) -> tuple[SafetyDecision | None, AgentEvent | None]:
        if not self._agent._safety_policy:
            return None, None

        decision = self._agent._safety_policy.check(
            tool_name=tool_name,
            args=tool_params,
            user_key=user_key,
            tenant_key=tenant_key,
        )
        if decision.level != SafetyLevel.DANGER:
            return decision, None

        request_id = f"approval-{uuid.uuid4().hex[:10]}"
        future = asyncio.get_running_loop().create_future()
        created_at = self._now()
        timeout_seconds = self.approval_timeout_seconds
        expires_at = created_at + timedelta(seconds=timeout_seconds)
        self._pending_approvals[request_id] = future
        self._approval_records[request_id] = {
            "request_id": request_id,
            "session_id": session_id,
            "tool_name": tool_name,
            "tool_args": tool_params,
            "reason": decision.reason,
            "decision_level": decision.level.value,
            "policy_scope": decision.policy_scope,
            "policy_action": decision.policy_action,
            "policy_matched": decision.policy_matched,
            "status": "pending",
            "approved": None,
            "expired": False,
            "timeout_seconds": timeout_seconds,
            "created_at": self._format_iso(created_at),
            "expires_at": self._format_iso(expires_at),
            "resolved_at": None,
        }
        self._persist_approval(request_id)
        event = AgentEvent.ask_user(
            decision.reason,
            tool_name,
            tool_params,
            session_id,
        )
        event.metadata.update({
            "request_id": request_id,
            "decision_level": decision.level.value,
            "pattern_matched": decision.pattern_matched,
            "timeout_seconds": timeout_seconds,
            "expires_at": self._format_iso(expires_at),
            "policy_scope": decision.policy_scope,
            "policy_action": decision.policy_action,
            "policy_matched": decision.policy_matched,
        })
        self._audit(tool_name, tool_params, decision, None, session_id, request_id=request_id)
        return decision, event

    async def wait_for_approval(self, request_id: str, timeout_seconds: Optional[float] = None) -> bool:
        future = self._pending_approvals.get(request_id)
        if not future:
            return False
        timeout_seconds = self.approval_timeout_seconds if timeout_seconds is None else timeout_seconds
        try:
            result = await asyncio.wait_for(future, timeout=timeout_seconds)
            if isinstance(result, dict):
                return bool(result.get("approved"))
            return bool(result)
        except asyncio.TimeoutError:
            self._expire_approval(request_id, timeout_seconds)
            return False
        finally:
            self._pending_approvals.pop(request_id, None)

    def resolve_approval(self, request_id: str, approved: bool, reason: str = "") -> bool:
        future = self._pending_approvals.get(request_id)
        if not future or future.done():
            return False
        future.set_result({"approved": approved, "reason": reason})
        if request_id in self._approval_records:
            self._approval_records[request_id]["status"] = "approved" if approved else "denied"
            self._approval_records[request_id]["approved"] = approved
            self._approval_records[request_id]["expired"] = False
            self._approval_records[request_id]["resolved_at"] = self._now_iso()
            self._approval_records[request_id]["resolution_reason"] = reason
            self._persist_approval(request_id)
        return True

    def list_approvals(self) -> list[dict[str, Any]]:
        records = dict(self._approval_records)
        if hasattr(self._agent, "store"):
            records.update(self._agent.store.latest_snapshots("approvals", "request_id"))
        return list(records.values())

    def _expire_approval(self, request_id: str, timeout_seconds: float) -> None:
        record = self._approval_records.get(request_id)
        if not record or record.get("status") != "pending":
            return
        record["status"] = "expired"
        record["approved"] = False
        record["expired"] = True
        record["resolved_at"] = self._now_iso()
        record["resolution_reason"] = "approval_timeout"
        record["timeout_seconds"] = timeout_seconds
        self._persist_approval(request_id)

    def _persist_approval(self, request_id: str) -> None:
        if not hasattr(self._agent, "store"):
            return
        record = self._approval_records.get(request_id)
        if record:
            self._agent.store.upsert_snapshot("approvals", "request_id", record)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _format_iso(self, value: datetime) -> str:
        return value.isoformat()

    def _now_iso(self) -> str:
        return self._format_iso(self._now())

    async def execute(
        self,
        tool_name: str,
        tool_params: dict[str, Any],
        session_id: str,
        user_context: Optional["UserContext"] = None,
        user_query: Optional[str] = None,
        decision: SafetyDecision | None = None,
        approved: Optional[bool] = None,
        request_id: Optional[str] = None,
        argument_resolution: Optional[ToolArgumentResolution] = None,
    ) -> tuple[ToolExecutionResult, AgentEvent]:
        started = perf_counter()
        tool = self._agent._tools.get(tool_name) if hasattr(self._agent, "_tools") else None
        argument_resolution = argument_resolution or self.resolve_tool_arguments(
            tool_name=tool_name,
            tool_params=tool_params,
            user_query=user_query,
        )
        tool_params = argument_resolution.params

        if argument_resolution.invalid:
            result, metadata = self._invalid_tool_args_payload(argument_resolution)
            execution = ToolExecutionResult(
                tool_name=tool_name,
                result=result,
                context_result=result,
                allowed=False,
                blocked=True,
                error=argument_resolution.validation_error,
                request_id=request_id,
                metadata=metadata,
            )
            self._audit(tool_name, tool_params, decision, False, session_id, result, started, request_id)
            event = AgentEvent.tool_result(tool_name, result, session_id)
            event.tool_args = argument_resolution.original_params
            event.metadata.update({
                "duration_ms": round((perf_counter() - started) * 1000, 2),
                "decision_level": decision.level.value if decision else "none",
                "approved": approved,
                "request_id": request_id,
            })
            event.metadata.update(metadata)
            return execution, event

        if self._agent._safety_policy and decision is None:
            user_key = getattr(user_context, "user_key", None) if user_context else None
            tenant_key = (
                getattr(user_context, "tenant_key", None)
                or getattr(user_context, "tenant_id", None)
            ) if user_context else None
            decision = self._agent._safety_policy.check(
                tool_name=tool_name,
                args=tool_params,
                user_key=user_key,
                tenant_key=tenant_key,
            )

        if decision and decision.level == SafetyLevel.FORBIDDEN:
            result = f"[SAFETY_BLOCKED] {decision.reason}"
            execution = ToolExecutionResult(
                tool_name=tool_name,
                result=result,
                context_result=result,
                allowed=False,
                blocked=True,
                request_id=request_id,
            )
            self._audit(tool_name, tool_params, decision, False, session_id, result, started, request_id)
            event = AgentEvent.tool_result(tool_name, result, session_id)
            event.tool_args = tool_params
            return execution, event

        if decision and decision.level == SafetyLevel.DANGER and not approved:
            result = f"[SAFETY_DENIED] {decision.reason}"
            execution = ToolExecutionResult(
                tool_name=tool_name,
                result=result,
                context_result=result,
                allowed=False,
                blocked=True,
                request_id=request_id,
            )
            self._audit(tool_name, tool_params, decision, False, session_id, result, started, request_id)
            event = AgentEvent.tool_result(tool_name, result, session_id)
            event.tool_args = tool_params
            return execution, event

        try:
            governed = await self._execute_and_govern(
                tool=tool,
                tool_name=tool_name,
                tool_params=tool_params,
                session_id=session_id,
                user_context=user_context,
            )
            result = governed.result
            execution = ToolExecutionResult(
                tool_name=tool_name,
                result=result,
                context_result=governed.context_result,
                metadata={**governed.metadata, **self._argument_metadata(argument_resolution)},
            )
        except Exception as exc:
            raw_result = f"[ERROR] {type(exc).__name__}: {exc}"
            if isinstance(exc, ValidationError):
                invalid_resolution = ToolArgumentResolution(
                    tool_name=tool_name,
                    original_params=argument_resolution.original_params,
                    params=tool_params,
                    validation_error=str(exc),
                    missing_required=self._missing_required_from_errors(getattr(exc, "errors", [])),
                    invalid=True,
                )
                result, metadata = self._invalid_tool_args_payload(invalid_resolution)
                execution = ToolExecutionResult(
                    tool_name=tool_name,
                    result=result,
                    context_result=result,
                    allowed=False,
                    blocked=True,
                    error=str(exc),
                    request_id=request_id,
                    metadata=metadata,
                )
                self._audit(tool_name, tool_params, decision, approved, session_id, result, started, request_id)
                event = AgentEvent.tool_result(tool_name, result, session_id)
                event.tool_args = invalid_resolution.original_params
                event.metadata.update({
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                    "decision_level": decision.level.value if decision else "none",
                    "approved": approved,
                    "request_id": request_id,
                })
                event.metadata.update(metadata)
                return execution, event

            governed = self._govern_mcp_result(
                tool=tool,
                tool_name=tool_name,
                tool_params=tool_params,
                result=raw_result,
                session_id=session_id,
            )
            result = governed.result
            execution = ToolExecutionResult(
                tool_name=tool_name,
                result=result,
                context_result=governed.context_result,
                error=None if governed.issue else str(exc),
                metadata={**governed.metadata, **self._argument_metadata(argument_resolution)},
            )

        self._audit(tool_name, tool_params, decision, approved, session_id, result, started, request_id)
        event = AgentEvent.tool_result(tool_name, result, session_id)
        event.tool_args = tool_params
        event.metadata.update({
            "duration_ms": round((perf_counter() - started) * 1000, 2),
            "decision_level": decision.level.value if decision else "none",
            "approved": approved,
            "request_id": request_id,
        })
        event.metadata.update(execution.metadata)
        return execution, event

    def resolve_tool_arguments(
        self,
        *,
        tool_name: str,
        tool_params: dict[str, Any],
        user_query: Optional[str] = None,
        original_tool_params: Optional[dict[str, Any]] = None,
    ) -> ToolArgumentResolution:
        params = dict(tool_params or {}) if isinstance(tool_params, dict) else {}
        original_params = (
            dict(original_tool_params)
            if isinstance(original_tool_params, dict)
            else dict(params)
        )
        tool = self._agent._tools.get(tool_name) if hasattr(self._agent, "_tools") else None
        if not tool:
            return ToolArgumentResolution(tool_name=tool_name, original_params=original_params, params=params)

        errors = tool.validate_params(params)
        if not errors:
            return ToolArgumentResolution(tool_name=tool_name, original_params=original_params, params=params)

        missing_required = self._missing_required_from_errors(errors)
        validation_error = f"Validation errors: {', '.join(errors)}"
        if (
            "query" in missing_required
            and self._is_search_tool(tool_name)
            and self._query_missing(params)
            and isinstance(user_query, str)
            and user_query.strip()
        ):
            repaired_params = dict(params)
            repaired_params["query"] = user_query.strip()
            repaired_errors = tool.validate_params(repaired_params)
            if not repaired_errors:
                return ToolArgumentResolution(
                    tool_name=tool_name,
                    original_params=original_params,
                    params=repaired_params,
                    validation_error=validation_error,
                    missing_required=missing_required,
                    repaired=True,
                    repair_reason="filled_missing_query_from_run_query",
                )
            errors = repaired_errors
            missing_required = self._missing_required_from_errors(errors)
            validation_error = f"Validation errors: {', '.join(errors)}"

        return ToolArgumentResolution(
            tool_name=tool_name,
            original_params=original_params,
            params=params,
            validation_error=validation_error,
            missing_required=missing_required,
            invalid=True,
        )

    def _argument_metadata(self, resolution: ToolArgumentResolution) -> dict[str, Any]:
        if not resolution.repaired and not resolution.invalid:
            return {}
        metadata = resolution.to_metadata()
        metadata["tool_arg_validation"] = resolution.to_metadata()
        metadata["validation_error"] = resolution.validation_error
        metadata["tool_args_repaired"] = resolution.repaired
        metadata["invalid_tool_args"] = resolution.invalid
        return metadata

    def _invalid_tool_args_payload(self, resolution: ToolArgumentResolution) -> tuple[str, dict[str, Any]]:
        metadata = self._argument_metadata(resolution)
        metadata["invalid_tool_args"] = True
        metadata["tool_arg_validation"]["invalid_tool_args"] = True
        payload = {
            "type": "tool_argument_issue",
            "error_code": "invalid_tool_args",
            "tool_name": resolution.tool_name,
            "validation_error": resolution.validation_error,
            "missing_required": resolution.missing_required,
            "retry": {
                "recommended": True,
                "hint": "Re-plan the tool call with all required parameters from the tool schema.",
            },
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True), metadata

    def _missing_required_from_errors(self, errors: list[str]) -> list[str]:
        missing: list[str] = []
        prefix = "Missing required parameter:"
        for error in errors:
            if not isinstance(error, str) or not error.startswith(prefix):
                continue
            field = error[len(prefix):].strip()
            if field:
                missing.append(field)
        return missing

    def _is_search_tool(self, tool_name: str) -> bool:
        normalized = str(tool_name or "").lower().replace(".", "_").replace("-", "_")
        return normalized == "search" or normalized.endswith("_search")

    def _query_missing(self, params: dict[str, Any]) -> bool:
        value = params.get("query")
        return value is None or (isinstance(value, str) and not value.strip())

    async def _execute_and_govern(
        self,
        *,
        tool: Any,
        tool_name: str,
        tool_params: dict[str, Any],
        session_id: str,
        user_context: Optional["UserContext"],
    ) -> GovernedToolOutput:
        result = await self._agent._tools.execute(
            tool_name,
            tool_params,
            user_context=user_context,
        )
        result, scope_result_metadata = self._enforce_hard_scope_on_result(
            tool_name=tool_name,
            tool_params=tool_params,
            result=result,
        )
        governed = self._govern_mcp_result(
            tool=tool,
            tool_name=tool_name,
            tool_params=tool_params,
            result=result,
            session_id=session_id,
        )
        governed.metadata.update(scope_result_metadata)
        if not governed.issue or not is_mcp_tool(tool):
            return governed

        retry_attempts = max(
            0,
            int(getattr(getattr(self._agent._config, "react", None), "mcp_tool_output_retry_attempts", 1)),
        )
        if retry_attempts <= 0:
            return governed

        original_issue = dict(governed.metadata.get("tool_output_governance", {}))
        current_params = dict(tool_params)
        current_governed = governed
        attempts = 0
        for _ in range(retry_attempts):
            retry_params = retry_params_for_tool(
                current_params,
                getattr(tool, "parameters", None),
                self._mcp_output_budget_chars,
            )
            if not retry_params:
                break
            attempts += 1
            retry_result = await self._agent._tools.execute(
                tool_name,
                retry_params,
                user_context=user_context,
            )
            retry_result, retry_scope_metadata = self._enforce_hard_scope_on_result(
                tool_name=tool_name,
                tool_params=retry_params,
                result=retry_result,
            )
            retry_governed = self._govern_mcp_result(
                tool=tool,
                tool_name=tool_name,
                tool_params=retry_params,
                result=retry_result,
                session_id=session_id,
            )
            retry_governed.metadata.update(retry_scope_metadata)
            retry_metadata = {
                "retried": True,
                "retry_attempts": attempts,
                "retry_params": self._changed_retry_params(current_params, retry_params),
                "previous_issue": original_issue,
            }
            retry_governed.metadata.setdefault("tool_output_governance", {}).update(retry_metadata)
            if not retry_governed.issue:
                retry_governed.metadata["tool_output_governance"]["recovered"] = True
                return retry_governed
            retry_governed.metadata["tool_output_governance"]["recovered"] = False
            current_params = retry_params
            current_governed = retry_governed

        if attempts == 0:
            return current_governed
        current_governed.metadata.setdefault("tool_output_governance", {}).update({
            "retried": attempts > 0,
            "retry_attempts": attempts,
            "recovered": False,
            "previous_issue": original_issue,
        })
        return current_governed

    def _govern_mcp_result(
        self,
        *,
        tool: Any,
        tool_name: str,
        tool_params: dict[str, Any],
        result: Any,
        session_id: str,
    ) -> GovernedToolOutput:
        if not is_mcp_tool(tool):
            text = result if isinstance(result, str) else str(result)
            return GovernedToolOutput(result=text, context_result=text)
        return govern_mcp_tool_output(
            tool_name=tool_name,
            tool_params=tool_params,
            tool_schema=getattr(tool, "parameters", None),
            result=result,
            configured_budget=self._mcp_output_budget_chars,
            preview_chars=self._mcp_output_preview_chars,
            session_id=session_id,
            store=getattr(self._agent, "store", None),
        )

    @property
    def _mcp_output_budget_chars(self) -> int:
        react = getattr(getattr(self._agent, "_config", None), "react", None)
        return int(getattr(react, "mcp_tool_output_budget_chars", 20000))

    @property
    def _mcp_output_preview_chars(self) -> int:
        react = getattr(getattr(self._agent, "_config", None), "react", None)
        return int(getattr(react, "mcp_tool_output_preview_chars", 1200))

    def _changed_retry_params(self, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        changed: dict[str, Any] = {}
        for key, value in after.items():
            if before.get(key) != value and key.startswith("max_"):
                changed[key] = value
        return changed

    def _enforce_hard_scope_on_result(
        self,
        *,
        tool_name: str,
        tool_params: dict[str, Any],
        result: Any,
    ) -> tuple[Any, dict[str, Any]]:
        allowed_source_ids = self._hard_scope_source_item_ids(tool_name, tool_params)
        if not allowed_source_ids:
            return result, {}
        text = result if isinstance(result, str) else str(result)
        parsed = self._try_parse_json(text)
        if parsed is None:
            return result, {
                "tool_policy_scope_result_filter": {
                    "applied": False,
                    "reason": "non_json_result",
                    "allowed_source_item_ids": sorted(allowed_source_ids),
                }
            }
        filtered, removed = self._filter_out_of_scope_source_refs(parsed, allowed_source_ids)
        metadata = {
            "tool_policy_scope_result_filter": {
                "applied": True,
                "allowed_source_item_ids": sorted(allowed_source_ids),
                "removed_source_ref_count": removed,
            }
        }
        if removed <= 0:
            return result, metadata
        filtered = self._annotate_scope_filter_notice(
            filtered,
            allowed_source_ids=allowed_source_ids,
            removed=removed,
        )
        return json.dumps(filtered, ensure_ascii=False, sort_keys=True), metadata

    def _hard_scope_source_item_ids(self, tool_name: str, tool_params: dict[str, Any]) -> set[str]:
        if not tool_policy_scope_applies(tool_name):
            return set()
        params = tool_params if isinstance(tool_params, dict) else {}
        nested_scope = params.get("scope") if isinstance(params.get("scope"), dict) else {}
        scope_mode = str(
            params.get("scope_mode")
            or nested_scope.get("scope_mode")
            or nested_scope.get("mode")
            or ""
        ).strip().lower()
        if scope_mode != "hard":
            return set()
        return set(self._string_list(params.get("source_item_ids") or nested_scope.get("source_item_ids")))

    def _filter_out_of_scope_source_refs(self, value: Any, allowed_source_ids: set[str]) -> tuple[Any, int]:
        if isinstance(value, list):
            filtered_items = []
            removed = 0
            for item in value:
                filtered_item, item_removed = self._filter_out_of_scope_source_refs(item, allowed_source_ids)
                removed += item_removed
                if filtered_item is None:
                    removed += 1
                    continue
                filtered_items.append(filtered_item)
            return filtered_items, removed

        if isinstance(value, dict):
            source_id = self._source_ref_id(value)
            if source_id and source_id not in allowed_source_ids:
                return None, 0
            filtered_dict: dict[str, Any] = {}
            removed = 0
            for key, inner in value.items():
                filtered_inner, inner_removed = self._filter_out_of_scope_source_refs(inner, allowed_source_ids)
                removed += inner_removed
                if filtered_inner is None and isinstance(inner, dict) and self._source_ref_id(inner):
                    removed += 1
                    continue
                filtered_dict[key] = filtered_inner
            return filtered_dict, removed

        return value, 0

    def _annotate_scope_filter_notice(
        self,
        value: Any,
        *,
        allowed_source_ids: set[str],
        removed: int,
    ) -> Any:
        notice = {
            "applied": True,
            "reason": "hard_scope_filtered_out_of_scope_source_refs",
            "removed_source_ref_count": removed,
            "allowed_source_item_ids": sorted(allowed_source_ids),
            "feedback": (
                "Some MCP result entries were outside the caller-selected hard scope. "
                "Their contents were withheld, but this marker is preserved for answer diagnostics."
            ),
        }
        if isinstance(value, dict):
            annotated = dict(value)
            diagnostics = annotated.get("diagnostics")
            diagnostics = dict(diagnostics) if isinstance(diagnostics, dict) else {}
            diagnostics["tool_policy_scope_result_filter"] = notice
            annotated["diagnostics"] = diagnostics
            annotated["scope_filter"] = notice
            return annotated
        return value

    def _source_ref_id(self, value: dict[str, Any]) -> str | None:
        for key in ("source_item_id", "source_ref"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return None

    def _try_parse_json(self, text: str) -> Any:
        stripped = text.strip()
        if not stripped or stripped[0] not in "[{":
            return None
        try:
            return json.loads(stripped)
        except Exception:
            return None

    def _string_list(self, value: Any) -> list[str]:
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

    def _audit(
        self,
        tool_name: str,
        tool_params: dict[str, Any],
        decision: SafetyDecision | None,
        approved: Optional[bool],
        session_id: str,
        result: str = "",
        started: float | None = None,
        request_id: str | None = None,
    ) -> None:
        if hasattr(self._agent, "store"):
            duration_ms = round((perf_counter() - started) * 1000, 2) if started else None
            self._agent.store.append("audit", {
                "session_id": session_id,
                "request_id": request_id,
                "tool_name": tool_name,
                "tool_args": tool_params,
                "decision_level": decision.level.value if decision else "none",
                "decision_reason": decision.reason if decision else "",
                "pattern_matched": decision.pattern_matched if decision else None,
                "policy_scope": decision.policy_scope if decision else None,
                "policy_action": decision.policy_action if decision else None,
                "policy_matched": decision.policy_matched if decision else False,
                "approved": approved,
                "duration_ms": duration_ms,
                "result_summary": result[:500] if result else "",
            })
