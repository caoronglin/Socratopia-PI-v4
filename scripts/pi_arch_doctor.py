#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "AGENTS.md",
    ".pi/skills/socratopia-learning/SKILL.md",
    ".pi/skills/socratopia-tutor/SKILL.md",
    ".pi/skills/socratopia-engineering/SKILL.md",
    "SYSTEM/SPEC/ARCHITECTURE.md",
    "SYSTEM/SPEC/RUNTIME_CONTRACT.md",
    "SYSTEM/SPEC/TRUST_EFFECTS.md",
    # Phase 1 restored deterministic runtime tools (approval §16 / §19).
    "scripts/lib/repository.py",
    "scripts/lib/handoff.py",
    "scripts/lib/budget.py",
    "scripts/lib/context_pack.py",
    "scripts/lib/duplicates.py",
    "scripts/lib/memory.py",
    "scripts/lib/prep.py",
    "scripts/memory.py",
    "scripts/prep.py",
    "scripts/export_obsidian.py",
    "scripts/handoff.py",
    "scripts/context_pack.py",
    "scripts/course_runtime.py",
    "scripts/task_queue.py",
    "scripts/review.py",
    "scripts/assessment.py",
    "scripts/build_reteach_queue.py",
    "scripts/prepare_after_upload.py",
]

CONTROL_FILES = [
    "AGENTS.md",
    ".pi/skills/*/SKILL.md",
    "SYSTEM/SPEC/*.md",
]

STALE_RULES = {
    r"\.claude/": "Claude-specific active skill path",
    r"D:\\\\": "machine-specific Windows path",
    r"\b[A-Za-z]:\\Users\\": "machine-specific Windows user path",
    r"(?<![\w.])/Users/[^/\s`]+/": "machine-specific macOS user path",
    r"Claude 子智能体": "hard dependency on Claude subagents",
}


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def _read_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Read one JSON object; never raises, never writes."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return None, f"invalid json: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON 根对象必须是 object"
    return payload, None


def _files(root: Path, excluded: set[str] | None = None):
    """Walk files without descending into excluded trees or directory symlinks."""
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in (excluded or set())
                         and not (Path(base) / d).is_symlink())
        for name in sorted(names):
            path = Path(base) / name
            if not path.is_symlink():
                yield path


def check_canonical_state(root: Path, errors: list[str], warnings: list[str],
                          course: str | None = None) -> None:
    """Validate each course's canonical runtime JSON (read-only).

    Closes the gap where plan.md §13 promised ERROR on `canonical state
    missing/invalid` but only the per-course CLIs performed the check.
    """
    data_root = root / "DATA"
    if not data_root.is_dir():
        return

    from scripts.lib.repository import iter_course_paths
    from scripts.lib.course_state import validate_state
    from scripts.lib.handoff import validate_handoff
    from scripts.lib.task_queue import validate_queue

    checks = (
        ("course_state.json", validate_state),
        ("tasks.json", validate_queue),
        ("handoff.json", validate_handoff),
    )
    for course_path in iter_course_paths(root, course=course):
        if course_path.is_symlink() or not course_path.is_dir():
            continue
        runtime = course_path / "runtime"
        if not runtime.is_dir():
            continue
        for name, validator in checks:
            target = runtime / name
            shown = target.relative_to(root)
            if not target.exists():
                fail(f"missing runtime file: {shown}", errors)
                continue
            payload, problem = _read_json_object(target)
            if problem:
                fail(f"{shown}: {problem}", errors)
                continue
            for message in validator(payload or {}):
                fail(f"{shown}: {message}", errors)
        # Course isolation: the record must claim the course it lives under.
        state, problem = _read_json_object(runtime / "course_state.json")
        if not problem and state and state.get("course") != course_path.name:
            fail(
                f"{course_path.relative_to(root)}/runtime/course_state.json: "
                f"course={state.get('course')!r} 与所在目录 {course_path.name!r} 不一致",
                errors,
            )
        # Queue data layer: every task must belong to the course it is stored under.
        queue, problem = _read_json_object(runtime / "tasks.json")
        if not problem and queue and isinstance(queue.get("tasks"), list):
            for index, task in enumerate(queue["tasks"]):
                owner = task.get("course") if isinstance(task, dict) else None
                if owner is not None and owner != course_path.name:
                    fail(
                        f"{course_path.relative_to(root)}/runtime/tasks.json: "
                        f"tasks[{index}].course={owner!r} 与所在目录 {course_path.name!r} 不一致（跨课程污染）",
                        errors,
                    )


