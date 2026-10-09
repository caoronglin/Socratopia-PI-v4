#!/usr/bin/env python3
"""Lesson clock: start/status/heartbeat/pause/resume/finish/interrupt.

No hidden background process and no writes to PROGRESS or active textbook.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.lesson_timer import MINIMUM_SECONDS, start, status, transition
from scripts.lib.repository import validate_course_name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="45 分钟课堂有效计时：空闲>5分钟自动暂停；提前结束不算完成")
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("start", "status", "heartbeat", "pause", "resume", "finish", "interrupt"):
        sub = commands.add_parser(name)
        sub.add_argument("--course", required=True)
        if name == "start":
            sub.add_argument("--lesson-id", required=True)
    args = parser.parse_args(argv)
    try:
        course = validate_course_name(args.course)
        if args.action == "start":
            outcome = start(ROOT, course, args.lesson_id)
        elif args.action == "status":
            outcome = status(ROOT, course)
        else:
            outcome = transition(ROOT, course, args.action)
        print(json.dumps(outcome, indent=2, ensure_ascii=False))
        if outcome.get("finish_denied") or outcome.get("heartbeat_not_recorded"):
            return 2
        return 0
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
