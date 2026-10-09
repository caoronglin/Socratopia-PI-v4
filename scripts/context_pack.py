#!/usr/bin/env python3
"""Print the smallest hot context for one course (read-only; nothing is written)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.context_pack import DEFAULT_BUDGET, build_pack, render_pack  # noqa: E402
from scripts.lib.repository import validate_course_name  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="按 plan §10 顺序输出课程热上下文包（只读）")
    parser.add_argument("--course", required=True)
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="总 token 预算（估算）")
    parser.add_argument("--no-prep", action="store_true", help="不包含当前 PREP")
    parser.add_argument("--recent", type=int, default=2, help="保留最近几课记录")
    args = parser.parse_args(argv)
    if args.budget < 200:
        parser.error("--budget 过小（至少 200）")
    try:
        course = validate_course_name(args.course)
    except ValueError as exc:
        parser.error(str(exc))
    pack = build_pack(ROOT, course, budget=args.budget, include_prep=not args.no_prep, recent_lessons=args.recent)
    sys.stdout.write(render_pack(pack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
