"""Create explicit, platform-verified v5 Web runtime ZIP + SHA-256.

Bundles Pi, Python API and Web assets; excludes user data, secrets and workspace.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAMP = (2020, 1, 1, 0, 0, 0)
PLATFORMS = {"linux-x86_64", "windows-x86_64", "macos-x86_64", "macos-arm64"}
TEMPLATES = ("PROGRESS.md", "CONTEXT_INDEX.md", "handoff.json", "tasks.json")


def _readable(path: Path, base: Path) -> Path:
    candidate = path.absolute()
    if not candidate.is_file() or candidate.is_symlink() or not candidate.is_relative_to(base):
        raise ValueError(f"Required bundled file missing or unsafe: {candidate}")
    for node in candidate.parents:
        if node == base:
            break
        if node.is_symlink():
            raise ValueError(f"Symlink in bundled asset parent: {node}")
    return candidate


def _walk_files(base: Path) -> list[Path]:
    if not base.is_dir() or base.is_symlink():
        raise ValueError(f"Missing or unsafe asset directory: {base}")
    files: list[Path] = []
    for root, dirs, filenames in os.walk(base, followlinks=False):
        at = Path(root)
        dirs[:] = sorted(d for d in dirs if not (at / d).is_symlink() and d != ".bin")
        for name in sorted(filenames):
            candidate = at / name
            if candidate.is_symlink():
                # npm's .bin launch symlinks are not used at runtime; reject
                # all other links instead of including a dangerous ZIP entry.
                raise ValueError(f"Symlink in bundle: {candidate}")
            if candidate.is_file():
                files.append(candidate)
    return files


def _magic(path: Path, platform: str) -> None:
    magic = path.open("rb").read(4)
    valid = (magic.startswith(b"MZ") if platform.startswith("windows")
             else magic.startswith(b"\x7fELF") if platform.startswith("linux")
             else magic in (
                 b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf",
                 b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
             ))
    if not valid:
        raise ValueError(f"Native binary does not match {platform}: {path}")


def build(platform: str, output: Path) -> dict:
    if platform not in PLATFORMS:
        raise ValueError("Unsupported Web target")
    win = platform.startswith("windows")
    executable = _readable(
        ROOT / "build" / "standalone-v5" / ("Socratopia-Web.exe" if win else "Socratopia-Web"),
        ROOT,
    )
    _magic(executable, platform)
    web = ROOT / "web" / "dist"
    if not (web / "index.html").is_file() or not list((web / "assets").glob("*.js")):
        raise ValueError("Web UI has not been built")
    node = _readable(ROOT / "build" / "standalone-v5" /
                     ("node.exe" if win else "node"), ROOT)
    _magic(node, platform)
    pi_root = ROOT / "runtimes" / "pi"
    _readable(pi_root / "node_modules" / "@earendil-works" / "pi-coding-agent" / "package.json", ROOT)
    entries: dict[str, Path] = {executable.name: executable, "runtime/" + node.name: node}
    for name in TEMPLATES:
        entries["templates/" + name] = _readable(ROOT / "templates" / name, ROOT)
    for required in ("server.mjs", "package.json"):
        entries["runtimes/pi/" + required] = _readable(pi_root / required, ROOT)
    for candidate in _walk_files(pi_root / "node_modules"):
        entries["runtimes/pi/node_modules/" +
                candidate.relative_to(pi_root / "node_modules").as_posix()] = candidate
    for candidate in _walk_files(web):
        entries["web/dist/" + candidate.relative_to(web).as_posix()] = candidate
    output.mkdir(parents=True, exist_ok=True)
    filename = f"Socratopia-v5-Web-alpha-{platform}.zip"
    dest = output / filename
    with zipfile.ZipFile(dest, "w", allowZip64=True, compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6) as archive:
        for relative, path in sorted(entries.items()):
            info = zipfile.ZipInfo("Socratopia-Web/" + relative, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            is_native = relative == executable.name or relative == "runtime/" + node.name
            info.external_attr = ((0o100755 if is_native else 0o100644) << 16)
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    sha = hashlib.sha256(dest.read_bytes()).hexdigest()
    checksum = dest.with_suffix(".zip.sha256")
    checksum.write_text(f"{sha}  {dest.name}\n", encoding="utf-8")
    with zipfile.ZipFile(dest) as archive:
        expected = {"Socratopia-Web/" + name for name in entries}
        if set(archive.namelist()) != expected:
            raise ValueError("Incomplete archive contents")
        if any(name.startswith(("Socratopia-Web/DATA/", "Socratopia-Web/TEXTBOOK/"))
               or "/.env" in name for name in expected):
            raise ValueError("User data was accidentally packaged")
    result = {"archive": str(dest), "checksum": str(checksum),
              "sha256": sha, "files": len(entries), "bytes": dest.stat().st_size}
    print(json.dumps(result, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=sorted(PLATFORMS), required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    build(args.platform, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
