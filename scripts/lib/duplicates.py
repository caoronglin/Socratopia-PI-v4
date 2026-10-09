"""Duplicate-rule detection and stale-projection checks (plan.md §13, WARN-level).

plan §10 names one owner per rule; other files should only say `see X`. A
sentence repeated verbatim across control files is a second rule source that
will drift. These checks are advisory: they return strings, never raise.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from scripts.lib.repository import iter_course_paths

MIN_CHARS = 20          # normalized chars; shorter sentences are too generic to call duplicates
MAX_REPORTED = 12
TOLERANCE_SECONDS = 2.0  # scaffold writes sibling files milliseconds apart

CONTROL_GLOBS = (
    "AGENTS.md",
    ".pi/skills/*/SKILL.md",
    ".pi/skills/*/references/*.md",
    ".pi/skills/*/profiles/TUTOR_*.md",
    ".pi/skills/*/moe/TUTOR_*.md",
    ".pi/prompts/*.md",
    "SYSTEM/SPEC/*.md",
)

_SPLIT = re.compile(r"[。；;！？!?\n]")
_STRIP = re.compile(r"[\s`*_>#|\-—:：，,、（）()\[\]\"“”'‘’·]+")


def _sentences(text: str) -> list[str]:
    """Candidate rule sentences; skip code fences, tables, frontmatter and headings."""
    out: list[str] = []
    in_fence = False
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":  # YAML frontmatter is metadata, not rules
        end = next((i for i, raw in enumerate(lines[1:], 1) if raw.strip() == "---"), None)
        lines = lines[end + 1:] if end is not None else lines
    for raw in lines:
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line or line.startswith(("#", "|", "---", "<!--")):
            continue
        for piece in _SPLIT.split(line):
            norm = _STRIP.sub("", piece)
            if len(norm) >= MIN_CHARS:
                out.append(norm)
    return out


def duplicate_rule_warnings(root: Path) -> list[str]:
    """One WARN per sentence that appears verbatim in two or more control files."""
    seen: dict[str, set[str]] = defaultdict(set)
    for pattern in CONTROL_GLOBS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            for sentence in _sentences(path.read_text(encoding="utf-8", errors="replace")):
                seen[sentence].add(rel)
    shared = sorted(
        ((s, files) for s, files in seen.items() if len(files) > 1),
        key=lambda item: (-len(item[0]), item[0]),
    )
    warnings = [
        f"duplicate rule phrase in {', '.join(sorted(files))}: “{sentence[:24]}…”（单一事实源：其余文件改写为 see X）"
        for sentence, files in shared[:MAX_REPORTED]
    ]
    if len(shared) > MAX_REPORTED:
        warnings.append(f"duplicate rule phrase: 另有 {len(shared) - MAX_REPORTED} 处未列出")
    return warnings


def stale_projection_warnings(root: Path, course: str | None = None) -> list[str]:
    """WARN when a derived file is older than the authoritative file it projects."""
    data_root = root / "DATA"
    if not data_root.is_dir():
        return []
    pairs = (
        ("ontology/graph.jsonl", "ontology/projection.json", "scripts/ontology.py compact"),
        ("runtime/course_state.json", "runtime/course_state.md", "scripts/course_runtime.py render"),
        ("runtime/tasks.json", "runtime/queue.md", "scripts/task_queue.py render --apply"),
    )
    warnings: list[str] = []
    for course_path in iter_course_paths(root, course=course):
        if course_path.is_symlink() or not course_path.is_dir():
            continue
        for source, derived, fix in pairs:
            src, dst = course_path / source, course_path / derived
            if not (src.is_file() and dst.is_file()):
                continue  # a missing optional projection is not "stale"
            if src.stat().st_mtime - dst.stat().st_mtime > TOLERANCE_SECONDS:
                warnings.append(
                    f"stale projection: {dst.relative_to(root).as_posix()} 早于 {source}（重建：{fix}）"
                )
    return warnings


def stale_cache_warnings(root: Path, course: str | None = None) -> list[str]:
    """WARN when the optional local vector index predates the course textbook.

    The index is regenerable and non-authoritative, so staleness only degrades
    search quality; it is never an ERROR and a missing index is never reported.
    """
    data_root = root / "DATA"
    if not data_root.is_dir():
        return []
    warnings: list[str] = []
    for course_path in iter_course_paths(root, course=course):
        if course_path.is_symlink() or not course_path.is_dir():
            continue
        index = course_path / "cache" / "vector" / "index.json"
        book = root / "TEXTBOOK" / course_path.name / "book.md"
        if not (index.is_file() and book.is_file()):
            continue
        if book.stat().st_mtime - index.stat().st_mtime > TOLERANCE_SECONDS:
            warnings.append(
                f"stale cache: {index.relative_to(root).as_posix()} 早于 book.md（重建：scripts/vector_index.py build --course X --apply）"
            )
    return warnings


def cross_course_symlink_errors(root: Path, course: str | None = None) -> list[str]:
    """ERROR: a symlink inside one course tree must not resolve outside that course."""
    errors: list[str] = []
    for top in ("DATA", "TEXTBOOK"):
        base = root / top
        if base.is_symlink():
            errors.append(f"course container is a symlink: {top}")
            continue
        if not base.is_dir():
            continue
        for course_path in iter_course_paths(root, top, course):
            if course_path.is_symlink():
                errors.append(f"course directory is a symlink: {course_path.relative_to(root).as_posix()}")
                continue
            if not course_path.is_dir():
                continue
            own = course_path.resolve()
            for path in course_path.rglob("*"):
                if not path.is_symlink():
                    continue
                try:
                    target = path.resolve()
                except (OSError, RuntimeError):
                    errors.append(f"unresolvable symlink: {path.relative_to(root).as_posix()}")
                    continue
                if target != own and own not in target.parents:
                    errors.append(
                        f"cross-course symlink: {path.relative_to(root).as_posix()} → {target}（课程隔离）"
                    )
    return errors
