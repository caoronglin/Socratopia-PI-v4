#!/usr/bin/env python3
"""One-shot verification used locally and in CI: doctor first, then the test suite.

Exit code is non-zero if either step fails. Doctor WARNs never fail the run
unless `--strict` is passed (useful in CI once the baseline is clean).
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(label: str, command: list[str]) -> subprocess.CompletedProcess[str]:
    print(f"==> {label}: {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="doctor + 测试一键校验")
    parser.add_argument("--strict", action="store_true", help="doctor 出现 WARN 也视为失败")
    args = parser.parse_args(argv)

    failed = False

    doctor = _run("doctor", [sys.executable, "scripts/pi_arch_doctor.py"])
    if doctor.returncode != 0:
        failed = True
    elif args.strict and "WARN:" in doctor.stdout:
        print("✗ --strict：doctor 存在 WARN", file=sys.stderr)
        failed = True

    # Static compilation catches script entrypoints that test discovery never imports.
    if _run("compile", [sys.executable, "-m", "compileall", "-q", "scripts", "tests"]).returncode != 0:
        failed = True

    if importlib.util.find_spec("pytest") is not None:
        tests = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"]
    else:
        tests = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."]
    if _run("tests", tests).returncode != 0:
        failed = True

    print("FAIL" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
