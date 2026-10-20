"""Structured PREP draft updates, independent of model runtimes.

All writes reuse the existing optimistic-locking atomic draft editor.
"""
from __future__ import annotations

import re
from pathlib import Path
from . import prep_editor

EDITABLE_SECTIONS = ("问题链", "预期证据", "教研会决议")
HEADING = re.compile(r"(?m)^## ([^\n]+)\n")


def sections(body: str) -> dict[str, str]:
    matches = list(HEADING.finditer(body))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        if name not in EDITABLE_SECTIONS:
            continue
        if name in result:
            raise prep_editor.DraftEditorError("重复的 PREP 标题")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        result[name] = body[match.end():end].strip("\n")
    return result


def save(root: Path, course: str, lesson_id: str,
         updates: dict[str, str], expected_sha256: str) -> dict:
    if not updates or set(updates) - set(EDITABLE_SECTIONS):
        raise prep_editor.DraftEditorError("只允许修改授权的 PREP 字段")
    for value in updates.values():
        if not isinstance(value, str) or "\x00" in value or len(value) > 65536:
            raise prep_editor.DraftEditorError("PREP 字段无效")
        if re.search(r"(?m)^##\s|^---\s*$", value):
            raise prep_editor.DraftEditorError("不得插入新的章节或 YAML 分隔符")
    document = prep_editor.get_document(root, course, lesson_id)
    if document["sha256"] != expected_sha256:
        raise prep_editor.DraftEditorError("PREP 已更新，请刷新后重试")
    body = document["body"]
    matches = list(HEADING.finditer(body))
    found: set[str] = set()
    for index in range(len(matches) - 1, -1, -1):
        match = matches[index]
        title = match.group(1).strip()
        if title not in updates:
            continue
        if title in found:
            raise prep_editor.DraftEditorError("重复的 PREP 标题")
        found.add(title)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        body = body[:match.end()] + updates[title].rstrip("\n") + "\n\n" + body[end:]
    if found != set(updates):
        raise prep_editor.DraftEditorError("PREP 缺少目标章节")
    return prep_editor.save_draft(root, course, lesson_id, body, expected_sha256)
