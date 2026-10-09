#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.course_state import default_state  # noqa: E402
from scripts.lib.repository import course_dir, textbook_dir, safe_child_path, validate_course_name  # noqa: E402


def valid_course(name: str) -> str:
    try:
        if "\x00" in name:
            raise ValueError(name)
        return validate_course_name(name)
    except ValueError:
        raise argparse.ArgumentTypeError("course must be a single safe directory name") from None


def write_if_missing(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return "skip"
    path.write_text(text, encoding="utf-8")
    return "create"


def main() -> int:
    ap = argparse.ArgumentParser(description="Create missing Socratopia course scaffolding without overwriting existing files.")
    ap.add_argument("course", type=valid_course)
    args = ap.parse_args()

    course = args.course
    data = course_dir(ROOT, course)
    book = textbook_dir(ROOT, course)
    now = datetime.now(timezone.utc).isoformat()

    created = []
    for path, text in [
        (safe_child_path(data, "PROGRESS.md"), (ROOT / "templates/PROGRESS.md").read_text(encoding="utf-8")),
        (safe_child_path(data, "CONTEXT/CONTEXT_INDEX.md"), (ROOT / "templates/CONTEXT_INDEX.md").read_text(encoding="utf-8")),
        (safe_child_path(data, "CONTEXT/LESSON_SUMMARIES.md"), "# Lesson Summaries\n"),
        (safe_child_path(data, "CONTEXT/RETEACH_QUEUE.md"), "# Reteach Queue\n"),
        (safe_child_path(data, "DIARY.md"), "# Learning Diary\n"),
        (safe_child_path(data, "MISTAKE_BOOK.md"), "# Mistake Book\n"),
        (safe_child_path(book, "_outline.md"), "# Coursebook Outline\n"),
        (safe_child_path(book, "PREP/_index.md"), "# Lesson Prep Index\n"),
    ]:
        if write_if_missing(path, text) == "create":
            created.append(path.relative_to(ROOT))

    # Single producer: templates/course_state.json is documentation, locked to this by tests.
    state = default_state(course)
    if write_if_missing(safe_child_path(data, "runtime/course_state.json"), json.dumps(state, ensure_ascii=False, indent=2)+"\n") == "create":
        created.append((safe_child_path(data, "runtime/course_state.json")).relative_to(ROOT))
    if write_if_missing(safe_child_path(data, "runtime/handoff.json"), (ROOT / "templates/handoff.json").read_text(encoding="utf-8")) == "create":
        created.append((safe_child_path(data, "runtime/handoff.json")).relative_to(ROOT))
    if write_if_missing(safe_child_path(data, "runtime/tasks.json"), (ROOT / "templates/tasks.json").read_text(encoding="utf-8")) == "create":
        created.append((safe_child_path(data, "runtime/tasks.json")).relative_to(ROOT))
    projection = {
        "schema_version": 1,
        "course": course,
        "generated_at": now,
        "derived": True,
        "authoritative": False,
        "nodes": {},
        "edges": [],
    }
    if write_if_missing(safe_child_path(data, "ontology/graph.jsonl"), "") == "create":
        created.append((safe_child_path(data, "ontology/graph.jsonl")).relative_to(ROOT))
    if write_if_missing(safe_child_path(data, "ontology/projection.json"), json.dumps(projection, ensure_ascii=False, indent=2) + "\n") == "create":
        created.append((safe_child_path(data, "ontology/projection.json")).relative_to(ROOT))

    (safe_child_path(book, "SOURCES/_raw")).mkdir(parents=True, exist_ok=True)
    (safe_child_path(book, "images")).mkdir(parents=True, exist_ok=True)

    print(f"course={course}")
    print(f"created={len(created)}")
    for p in created:
        print(f"+ {p}")
    print("Existing files were never overwritten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
