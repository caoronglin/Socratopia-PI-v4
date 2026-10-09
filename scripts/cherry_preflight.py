#!/usr/bin/env python3
"""Read-only, offline workspace preflight for a Cherry Studio Pi Agent.

Cherry tool availability is session-dependent and cannot be determined by
reading local files; report it as unverified rather than inventing success.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.repository import course_dir, textbook_dir, validate_course_name  # noqa: E402

REQUIRED = (
    "AGENTS.md",
    ".pi/skills/socratopia-learning/SKILL.md",
    ".pi/skills/socratopia-tutor/SKILL.md",
    ".pi/skills/socratopia-engineering/SKILL.md",
    ".pi/prompts/start-class.md",
    "scripts/web_article.py",
    "integrations/cherry-studio/AGENT_PROMPT.md",
)

HOST_CAPABILITIES = (
    "cherry-tool-guide",
    "web_fetch / web_search",
    "kb_list / kb_search / kb_read (requires bound knowledge base)",
    "to_markdown (when supported)",
    "agent-memory (when exposed)",
)


def inspect(root: Path, course: str | None = None) -> dict:
    """Never calls Cherry tools, network services or write operations."""
    root = root.resolve()
    missing = [name for name in REQUIRED if not (root / name).is_file()]
    result: dict = {
        "workspace": str(root),
        "runtime": "pi (must be chosen in Cherry Studio)",
        "project_files": "ok" if not missing else "incomplete",
        "missing": missing,
        "cherry_tools": {name: "unverified: check live Agent tool list" for name in HOST_CAPABILITIES},
        "warnings": [],
        "course": None,
    }
    if course is not None:
        name = validate_course_name(course)
        data = course_dir(root, name)
        textbook = textbook_dir(root, name)
        status = {
            "name": name,
            "data_exists": data.is_dir(),
            "textbook_exists": textbook.is_dir(),
            "book_exists": (textbook / "book.md").is_file(),
            "progress_exists": (data / "PROGRESS.md").is_file(),
            "runtime_exists": (data / "runtime/course_state.json").is_file(),
        }
        result["course"] = status
        if not status["runtime_exists"]:
            result["warnings"].append("课程 runtime 文件不存在：不可将默认值当成有效开课状态")
        if not status["book_exists"]:
            result["warnings"].append("缺少 active book.md：仅能进行来源阅读，不能宣称主课本就绪")
    else:
        result["warnings"].append("尚未指定课程：对具体课程操作前按 course-binding.md 绑定唯一课程")
    result["ready_to_configure_agent"] = not missing
    result["ready_to_teach"] = None  # determined by the runtime/PREP gates, never this preflight
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cherry Pi Agent 本地环境只读预检（不访问 Cherry API）")
    parser.add_argument("--course", help="可选，检查单个课程的文件是否存在")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        report = inspect(args.root, args.course)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready_to_configure_agent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
