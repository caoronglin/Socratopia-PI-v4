"""Bounded, optimistic-locking draft PREP editor for the local Web workspace.

Only the Markdown BODY is editable. The original YAML front matter (course,
lesson, textbook hash, chapter anchors, sources and draft status) is immutable.
This module never grants readiness, lesson time, grades, or mastery.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
import tempfile
from pathlib import Path

from scripts.lib.prep import check_prep, parse_front_matter, prep_path, prep_status
from scripts.lib.repository import validate_course_name, validate_lesson_id

MAX_DRAFT_BYTES = 262_144
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class DraftEditorError(ValueError):
    """Invalid draft, conflicting revision or unsafe workspace file."""


def _path(root: Path, course: str, lesson_id: str) -> Path:
    validate_course_name(course)
    validate_lesson_id(lesson_id)
    path = prep_path(root, course, lesson_id)
    if path.parent.is_symlink() or path.is_symlink():
        raise DraftEditorError("PREP 文件或目录不可为符号链接")
    if not path.is_file():
        raise DraftEditorError("教案不存在，请先创建章节草稿")
    if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_nlink != 1:
        raise DraftEditorError("PREP 文件必须是独立普通文件")
    return path


def _read(root: Path, course: str, lesson_id: str) -> tuple[Path, bytes, str, dict, str, str]:
    path = _path(root, course, lesson_id)
    if path.stat().st_size > MAX_DRAFT_BYTES:
        raise DraftEditorError("教案超过编辑大小上限")
    data = path.read_bytes()
    if len(data) > MAX_DRAFT_BYTES:
        raise DraftEditorError("教案超过编辑大小上限")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DraftEditorError("教案必须是 UTF-8 文本") from exc
    if not text.startswith("---\n"):
        raise DraftEditorError("旧版自由格式 PREP 不支持网页编辑")
    end = text.find("\n---", 4)
    if end < 0:
        raise DraftEditorError("PREP YAML front matter 缺少结束标记")
    front, body = parse_front_matter(text)
    if front.get("schema") != "prep-1" or front.get("course") != course or front.get("lesson_id") != lesson_id:
        raise DraftEditorError("PREP 课程、课号或版本声明不一致，拒绝编辑")
    return path, data, text[: end + 4], front, body, hashlib.sha256(data).hexdigest()


def get_document(root: Path, course: str, lesson_id: str) -> dict:
    _, _, _, front, body, digest = _read(root, course, lesson_id)
    errors, warnings = check_prep(root, course, lesson_id)
    status = prep_status(root, course).get(lesson_id, "missing")
    return {
        "course": course, "lesson_id": lesson_id, "chapter": front.get("chapter", ""),
        "status": status, "editable": front.get("status") == "draft",
        "body": body, "sha256": digest,
        "errors": errors, "warnings": warnings,
        "ready_granted": False, "mastery_updated": False,
    }


def save_draft(root: Path, course: str, lesson_id: str, body: str, expected_sha256: str) -> dict:
    if not SHA256.fullmatch(expected_sha256):
        raise DraftEditorError("保存时必须提供有效的原始 SHA-256")
    if not isinstance(body, str) or not body.strip():
        raise DraftEditorError("草稿正文不能清空")
    if "\x00" in body:
        raise DraftEditorError("草稿不得包含 NUL 字符")

    # A filesystem lock coordinates all local API workers. A remaining lock is
    # treated as a conflict, never removed by an unrelated writer.
    path = _path(root, course, lesson_id)
    lock_path = path.with_name("." + path.name + ".lock")
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise DraftEditorError("其他窗口正在保存此教案，请稍后重试") from exc
    temp_path: Path | None = None
    try:
        os.close(lock_fd)
        path, original, header, front, _, current_sha = _read(root, course, lesson_id)
        if front.get("status") != "draft":
            raise DraftEditorError("只能编辑 draft 教案；ready/legacy 教案只读")
        if current_sha != expected_sha256:
            raise DraftEditorError("教案在其他窗口或本地文件中已更改，请先重新读取，未覆盖任何数据")
        new_text = header + "\n" + body.rstrip("\n") + "\n"
        encoded = new_text.encode("utf-8")
        if len(encoded) > MAX_DRAFT_BYTES:
            raise DraftEditorError("草稿超过 256 KiB 上限")
        # The front matter is re-used byte-for-byte from the server copy.
        # Do not write a caller-provided course, status, book hash or anchors.
        fd, temp_name = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=path.parent)
        temp_path = Path(temp_name)
        os.chmod(temp_name, stat.S_IMODE(path.stat().st_mode))
        with os.fdopen(fd, "wb") as file:
            file.write(encoded)
            file.flush()
            os.fsync(file.fileno())
        # Re-check the workspace before replacement; do not follow a swapped
        # symlink. Other Web writers are serialized by the lock file.
        if _path(root, course, lesson_id) != path:
            raise DraftEditorError("PREP 文件位置在保存期间发生变化")
        if hashlib.sha256(path.read_bytes()).hexdigest() != current_sha:
            raise DraftEditorError("PREP 文件在保存期间发生变化，未执行覆盖")
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        lock_path.unlink(missing_ok=True)
    return get_document(root, course, lesson_id)
