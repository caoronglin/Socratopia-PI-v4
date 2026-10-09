"""Filesystem primitives for the Socratopia v4 repository.

Course-isolated, path-safe, atomic. No host-specific paths; no network.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_COURSE_NAME_RE = re.compile(r"^[^/\\.][^/\\]*$")
_SECRET_PATTERNS = [
    re.compile(r"(?i)(token|api[_-]?key|apikey|secret|password)=[^\s&\"']+"),
    re.compile(r"(?i)authorization:\s*[^\s]+"),
    re.compile(r"(?i)bearer\s+[^\s]+"),
    re.compile(r"sk-[A-Za-z0-9]{8,}"),
]


def validate_course_name(course: str) -> str:
    """Return a safe single-segment course name or raise ValueError."""
    normalized = course.strip()
    if "\x00" in normalized:
        raise ValueError(f"非法课程名：{course!r}")
    if not normalized or normalized in {".", ".."} or not _COURSE_NAME_RE.fullmatch(normalized):
        raise ValueError(f"非法课程名：{course!r}")
    return normalized


def _safe_dir(root: Path, top: str, course: str) -> Path:
    safe_name = validate_course_name(course)
    container = root / top
    if container.is_symlink():
        raise ValueError(f"课程容器不能是符号链接：{container}")
    base = container.resolve()
    if (base / safe_name).is_symlink():
        raise ValueError(f"课程目录不能是符号链接：{course!r}")
    result = (base / safe_name).resolve()
    if base != result and base not in result.parents:
        raise ValueError(f"课程路径越界：{course!r}")
    return result


def course_dir(root: Path, course: str) -> Path:
    """Return the validated course directory under DATA/."""
    return _safe_dir(root, "DATA", course)


def textbook_dir(root: Path, course: str) -> Path:
    """Return the validated course directory under TEXTBOOK/."""
    return _safe_dir(root, "TEXTBOOK", course)


def validate_lesson_id(value: str) -> str:
    """Validate lesson identifiers used as filenames."""
    if not isinstance(value, str) or not re.fullmatch(r"lesson_[0-9]{3,}", value):
        raise ValueError(f"Invalid lesson identifier: {value!r}")
    return value


def safe_child_path(base: Path, *parts: str) -> Path:
    """Check that a resolved target remains under its intended directory."""
    root = base.resolve()
    target = root.joinpath(*parts).resolve()
    if root not in target.parents:
        raise ValueError(f"Target is outside the allowed directory: {target}")
    return target


def iter_course_paths(root: Path, top: str = "DATA", course: str | None = None) -> list[Path]:
    """List course roots without reading another course when a scope is supplied."""
    base = root / top
    if course is not None:
        name = validate_course_name(course)
        path = base / name
        return [path] if path.exists() or path.is_symlink() else []
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir() or p.is_symlink())


def read_json(path: Path) -> dict[str, Any] | None:
    """Read a JSON object or return None when the file does not exist."""
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 根对象必须是 object：{path}")
    return value


def read_json_list(path: Path, key: str) -> list[dict[str, Any]]:
    """Read a list stored under `key`, tolerating a missing file."""
    payload = read_json(path) or {key: []}
    values = payload.get(key, [])
    if not isinstance(values, list):
        raise ValueError(f"{path.name} 的 {key} 必须为列表")
    for index, record in enumerate(values):
        if not isinstance(record, dict):
            raise ValueError(f"{path.name} 的 {key}[{index}] 必须是 object")
    return values


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    """Atomically persist UTF-8 JSON: temp file, flush, os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name
    os.replace(temp_name, path)


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    """Append one complete JSON line; single-writer, flush + fsync per event."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def redact(text: str, limit: int = 1000) -> str:
    """Mask secrets and clamp length for safe persistence/logging."""
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted[:limit]


def backup_file(path: Path) -> Path | None:
    """Copy an existing file to a deterministic .bak sibling before migration."""
    if not path.exists():
        return None
    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)
    return backup
