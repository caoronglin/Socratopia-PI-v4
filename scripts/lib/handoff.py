"""Structured tutor-handoff validation (SYSTEM/SPEC/RUNTIME_CONTRACT.md).

ADR-006 makes `runtime/handoff.json` the authoritative cross-tutor carry-over
carrier, so a course that has not taught yet must be able to say "no handoff
yet" instead of inventing one. This module encodes that distinction so neither
the scaffold nor a hand edit can fabricate teaching history.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts.lib.repository import course_dir, read_json, redact, write_json_atomic

REQUIRED = ("schema_version", "lesson_id", "from_tutor", "to_tutor", "carry")
OPTIONAL = ("opening_anchor", "tone_note")
CARRY_REQUIRED = ("knowledge_point", "status", "evidence")
CARRY_OPTIONAL = ("recommended_angle",)
CARRY_STATUSES = {"verified", "needs_review", "introduced", "unseen"}

# Fields that describe *who* is carrying teaching state. All null means the
# course has no handoff yet; all set means a real carry-over exists.
PARTY_FIELDS = ("lesson_id", "from_tutor", "to_tutor")


def handoff_path(root: Path, course: str) -> Path:
    return course_dir(root, course) / "runtime" / "handoff.json"


def default_handoff() -> dict[str, Any]:
    """The "no handoff yet" record; never invents teaching history."""
    return {
        "schema_version": 1,
        "lesson_id": None,
        "from_tutor": None,
        "to_tutor": None,
        "carry": [],
        "opening_anchor": "",
        "tone_note": "",
    }


def load_handoff(root: Path, course: str) -> dict[str, Any]:
    stored = read_json(handoff_path(root, course))
    return stored if stored is not None else default_handoff()


def set_handoff(
    root: Path,
    course: str,
    lesson_id: str,
    from_tutor: str,
    to_tutor: str,
    carry: Sequence[Mapping[str, Any]],
    opening_anchor: str = "",
    tone_note: str = "",
) -> dict[str, Any]:
    """Validate then persist one real carry-over; raises ValueError, writes nothing on failure."""
    if from_tutor == to_tutor:
        raise ValueError("from_tutor 与 to_tutor 不能相同：同一导师没有承接")
    record: dict[str, Any] = {
        "schema_version": 1,
        "lesson_id": lesson_id,
        "from_tutor": from_tutor,
        "to_tutor": to_tutor,
        "carry": [
            {key: redact(value) if isinstance(value, str) else value for key, value in item.items()}
            for item in carry
        ],
        "opening_anchor": redact(opening_anchor),
        "tone_note": redact(tone_note),
    }
    problems = validate_handoff(record)
    if problems:
        raise ValueError("; ".join(problems))
    write_json_atomic(handoff_path(root, course), record)
    return record


def clear_handoff(root: Path, course: str) -> dict[str, Any]:
    """Reset to "尚未承接" (e.g. after the carry-over has been consumed)."""
    record = default_handoff()
    write_json_atomic(handoff_path(root, course), record)
    return record


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_handoff(record: Mapping[str, Any] | None) -> list[str]:
    """Return human-readable errors for one handoff record.

    Mirrors `SYSTEM/schemas/handoff.schema.json`; the anti-fabrication rule
    lives here because JSON Schema cannot express "carry must be non-empty".
    """
    if record is None:
        return []

    errors: list[str] = []

    for key in REQUIRED:
        if key not in record:
            errors.append(f"缺少字段：{key}")
    if record.get("schema_version") != 1:
        errors.append("schema_version 必须为 1")

    extra = set(record) - set(REQUIRED) - set(OPTIONAL)
    if extra:
        errors.append(f"不允许的额外字段：{sorted(extra)}")

    for key in PARTY_FIELDS:
        value = record.get(key)
        if value is not None and not _nonempty_str(value):
            errors.append(f"{key} 必须是非空字符串或 null")

    for key in OPTIONAL:
        if key in record and not isinstance(record[key], str):
            errors.append(f"{key} 必须是字符串")

    carry = record.get("carry")
    if not isinstance(carry, list):
        errors.append("carry 必须为列表")
        return errors

    for index, item in enumerate(carry):
        if not isinstance(item, dict):
            errors.append(f"carry[{index}] 必须为 object")
            continue
        for key in CARRY_REQUIRED:
            if not _nonempty_str(item.get(key)):
                errors.append(f"carry[{index}] 缺少字段：{key}")
        if item.get("status") not in CARRY_STATUSES:
            errors.append(f"carry[{index}] 非法 status：{item.get('status')!r}")
        extra_item = set(item) - set(CARRY_REQUIRED) - set(CARRY_OPTIONAL)
        if extra_item:
            errors.append(f"carry[{index}] 不允许的额外字段：{sorted(extra_item)}")

    errors.extend(_check_consistency(record, carry))
    return errors


def _check_consistency(record: Mapping[str, Any], carry: list[Any]) -> list[str]:
    """Reject placeholder handoffs that would fabricate teaching history."""
    nulls = [record.get(key) is None for key in PARTY_FIELDS]
    if any(nulls) and not all(nulls):
        return [
            "lesson_id/from_tutor/to_tutor 必须同时为 null 或同时有值（部分填写属于占位）"
        ]
    if all(nulls):
        if carry:
            return ["无承接人（全部为 null）时 carry 必须为空"]
        return []
    if not carry:
        return [
            "承接人已填写但 carry 为空：属于占位伪造的承接记录，必须改为全 null 或补真实理解证据"
        ]
    return []
