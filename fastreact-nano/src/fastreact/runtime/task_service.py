"""Durable task/plan service backed by JSONL snapshots."""

import uuid
from datetime import datetime
from typing import Any, Optional

from fastreact.core.tools import Tool


VALID_STATUSES = {"pending", "in_progress", "blocked", "completed", "cancelled"}
VALID_PRIORITIES = {"low", "normal", "high", "urgent"}


class TaskService:
    """Append-only task board with latest-snapshot reads."""

    def __init__(self, store):
        self._store = store

    def create(
        self,
        title: str,
        description: str = "",
        priority: str = "normal",
        owner: str = "",
        dependencies: Optional[list[str]] = None,
        session_id: str = "",
    ) -> dict[str, Any]:
        if priority not in VALID_PRIORITIES:
            priority = "normal"
        now = datetime.utcnow().isoformat()
        task = {
            "task_id": f"task-{uuid.uuid4().hex[:10]}",
            "title": title,
            "description": description,
            "status": "pending",
            "priority": priority,
            "owner": owner,
            "dependencies": dependencies or [],
            "session_id": session_id,
            "created_at": now,
            "updated_at": now,
        }
        self._store.upsert_snapshot("tasks", "task_id", task)
        return task

    def update(self, task_id: str, **changes: Any) -> dict[str, Any]:
        current = self.get(task_id)
        if not current:
            raise ValueError(f"Task not found: {task_id}")

        allowed = {"title", "description", "status", "priority", "owner", "dependencies", "session_id"}
        for key, value in changes.items():
            if key not in allowed or value is None:
                continue
            if key == "status" and value not in VALID_STATUSES:
                raise ValueError(f"Invalid status: {value}")
            if key == "priority" and value not in VALID_PRIORITIES:
                raise ValueError(f"Invalid priority: {value}")
            current[key] = value

        current["updated_at"] = datetime.utcnow().isoformat()
        self._store.upsert_snapshot("tasks", "task_id", current)
        return current

    def get(self, task_id: str) -> Optional[dict[str, Any]]:
        tasks = self.list(limit=0)
        return tasks.get(task_id) if isinstance(tasks, dict) else None

    def list(
        self,
        status: Optional[str] = None,
        owner: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 200,
    ) -> list[dict[str, Any]] | dict[str, dict[str, Any]]:
        snapshots = self._store.read("tasks", limit=0)
        latest: dict[str, dict[str, Any]] = {}
        for record in snapshots:
            task_id = record.get("task_id")
            if task_id:
                latest[task_id] = record
        if limit == 0 and not any([status, owner, session_id]):
            return latest
        tasks = list(latest.values())
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        if owner:
            tasks = [task for task in tasks if task.get("owner") == owner]
        if session_id:
            tasks = [task for task in tasks if task.get("session_id") == session_id]
        tasks.sort(key=lambda task: task.get("updated_at", ""), reverse=True)
        return tasks[:limit] if limit else tasks

    def prompt_context(self, session_id: str = "") -> str:
        tasks = self.list(limit=20)
        if not tasks:
            return ""
        lines = ["# Current Task Board", "Use this durable task state for multi-step planning."]
        for task in tasks:
            if session_id and task.get("session_id") not in ("", session_id):
                continue
            deps = ",".join(task.get("dependencies") or [])
            lines.append(
                f"- {task['task_id']} [{task.get('status')}] ({task.get('priority')}) "
                f"{task.get('title')} deps={deps or '-'}"
            )
        return "\n".join(lines) if len(lines) > 2 else ""


class _TaskTool(Tool):
    def __init__(self, service: TaskService):
        self._service = service


class TaskCreateTool(_TaskTool):
    @property
    def name(self) -> str:
        return "task_create"

    @property
    def description(self) -> str:
        return "Create a durable task for multi-step work."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string"},
                "owner": {"type": "string"},
                "dependencies": {"type": "array"},
                "session_id": {"type": "string"},
            },
            "required": ["title"],
        }

    async def execute(self, title: str, description: str = "", priority: str = "normal", owner: str = "", dependencies: Optional[list[str]] = None, session_id: str = "", **_: Any) -> str:
        task = self._service.create(title, description, priority, owner, dependencies, session_id)
        return f"[TASK_CREATED] {task['task_id']} {task['title']}"


class TaskUpdateTool(_TaskTool):
    @property
    def name(self) -> str:
        return "task_update"

    @property
    def description(self) -> str:
        return "Update a durable task status or metadata."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "status": {"type": "string"},
                "priority": {"type": "string"},
                "owner": {"type": "string"},
                "dependencies": {"type": "array"},
            },
            "required": ["task_id"],
        }

    async def execute(self, task_id: str, **changes: Any) -> str:
        task = self._service.update(task_id, **changes)
        return f"[TASK_UPDATED] {task['task_id']} status={task['status']}"


class TaskListTool(_TaskTool):
    @property
    def name(self) -> str:
        return "task_list"

    @property
    def description(self) -> str:
        return "List durable tasks."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "owner": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": [],
        }

    async def execute(self, status: str = "", owner: str = "", session_id: str = "", **_: Any) -> str:
        tasks = self._service.list(status=status or None, owner=owner or None, session_id=session_id or None)
        if not tasks:
            return "[TASKS] No tasks"
        return "\n".join(f"{task['task_id']} [{task['status']}] {task['title']}" for task in tasks)


class TaskGetTool(_TaskTool):
    @property
    def name(self) -> str:
        return "task_get"

    @property
    def description(self) -> str:
        return "Get one durable task by id."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        }

    async def execute(self, task_id: str, **_: Any) -> str:
        task = self._service.get(task_id)
        if not task:
            return f"[ERROR] Task not found: {task_id}"
        deps = ", ".join(task.get("dependencies") or [])
        return (
            f"{task['task_id']} [{task['status']}] {task['title']}\n"
            f"priority={task.get('priority')} owner={task.get('owner') or '-'} deps={deps or '-'}\n"
            f"{task.get('description') or ''}"
        )
