"""Course-scoped logical AgentScope identities with bounded opt-in capabilities.

Persistent memory is NOT held in AgentScope's in-process context. Verified
SQLite transcript and the current textbook are authoritative at each turn.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.lib.repository import course_dir, read_json, validate_course_name, write_json_atomic

DEFAULT_FEATURES = {"chat": True, "memory": True, "group": False}
MUTABLE_FEATURES = {"memory", "group"}


class CourseAgentError(ValueError):
    pass


def _settings_path(root: Path, course: str) -> Path:
    directory = course_dir(root, validate_course_name(course))
    if not directory.is_dir() or directory.is_symlink():
        raise CourseAgentError("Course does not exist or is unsafe")
    runtime = directory / "runtime"
    if runtime.is_symlink():
        raise CourseAgentError("Course runtime cannot be a symlink")
    runtime.mkdir(parents=True, exist_ok=True)
    target = runtime / "agent_features.json"
    if target.is_symlink():
        raise CourseAgentError("Agent settings cannot be a symlink")
    return target


def identity(course: str) -> str:
    """Stable, non-secret identity; never used for authentication."""
    return "course-" + hashlib.sha256(validate_course_name(course).encode("utf-8")).hexdigest()[:16]


def status(root: Path, course: str) -> dict:
    path = _settings_path(root, course)
    value = read_json(path) or {}
    features = value.get("features", {})
    if not isinstance(features, dict):
        raise CourseAgentError("Invalid agent feature settings")
    flags = dict(DEFAULT_FEATURES)
    for key in MUTABLE_FEATURES:
        if key in features:
            if not isinstance(features[key], bool):
                raise CourseAgentError("Agent feature must be a boolean")
            flags[key] = features[key]
    return {"course": validate_course_name(course), "agent_id": identity(course),
            "backend": "agentscope", "features": flags,
            "memory_policy": "current-course-current-book-citation-checked",
            "tool_access": False, "active_external_tools": []}


def configure(root: Path, course: str, feature: str, enabled: bool) -> dict:
    if feature not in MUTABLE_FEATURES or not isinstance(enabled, bool):
        raise CourseAgentError("Feature must be 'memory' or 'group'")
    path = _settings_path(root, course)
    current = status(root, course)
    flags = current["features"]
    flags[feature] = enabled
    write_json_atomic(path, {"schema_version": 1, "features": flags})
    return status(root, course)
