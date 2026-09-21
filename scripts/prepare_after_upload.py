#!/usr/bin/env python3
"""教材/资料上传完成后的受控本地流水线（v4）。

不编造或重写主课本：`TEXTBOOK/<课程>/book.md` 必须已存在。
仅编排**已恢复的本地工具**；不执行远程 OCR/MinerU、视觉备课或自动备课（分阶段门控）。
绝不修改 PROGRESS.md。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("\n$", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="教材/资料上传完成后的受控本地流水线")
    parser.add_argument("--course", required=True, help="课程名，对应 TEXTBOOK/<课程>")
    args = parser.parse_args()

    book = ROOT / "TEXTBOOK" / args.course / "book.md"
    if not book.exists():
        raise SystemExit(
            f"缺少 active 主课本：{book}。先执行教材编目，建立 book.md、_outline.md 和 manifest.json；"
            "本流水线不会猜测或覆盖教材正文。"
        )

    run([sys.executable, "scripts/build_reteach_queue.py", "--course", args.course])
    run([sys.executable, "scripts/course_runtime.py", "migrate", "--course", args.course])
    run([sys.executable, "scripts/pi_arch_doctor.py"])

    print("\n完成：补讲候选与 runtime 投影已刷新，架构 doctor 已通过。")
    print("说明：未修改 PROGRESS.md；候选补讲是草案，真实掌握仅在课堂验证后记录。")
    print("未执行：远程 OCR/MinerU、视觉备课、自动备课——均为分阶段门控能力，需显式开启。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
