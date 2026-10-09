#!/usr/bin/env python3
"""教材/资料上传完成后的受控本地流水线（v4）。

不编造或重写主课本：`TEXTBOOK/<课程>/book.md` 必须已存在。
仅编排本地流水线；不执行远程 OCR/MinerU（`mineru_ingest.py` 只提供需逐次授权的远程解析）、视觉备课或自动备课（分阶段门控）。
绝不修改 PROGRESS.md。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.repository import textbook_dir, validate_course_name


def run(command: list[str]) -> None:
    print("\n$", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="教材/资料上传完成后的受控本地流水线")
    parser.add_argument("--course", required=True, help="课程名，对应 TEXTBOOK/<课程>")
    args = parser.parse_args()

    try:
        args.course = validate_course_name(args.course)
        book = textbook_dir(ROOT, args.course) / "book.md"
    except ValueError as exc:
        parser.error(str(exc))
    if not book.is_file():
        raise SystemExit(
            f"缺少 active 主课本：{book}。先执行教材编目，建立 book.md、_outline.md 和 manifest.json；"
            "本流水线不会猜测或覆盖教材正文。"
        )

    stages = (
        ("补讲候选刷新", [sys.executable, "scripts/build_reteach_queue.py", "--course", args.course]),
        ("runtime 迁移与投影", [sys.executable, "scripts/course_runtime.py", "migrate", "--course", args.course]),
        ("单课健康检查", [sys.executable, "scripts/pi_arch_doctor.py", "--course", args.course]),
    )
    completed: list[str] = []
    for label, command in stages:
        try:
            run(command)
        except subprocess.CalledProcessError as exc:
            print(f"\n失败：{label}（exit={exc.returncode}）。已完成：{'、'.join(completed) or '无'}。", file=sys.stderr)
            print("已完成阶段的写入未回滚；未执行后续阶段，不宣称流水线完成。", file=sys.stderr)
            return 1
        completed.append(label)

    print("\n完成：补讲候选与 runtime 投影已刷新，架构 doctor 已通过。")
    print("说明：未修改 PROGRESS.md；候选补讲是草案，真实掌握仅在课堂验证后记录。")
    print("未执行：远程 OCR/MinerU、视觉备课、自动备课——均为分阶段门控能力，需逐次显式授权。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
