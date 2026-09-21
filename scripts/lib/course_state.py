"""Socratopia v4 course runtime-state: phase + readiness + blockers.

Replaces the v3 linear `lifecycle` with orthogonal runtime state per
SYSTEM/SPEC/RUNTIME_CONTRACT.md. `migrate` maps legacy lifecycle records.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.lib.repository import (
    backup_file,
    course_dir,
    read_json,
    validate_course_name,
    write_json_atomic,
)

SOURCE_OF_TRUTH = "DATA/<course>/PROGRESS.md"
PHASES = {"setup", "ready", "in_lesson", "post_lesson"}
CATALOG = {"ok", "missing", "stale"}
PREP = {"ok", "missing", "stale"}
RUNTIME = {"ok", "invalid"}
RETEACH = {"clear", "pending"}

# Legacy v3 linear lifecycle -> v4 orthogonal state (MIGRATION_PI.md).
LIFECYCLE_TO_V4: dict[str, dict[str, Any]] = {
    "needs_catalog": {"phase": "setup", "readiness": {"catalog": "missing", "prep": "missing", "runtime": "ok", "reteach": "clear"}, "blockers": ["missing_coursebook"]},
    "needs_prepare": {"phase": "setup", "readiness": {"catalog": "ok", "prep": "missing", "runtime": "ok", "reteach": "clear"}, "blockers": ["missing_prep"]},
    "needs_reteach": {"phase": "ready", "readiness": {"catalog": "ok", "prep": "ok", "runtime": "ok", "reteach": "pending"}, "blockers": ["pending_reteach"]},
    "ready_for_lesson": {"phase": "ready", "readiness": {"catalog": "ok", "prep": "ok", "runtime": "ok", "reteach": "clear"}, "blockers": []},
    "in_lesson": {"phase": "in_lesson", "readiness": {"catalog": "ok", "prep": "ok", "runtime": "ok", "reteach": "clear"}, "blockers": []},
    "post_lesson_A_done": {"phase": "post_lesson", "readiness": {"catalog": "ok", "prep": "ok", "runtime": "ok", "reteach": "clear"}, "blockers": []},
    "background_pending": {"phase": "post_lesson", "readiness": {"catalog": "ok", "prep": "ok", "runtime": "ok", "reteach": "clear"}, "blockers": []},
    "stable": {"phase": "post_lesson", "readiness": {"catalog": "ok", "prep": "ok", "runtime": "ok", "reteach": "clear"}, "blockers": []},
}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def default_state(course: str) -> dict[str, Any]:
    """Build the smallest valid v4 runtime state for one course."""
    return {
        "schema_version": 1,
        "course": validate_course_name(course),
        "phase": "setup",
        "lesson_id": None,
        "readiness": {"catalog": "missing", "prep": "missing", "runtime": "ok", "reteach": "clear"},
        "blockers": ["missing_coursebook", "missing_prep"],
        "current_chapter": "",
        "active_tutor": None,
        "updated_at": _now(),
        "source_of_truth": SOURCE_OF_TRUTH,
    }


def state_path(root: Path, course: str) -> Path:
    return course_dir(root, course) / "runtime" / "course_state.json"


def validate_state(state: Mapping[str, Any]) -> list[str]:
    """Return human-readable validation errors for a v4 state record."""
    errors: list[str] = []
    for key in ("schema_version", "course", "phase", "readiness", "blockers", "updated_at"):
        if key not in state:
            errors.append(f"缺少字段：{key}")
    if state.get("schema_version") != 1:
        errors.append("schema_version 必须为 1")
    course = state.get("course")
    if isinstance(course, str):
        try:
            validate_course_name(course)
        except ValueError as exc:
            errors.append(str(exc))
    elif course is not None:
        errors.append("course 必须为字符串")
    if state.get("phase") not in PHASES:
        errors.append(f"phase 不在允许集合：{sorted(PHASES)}")
    readiness = state.get("readiness")
    if not isinstance(readiness, dict):
        errors.append("readiness 必须为 object")
    else:
        for key, allowed in (("catalog", CATALOG), ("prep", PREP), ("runtime", RUNTIME), ("reteach", RETEACH)):
            if key not in readiness:
                errors.append(f"readiness 缺少：{key}")
            elif readiness[key] not in allowed:
                errors.append(f"readiness.{key}={readiness[key]!r} 不在 {sorted(allowed)}")
    blockers = state.get("blockers")
    if not isinstance(blockers, list) or any(not isinstance(item, str) for item in blockers):
        errors.append("blockers 必须为字符串列表")
    elif len(set(blockers)) != len(blockers):
        errors.append("blockers 含重复项")
    lesson_id = state.get("lesson_id", None)
    if lesson_id is not None and not isinstance(lesson_id, str):
        errors.append("lesson_id 必须为字符串或 null")
    if not isinstance(state.get("updated_at", ""), str):
        errors.append("updated_at 必须为字符串")
    return errors


def _progress_chapter(progress: Path) -> str:
    if not progress.exists():
        return ""
    matches = [
        line.strip()
        for line in progress.read_text(encoding="utf-8", errors="replace").splitlines()
        if "当前章节" in line
    ]
    if not matches:
        return ""
    return matches[-1].split("：", 1)[-1].split(":", 1)[-1].strip()


def load_state(root: Path, course: str) -> dict[str, Any]:
    """Load stored state, or an in-memory v4 default when absent."""
    stored = read_json(state_path(root, course))
    return stored if stored is not None else default_state(course)


def to_v4(raw: Mapping[str, Any], course: str) -> dict[str, Any]:
    """Normalize a v3 (lifecycle) or partial v4 record into full v4 shape."""
    state = default_state(course)
    state.update({k: v for k, v in raw.items() if k != "readiness"})
    if "lifecycle" in raw and "phase" not in raw:
        mapped = LIFECYCLE_TO_V4.get(str(raw.get("lifecycle")))
        if mapped is not None:
            state["phase"] = mapped["phase"]
            state["readiness"] = dict(mapped["readiness"])
            state["blockers"] = list(mapped["blockers"])
    readiness = raw.get("readiness")
    if isinstance(readiness, dict):
        merged = dict(state["readiness"])
        merged.update({k: v for k, v in readiness.items() if k in merged})
        state["readiness"] = merged
    lesson_number = raw.get("lesson_number")
    if state.get("lesson_id") in (None, "") and isinstance(lesson_number, int) and lesson_number > 0:
        state["lesson_id"] = f"lesson_{lesson_number:03d}"
    state["course"] = validate_course_name(course)
    state["schema_version"] = 1
    state["source_of_truth"] = SOURCE_OF_TRUTH
    return state


def render_state_markdown(state: Mapping[str, Any]) -> str:
    """Render a human-readable, non-authoritative projection."""
    readiness = state.get("readiness", {})
    return "\n".join(
        [
            f"# 课程运行状态：{state.get('course', '')}",
            "",
            "> 由 `scripts/course_runtime.py` 生成；JSON 为操作契约，本文件为只读投影。",
            "",
            f"- phase：`{state.get('phase', '')}`",
            f"- lesson_id：{state.get('lesson_id') or '未设置'}",
            f"- catalog：`{readiness.get('catalog', '')}` · prep：`{readiness.get('prep', '')}`"
            f" · runtime：`{readiness.get('runtime', '')}` · reteach：`{readiness.get('reteach', '')}`",
            f"- blockers：{', '.join(state.get('blockers', [])) or '无'}",
            f"- 当前章节：{state.get('current_chapter') or '未定位'}",
            f"- 当前导师：{state.get('active_tutor') or '未设置'}",
            f"- 更新时间：{state.get('updated_at', '')}",
            f"- 课堂历史来源：`{state.get('source_of_truth', SOURCE_OF_TRUTH)}`",
            "",
        ]
    )


def migrate_state(root: Path, course: str) -> dict[str, Any]:
    """Normalize/refresh the runtime projection while preserving PROGRESS.md."""
    course_path = course_dir(root, course)
    raw = read_json(state_path(root, course)) or {}
    state = to_v4(raw, course)
    state["current_chapter"] = _progress_chapter(course_path / "PROGRESS.md")
    state["updated_at"] = _now()
    target = state_path(root, course)
    if target.exists():
        backup_file(target)
    write_json_atomic(target, state)
    (course_path / "runtime" / "course_state.md").write_text(
        render_state_markdown(state), encoding="utf-8"
    )
    return state
