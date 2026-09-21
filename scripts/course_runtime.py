#!/usr/bin/env python3
"""Inspect, validate and migrate Socratopia v4 course runtime-state projections."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.course_state import (  # noqa: E402
    load_state,
    migrate_state,
    render_state_markdown,
    validate_state,
)
from scripts.lib.repository import validate_course_name  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="课程运行状态管理（phase+readiness+blockers）")
    parser.add_argument("command", choices=["status", "migrate", "validate", "render"])
    parser.add_argument("--course", required=True, help="课程名")
    args = parser.parse_args()
    validate_course_name(args.course)

    if args.command == "migrate":
        state = migrate_state(ROOT, args.course)
        print(render_state_markdown(state))
        return 0

    state = load_state(ROOT, args.course)
    if args.command == "validate":
        errors = validate_state(state)
        print("有效" if not errors else "\n".join(errors))
        return 0 if not errors else 1
    if args.command == "render":
        print(render_state_markdown(state))
        return 0
    # status: compact JSON projection for tooling
    print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
