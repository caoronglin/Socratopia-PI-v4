#!/usr/bin/env python3
"""Smoke-test a published standalone ZIP on the *native* runner.

Checks content, checksum, native binaries and real subprocess behavior.
All subprocess capture uses UTF-8 on Windows (CP1252 is not reliable).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import zipfile

PLATFORMS = ("linux-x86_64", "windows-x86_64", "macos-x86_64", "macos-arm64")


def verify(archive: pathlib.Path, platform: str, version: str) -> None:
    if platform not in PLATFORMS or not archive.is_file():
        raise ValueError("目标平台或安装包无效")
    expected = archive.with_suffix(".zip.sha256").read_text(encoding="utf-8").split()[0]
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("ZIP SHA-256 校验失败")
    folder = f"Socratopia-PI-v4-{version}"
    exe = ".exe" if platform.startswith("windows") else ""
    cli_name = f"{folder}/bin/socratopia{exe}"
    backend_name = f"{folder}/bin/socratopia-backend{exe}"
    with tempfile.TemporaryDirectory(prefix="socratopia-smoke-") as tmp:
        base = pathlib.Path(tmp)
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            if len(names) != len(set(names)):
                raise ValueError("ZIP 重复路径")
            for name in names:
                path = pathlib.PurePosixPath(name)
                if (path.is_absolute() or ".." in path.parts or "\\" in name or
                        len(path.parts) < 2 or path.parts[0] != folder):
                    raise ValueError("ZIP 含路径越界项")
                if any(part in ("DATA", "TEXTBOOK") for part in path.parts):
                    raise ValueError("ZIP 不允许包含个人课程数据")
            for name in (cli_name, backend_name, f"{folder}/AGENTS.md",
                         f"{folder}/scripts/initialize.py"):
                if name not in names:
                    raise ValueError(f"安装包缺失必要文件: {name}")
            for name in (cli_name, backend_name):
                if not (bundle.getinfo(name).external_attr >> 16 & 0o111):
                    raise ValueError("安装包可执行权限缺失")
            bundle.extractall(base)
        cli = base / cli_name
        backend = base / backend_name
        if os.name != "nt":
            cli.chmod(cli.stat().st_mode | stat.S_IXUSR)
            backend.chmod(backend.stat().st_mode | stat.S_IXUSR)
        env = os.environ.copy()
        env["SOCRATOPIA_REQUIRE_BUNDLED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env.pop("SOCRATOPIA_PYTHON", None)
        for args in (
            ["--version"], ["status", "--course", "遗传学"],
            ["preflight"], ["init", "plan", "--course", "遗传学"],
            ["group", "status", "--course", "遗传学"],
            ["timer", "status", "--course", "遗传学"],
        ):
            completed = subprocess.run(
                [str(cli.resolve()), *args], cwd=cli.parent.parent, env=env,
                capture_output=True, encoding="utf-8", errors="replace", check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"命令 {args!r} 失败 ({completed.returncode})\n"
                    f"stdout: {completed.stdout[:1200]}\n"
                    f"stderr: {completed.stderr[:1200]}"
                )
            if args == ["--version"] and completed.stdout.strip() != (
                    f"socratopia {version.removeprefix('v')}"):
                raise ValueError("随包 Rust CLI 版本与标签不一致")
        # A ZIP-installed binary must work with a separate --root workspace,
        # using the sibling frozen backend rather than a local Python runtime.
        external = base / "alternate-workspace"
        external.mkdir()
        project = cli.parent.parent
        for label in ("AGENTS.md", "manifest.json"):
            shutil.copy2(project / label, external / label)
        shutil.copytree(project / "scripts", external / "scripts")
        alternate = subprocess.run(
            [str(cli.resolve()), "--root", str(external.resolve()),
             "init", "plan", "--course", "遗传学"],
            cwd=project, env=env, capture_output=True,
            encoding="utf-8", errors="replace", check=False,
        )
        if alternate.returncode != 0 or "遗传学" not in alternate.stdout:
            raise RuntimeError(
                f"冻结后端未正确绑定外部工作区: {alternate.returncode}\n"
                f"{alternate.stdout[:500]}\n{alternate.stderr[:500]}"
            )
        # Installed CLI must fail closed rather than silently find system Python
        # if the frozen runtime is absent. The recovery move is inside TempDir.
        hidden_backend = backend.with_name(backend.name + ".missing")
        backend.rename(hidden_backend)
        try:
            no_runtime = subprocess.run(
                [str(cli.resolve()), "init", "plan", "--course", "遗传学"],
                cwd=project, env={k: v for k, v in env.items()
                                  if k != "SOCRATOPIA_REQUIRE_BUNDLED"},
                capture_output=True, encoding="utf-8", errors="replace",
                check=False,
            )
            if no_runtime.returncode == 0 or "安装包不完整" not in no_runtime.stderr:
                raise RuntimeError("缺少冻结后端时没有拒绝系统 Python 回退")
        finally:
            hidden_backend.rename(backend)
    print(f"PASS standalone {platform}: {archive.name}, SHA-256 {actual}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=PLATFORMS, required=True)
    parser.add_argument("--version-file", type=pathlib.Path,
                        default=pathlib.Path("release/VERSION"))
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path("dist"))
    args = parser.parse_args()
    version = args.version_file.read_text(encoding="utf-8").strip()
    archive = args.output_dir / f"Socratopia-PI-v4-{version}-{args.platform}.zip"
    verify(archive, args.platform, version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
