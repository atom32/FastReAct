"""Tool execution boundary for safety, approvals, audit, and result shaping."""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Optional, TYPE_CHECKING

from fastreact.core.events import AgentEvent
from fastreact.core.safety import SafetyDecision, SafetyLevel

if TYPE_CHECKING:
    from fastreact.agent import Agent
    from fastreact.core.multitenant import UserContext


@dataclass
class ToolExecutionResult:
    tool_name: str
    result: str
    allowed: bool = True
    blocked: bool = False
    error: Optional[str] = None
    request_id: Optional[str] = None


class ToolExecutionService:
    """Centralized tool execution with safety policy integration."""

    def __init__(self, agent: "Agent"):
        self._agent = agent
        self._pending_approvals: dict[str, asyncio.Future] = {}
        self._approval_records: dict[str, dict[str, Any]] = {}

    def assess(
        self,
        tool_name: str,
        tool_params: dict[str, Any],
        session_id: str,
        user_key: Optional[str] = None,
    ) -> tuple[SafetyDecision | None, AgentEvent | None]:
        if not self._agent._safety_policy:
            return None, None

        decision = self._agent._safety_policy.check(tool_name=tool_name, args=tool_params, user_key=user_key)
        if decision.level != SafetyLevel.DANGER:
            return decision, None

        request_id = f"approval-{uuid.uuid4().hex[:10]}"
        future = asyncio.get_running_loop().create_future()
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
            "created_at": self._now_iso(),
            "resolved_at": None,
        }
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
            "policy_scope": decision.policy_scope,
            "policy_action": decision.policy_action,
            "policy_matched": decision.policy_matched,
        })
        self._audit(tool_name, tool_params, decision, None, session_id, request_id=request_id)
        return decision, event

    async def wait_for_approval(self, request_id: str, timeout_seconds: float = 300.0) -> bool:
        future = self._pending_approvals.get(request_id)
        if not future:
            return False
        try:
            result = await asyncio.wait_for(future, timeout=timeout_seconds)
            if isinstance(result, dict):
                return bool(result.get("approved"))
            return bool(result)
        except asyncio.TimeoutError:
            if request_id in self._approval_records:
                self._approval_records[request_id]["status"] = "expired"
                self._approval_records[request_id]["approved"] = False
                self._approval_records[request_id]["expired"] = True
                self._approval_records[request_id]["resolved_at"] = self._now_iso()
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
        return True

    def list_approvals(self) -> list[dict[str, Any]]:
        return list(self._approval_records.values())

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def execute(
        self,
        tool_name: str,
        tool_params: dict[str, Any],
        session_id: str,
        user_context: Optional["UserContext"] = None,
        decision: SafetyDecision | None = None,
        approved: Optional[bool] = None,
        request_id: Optional[str] = None,
    ) -> tuple[ToolExecutionResult, AgentEvent]:
        started = perf_counter()
        if self._agent._safety_policy and decision is None:
            user_key = getattr(user_context, "user_key", None) if user_context else None
            tenant_key = getattr(user_context, "tenant_id", None) if user_context else None
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
                allowed=False,
                blocked=True,
                request_id=request_id,
            )
            self._audit(tool_name, tool_params, decision, False, session_id, result, started, request_id)
            return execution, AgentEvent.tool_result(tool_name, result, session_id)

        if decision and decision.level == SafetyLevel.DANGER and not approved:
            result = f"[SAFETY_DENIED] {decision.reason}"
            execution = ToolExecutionResult(
                tool_name=tool_name,
                result=result,
                allowed=False,
                blocked=True,
                request_id=request_id,
            )
            self._audit(tool_name, tool_params, decision, False, session_id, result, started, request_id)
            return execution, AgentEvent.tool_result(tool_name, result, session_id)

        try:
            result = await self._agent._tools.execute(
                tool_name,
                tool_params,
                user_context=user_context,
            )
            if self._agent._context_monitor:
                result = self._agent._context_monitor.truncate_tool_output(result)
            execution = ToolExecutionResult(tool_name=tool_name, result=result)
        except Exception as exc:
            result = f"[ERROR] {exc}"
            execution = ToolExecutionResult(tool_name=tool_name, result=result, error=str(exc))

        self._audit(tool_name, tool_params, decision, approved, session_id, result, started, request_id)
        event = AgentEvent.tool_result(tool_name, result, session_id)
        event.metadata.update({
            "duration_ms": round((perf_counter() - started) * 1000, 2),
            "decision_level": decision.level.value if decision else "none",
            "approved": approved,
            "request_id": request_id,
        })
        return execution, event

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
