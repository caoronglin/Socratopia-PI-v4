"""Extract v5 release ZIP and run its real frozen Web API, not system Python."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


def fetch(url: str, *, token: str | None = None) -> tuple[int, str]:
    request = urllib.request.Request(url, headers=({"Authorization": "Bearer " + token} if token else {}))
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, response.read(15000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(1000).decode("utf-8", errors="replace")


def smoke(archive: Path, platform: str) -> None:
    with tempfile.TemporaryDirectory(prefix="socratopia-v5-web-") as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(archive) as zip_file:
            for entry in zip_file.infolist():
                path = Path(entry.filename)
                if path.is_absolute() or ".." in path.parts or not entry.filename.startswith("Socratopia-Web/"):
                    raise RuntimeError(f"Unsafe ZIP entry: {entry.filename}")
            zip_file.extractall(root)
        folder = root / "Socratopia-Web"
        binary = folder / ("Socratopia-Web.exe" if platform.startswith("windows") else "Socratopia-Web")
        node = folder / "runtime" / "node" / ("node.exe" if platform.startswith("windows") else "node")
        if os.name != "nt":
            binary.chmod(0o755)
            node.chmod(0o755)
        completed = subprocess.run([str(binary), "--check"], capture_output=True, text=True, timeout=100)
        if completed.returncode != 0 or "bundle: complete" not in completed.stdout:
            raise RuntimeError("Bundle self-check failed: " + completed.stderr)
        course_root = root / "private-course-data"
        env = {**os.environ, "SOCRATOPIA_ROOT": str(course_root),
               "SOCRATOPIA_API_TOKEN": "e2e-package-token-0123456789"}
        port = 18765
        process = subprocess.Popen(
            [str(binary), "--no-browser", "--port", str(port)],
            cwd=folder, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        try:
            for _ in range(90):
                if process.poll() is not None:
                    raise RuntimeError("Frozen Web app exited early")
                try:
                    status, text = fetch(f"http://127.0.0.1:{port}/api/health")
                    if status == 200 and '"socratopia"' in text:
                        break
                except (OSError, urllib.error.URLError):
                    time.sleep(1)
            else:
                raise RuntimeError("Bundled Web API did not start")
            code, html = fetch(f"http://127.0.0.1:{port}/")
            if code != 200 or "<div id=\"root\">" not in html:
                raise RuntimeError("React HTML is missing from packaged Web")
            unauthorized, _ = fetch(f"http://127.0.0.1:{port}/api/courses")
            authorized, _ = fetch(f"http://127.0.0.1:{port}/api/courses", token=env["SOCRATOPIA_API_TOKEN"])
            if unauthorized != 401 or authorized != 200:
                raise RuntimeError(f"Packaged API authentication failed: {unauthorized}/{authorized}")
            if not all((course_root / "templates" / name).is_file()
                       for name in ("PROGRESS.md", "CONTEXT_INDEX.md", "handoff.json", "tasks.json")):
                raise RuntimeError("User workspace templates were not initialized")
            if any((folder / name).exists() for name in ("DATA", "TEXTBOOK")):
                raise RuntimeError("Bundled package contains unexpected user data")
            print(f"PASS: frozen Web + bundled Pi process + UI + API auth on {platform}", flush=True)
        finally:
            process.terminate()
            try:
                process.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--platform", required=True)
    args = parser.parse_args()
    smoke(args.archive, args.platform)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
