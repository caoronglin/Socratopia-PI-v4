"""Durable, course-scoped task queue for Socratopia v4.

Conforms to SYSTEM/schemas/tasks.schema.json: top-level {schema_version, tasks};
each task carries its own `course`. Queue is a persistent TODO list, not a worker.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from scripts.lib.repository import course_dir, read_json, redact, safe_child_path, write_json_atomic

STATUSES = {"pending", "running", "completed", "failed", "blocked", "cancelled"}
TERMINAL = {"completed", "cancelled"}
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"running", "cancelled", "blocked"},
    "running": {"completed", "failed", "blocked"},
    "failed": {"pending", "cancelled", "blocked"},
    "blocked": {"pending", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def queue_path(root: Path, course: str) -> Path:
    return course_dir(root, course) / "runtime" / "tasks.json"


@contextmanager
def _queue_lock(root: Path, course: str):
    """Cross-process lock around read-modify-write (Linux/macOS/Windows)."""
    path = safe_child_path(course_dir(root, course), "runtime", "tasks.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _load(root: Path, course: str) -> dict[str, Any]:
    stored = read_json(queue_path(root, course))
    if stored is None:
        return {"schema_version": 1, "tasks": []}
    stored.setdefault("schema_version", 1)
    stored.setdefault("tasks", [])
    return stored


def _save(root: Path, course: str, queue: Mapping[str, Any]) -> None:
    payload = {"schema_version": 1, "tasks": list(queue.get("tasks", []))}
    write_json_atomic(queue_path(root, course), payload)


def validate_queue(queue: Mapping[str, Any]) -> list[str]:
    """Validate against the v4 tasks schema essentials."""
    errors: list[str] = []
    if queue.get("schema_version") != 1:
        errors.append("schema_version 必须为 1")
    extra = set(queue) - {"schema_version", "tasks"}
    if extra:
        errors.append(f"顶层不允许额外字段：{sorted(extra)}")
    tasks = queue.get("tasks")
    if not isinstance(tasks, list):
        errors.append("tasks 必须为列表")
        return errors
    seen_ids: set[str] = set()
    for i, task in enumerate(tasks):
        if not isinstance(task, Mapping):
            errors.append(f"tasks[{i}] 必须为 object")
            continue
        for key in ("id", "idempotency_key", "kind", "course", "status", "attempts"):
            if key not in task or task.get(key) in (None, ""):
                errors.append(f"tasks[{i}] 缺少字段：{key}")
        if task.get("status") not in STATUSES:
            errors.append(f"tasks[{i}] 非法 status：{task.get('status')}")
        if not isinstance(task.get("attempts"), int) or task.get("attempts", -1) < 0:
            errors.append(f"tasks[{i}] attempts 必须为非负整数")
        tid = task.get("id")
        if tid in seen_ids:
            errors.append(f"tasks[{i}] 重复 id：{tid}")
        seen_ids.add(tid)
    return errors


def enqueue_task(
    root: Path,
    course: str,
    kind: str,
    idempotency_key: str,
    lesson_id: str | None = None,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create or reuse a non-terminal task with matching kind + idempotency_key."""
    with _queue_lock(root, course):
        queue = _load(root, course)
        for task in queue["tasks"]:
            if (
                task.get("kind") == kind
                and task.get("idempotency_key") == idempotency_key
                and task.get("status") not in TERMINAL
            ):
                return task
        now = _now()
        task = {
            "id": str(uuid4()),
            "idempotency_key": idempotency_key,
            "kind": kind,
            "course": course,
            "lesson_id": lesson_id,
            "status": "pending",
            "attempts": 0,
            "last_error": None,
            "created_at": now,
            "updated_at": now,
            "payload": dict(payload or {}),
        }
        queue["tasks"].append(task)
        _save(root, course, queue)
        return task


def transition_task(
    root: Path, course: str, task_id: str, new_status: str, error: str | None = None
) -> dict[str, Any]:
    """Apply one legal status transition and persist the queue."""
    with _queue_lock(root, course):
        if new_status not in STATUSES:
            raise ValueError(f"非法目标状态：{new_status}")
        queue = _load(root, course)
        task = next((item for item in queue["tasks"] if item.get("id") == task_id), None)
        if task is None:
            raise ValueError(f"未找到任务：{task_id}")
        if new_status not in ALLOWED_TRANSITIONS.get(task.get("status"), set()):
            raise ValueError(f"非法状态转换：{task.get('status')} -> {new_status}")
        task["status"] = new_status
        task["updated_at"] = _now()
        if new_status == "running":
            task["attempts"] = int(task.get("attempts", 0)) + 1
        if error:
            task["last_error"] = redact(error)
        _save(root, course, queue)
        return task


def queue_summary(root: Path, course: str) -> dict[str, int]:
    """Count queue tasks by status without making changes."""
    counts = {status: 0 for status in STATUSES}
    for task in _load(root, course)["tasks"]:
        counts[task.get("status", "pending")] = counts.get(task.get("status", "pending"), 0) + 1
    return counts


def render_queue(root: Path, course: str) -> str:
    """Render a non-authoritative Markdown queue projection."""
    queue = _load(root, course)
    lines = [f"# {course} · 持久任务队列", "", "| ID | 类型 | 状态 | 尝试 |", "|---|---|---|---:|"]
    for task in queue["tasks"]:
        lines.append(
            f"| `{str(task.get('id', ''))[:8]}` | {task.get('kind', '')} "
            f"| `{task.get('status', '')}` | {task.get('attempts', 0)} |"
        )
    if not queue["tasks"]:
        lines.append("| - | 暂无任务 | - | 0 |")
    return "\n".join(lines) + "\n"
