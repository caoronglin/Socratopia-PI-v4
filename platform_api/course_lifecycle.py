"""Separate non-destructive archive flag; never edits course state or mastery."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from scripts.lib.repository import course_dir, read_json, validate_course_name, write_json_atomic

class ArchivedCourse(ValueError):
    pass

def _path(root: Path, course: str) -> Path:
    location = course_dir(root, validate_course_name(course))
    if not location.is_dir() or location.is_symlink():
        raise ArchivedCourse("Course missing or unsafe")
    runtime = location / "runtime"
    if runtime.is_symlink():
        raise ArchivedCourse("Unsafe course runtime")
    target = runtime / "archive_state.json"
    if target.is_symlink():
        raise ArchivedCourse("Unsafe archive record")
    return target

def status(root: Path, course: str) -> dict:
    data = read_json(_path(root, course)) or {}
    archived = data.get("archived", False)
    if not isinstance(archived, bool):
        raise ArchivedCourse("Invalid archive record")
    return {"course": validate_course_name(course), "archived": archived,
            "archived_at": data.get("archived_at") if archived else None}

def set_archive(root: Path, course: str, archived: bool) -> dict:
    if not isinstance(archived, bool):
        raise ArchivedCourse("Invalid archive flag")
    path = _path(root, course)
    if status(root, course)["archived"] == archived:
        return status(root, course)
    write_json_atomic(path, {"schema_version": 1, "archived": archived,
        "archived_at": datetime.now(timezone.utc).isoformat(timespec="seconds") if archived else None})
    return status(root, course)

def require_active(root: Path, course: str) -> None:
    if status(root, course)["archived"]:
        raise ArchivedCourse("Course archived: read only until restored")
