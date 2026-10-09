"""Chapter-first PREP scaffolding: one logical lesson per textbook chapter.

Opt-in: preserves existing prep-1 files, runtime lesson IDs, and PROGRESS.
All supplemental materials must already exist within this course's SOURCES.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from scripts.lib.course_state import state_path
from scripts.lib.prep import book_hash, parse_front_matter, prep_path, scaffold_text
from scripts.lib.repository import (
    course_dir, read_json, safe_child_path, textbook_dir, validate_course_name,
)

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
LESSON = re.compile(r"lesson_(\d{3,})")
MAX_SECTIONS = 80
MAX_SOURCES = 16


def _headings(path: Path) -> list[tuple[int, str]]:
    if not path.is_file():
        return []
    return [(len(m.group(1)), m.group(2).strip()) for line in
            path.read_text(encoding="utf-8", errors="replace").splitlines()
            if (m := HEADING.match(line.strip()))]


def chapter_outline(root: Path, course: str, chapter: str) -> tuple[str, list[str]]:
    """Resolve a chapter heading and all contained subsection headings without guessing."""
    name = chapter.strip()
    if not name or len(name) > 160 or any(ch in name for ch in "\r\n|<>"):
        raise ValueError("章节名必须是单行、明确的教材章节标题（最多160字符）")
    base = textbook_dir(root, course)
    if not (base / "book.md").is_file():
        raise ValueError("缺少 active book.md，不允许生成虚构章节教案")
    headings = _headings(base / "_outline.md") or _headings(base / "book.md")
    exact = [i for i, (_, title) in enumerate(headings) if title == name]
    candidate = exact or [i for i, (_, title) in enumerate(headings) if title.startswith(name + " ")]
    if len(candidate) != 1:
        raise ValueError("教材中未找到唯一章节标题，请使用 _outline.md 的实际章节名称")
    i = candidate[0]
    level, title = headings[i]
    collected: list[str] = []
    for next_level, next_title in headings[i + 1:]:
        if next_level <= level:
            break
        collected.append(next_title)
    if len(collected) > MAX_SECTIONS:
        raise ValueError("章节超过80个小节，请先明确教材章节层级，避免默默截断")
    return title, collected or [title]


def _source_base(root: Path, course: str) -> Path:
    base = textbook_dir(root, course) / "SOURCES"
    if base.is_symlink():
        raise ValueError("SOURCES 不能是符号链接")
    return base


def _source_file(root: Path, course: str, label: str) -> Path:
    base = _source_base(root, course)
    if not label.startswith("SOURCES/"):
        raise ValueError("补充资料必须是 SOURCES/ 下的已登记相对路径")
    rel = label.removeprefix("SOURCES/")
    raw = base / rel
    # Check every original path component BEFORE resolving, including an alias
    # pointing to another file within SOURCES (or to a different course).
    probe = raw
    while probe != base and base in probe.parents:
        if probe.is_symlink():
            raise ValueError("拒绝读取符号链接补充资料")
        probe = probe.parent
    target = safe_child_path(base, rel)
    if not target.is_file():
        raise ValueError(f"补充资料尚未登记：{label}")
    if target.suffix.lower() not in {".md", ".txt", ".html", ".htm", ".pdf"}:
        raise ValueError("补充资料类型不支持；请先编目为文本或 PDF")
    return target


def source_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()[:12]


def resolve_sources(root: Path, course: str, sources: list[str]) -> list[dict[str, str]]:
    if len(sources) > MAX_SOURCES:
        raise ValueError("单章最多登记16份补充资料，避免无界加载")
    result = []
    for label in sources:
        if not isinstance(label, str) or any(c in label for c in "\r\n|<>\"\\") or len(label) > 240:
            raise ValueError("补充资料路径包含非法字符")
        path = _source_file(root, course, label)
        result.append({"path": label, "sha256": source_digest(path),
                       "type": path.suffix.lstrip(".").lower()})
    if len({x["path"] for x in result}) != len(result):
        raise ValueError("补充资料重复登记")
    return result


def _existing_chapter(root: Path, course: str, chapter: str) -> str | None:
    folder = textbook_dir(root, course) / "PREP"
    if not folder.is_dir():
        return None
    matches = []
    for file in sorted(folder.glob("lesson_*.md")):
        if not LESSON.fullmatch(file.stem):
            continue
        front, _ = parse_front_matter(file.read_text(encoding="utf-8", errors="replace"))
        if front.get("chapter") == chapter:
            matches.append(file.stem)
    if len(matches) > 1:
        raise ValueError(f"章节已映射到多个 PREP：{matches}，请先处理冲突")
    return matches[0] if matches else None


def _next_lesson(root: Path, course: str) -> str:
    used = set()
    folder = textbook_dir(root, course) / "PREP"
    for path in folder.glob("lesson_*.md") if folder.is_dir() else ():
        match = LESSON.fullmatch(path.stem)
        if match:
            used.add(int(match.group(1)))
    state = read_json(state_path(root, course))
    if state and isinstance(state.get("lesson_id"), str):
        match = LESSON.fullmatch(state["lesson_id"])
        if match:
            used.add(int(match.group(1)))
    progress = course_dir(root, course) / "PROGRESS.md"
    if progress.is_file():
        used.update(int(v) for v in LESSON.findall(progress.read_text(encoding="utf-8", errors="replace")))
    return f"lesson_{max(used, default=0) + 1:03d}"


def _cell(value: str) -> str:
    return re.sub(r"[\r\n|]+", " / ", value).strip()


def scaffold_chapter(root: Path, course: str, lesson_id: str, chapter: str,
                     sections: list[str], sources: list[dict[str, str]]) -> str:
    draft = scaffold_text(root, course, lesson_id, chapter)
    draft = draft.replace("schema: prep-1\n", "schema: prep-1\nplan_mode: chapter\n", 1)
    # Use actual outline anchors for ALL subsections; do not truncate to the first six.
    first = draft.index("anchors:\n")
    last = draft.index("sources:", first)
    anchors = "\n".join("  - " + '"' + a.replace('"', "'") + '"' for a in [chapter, *sections])
    draft = draft[:first] + "anchors:\n" + anchors + "\n" + draft[last:]
    if sources:
        refs = "\n".join('  - "' + s["path"] + '"' for s in sources)
        draft = draft.replace("sources: []", "sources:\n" + refs, 1)

    section_lines = "\n".join(
        f"| {_cell(s)} | {_cell(s)} | TODO | TODO | 待教 |" for s in sections)
    material_lines = "\n".join(
        f"| {_cell(s['path'])} | {s['sha256']} | TODO | TODO | 待核实 |" for s in sources)
    block = (
        "## 章节小节与教学单元\n\n"
        "按本章实际小节逐项设计。一次教学单元通常1–3个核心点，可跨会话延续，**不得省略整章范围**。\n\n"
        "| 小节 | 教材锚点 | 核心知识/活动 | 可观察证据 | 计划状态 |\n"
        "|---|---|---|---|---|\n" + section_lines + "\n\n"
        "## 补充资料\n\n"
        "仅使用本课已登记的 SOURCES。资料用于补充/反例/纠偏/拓展，不能覆盖主教材。"
        "外部资料标记待核实，核对作者和证据后再引用。\n\n"
        "| 来源 | SHA256 | 使用目的 | 关联教材锚点 | 可靠性 |\n"
        "|---|---|---|---|---|\n" + material_lines + "\n\n"
        "## 章末收束\n\n"
        "- 主线复述及至少两条概念关系：TODO\n"
        "- 综合题与评分依据：TODO\n"
        "- 迁移题与边界条件：TODO\n"
        "- 图表/例题/习题和未覆盖项处理：TODO\n\n"
    )
    marker = "## Coverage 种子\n"
    if marker not in draft:
        raise ValueError("PREP 模板缺失 Coverage 种子插入点")
    return draft.replace(marker, block + marker, 1)


def plan_chapter(root: Path, course: str, chapter: str, *,
                 sources: list[str] | None = None, apply: bool = False) -> dict[str, Any]:
    validate_course_name(course)
    title, sections = chapter_outline(root, course, chapter)
    existing = _existing_chapter(root, course, title)
    if existing:
        if sources:
            raise ValueError("章节 PREP 已存在：补充资料请先人工对照已有教案，拒绝覆盖")
        return {"course": course, "chapter": title, "lesson_id": existing,
                "exists": True, "path": str(prep_path(root, course, existing)),
                "message": "复用本章教案，不创建新课号；先检查当前 PREP 与运行断点"}
    refs = resolve_sources(root, course, sources or [])
    lesson_id = _next_lesson(root, course)
    text = scaffold_chapter(root, course, lesson_id, title, sections, refs)
    path = prep_path(root, course, lesson_id)
    result: dict[str, Any] = {
        "course": course, "chapter": title, "lesson_id": lesson_id,
        "path": str(path), "exists": False, "draft": True,
        "section_count": len(sections), "source_count": len(refs),
        "dry_run": not apply, "mastery_changed": False,
    }
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8") as fh:
                fh.write(text)
        except FileExistsError:
            raise ValueError("并发创建冲突：PREP 已存在，未覆盖") from None
    else:
        result["preview"] = text
    return result
