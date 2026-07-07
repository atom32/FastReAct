"""Govern MCP tool output before it is exposed to the LLM context."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any


DEFAULT_MCP_TOOL_OUTPUT_PREVIEW_CHARS = 1200


@dataclass
class GovernedToolOutput:
    """Result of MCP output governance."""

    result: str
    context_result: str
    metadata: dict[str, Any] = field(default_factory=dict)
    issue: bool = False
    issue_code: str | None = None


def is_mcp_tool(tool: Any) -> bool:
    """Return whether a registered tool is an MCP wrapper without hard coupling tests."""
    return tool.__class__.__name__ == "MCPToolWrapper"


def is_upstream_chunk_limit_error(result: str) -> bool:
    """Detect parser/chunk limit failures without depending on a specific MCP server."""
    lowered = result.lower()
    if not (lowered.startswith("[mcp_error]") or lowered.startswith("[error]")):
        return False
    return (
        "separator" in lowered
        and "chunk" in lowered
        and ("limit" in lowered or "exceed" in lowered or "longer than" in lowered)
    )


def retry_params_for_tool(
    tool_params: dict[str, Any],
    tool_schema: dict[str, Any] | None,
    configured_budget: int,
) -> dict[str, Any] | None:
    """Build one conservative retry payload by reducing declared or supplied max_* fields."""
    retry_params = dict(tool_params)
    changed = False
    floor = 1
    target_cap = max(floor, min(4096, max(floor, configured_budget // 2)))

    for key, value in list(retry_params.items()):
        if not _is_retry_size_key(key) or not isinstance(value, int) or isinstance(value, bool):
            continue
        reduced = max(floor, min(value - 1 if value > floor else value, value // 2, target_cap))
        if reduced < value:
            retry_params[key] = reduced
            changed = True

    properties = {}
    if isinstance(tool_schema, dict):
        properties = tool_schema.get("properties") or {}
    for key, schema in properties.items():
        if not _is_retry_size_key(key) or key in retry_params:
            continue
        if not isinstance(schema, dict):
            continue
        schema_type = schema.get("type")
        if schema_type not in ("integer", "number"):
            continue
        retry_params[key] = target_cap
        changed = True

    return retry_params if changed and retry_params != tool_params else None


def govern_mcp_tool_output(
    *,
    tool_name: str,
    tool_params: dict[str, Any],
    tool_schema: dict[str, Any] | None,
    result: Any,
    configured_budget: int,
    preview_chars: int = DEFAULT_MCP_TOOL_OUTPUT_PREVIEW_CHARS,
    session_id: str = "",
    store: Any = None,
    issue_hint: str | None = None,
) -> GovernedToolOutput:
    """Return a safe event/context representation for MCP tool output."""
    text = result if isinstance(result, str) else str(result)
    budget = max(1, int(configured_budget))
    estimated_size = len(text)
    chunk_limit_error = issue_hint == "upstream_chunk_limit" or is_upstream_chunk_limit_error(text)
    over_budget = estimated_size > budget

    if not chunk_limit_error and not over_budget:
        return GovernedToolOutput(result=text, context_result=text)

    issue_code = "upstream_chunk_limit" if chunk_limit_error else "tool_result_over_budget"
    artifact_id = None
    artifact_record = None
    if over_budget and store is not None:
        artifact_id = f"mcp-tool-output-{uuid.uuid4().hex[:12]}"
        artifact_record = {
            "artifact_id": artifact_id,
            "kind": "mcp_tool_result",
            "tool_name": tool_name,
            "session_id": session_id,
            "content": text,
            "content_length": estimated_size,
            "content_sha256": hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest(),
        }
        store.append("artifacts", artifact_record)

    retry_params = retry_params_for_tool(tool_params, tool_schema, budget)
    envelope = {
        "type": "mcp_tool_result_issue",
        "error_code": "tool_output_too_large",
        "issue_code": issue_code,
        "tool_name": tool_name,
        "estimated_size": estimated_size if not chunk_limit_error else 0,
        "estimated_size_available": not chunk_limit_error,
        "configured_budget": budget,
        "artifact": {
            "available": bool(artifact_id),
            "artifact_id": artifact_id,
            "content_stored": bool(artifact_id),
        },
        "preview": _safe_preview_metadata(text, preview_chars=preview_chars, include_text=False),
        "retry": {
            "recommended": True,
            "suggested_params": retry_params or {},
            "hint": (
                "Retry with smaller numeric max_* parameters, narrower selectors, "
                "or pagination/batching when the tool supports it."
            ),
        },
    }
    envelope_text = json.dumps(envelope, ensure_ascii=False, sort_keys=True)
    metadata = {
        "tool_output_governance": {
            "error_code": envelope["error_code"],
            "issue_code": issue_code,
            "tool_name": tool_name,
            "estimated_size": envelope["estimated_size"],
            "estimated_size_available": envelope["estimated_size_available"],
            "configured_budget": budget,
            "artifact_id": artifact_id,
            "artifact_available": bool(artifact_id),
            "retry_suggested_params": retry_params or {},
            "context_compressed": True,
            "full_content_in_context": False,
        },
        "tool_output_too_large": True,
        "tool_result_over_budget": over_budget,
    }
    return GovernedToolOutput(
        result=envelope_text,
        context_result=envelope_text,
        metadata=metadata,
        issue=True,
        issue_code=issue_code,
    )


def _is_retry_size_key(key: str) -> bool:
    return key.startswith("max_")


def _safe_preview_metadata(text: str, *, preview_chars: int, include_text: bool) -> dict[str, Any]:
    """Describe result shape without leaking raw tool content into the error envelope."""
    preview: dict[str, Any] = {
        "mode": "metadata_only",
        "text_preview_included": False,
        "text_length": len(text),
    }
    parsed = _try_parse_json(text)
    if isinstance(parsed, dict):
        preview["json_type"] = "object"
        preview["top_level_keys"] = sorted(str(key) for key in parsed.keys())[:50]
        preview["source_key_fields"] = _source_key_fields(parsed)
    elif isinstance(parsed, list):
        preview["json_type"] = "array"
        preview["item_count"] = len(parsed)
        if parsed and isinstance(parsed[0], dict):
            preview["first_item_keys"] = sorted(str(key) for key in parsed[0].keys())[:50]
            preview["source_key_fields"] = _source_key_fields(parsed[0])
    else:
        preview["text_segments_estimate"] = _segment_estimate(text)

    if include_text:
        preview["mode"] = "text"
        preview["text_preview_included"] = True
        preview["text"] = text[: max(0, preview_chars)]
    return preview


def _try_parse_json(text: str) -> Any:
    stripped = text.strip()
    if not stripped or stripped[0] not in "[{":
        return None
    try:
        return json.loads(stripped)
    except Exception:
        return None


def _source_key_fields(value: dict[str, Any]) -> list[str]:
    candidates = {
        "source",
        "source_id",
        "source_key",
        "source_ref",
        "source_refs",
        "citation",
        "citations",
        "uri",
        "url",
        "id",
    }
    return sorted(str(key) for key in value.keys() if str(key).lower() in candidates)


def _segment_estimate(text: str) -> int:
    if not text:
        return 0
    separators = ["\n\n", "\n", ". ", "; "]
    counts = [text.count(separator) + 1 for separator in separators if separator in text]
    return max(counts) if counts else 1