def check_manifest(root: Path, errors: list[str], warnings: list[str]) -> None:
    """Keep manifest.json honest about the shipped file set."""
    manifest = root / "manifest.json"
    if not manifest.exists():
        warnings.append("missing manifest.json")
        return
    payload, problem = _read_json_object(manifest)
    if problem:
        fail(f"invalid json manifest.json: {problem}", errors)
        return
    listed = set(payload.get("files") or [])
    # DATA/ and TEXTBOOK/ are per-course user data (.gitignore); they are never
    # shipped, so they must not be reported as manifest drift.
    untracked = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "DATA", "TEXTBOOK"}
    on_disk = {
        str(p.relative_to(root)).replace("\\", "/")
        for p in _files(root, untracked)
        if p.is_file()
    }
    for rel in sorted(listed - on_disk):
        fail(f"manifest lists missing file: {rel}", errors)
    for rel in sorted(on_disk - listed):
        fail(f"file missing from manifest: {rel}", errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="只读架构与课程状态健康检查")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="项目根目录（默认本仓库）")
    parser.add_argument("--course", help="只检查指定课程数据；省略时检查全部课程")
    parser.add_argument("--budget", action="store_true", help="打印上下文 token 预算报告")
    parser.add_argument("--window", type=int, default=128_000, help="预算报告使用的模型上下文窗口（tokens）")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from scripts.lib.repository import iter_course_paths, validate_course_name
    from scripts.lib.duplicates import cross_course_symlink_errors

    errors: list[str] = []
    warnings: list[str] = []
    if args.course is not None:
        try:
            args.course = validate_course_name(args.course)
        except ValueError as exc:
            parser.error(str(exc))
        if not any(iter_course_paths(root, top, args.course) for top in ("DATA", "TEXTBOOK")):
            fail(f"missing course: {args.course}", errors)

    # Reject escaping links before any course content is read.
    link_errors = cross_course_symlink_errors(root, args.course)
    errors.extend(link_errors)
    safe_courses = not link_errors

    for rel in REQUIRED:
        if not (root / rel).exists():
            fail(f"missing required file: {rel}", errors)

    # Phase 0 freeze: exactly three active skills (approval §1.2 / §22).
    active_skills = sorted(p.parent.name for p in (root / ".pi/skills").glob("*/SKILL.md"))
    if len(active_skills) != 3:
        fail(f"active skill count must be 3, found {len(active_skills)}: {active_skills}", errors)

    # Phase 0 quarantine manifest must exist and be valid JSON.
    quarantine = root / "quarantine/sources.json"
    if not quarantine.exists():
        fail("missing quarantine manifest: quarantine/sources.json", errors)
    else:
        try:
            json.loads(quarantine.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"invalid json quarantine/sources.json: {exc}", errors)

    # Root duplicates raise always-loaded token cost / ambiguity in Pi.
    for rel in ["CLAUDE.md", "AGENT_SYSTEM_PROMPT.md"]:
        if (root / rel).exists():
            warnings.append(f"avoid active duplicate/override: {rel}")
    # ADR-002: replacing PI's system prompt is forbidden, not merely discouraged (plan §13 ERROR).
    if (root / ".pi/SYSTEM.md").exists():
        fail("forbidden override: .pi/SYSTEM.md (ADR-002)", errors)

    # Validate skill frontmatter.
    for p in (root / ".pi/skills").glob("*/SKILL.md"):
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\nname:" not in text or "\ndescription:" not in text:
            fail(f"invalid skill frontmatter: {p.relative_to(root)}", errors)

    # Control-plane traversal prunes user data; a scoped check never enumerates other courses.
    excluded = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "DATA", "TEXTBOOK"}
    json_files = [p for p in _files(root, excluded) if p.suffix == ".json"]
    if safe_courses:
        for top in ("DATA", "TEXTBOOK"):
            for course_path in iter_course_paths(root, top, args.course):
                if course_path.is_dir():
                    json_files.extend(p for p in _files(course_path) if p.suffix == ".json")
    for p in json_files:
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"invalid json {p.relative_to(root)}: {exc}", errors)

    # Validate ontology append-only JSONL graphs (read-only; never rewrites history).
    data_root = root / "DATA"
    if safe_courses and data_root.exists():
        for course_path in iter_course_paths(root, course=args.course):
            graph = course_path / "ontology/graph.jsonl"
            if not graph.is_file():
                continue
            lineno = 0
            try:
                for lineno, raw in enumerate(graph.read_text(encoding="utf-8").splitlines(), 1):
                    line = raw.strip()
                    if line:
                        json.loads(line)
            except Exception as exc:
                fail(f"malformed ontology graph {graph.relative_to(root)} (line {lineno}): {exc}", errors)

    if safe_courses:
        if args.course is None:
            check_canonical_state(root, errors, warnings)
        else:
            check_canonical_state(root, errors, warnings, args.course)
    check_manifest(root, errors, warnings)

    # plan.md §10 soft thresholds: WARN only, never fail the doctor.
    from scripts.lib.budget import budget_warnings, render_report, soft_threshold_warnings

    warnings.extend(soft_threshold_warnings(root))
    warnings.extend(budget_warnings(root, args.window))

    # plan.md §13: duplicate rule sources and stale projections are WARN; cross-course symlinks are ERROR.
    from scripts.lib.duplicates import (
        cross_course_symlink_errors,
        duplicate_rule_warnings,
        stale_cache_warnings,
        stale_projection_warnings,
    )

    warnings.extend(duplicate_rule_warnings(root))
    if safe_courses:
        warnings.extend(stale_projection_warnings(root, args.course))
        warnings.extend(stale_cache_warnings(root, args.course))

    # Memory compression invariants are hard (ERROR); PREP staleness is advisory (WARN).
    from scripts.lib.memory import doctor_findings
    from scripts.lib.prep import doctor_warnings

    if safe_courses:
        memory_errors, memory_warnings = doctor_findings(root, args.course)
        for message in memory_errors:
            fail(message, errors)
        warnings.extend(memory_warnings)
        warnings.extend(doctor_warnings(root, args.course))

    for pattern in CONTROL_FILES:
        for p in sorted(root.glob(pattern)):
            text = p.read_text(encoding="utf-8")
            for rule, label in STALE_RULES.items():
                if re.search(rule, text, flags=re.I):
                    fail(f"{p.relative_to(root)} contains {label}", errors)

    print("Socratopia PI architecture doctor")
    if args.budget:
        print(render_report(root, args.window))
    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS: {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
