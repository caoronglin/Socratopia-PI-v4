#!/usr/bin/env python3
"""Operate the durable Socratopia v4 course task queue (persistent TODO, not a worker)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.repository import course_dir, validate_course_name  # noqa: E402
from scripts.lib.task_queue import (  # noqa: E402
    enqueue_task,
    queue_summary,
    render_queue,
    transition_task,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="课程持久任务队列")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--course", required=True)

    p_enq = sub.add_parser("enqueue")
    p_enq.add_argument("--course", required=True)
    p_enq.add_argument("--kind", required=True)
    p_enq.add_argument("--key", required=True)
    p_enq.add_argument("--lesson-id", default=None)
    p_enq.add_argument("--payload", default="{}")
    p_enq.add_argument("--apply", action="store_true")

    for command in ("start", "complete", "fail"):
        action = sub.add_parser(command)
        action.add_argument("--course", required=True)
        action.add_argument("--task-id", required=True)
        action.add_argument("--error", default=None)
        action.add_argument("--apply", action="store_true")

    p_render = sub.add_parser("render")
    p_render.add_argument("--course", required=True)
    p_render.add_argument("--apply", action="store_true")

    args = parser.parse_args()
    validate_course_name(args.course)

    if args.command == "list":
        print(json.dumps(queue_summary(ROOT, args.course), ensure_ascii=False, indent=2))
        return 0
    if not args.apply:
        raise SystemExit("变更操作需要显式传入 --apply。")
    if args.command == "enqueue":
        task = enqueue_task(
            ROOT,
            args.course,
            args.kind,
            args.key,
            lesson_id=args.lesson_id,
            payload=json.loads(args.payload),
        )
        print(json.dumps(task, ensure_ascii=False, indent=2))
        return 0
    if args.command == "render":
        path = course_dir(ROOT, args.course) / "runtime" / "queue.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_queue(ROOT, args.course), encoding="utf-8")
        print(path)
        return 0
    status = {"start": "running", "complete": "completed", "fail": "failed"}[args.command]
    task = transition_task(ROOT, args.course, args.task_id, status, args.error)
    print(json.dumps(task, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
