#!/usr/bin/env python3
"""Lesson preparation (PREP): scaffold from real course state, check alignment, report staleness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.prep import check_prep, new_prep, prep_status  # noqa: E402
from scripts.lib.repository import validate_course_name  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="备课：生成骨架 / 教学评一致性检查 / 过期检测")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="生成 PREP 骨架（不覆盖已有；默认 dry-run）")
    new.add_argument("--course", required=True)
    new.add_argument("--lesson-id", required=True)
    new.add_argument("--chapter", default="")
    new.add_argument("--apply", action="store_true")

    check = sub.add_parser("check", help="校验一份 PREP（错误退出码 1）")
    check.add_argument("--course", required=True)
    check.add_argument("--lesson-id", required=True)

    status = sub.add_parser("status", help="列出本课程各 PREP 状态（ready/draft/stale/invalid/legacy）")
    status.add_argument("--course", required=True)

    args = parser.parse_args(argv)
    try:
        course = validate_course_name(args.course)
        if args.command == "new":
            result = new_prep(ROOT, course, args.lesson_id, args.chapter, apply=args.apply)
            preview = result.pop("preview", None)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if preview:
                print("\n--- 预览（加 --apply 写入）---\n" + preview)
            return 0
        if args.command == "check":
            errors, warnings = check_prep(ROOT, course, args.lesson_id)
            for message in warnings:
                print(f"WARN: {message}")
            for message in errors:
                print(f"ERROR: {message}")
            print("FAIL" if errors else "PASS")
            return 1 if errors else 0
        print(json.dumps(prep_status(ROOT, course), ensure_ascii=False, indent=2))
        return 0
    except ValueError as exc:
        print(f"✗ {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
