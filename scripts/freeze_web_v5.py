"""Freeze a single native Socratopia-Web(.exe) entrypoint (Python 3.15)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if sys.version_info[:2] != (3, 15):
        raise RuntimeError("v5 frozen desktop API requires Python 3.15")
    import PyInstaller

    build = ROOT / "build" / "standalone-v5"
    build.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--clean", "--noconfirm", "--console",
        "--name", "Socratopia-Web",
        "--distpath", str(build),
        "--workpath", str(ROOT / "build" / "web-pyinstaller"),
        "--specpath", str(ROOT / "build" / "web-pyinstaller"),
        "--add-data", str(ROOT / "templates") + os.pathsep + "templates",
        "--collect-submodules", "platform_api",
        "--collect-submodules", "scripts",
        "--collect-all", "agentscope",
        "--collect-all", "fastapi",
        "--collect-all", "starlette",
        "--collect-all", "uvicorn",
        "--collect-all", "pydantic",
        "--collect-all", "pydantic_core",
        "--collect-all", "httpx",
        str(ROOT / "platform_api" / "desktop.py"),
    ]
    print("PyInstaller", PyInstaller.__version__, "on", sys.version, flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
    binary = build / ("Socratopia-Web.exe" if os.name == "nt" else "Socratopia-Web")
    if not binary.is_file() or binary.stat().st_size < 1_000_000:
        raise RuntimeError("Missing or implausibly small native Web binary")
    print(f"Frozen executable: {binary} ({binary.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
