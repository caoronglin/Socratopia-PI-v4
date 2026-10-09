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


def make_zip(root: Path, output_dir: Path, version: str) -> dict[str, str | int]:
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError("版本号必须遵守 vMAJOR.MINOR.PATCH[-PRERELEASE]")
    root = root.resolve()
    files = _paths(root)
    folder = f"Socratopia-PI-v4-{version}"
    archive = output_dir / f"{folder}.zip"
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9, allowZip64=True) as stream:
        for label in files:
            entry = zipfile.ZipInfo(f"{folder}/{label}", ZIP_TIME)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o100644 << 16)
            stream.writestr(entry, (root / label).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    with zipfile.ZipFile(archive) as stream:
        if sorted(stream.namelist()) != [f"{folder}/{p}" for p in files]:
            raise ValueError("ZIP 内容与发布清单不一致")
        for name in stream.namelist():
            if stream.getinfo(name).file_size != (root / name.removeprefix(folder + "/")).stat().st_size:
                raise ValueError("ZIP 内容大小核验失败")
    return {"archive": str(archive), "checksum": str(checksum),
            "sha256": digest, "files": len(files), "bytes": archive.stat().st_size}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按 manifest 构建可复现、无私人课程数据的 Release ZIP")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--version-file", type=Path, default=ROOT / "release/VERSION")
    args = parser.parse_args(argv)
    version = args.version_file.read_text(encoding="utf-8").strip()
    print(json.dumps(make_zip(args.root, args.output_dir, version), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
