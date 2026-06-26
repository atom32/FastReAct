"""Workspace path guard helpers for native tools."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fastreact.core.multitenant import UserContext


def resolve_user_path(path: str, user_context: Optional["UserContext"] = None) -> tuple[Path | None, str | None]:
    """
    Resolve a tool path and keep tenant-scoped calls inside the user workspace.

    Without user_context this preserves legacy single-tenant behavior. With
    user_context, relative paths are rooted at user_context.workspace and
    absolute paths must already be inside that workspace.
    """

    raw_path = Path(path).expanduser()
    if not user_context:
        return raw_path, None

    workspace = Path(user_context.workspace).expanduser().resolve()
    candidate = raw_path if raw_path.is_absolute() else workspace / raw_path
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(workspace)
    except ValueError:
        return None, f"[ERROR] Path outside user workspace: {path} (workspace: {workspace})"
    return resolved, None


def user_working_dir(default_dir: Path, user_context: Optional["UserContext"] = None) -> Path:
    """Return the execution working directory for native commands."""

    if not user_context:
        return default_dir
    workspace = Path(user_context.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace
