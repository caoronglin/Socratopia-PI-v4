#!/usr/bin/env python3
"""Memory layers: build the hot index, summarize lessons (warm), check compression invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib import memory as mem  # noqa: E402
from scripts.lib.repository import validate_course_name  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="记忆系统：热层生成 / 温层摘要 / 压缩不变量校验")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="生成热层（CONTEXT_INDEX.md 的标记块；默认 dry-run）")
    build.add_argument("--course", required=True)
    build.add_argument("--apply", action="store_true")

    summ = sub.add_parser("summarize", help="生成/刷新温层摘要（LESSON_SUMMARIES.md）")
    summ.add_argument("--course", required=True)
    summ.add_argument("--lesson-id", default=None, help="只处理一课；省略则处理 PROGRESS 中全部课")
    summ.add_argument("--apply", action="store_true")

    chk = sub.add_parser("check", help="校验压缩不变量（违反退出码 1）")
    chk.add_argument("--course", required=True)

    args = parser.parse_args(argv)
    try:
        course = validate_course_name(args.course)
        if args.command == "build":
            print(json.dumps(mem.build_hot(ROOT, course, args.apply), ensure_ascii=False, indent=2))
            return 0
        if args.command == "summarize":
            print(json.dumps(mem.build_summaries(ROOT, course, args.lesson_id, args.apply), ensure_ascii=False, indent=2))
            return 0
        errors, warnings = mem.check(ROOT, course)
        for message in warnings:
            print(f"WARN: {message}")
        for message in errors:
            print(f"ERROR: {message}")
        print("FAIL" if errors else "PASS")
        return 1 if errors else 0
    except ValueError as exc:
        print(f"✗ {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
