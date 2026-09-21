#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    "scripts/course_runtime.py",
    "scripts/task_queue.py",
    "scripts/review.py",
    "scripts/assessment.py",
    "scripts/build_reteach_queue.py",
    "scripts/prepare_after_upload.py",
]

CONTROL_FILES = [
    ROOT / "AGENTS.md",
    *(ROOT / ".pi/skills").glob("*/SKILL.md"),
    *(ROOT / "SYSTEM/SPEC").glob("*.md"),
]


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            fail(f"missing required file: {rel}", errors)

    # Phase 0 freeze: exactly three active skills (approval §1.2 / §22).
    active_skills = sorted(p.parent.name for p in (ROOT / ".pi/skills").glob("*/SKILL.md"))
    if len(active_skills) != 3:
        fail(f"active skill count must be 3, found {len(active_skills)}: {active_skills}", errors)

    # Phase 0 quarantine manifest must exist and be valid JSON.
    manifest = ROOT / "quarantine/sources.json"
    if not manifest.exists():
        fail("missing quarantine manifest: quarantine/sources.json", errors)
    else:
        try:
            json.loads(manifest.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"invalid json quarantine/sources.json: {exc}", errors)

    # Root duplicates raise always-loaded token cost / ambiguity in Pi.
    for rel in ["CLAUDE.md", "AGENT_SYSTEM_PROMPT.md", ".pi/SYSTEM.md"]:
        if (ROOT / rel).exists():
            warnings.append(f"avoid active duplicate/override: {rel}")

    # Validate skill frontmatter.
    for p in (ROOT / ".pi/skills").glob("*/SKILL.md"):
        text = p.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\nname:" not in text or "\ndescription:" not in text:
            fail(f"invalid skill frontmatter: {p.relative_to(ROOT)}", errors)

    # Validate shipped JSON files/schemas.
    for p in ROOT.rglob("*.json"):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"invalid json {p.relative_to(ROOT)}: {exc}", errors)

    # Validate ontology append-only JSONL graphs (read-only; never rewrites history).
    data_root = ROOT / "DATA"
    if data_root.exists():
        for graph in data_root.glob("*/ontology/graph.jsonl"):
            try:
                for lineno, raw in enumerate(graph.read_text(encoding="utf-8").splitlines(), 1):
                    line = raw.strip()
                    if line:
                        json.loads(line)
            except Exception as exc:
                fail(f"malformed ontology graph {graph.relative_to(ROOT)} (line {lineno}): {exc}", errors)

    stale = {
        r"\.claude/": "Claude-specific active skill path",
        r"D:\\\\": "machine-specific Windows path",
        r"Claude 子智能体": "hard dependency on Claude subagents",
    }
    for p in CONTROL_FILES:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for pattern, label in stale.items():
            if re.search(pattern, text, flags=re.I):
                fail(f"{p.relative_to(ROOT)} contains {label}", errors)

    print("Socratopia PI architecture doctor")
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
