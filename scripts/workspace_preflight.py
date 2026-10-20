#!/usr/bin/env python3
"""Read-only offline preflight: local Socratopia project, no model SDK invocation.

This reports file presence and course status but never claims that a configured
provider is reachable, that PREP is ready, or that course mastery is verified.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.repository import course_dir, textbook_dir, validate_course_name  # noqa: E402

REQUIRED = (
    "AGENTS.md",
    "education/skills/socratopia-learning/SKILL.md",
    "education/skills/socratopia-tutor/SKILL.md",
    "education/skills/socratopia-engineering/SKILL.md",
    "education/prompts/start-class.md",
    "scripts/web_article.py",
    "platform_api/agentscope_runtime.py",
)


def inspect(root: Path, course: str | None = None) -> dict:
    """A side-effect-free, explicitly course-scoped local readiness report."""
    root = root.resolve()
    missing = [
        path for path in REQUIRED
        if (root / path).is_symlink() or not (root / path).is_file()
    ]
    result = {
        "workspace": str(root),
        "runtime": "agentscope",
        "project_files": "ok" if not missing else "incomplete",
        "missing": missing,
        "model_credentials_configured": bool(os.getenv("OPENAI_API_KEY")),
        "model_credentials_verified": False,
        "warnings": [],
        "course": None,
    }
    if course is not None:
        name = validate_course_name(course)
        data = course_dir(root, name)
        textbook = textbook_dir(root, name)
        info = {
            "name": name,
            "data_exists": data.is_dir(),
            "textbook_exists": textbook.is_dir(),
            "book_exists": (textbook / "book.md").is_file(),
            "progress_exists": (data / "PROGRESS.md").is_file(),
            "runtime_exists": (data / "runtime/course_state.json").is_file(),
        }
        result["course"] = info
        if not info["runtime_exists"]:
            result["warnings"].append("课程状态文件缺失；默认值不是有效开课状态")
        if not info["book_exists"]:
            result["warnings"].append("没有活动主教材；不能宣称课堂已就绪")
    else:
        result["warnings"].append("未指定课程：预检不代表任何课程已就绪")
    result["ready_to_configure_agent"] = not missing
    result["ready_to_teach"] = None
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AgentScope 课程工作区只读预检")
    parser.add_argument("--course", help="可选：仅检查一门课程")
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
