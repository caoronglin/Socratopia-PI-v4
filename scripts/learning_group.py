#!/usr/bin/env python3
"""Learning group scheduler for one Cherry Pi agent simulating D/E/F voices."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib import learning_group as group  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="多导师学习讨论：配置/开始/逐人发言/下一轮/停止")
    cmd = parser.add_subparsers(dest="action", required=True)
    for action in ("configure", "status", "start", "record", "continue", "stop"):
        sub = cmd.add_parser(action)
        sub.add_argument("--course", required=True)
        if action == "configure":
            sub.add_argument("--tutors", nargs="+", required=True, help="D E F 中任选 2-3 位")
            sub.add_argument("--lead", required=True, help="主持导师必须为成员")
        if action == "start":
            sub.add_argument("--topic", required=True)
            sub.add_argument("--rounds", type=int, choices=(1, 2, 3), default=2)
        if action == "record":
            sub.add_argument("--speaker", required=True)
            sub.add_argument("--text-file", default="-", help="发言正文文件或 -（stdin），不作为 shell 指令")
        if action == "continue":
            sub.add_argument("--question", default="")
    args = parser.parse_args(argv)
    try:
        if args.action == "configure":
            result = group.configure(ROOT, args.course, args.tutors, args.lead)
        elif args.action == "status":
            result = group.status(ROOT, args.course)
        elif args.action == "start":
            result = group.start(ROOT, args.course, args.topic, args.rounds)
        elif args.action == "record":
            if args.text_file == "-":
                statement = sys.stdin.read(group.MAX_UTTERANCE + 1)
            else:
                # Local user-supplied text; treated only as data.
                file = Path(args.text_file)
                if not file.is_file() or file.stat().st_size > 16000:
                    raise ValueError("发言文件不存在或超过读取上限")
                statement = file.read_text(encoding="utf-8")
            result = group.record(ROOT, args.course, args.speaker, statement)
        elif args.action == "continue":
            result = group.continue_round(ROOT, args.course, args.question)
        else:
            result = group.stop(ROOT, args.course)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
