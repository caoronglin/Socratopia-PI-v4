"""Read-only chapter catalog and create-only Markdown textbook onboarding."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from platform_api.evidence import EvidenceError, MAX_BOOK_BYTES, _read_book
from scripts.lib.repository import textbook_dir, validate_course_name


class BookError(ValueError):
    """Invalid, stale or unsafe course content."""


def _target(root: Path, course: str) -> Path:
    parent = textbook_dir(root, validate_course_name(course))
    parent.mkdir(parents=True, exist_ok=True)
    path = parent / "book.md"
    if path.is_symlink():
        raise BookError("Course book cannot be a symlink")
    return path


def info(root: Path, course: str) -> dict:
    path = _target(root, course)
    if not path.exists():
        return {"course": course, "available": False, "can_import": True, "chapters": []}
    try:
        content, sha = _read_book(root, course)
    except (EvidenceError, ValueError) as exc:
        raise BookError(str(exc)) from exc
    chapters = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        found = re.match(r"^(#{1,4})\s+(.+?)\s*$", line)
        if found:
            chapters.append({
                "level": len(found.group(1)),
                "title": found.group(2)[:120],
                "line": line_number,
            })
            if len(chapters) >= 200:
                break
    return {
        "course": course, "available": True, "can_import": False,
        "chapters": chapters, "sha256": sha, "bytes": len(content.encode("utf-8")),
        "source": f"TEXTBOOK/{course}/book.md",
    }


def import_markdown(root: Path, course: str, content: str) -> dict:
    course = validate_course_name(course)
    if "\x00" in content or not content.strip():
        raise BookError("Course textbook must be non-empty UTF-8 Markdown")
    data = content.encode("utf-8")
    if not 32 <= len(data) <= MAX_BOOK_BYTES:
        raise BookError("Textbook must have 32–2,000,000 bytes")
    path = _target(root, course)
    # 'x' enforces no overwrite even with competing requests; never truncate
    # the primary book or reset runtime/mastery on onboarding.
    try:
        with path.open("x", encoding="utf-8", newline="\n") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
    except FileExistsError as exc:
        raise BookError("Course already has a textbook; overwrite is forbidden") from exc
    return {"course": course, "created": True, "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data), "ready_for_formal_lesson": False}
