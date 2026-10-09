"""Hot / warm memory maintenance (SYSTEM/SPEC/MEMORY_CONTRACT.md), deterministic and read-only on facts.

Everything generated here is a *projection* of `PROGRESS.md` + runtime state; it
never records mastery and never edits `PROGRESS.md`. Generated text lives between
markers so hand-written notes outside the markers survive a rebuild. There are no
timestamps inside generated blocks, so rebuilding unchanged facts is a no-op.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.export_stellar import parse_checkpoint, parse_coverage, parse_lessons
from scripts.lib.budget import estimate_tokens
from scripts.lib.prep import parse_front_matter
from scripts.lib.repository import course_dir, iter_course_paths, read_json, textbook_dir, validate_course_name

HOT_BEGIN = "<!-- socratopia:hot:begin -->"
HOT_END = "<!-- socratopia:hot:end -->"
HOT_MAX_CHARS = 1600          # MEMORY_CONTRACT: hot layer ≈ 800–1600 中文字
EVIDENCE_CLIP = 120           # evidence is shortened, never dropped
SUMMARY_CLIP = 280
OPEN_RETEACH = {"pending", "needs_review", "needs_reteach"}
LESSON_ID = re.compile(r"^lesson_\d{3,}$")


def _clip(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def open_reteach(text: str) -> list[dict[str, str]]:
    """Open items from the reteach table (id, chapter, type, status, evidence)."""
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) >= 6 and cells[4] in OPEN_RETEACH:
            rows.append({"id": cells[0], "chapter": cells[1], "type": cells[2],
                         "status": cells[4], "evidence": cells[5]})
    return rows


def collect(root: Path, course: str) -> dict[str, Any]:
    """Gather the real facts the hot layer may state. Nothing is inferred."""
    validate_course_name(course)
    data = course_dir(root, course)
    progress = _read(data / "PROGRESS.md")
    state = read_json(data / "runtime" / "course_state.json") or {}
    checkpoint = parse_checkpoint(progress)
    coverage = parse_coverage(progress)
    lesson_id = checkpoint.get("lesson_id") or state.get("lesson_id") or ""
    anchors: list[str] = []
    prep = textbook_dir(root, course) / "PREP" / f"{lesson_id}.md"
    if LESSON_ID.match(lesson_id) and prep.is_file():
        front, _ = parse_front_matter(_read(prep))
        value = front.get("anchors")
        anchors = list(value) if isinstance(value, list) else []
    return {
        "course": course,
        "lesson_id": lesson_id,
        "chapter": checkpoint.get("chapter") or state.get("current_chapter") or "",
        "tutor": checkpoint.get("tutor") or state.get("active_tutor") or "",
        "next_entry": checkpoint.get("next_entry") or "",
        "phase": state.get("phase") or "",
        "blockers": list(state.get("blockers") or []),
        "coverage": coverage,
        "reteach": open_reteach(_read(data / "CONTEXT" / "RETEACH_QUEUE.md")),
        "anchors": anchors,
        "lessons": parse_lessons(progress),
    }


def render_hot(facts: dict[str, Any]) -> str:
    """The hot block. Only real facts; every needs_review item is kept by name."""
    coverage = facts["coverage"]
    counts: dict[str, int] = {}
    for row in coverage:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    review = [r for r in coverage if r["status"] == "needs_review"]
    open_rows = [r for r in coverage if r["status"] in {"unseen", "introduced"}]

    where = " · ".join(x for x in (facts["lesson_id"], facts["chapter"],
                                   f"导师 {facts['tutor']}" if facts["tutor"] else "",
                                   f"phase {facts['phase']}" if facts["phase"] else "") if x)
    lines = [HOT_BEGIN,
             "> 只读投影，生成自 `PROGRESS.md` 与 runtime；掌握事实以 `PROGRESS.md` 为准。",
             "",
             f"- **当前**：{where or '未定位'}"]
    if facts["blockers"]:
        lines.append(f"- **阻塞**：{', '.join(facts['blockers'])}")
    lines.append("- **覆盖**：" + (" · ".join(f"{s} {n}" for s, n in sorted(counts.items())) or "无账本记录"))
    if review:
        lines.append("- **needs_review**（压缩时不得丢弃）：")
        lines += [f"  - {r['item']} — {_clip(r['evidence'] or '无证据文字', EVIDENCE_CLIP)}" for r in review]
    if open_rows:
        names = "、".join(r["item"] for r in open_rows[:8])
        more = f" 等 {len(open_rows)} 项" if len(open_rows) > 8 else ""
        lines.append(f"- **未完成**：{names}{more}")
    if facts["reteach"]:
        lines.append("- **待补讲**：")
        lines += [f"  - {r['id']} [{r['status']}] {r['chapter']} · {r['type']} — {_clip(r['evidence'], 60)}"
                  for r in facts["reteach"]]
    if facts["next_entry"]:
        lines.append(f"- **下节入口**：{_clip(facts['next_entry'], 160)}")
    if facts["anchors"]:
        lines.append("- **教材锚点**：" + "；".join(_clip(a, 60) for a in facts["anchors"][:4]))
    lines.append(HOT_END)
    return "\n".join(lines)


def _splice(existing: str, block: str, begin: str, end: str, header: str) -> str:
    """Replace the marked block, or append it; text outside the markers is preserved."""
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    if pattern.search(existing):
        return pattern.sub(lambda _m: block, existing, count=1)
    base = existing.rstrip("\n") if existing.strip() else header
    return base + "\n\n" + block + "\n"


def _write_if_changed(path: Path, text: str, apply: bool) -> str:
    old = path.read_text(encoding="utf-8") if path.is_file() else None
    if old == text:
        return "unchanged"
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return "written"
    return "would_write"


def index_path(root: Path, course: str) -> Path:
    return course_dir(root, course) / "CONTEXT" / "CONTEXT_INDEX.md"


def summaries_path(root: Path, course: str) -> Path:
    return course_dir(root, course) / "CONTEXT" / "LESSON_SUMMARIES.md"


def build_hot(root: Path, course: str, apply: bool = False) -> dict[str, Any]:
    facts = collect(root, course)
    block = render_hot(facts)
    path = index_path(root, course)
    text = _splice(_read(path), block, HOT_BEGIN, HOT_END, "# Hot Context\n")
    outcome = _write_if_changed(path, text, apply)
    return {"course": course, "path": str(path), "outcome": outcome,
            "chars": len(block), "tokens": estimate_tokens(block),
            "over_budget": len(block) > HOT_MAX_CHARS}


def _lesson_block(lesson: dict[str, str], coverage: list[dict[str, str]]) -> str:
    lid = lesson["lesson_id"]
    pattern = re.compile(re.escape(lid).replace("_", "[_\\-]"), re.I)
    cited = [r for r in coverage if pattern.search(r["evidence"] or "")]
    record = _clip(lesson.get("body") or "", SUMMARY_CLIP) or "（PROGRESS.md 未记录本课正文）"
    title = f" · {lesson['title']}" if lesson.get("title") else ""
    lines = [f"<!-- lesson:{lid}:begin -->", f"## {lid}{title}", f"- 记录：{record}"]
    for row in cited:
        lines.append(f"- 证据：{row['item']} [{row['status']}] {_clip(row['evidence'], EVIDENCE_CLIP)}")
    if not cited:
        lines.append("- 证据：账本中没有引用本课的行（不猜测）")
    unresolved = [r["item"] for r in cited if r["status"] == "needs_review"]
    if unresolved:
        lines.append("- 未解决：" + "、".join(unresolved))
    lines.append(f"<!-- lesson:{lid}:end -->")
    return "\n".join(lines)


def build_summaries(root: Path, course: str, lesson_id: str | None = None, apply: bool = False) -> dict[str, Any]:
    """Create/refresh warm-layer entries from real lesson records (one marked block per lesson)."""
    facts = collect(root, course)
    lessons = facts["lessons"]
    if lesson_id:
        if not LESSON_ID.match(lesson_id):
            raise ValueError(f"非法 lesson_id：{lesson_id!r}")
        lessons = [lesson for lesson in lessons if lesson["lesson_id"] == lesson_id]
        if not lessons:
            raise ValueError(f"PROGRESS.md 中没有 {lesson_id} 的记录；不会凭空生成摘要")
    path = summaries_path(root, course)
    text = _read(path) or "# Lesson Summaries\n"
    for lesson in lessons:
        lid = lesson["lesson_id"]
        block = _lesson_block(lesson, facts["coverage"])
        begin, end = f"<!-- lesson:{lid}:begin -->", f"<!-- lesson:{lid}:end -->"
        text = _splice(text, block, begin, end, "# Lesson Summaries\n")
    outcome = _write_if_changed(path, text, apply)
    return {"course": course, "path": str(path), "outcome": outcome, "lessons": [x["lesson_id"] for x in lessons]}


def doctor_findings(root: Path, course: str | None = None) -> tuple[list[str], list[str]]:
    """Per-course hot-layer findings for pi_arch_doctor. Opt-in: only courses whose index has our marker."""
    errors: list[str] = []
    warnings: list[str] = []
    data_root = root / "DATA"
    if not data_root.is_dir():
        return errors, warnings
    for course_path in iter_course_paths(root, course=course):
        if course_path.is_symlink() or not course_path.is_dir():
            continue
        index = course_path / "CONTEXT" / "CONTEXT_INDEX.md"
        if not index.is_file() or HOT_BEGIN not in index.read_text(encoding="utf-8", errors="replace"):
            continue
        try:
            found_errors, found_warnings = check(root, course_path.name)
        except ValueError:
            continue
        errors += [f"memory[{course_path.name}]: {m}" for m in found_errors]
        warnings += [f"memory[{course_path.name}]: {m}" for m in found_warnings]
    return errors, warnings


def check(root: Path, course: str) -> tuple[list[str], list[str]]:
    """Compression invariants. Returns (errors, warnings); read-only."""
    facts = collect(root, course)
    errors: list[str] = []
    warnings: list[str] = []
    path = index_path(root, course)
    if not path.is_file():
        return [], ["热层 CONTEXT_INDEX.md 不存在（运行 scripts/memory.py build）"]
    text = path.read_text(encoding="utf-8", errors="replace")

    for row in facts["coverage"]:
        if row["status"] == "needs_review" and row["item"] not in text:
            errors.append(f"压缩不变量：needs_review「{row['item']}」不在热层")
    for item in facts["reteach"]:
        if item["id"] not in text:
            errors.append(f"压缩不变量：待补讲 {item['id']} 不在热层")
    if facts["next_entry"] and _clip(facts["next_entry"], 24)[:20] not in text:
        errors.append("压缩不变量：PROGRESS 的 next_entry 不在热层（下节入口丢失）")

    block = re.search(re.escape(HOT_BEGIN) + r".*?" + re.escape(HOT_END), text, re.S)
    size = len(block.group(0)) if block else len(text)
    if size > HOT_MAX_CHARS:
        warnings.append(f"热层 {size} 字超过约定上限 {HOT_MAX_CHARS}（MEMORY_CONTRACT）")
    progress = course_dir(root, course) / "PROGRESS.md"
    if progress.is_file() and progress.stat().st_mtime - path.stat().st_mtime > 2:
        warnings.append("热层早于 PROGRESS.md（stale）：运行 scripts/memory.py build --apply")

    summaries = _read(summaries_path(root, course))
    for lesson in facts["lessons"]:
        if f"<!-- lesson:{lesson['lesson_id']}:begin -->" not in summaries and lesson.get("body"):
            warnings.append(f"{lesson['lesson_id']} 尚无温层摘要（scripts/memory.py summarize）")
    return errors, warnings

