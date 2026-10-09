#!/usr/bin/env python3
"""Read, validate, write and clear `runtime/handoff.json` (ADR-006 carrier)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.handoff import (  # noqa: E402
    clear_handoff,
    load_handoff,
    set_handoff,
    validate_handoff,
)
from scripts.lib.repository import validate_course_name  # noqa: E402


def _print(record: object) -> None:
    print(json.dumps(record, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导师承接记录（runtime/handoff.json）")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("show", "validate", "clear"):
        p = sub.add_parser(name)
        p.add_argument("--course", required=True)
        if name == "clear":
            p.add_argument("--apply", action="store_true")

    p_set = sub.add_parser("set", help="写入一条真实承接（需 --apply）")
    p_set.add_argument("--course", required=True)
    p_set.add_argument("--lesson-id", required=True)
    p_set.add_argument("--from-tutor", required=True)
    p_set.add_argument("--to-tutor", required=True)
    p_set.add_argument(
        "--carry",
        required=True,
        help='JSON 列表：[{"knowledge_point":..,"status":..,"evidence":..,"recommended_angle":..}]',
    )
    p_set.add_argument("--opening-anchor", default="")
    p_set.add_argument("--tone-note", default="")
    p_set.add_argument("--apply", action="store_true")

    args = parser.parse_args(argv)
    course = validate_course_name(args.course)

    if args.command == "show":
        _print(load_handoff(ROOT, course))
        return 0
    if args.command == "validate":
        problems = validate_handoff(load_handoff(ROOT, course))
        for problem in problems:
            print(f"ERROR: {problem}")
        print("FAIL" if problems else "PASS")
        return 1 if problems else 0

    if not args.apply:
        raise SystemExit("变更操作需要显式传入 --apply。")
    if args.command == "clear":
        _print(clear_handoff(ROOT, course))
        return 0

    try:
        carry = json.loads(args.carry)
        if not isinstance(carry, list):
            raise ValueError("--carry 必须是 JSON 列表")
        _print(
            set_handoff(
                ROOT,
                course,
                args.lesson_id,
                args.from_tutor,
                args.to_tutor,
                carry,
                opening_anchor=args.opening_anchor,
                tone_note=args.tone_note,
            )
        )
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"✗ 未写入：{exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
