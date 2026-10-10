"""Reproducible release ZIP, built solely from the verified manifest allowlist.

Never bundle DATA/, TEXTBOOK/, .git/, .env, runtime records, or symlinks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
ZIP_TIME = (2020, 1, 1, 0, 0, 0)
EXTRAS = ("manifest.json", "release/VERSION", "release/NOTES.md")
DENY = {"DATA", "TEXTBOOK", ".git", "__pycache__"}


def _paths(root: Path) -> list[str]:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("manifest.json 没有有效文件清单")
    result = sorted(set(files) | set(EXTRAS))
    for label in result:
        pure = PurePosixPath(label)
        if (not isinstance(label, str) or pure.is_absolute()
                or len(pure.parts) == 0 or any(p in DENY or p in {".", ".."} for p in pure.parts)
                or any(part.startswith(".env") for part in pure.parts) or "\\" in label):
            raise ValueError(f"禁止打包的路径：{label}")
        src = root.joinpath(*pure.parts)
        if not src.is_file() or src.is_symlink():
            raise ValueError(f"文件缺失或为符号链接：{label}")
        node = src.parent
        while node != root:
            if node.is_symlink():
                raise ValueError(f"目录存在符号链接：{label}")
            node = node.parent
    return result


def _validated_cli(root: Path, platform: str | None, cli_binary: Path | None) -> tuple[Path, str] | None:
    """Only embed a freshly built local target/release binary, never arbitrary files."""
    if (platform is None) != (cli_binary is None):
        raise ValueError("--platform 与 --cli-binary 必须同时指定")
    if platform is None:
        return None  # Backward-compatible source-only packaging for developer tests.
    formats = {
        "linux-x86_64": ("socratopia", b"\x7fELF"),
        "windows-x86_64": ("socratopia.exe", b"MZ"),
        "macos-x86_64": ("socratopia", None),
    }
    if platform not in formats:
        raise ValueError(f"不支持的 CLI 目标平台：{platform}")
    expected, magic = formats[platform]
    candidate = cli_binary if cli_binary.is_absolute() else root / cli_binary
    candidate = candidate.absolute()
    if candidate.name != expected or candidate.is_symlink() or not candidate.is_file():
        raise ValueError("缺少该平台对应的已编译 CLI，或输入为符号链接")
    # No external binaries or symlinked directories are allowed in release archives.
    if not candidate.is_relative_to(root):
        raise ValueError("CLI 二进制必须位于当前仓库内")
    for parent in candidate.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError("CLI 二进制路径不得通过符号链接")
    if candidate.parent != root / "rust" / "target" / "release":
        raise ValueError("CLI 必须使用仓库 rust/target/release 的产物")
    if magic and candidate.open("rb").read(len(magic)) != magic:
        raise ValueError("CLI 文件头与目标平台不匹配")
    if platform == "macos-x86_64" and candidate.open("rb").read(4) not in (
            b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf",
            b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"):
        raise ValueError("目标 macOS CLI 不是 Mach-O 二进制")
    return candidate, expected


def make_zip(root: Path, output_dir: Path, version: str, *,
             platform: str | None = None, cli_binary: Path | None = None) -> dict[str, str | int]:
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError("版本号必须遵守 vMAJOR.MINOR.PATCH[-PRERELEASE]")
    root = root.resolve()
    files = _paths(root)
    cli = _validated_cli(root, platform, cli_binary)
    folder = f"Socratopia-PI-v4-{version}"
    suffix = f"-{platform}" if platform else ""
    archive = output_dir / f"{folder}{suffix}.zip"
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9, allowZip64=True) as stream:
        for label in files:
            entry = zipfile.ZipInfo(f"{folder}/{label}", ZIP_TIME)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o100644 << 16)
            stream.writestr(entry, (root / label).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        if cli:
            binary, filename = cli
            entry = zipfile.ZipInfo(f"{folder}/bin/{filename}", ZIP_TIME)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o100755 << 16)
            stream.writestr(entry, binary.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    with zipfile.ZipFile(archive) as stream:
        expected = sorted([f"{folder}/{p}" for p in files] +
                          ([f"{folder}/bin/{cli[1]}"] if cli else []))
        if sorted(stream.namelist()) != expected:
            raise ValueError("ZIP 内容与发布清单不一致")
        for name in stream.namelist():
            source = cli[0] if cli and name == f"{folder}/bin/{cli[1]}" else root / name.removeprefix(folder + "/")
            if stream.getinfo(name).file_size != source.stat().st_size:
                raise ValueError("ZIP 内容大小核验失败")
    return {"archive": str(archive), "checksum": str(checksum),
            "sha256": digest, "files": len(files) + int(cli is not None),
            "bytes": archive.stat().st_size}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按 manifest 构建可复现、无私人课程数据的 Release ZIP")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--version-file", type=Path, default=ROOT / "release/VERSION")
    parser.add_argument("--platform", choices=("linux-x86_64", "windows-x86_64", "macos-x86_64"),
                        help="平台标识，须与 --cli-binary 一起指定")
    parser.add_argument("--cli-binary", type=Path, help="本仓库 rust/target/release 的已编译文件")
    args = parser.parse_args(argv)
    version = args.version_file.read_text(encoding="utf-8").strip()
    print(json.dumps(make_zip(args.root, args.output_dir, version,
                              platform=args.platform, cli_binary=args.cli_binary),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
