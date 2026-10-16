"""Socratopia v5 offline desktop Web launcher (PyInstaller executable).

Owns localhost FastAPI and one native Pi child process. AgentScope handles only tutor collaboration.
The app ships built static assets; it never runs npm, pip or an online installer.
"""
from __future__ import annotations

import argparse
import os
import secrets
import socket
import subprocess
import shutil
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
    required = [static / "index.html", _bundle_root() / "runtimes" / "pi" / "server.mjs",
                _bundle_root() / "runtimes" / "pi" / "node_modules" / "@earendil-works" / "pi-coding-agent" / "package.json"]
    required.extend(_templates_root() / filename for filename in TEMPLATE_NAMES)
    for path in required:
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Incomplete Web bundle: {path}")
    if not list((static / "assets").glob("*.js")):
        raise RuntimeError("Incomplete Web bundle: missing Vite JavaScript assets")
    if not _node_binary():
        raise RuntimeError("Missing platform-native Node runtime for Pi SDK")
    for path in (static, static / "assets"):
        if path.is_symlink():
            raise RuntimeError("Symlinked distribution asset is not accepted")


def _node_binary() -> str | None:
    """Frozen releases always use bundled Node, never an unverified system binary."""
    filename = "node.exe" if os.name == "nt" else "node"
    bundled = _bundle_root() / "runtime" / filename
    if bundled.is_file() and not bundled.is_symlink():
        return str(bundled)
    return None if getattr(sys, "frozen", False) else shutil.which("node")


def _start_pi(workspace: Path, token: str) -> subprocess.Popen:
    binary = _node_binary()
    if not binary:
        raise RuntimeError("Pi SDK Node executable missing")
    script = _bundle_root() / "runtimes" / "pi" / "server.mjs"
    # Local ephemeral port; server binds exclusively to 127.0.0.1.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "SOCRATOPIA_PI_PORT": str(port),
           "SOCRATOPIA_ROOT": str(workspace), "SOCRATOPIA_API_TOKEN": token}
    os.environ["SOCRATOPIA_PI_URL"] = f"http://127.0.0.1:{port}"
    child = subprocess.Popen(
        [binary, str(script)], cwd=script.parent, env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    request = Request(os.environ["SOCRATOPIA_PI_URL"] + "/internal/health",
                      headers={"Authorization": "Bearer " + token})
    try:
        for _ in range(60):
            if child.poll() is not None:
                raise RuntimeError("Pi gateway exited during startup")
            try:
                with urlopen(request, timeout=0.5) as response:
                    if response.status == 200:
                        return child
            except OSError:
                time.sleep(0.25)
        raise RuntimeError("Pi gateway did not pass its local health check")
    except Exception:
        child.terminate()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
        raise


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
    parser.add_argument("--no-pi", action="store_true", help=argparse.SUPPRESS)  # legacy no-op
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
        print("Model runtime: AgentScope course agents; Pi compatibility service bundled; supervisor: Python")
        print("Close this terminal / press Ctrl+C to stop.\n", flush=True)
        pi_child = _start_pi(root, token)
        try:
            if not args.no_browser:
                threading.Thread(target=_open_when_ready, args=(url,), daemon=True).start()
            uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
        finally:
            pi_child.terminate()
            try:
                pi_child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pi_child.kill()
                pi_child.wait()
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
