"""Embedded Python entrypoint invoked by the bundled Rust CLI.

Only approved repository scripts may execute. The installed scripts remain the
authoritative business implementation; PyInstaller supplies its own CPython
runtime and bundled imported dependencies. No eval, shell, network, or writes.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

ALLOWED = frozenset({
    "initialize.py", "learning_group.py", "lesson_timer.py",
    "prep.py", "web_article.py", "context_pack.py",
    "course_runtime.py", "cherry_preflight.py", "local_search.py",
    "review.py", "handoff.py", "task_queue.py", "memory.py",
    "package_release.py",
})


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ALLOWED:
        print("ERROR: 非法或未支持的后端命令", file=sys.stderr)
        return 2

    name, rest = args[0], args[1:]
    # In a PyInstaller onefile bundle sys.executable is the *backend binary*,
    # not a Python interpreter. Its sibling Rust CLI shares bin/.
    base = (Path(sys.executable).resolve().parent.parent
            if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1])
    scripts = base / "scripts"
    target = scripts / name
    if (scripts.is_symlink() or target.is_symlink() or not target.is_file()
            or target.resolve().parent != scripts.resolve()):
        print("ERROR: 脚本不存在、不受信任或路径越界", file=sys.stderr)
        return 2
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))
    sys.argv = [str(target), *rest]
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        if exc.code:
            print(str(exc.code), file=sys.stderr)
            return 1
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
