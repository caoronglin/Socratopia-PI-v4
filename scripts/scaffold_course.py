#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def valid_course(name: str) -> str:
    name = name.strip()
    if not name or name in {".", ".."} or "/" in name or "\\" in name or "\x00" in name:
        raise argparse.ArgumentTypeError("course must be a single safe directory name")
    return name


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
    data = ROOT / "DATA" / course
    book = ROOT / "TEXTBOOK" / course
    now = datetime.now(timezone.utc).isoformat()

    created = []
    for path, text in [
        (data / "PROGRESS.md", (ROOT / "templates/PROGRESS.md").read_text(encoding="utf-8")),
        (data / "CONTEXT/CONTEXT_INDEX.md", (ROOT / "templates/CONTEXT_INDEX.md").read_text(encoding="utf-8")),
        (data / "CONTEXT/LESSON_SUMMARIES.md", "# Lesson Summaries\n"),
        (data / "CONTEXT/RETEACH_QUEUE.md", "# Reteach Queue\n"),
        (data / "DIARY.md", "# Learning Diary\n"),
        (data / "MISTAKE_BOOK.md", "# Mistake Book\n"),
        (book / "_outline.md", "# Coursebook Outline\n"),
        (book / "PREP/_index.md", "# Lesson Prep Index\n"),
    ]:
        if write_if_missing(path, text) == "create":
            created.append(path.relative_to(ROOT))

    state = json.loads((ROOT / "templates/course_state.json").read_text(encoding="utf-8"))
    state["course"] = course
    state["updated_at"] = now
    if write_if_missing(data / "runtime/course_state.json", json.dumps(state, ensure_ascii=False, indent=2)+"\n") == "create":
        created.append((data / "runtime/course_state.json").relative_to(ROOT))
    if write_if_missing(data / "runtime/handoff.json", (ROOT / "templates/handoff.json").read_text(encoding="utf-8")) == "create":
        created.append((data / "runtime/handoff.json").relative_to(ROOT))
    if write_if_missing(data / "runtime/tasks.json", (ROOT / "templates/tasks.json").read_text(encoding="utf-8")) == "create":
        created.append((data / "runtime/tasks.json").relative_to(ROOT))
    projection = {
        "schema_version": 1,
        "course": course,
        "generated_at": now,
        "derived": True,
        "authoritative": False,
        "nodes": {},
        "edges": [],
    }
    if write_if_missing(data / "ontology/graph.jsonl", "") == "create":
        created.append((data / "ontology/graph.jsonl").relative_to(ROOT))
    if write_if_missing(data / "ontology/projection.json", json.dumps(projection, ensure_ascii=False, indent=2) + "\n") == "create":
        created.append((data / "ontology/projection.json").relative_to(ROOT))

    (book / "SOURCES/_raw").mkdir(parents=True, exist_ok=True)
    (book / "images").mkdir(parents=True, exist_ok=True)

    print(f"course={course}")
    print(f"created={len(created)}")
    for p in created:
        print(f"+ {p}")
    print("Existing files were never overwritten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
