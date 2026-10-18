"""Socratopia v5 offline desktop Web launcher (PyInstaller executable).

Owns localhost FastAPI. AgentScope is the sole model runtime.
The app ships built static assets; it never runs npm, pip or an online installer.
"""
from __future__ import annotations

import argparse
import os
import secrets
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.request import Request, urlopen

TEMPLATE_NAMES = ("PROGRESS.md", "CONTEXT_INDEX.md", "handoff.json", "tasks.json")


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _templates_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "templates"
    return _bundle_root() / "templates"


def _workspace() -> Path:
    configured = os.environ.get("SOCRATOPIA_ROOT")
    if configured:
        result = Path(configured).expanduser().absolute()
    else:
        result = Path.home() / ".socratopia" / "workspace"
    if result.is_symlink():
        raise RuntimeError("Workspace must not be a symbolic link")
    result.mkdir(parents=True, exist_ok=True)
    if not result.is_dir():
        raise RuntimeError("Workspace is not a directory")
    return result.resolve()


def _prepare_templates(workspace: Path) -> None:
    source = _templates_root()
    dest = workspace / "templates"
    if dest.is_symlink():
        raise RuntimeError("Workspace templates cannot be a symbolic link")
    dest.mkdir(parents=True, exist_ok=True)
    for filename in TEMPLATE_NAMES:
        original = source / filename
        if not original.is_file() or original.is_symlink():
            raise RuntimeError(f"Bundled template missing: {filename}")
        target = dest / filename
        if target.is_symlink():
            raise RuntimeError(f"Workspace template cannot be a symlink: {filename}")
        # Existing user templates and data are never overwritten by upgrades.
        if not target.exists():
            try:
                with target.open("xb") as handle:
                    handle.write(original.read_bytes())
            except FileExistsError:
                pass


def _static_path() -> Path:
    return _bundle_root() / "web" / "dist"


def check_distribution() -> None:
    static = _static_path()
    required = [static / "index.html"]
    required.extend(_templates_root() / filename for filename in TEMPLATE_NAMES)
    for path in required:
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Incomplete Web bundle: {path}")
    if not list((static / "assets").glob("*.js")):
        raise RuntimeError("Incomplete Web bundle: missing Vite JavaScript assets")
    for path in (static, static / "assets"):
        if path.is_symlink():
            raise RuntimeError("Symlinked distribution asset is not accepted")


def _open_when_ready(url: str) -> None:
    for _ in range(60):
        try:
            with urlopen(url + "/api/health", timeout=0.5) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except OSError:
            time.sleep(0.25)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Socratopia v5 native local Web launcher")
    parser.add_argument("--port", type=int, default=8765, help="Local Web port (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser")
    parser.add_argument("--check", action="store_true", help="Check bundled runtime and exit")
    args = parser.parse_args(argv)
    try:
        if not 1024 <= args.port <= 65535:
            raise RuntimeError("Port must be between 1024 and 65535")
        check_distribution()
        if args.check:
            print("Socratopia Web bundle: complete")
            return 0
        root = _workspace()
        _prepare_templates(root)
        supplied = os.environ.get("SOCRATOPIA_API_TOKEN")
        if supplied and len(supplied) < 16:
            raise RuntimeError("SOCRATOPIA_API_TOKEN must be at least 16 characters")
        token = supplied or secrets.token_urlsafe(32)
        os.environ["SOCRATOPIA_API_TOKEN"] = token
        os.environ["SOCRATOPIA_ROOT"] = str(root)
        static = _static_path()
        from fastapi.staticfiles import StaticFiles
        from platform_api.app import app
        import uvicorn

        app.mount("/", StaticFiles(directory=str(static), html=True), name="desktop-static")
        url = f"http://127.0.0.1:{args.port}"
        print(f"\nSocratopia Web: {url}")
        print(f"API token (paste into Web login): {token}")
        print(f"Workspace: {root}")
        print("Model runtime: AgentScope 2.0.10; supervisor: Python")
        print("Close this terminal / press Ctrl+C to stop.\n", flush=True)
        if not args.no_browser:
            threading.Thread(target=_open_when_ready, args=(url,), daemon=True).start()
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
