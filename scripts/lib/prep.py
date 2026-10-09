"""PREP (lesson preparation) scaffolding and teaching-assessment-alignment checks.

PREP is a *plan*: it never claims mastery (`PROGRESS.md` owns that) and never
rewrites `book.md`. Files opt in to validation with `schema: prep-1` in the front
matter, so legacy free-form PREP files are left alone.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from scripts.export_stellar import parse_coverage
from scripts.lib.context_pack import _reteach_body
from scripts.lib.repository import course_dir, iter_course_paths, redact, textbook_dir, validate_course_name

SCHEMA = "prep-1"
LESSON_ID = re.compile(r"^lesson_\d{3,}$")
STATUSES = {"draft", "ready"}
SEED_STATES = {"unseen", "introduced"}
SCAFFOLDS = ("A", "B", "C")
REQUIRED_KEYS = ("course", "lesson_id", "chapter", "status", "book_hash")
MASTERY_CLAIMS = ("已掌握", "已学会", "掌握度为", "宣布掌握")
OBJECTIVE_HEADERS = ["id", "学习目标", "问题/活动", "可观察证据", "支架"]
SECTION_OBJECTIVES = "教学评一致性"
SECTION_SEEDS = "Coverage 种子"
SECTION_CHAPTER = "章节小节与教学单元"
SECTION_SUPPLEMENTS = "补充资料"
SECTION_CLOSURE = "章末收束"
CHAPTER_HEADERS = ["小节", "教材锚点", "核心知识/活动", "可观察证据", "计划状态"]
SUPPLEMENT_HEADERS = ["来源", "SHA256", "使用目的", "关联教材锚点", "可靠性"]
CLOSURE_FIELDS = ("主线复述", "综合题", "迁移题", "图表/例题/习题")
SECTION_MISCONCEPTIONS = "预期误概念"
SECTION_MOE = "教研会决议"
MC_HEADERS = ["误概念", "触发条件", "纠偏问法"]
SEED_HEADERS = ["item", "计划状态", "期望元素"]
MOE_LENSES = ("A", "B", "C")
# 教研会必须逐条交代的字段：缺一项等于没开会，不允许 ready。
MOE_FIELDS = ("目标粒度", "期望元素与误概念", "表征与迁移路径", "最可能卡点与预案")
# Only the scaffold's own tokens count as unfilled; free text like `List<int>` must not.
PLACEHOLDER = re.compile(r"\bTODO\b|<(?:course|lesson_id|chapter|book_hash|carry|seeds)>")


def prep_path(root: Path, course: str, lesson_id: str) -> Path:
    if not LESSON_ID.match(lesson_id):
        raise ValueError(f"非法 lesson_id：{lesson_id!r}（应为 lesson_001 形式）")
    return textbook_dir(root, course) / "PREP" / f"{lesson_id}.md"


def book_hash(root: Path, course: str) -> str | None:
    book = textbook_dir(root, course) / "book.md"
    if not book.is_file():
        return None
    return hashlib.sha256(book.read_bytes()).hexdigest()[:12]


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Tiny front-matter reader: `key: scalar`, `key: []`, and `key:` + `- item` lists."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    data: dict[str, Any] = {}
    key: str | None = None
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        match = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if match and not line.startswith((" ", "\t")):
            key, value = match.group(1), match.group(2).strip()
            data[key] = [] if value in ("", "[]") else _unquote(value)
        elif line.lstrip().startswith("- ") and key and isinstance(data.get(key), list):
            data[key].append(_unquote(line.lstrip()[2:]))
    return data, text[end + 4:].lstrip("\n")


def _sections(body: str) -> dict[str, str]:
    parts: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            parts[current] = []
        elif current is not None:
            parts[current].append(line)
    return {name: "\n".join(lines) for name, lines in parts.items()}


def _table(section: str) -> tuple[list[str], list[list[str]]]:
    header: list[str] = []
    rows: list[list[str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", stripped.strip("|"))]
        if set("".join(cells)) <= set("-: "):
            continue
        if not header:
            header = cells
        else:
            rows.append(cells)
    return header, rows


def parse_prep(text: str) -> dict[str, Any]:
    front, body = parse_front_matter(text)
    sections = _sections(body)
    header, rows = _table(sections.get(SECTION_OBJECTIVES, ""))
    seed_header, seed_rows = _table(sections.get(SECTION_SEEDS, ""))
    mc_header, mc_rows = _table(sections.get(SECTION_MISCONCEPTIONS, ""))
    chapter_header, chapter_rows = _table(sections.get(SECTION_CHAPTER, ""))
    source_header, source_rows = _table(sections.get(SECTION_SUPPLEMENTS, ""))
    return {
        "front": front, "body": body, "sections": sections,
        "objective_header": header, "objectives": rows,
        "seed_header": seed_header, "seeds": seed_rows,
        "misconception_header": mc_header, "misconceptions": mc_rows,
        "chapter_header": chapter_header, "chapter_rows": chapter_rows,
        "source_header": source_header, "source_rows": source_rows,
    }


def check_prep_text(text: str, *, course: str, lesson_id: str, current_hash: str | None) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors block `ready`; warnings are advisory."""
    errors: list[str] = []
    warnings: list[str] = []
    parsed = parse_prep(text)
    front = parsed["front"]

    for key in REQUIRED_KEYS:
        if not front.get(key):
            errors.append(f"front matter 缺少 {key}")
    if front.get("course") and front["course"] != course:
        errors.append(f"course={front['course']!r} 与所在课程 {course!r} 不一致（课程隔离）")
    if front.get("lesson_id") and front["lesson_id"] != lesson_id:
        errors.append(f"lesson_id={front['lesson_id']!r} 与文件名 {lesson_id!r} 不一致")
    status = front.get("status")
    if status and status not in STATUSES:
        errors.append(f"status={status!r} 必须是 {sorted(STATUSES)}")
    ready = status == "ready"

    # Chapter-mode is opt-in; all legacy prep-1 plans keep their existing gates.
    if front.get("plan_mode") == "chapter":
        chapter_head, chapter_rows = parsed["chapter_header"], parsed["chapter_rows"]
        if chapter_head != CHAPTER_HEADERS:
            errors.append("章节小节表头缺失或不匹配")
        elif not chapter_rows:
            errors.append("章节小节必须逐项编排，不得把整章缩成一个空目标")
        seen_anchors: set[str] = set()
        for row in chapter_rows if chapter_head == CHAPTER_HEADERS else []:
            cells = (row + [""] * 5)[:5]
            heading, anchor, activity, evidence, state = cells
            if not heading or not anchor or anchor in seen_anchors:
                errors.append(f"章节小节锚点缺失或重复：{anchor!r}")
            seen_anchors.add(anchor)
            if ready and (not activity or not evidence or not state or
                          any("TODO" in field for field in cells)):
                errors.append(f"章节小节「{heading}」未完成教学活动/可观察证据/计划状态")
        material_head, material_rows = parsed["source_header"], parsed["source_rows"]
        if material_head != SUPPLEMENT_HEADERS:
            errors.append("补充资料表头缺失或不匹配")
        declared_sources = front.get("sources", [])
        if not isinstance(declared_sources, list):
            errors.append("章节计划的 sources 必须是来源列表")
            declared_sources = []
        listed = [row[0] for row in material_rows if row]
        if sorted(listed) != sorted(declared_sources):
            errors.append("补充资料表与 front matter sources 不一致")
        for row in material_rows:
            cells = (row + [""] * 5)[:5]
            if len(row) != 5 or not re.fullmatch(r"[a-f0-9]{12}", cells[1]):
                errors.append("补充资料 SHA256/表格格式无效")
            if ready and (any(not value or "TODO" in value for value in cells) or
                          cells[4] not in {"待核实", "已核实", "存在冲突"}):
                errors.append(f"补充资料 {cells[0]!r} 需填写用途、关联锚点和可靠性")
        if ready:
            closure = parsed["sections"].get(SECTION_CLOSURE, "")
            for item in CLOSURE_FIELDS:
                lines = [line for line in closure.splitlines() if line.lstrip().startswith("- ") and item in line]
                if not lines or any("TODO" in line or not line.split("：", 1)[-1].strip() for line in lines):
                    errors.append(f"章末收束缺少可执行项：{item}")
    # --- teaching-assessment alignment ---------------------------------------------------
    header, rows = parsed["objective_header"], parsed["objectives"]
    if header != OBJECTIVE_HEADERS:
        errors.append(f"「{SECTION_OBJECTIVES}」表头必须是 {' | '.join(OBJECTIVE_HEADERS)}")
    elif not rows:
        errors.append(f"「{SECTION_OBJECTIVES}」至少要有一个学习目标")
    seen_ids: set[str] = set()
    for row in rows if header == OBJECTIVE_HEADERS else []:
        row = (row + [""] * 5)[:5]
        oid, goal, activity, evidence, scaffold = row
        if oid in seen_ids:
            warnings.append(f"目标 id 重复：{oid}")
        seen_ids.add(oid)
        for label, value in (("学习目标", goal), ("问题/活动", activity), ("可观察证据", evidence)):
            if not value.strip():
                errors.append(f"{oid or '?'} 缺少{label}：目标、活动、证据必须一一对应（教学评一致性）")
        levels = [p.strip() for p in re.split(r"[→,/、\s]+", scaffold) if p.strip()]
        bad = [lv for lv in levels if lv not in SCAFFOLDS]
        if not levels or bad:
            errors.append(f"{oid or '?'} 支架必须是 A/B/C（收到 {scaffold!r}）")
        elif len(set(levels)) > 2:
            errors.append(f"{oid or '?'} 支架跨 {len(set(levels))} 级：目标切得太粗，应先拆目标")
        if goal.strip() and activity.strip() and goal.strip() == activity.strip():
            warnings.append(f"{oid} 的活动与目标文字相同：活动应是引出证据的动作，不是目标的复述")

    # --- anticipated misconceptions: correction is designed, not improvised ---------------
    mc_header, mc_rows = parsed["misconception_header"], parsed["misconceptions"]
    if mc_header and mc_header != MC_HEADERS:
        errors.append(f"「{SECTION_MISCONCEPTIONS}」表头必须是 {' | '.join(MC_HEADERS)}")
    for row in mc_rows if mc_header == MC_HEADERS else []:
        cells = (row + [""] * 3)[:3]
        if any(not c.strip() for c in cells):
            errors.append(
                "误概念行不完整（误概念/触发条件/纠偏问法都要写）：" + " | ".join(c or "空" for c in cells)
            )

    # --- coverage seed must not promote; each seed must carry its expectation elements -----
    seed_header = parsed["seed_header"]
    if seed_header and seed_header != SEED_HEADERS:
        errors.append(f"「{SECTION_SEEDS}」表头必须是 {' | '.join(SEED_HEADERS)}")
    for row in parsed["seeds"]:
        item, state, elements = (row + ["", "", ""])[:3]
        if state and state not in SEED_STATES and not PLACEHOLDER.search(state):
            errors.append(f"Coverage 种子「{item}」计划状态 {state!r} 非法：PREP 只能写 unseen/introduced")
        if ready and item and not elements.strip():
            errors.append(
                f"Coverage 种子「{item}」缺期望元素：写清该条目说对才算懂的独立子元素，否则一段流畅叙述就会冒充覆盖"
            )

    for claim in MASTERY_CLAIMS:
        if claim in text:
            errors.append(f"PREP 出现掌握声明 {claim!r}：掌握只来自 PROGRESS.md 的理解证据")

    # --- readiness gate -----------------------------------------------------------------------
    if ready:
        if PLACEHOLDER.search(text):
            errors.append("status: ready 但仍有 TODO/未填占位")
        if not front.get("anchors"):
            errors.append("status: ready 必须有教材锚点 anchors")
        if front.get("book_hash") in (None, "", "none"):
            errors.append("status: ready 必须记录 book_hash（对应的教材版本）")
        # 教研组必须真的开过会：仅留标题、或只写镜头标记，都不算决议。
        for name in (SECTION_MISCONCEPTIONS, SECTION_MOE):
            if not parsed["sections"].get(name, "").strip():
                errors.append(f"status: ready 却缺「{name}」段：教研组须在 ready 前召开（references/moe.md）")
        moe_body = parsed["sections"].get(SECTION_MOE, "")
        for field in MOE_FIELDS:
            if field not in moe_body:
                errors.append(f"「{SECTION_MOE}」缺交代项：{field}")

    # --- staleness ----------------------------------------------------------------------------
    recorded = front.get("book_hash")
    if current_hash and recorded and recorded != "none" and recorded != current_hash:
        warnings.append(f"stale：PREP 基于教材 {recorded}，当前 book.md 为 {current_hash}，需重建/复核")
    if current_hash is None and recorded not in (None, "", "none"):
        warnings.append("book.md 不存在，无法核对教材版本")
    return errors, warnings


def check_prep(root: Path, course: str, lesson_id: str) -> tuple[list[str], list[str]]:
    validate_course_name(course)
    path = prep_path(root, course, lesson_id)
    if not path.is_file():
        return [f"PREP 不存在：{path.name}"], []
    text = path.read_text(encoding="utf-8", errors="replace")
    errors, warnings = check_prep_text(text, course=course, lesson_id=lesson_id,
                                       current_hash=book_hash(root, course))
    front, _ = parse_front_matter(text)
    if front.get("plan_mode") == "chapter":
        from scripts.lib.chapter_prep import chapter_outline, resolve_sources
        try:
            canonical, sections = chapter_outline(root, course, str(front.get("chapter", "")))
            parsed = parse_prep(text)
            planned = [row[1] for row in parsed["chapter_rows"] if len(row) > 1]
            if canonical != front.get("chapter") or sorted(planned) != sorted(sections):
                errors.append("教材章节小节与本教案不一致：必须逐项检查章节范围")
            entries = parsed["source_rows"]
            for entry in entries:
                if len(entry) != 5:
                    continue
                try:
                    actual = resolve_sources(root, course, [entry[0]])[0]
                except ValueError as exc:
                    errors.append(f"补充资料不存在或越界：{exc}")
                    continue
                if actual["sha256"] != entry[1]:
                    warnings.append(f"stale：补充资料 {entry[0]} 内容已变化，需要复核")
        except ValueError as exc:
            errors.append(f"章节范围不可核验：{exc}")
    return errors, warnings


def is_opted_in(path: Path) -> bool:
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:400]
    except OSError:
        return False
    return head.startswith("---\n") and f"schema: {SCHEMA}" in head


def prep_status(root: Path, course: str) -> dict[str, str]:
    """`lesson_id -> ready | draft | stale | invalid | legacy` (read-only)."""
    out: dict[str, str] = {}
    base = textbook_dir(root, course) / "PREP"
    if not base.is_dir():
        return out
    for path in sorted(base.glob("lesson_*.md")):
        lesson_id = path.stem
        if not LESSON_ID.match(lesson_id):
            continue
        if not is_opted_in(path):
            out[lesson_id] = "legacy"
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        front, _ = parse_front_matter(text)
        if front.get("plan_mode") == "chapter":
            errors, warnings = check_prep(root, course, lesson_id)
        else:
            errors, warnings = check_prep_text(text, course=course, lesson_id=lesson_id,
                                               current_hash=book_hash(root, course))
        front, _ = parse_front_matter(text)
        if any(w.startswith("stale") for w in warnings):
            out[lesson_id] = "stale"
        elif front.get("status") == "ready":
            out[lesson_id] = "invalid" if errors else "ready"
        else:
            out[lesson_id] = "draft"
    return out


def doctor_warnings(root: Path, course: str | None = None) -> list[str]:
    """stale/invalid PREP per course (opt-in files only; legacy PREP is never judged)."""
    warnings: list[str] = []
    data_root = root / "DATA"
    if not data_root.is_dir():
        return warnings
    for course_path in iter_course_paths(root, course=course):
        if course_path.is_symlink() or not course_path.is_dir():
            continue
        try:
            statuses = prep_status(root, course_path.name)
        except ValueError:
            continue
        for lesson_id, status in statuses.items():
            if status in {"stale", "invalid"}:
                warnings.append(f"prep[{course_path.name}]: {lesson_id} 状态 {status}（scripts/prep.py check）")
    return warnings


def _outline_anchors(root: Path, course: str, chapter: str) -> list[str]:
    outline = textbook_dir(root, course) / "_outline.md"
    if not outline.is_file() or not chapter:
        return []
    needle = chapter.strip()
    return [line.strip() for line in outline.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.lstrip().startswith("#") and needle in line][:6]


def _carry_over(root: Path, course: str) -> tuple[list[str], list[str]]:
    """(carry lines, seed items) from REAL records only: needs_review rows + pending reteach."""
    progress = course_dir(root, course) / "PROGRESS.md"
    rows = parse_coverage(progress.read_text(encoding="utf-8", errors="replace")) if progress.is_file() else []
    carry = [f"- needs_review：{redact(r['item'], 80)} —— {redact(r['evidence'] or '无证据文字', 80)}"
             for r in rows if r["status"] == "needs_review"]
    queue = course_dir(root, course) / "CONTEXT" / "RETEACH_QUEUE.md"
    if queue.is_file():
        carry += [redact(line, 160) for line in
                  _reteach_body(queue.read_text(encoding="utf-8", errors="replace")).splitlines()]
    seeds = [(r["item"], r.get("elements", "")) for r in rows if r["status"] in {"unseen", "introduced"}]
    return carry, seeds


def scaffold_text(root: Path, course: str, lesson_id: str, chapter: str) -> str:
    template = (Path(__file__).resolve().parents[2] / "templates" / "PREP.md").read_text(encoding="utf-8")
    carry, seed_items = _carry_over(root, course)
    anchors = _outline_anchors(root, course, chapter)
    seeds = "\n".join(
        f"| {item.replace('|', '/')} | unseen | {(elements or 'TODO').replace('|', '/')} |"
        for item, elements in seed_items[:12]
    ) or "| TODO | unseen | TODO |"
    text = (template
            .replace("<carry>", "\n".join(carry) if carry else "（无 needs_review 与待补讲：这是真实状态，不是遗漏）")
            .replace("<seeds>", seeds)
            .replace("<book_hash>", book_hash(root, course) or "none")
            .replace("<course>", course)
            .replace("<lesson_id>", lesson_id)
            .replace("<chapter>", chapter or "TODO"))
    if anchors:
        text = text.replace("anchors:\n", "anchors:\n" + "".join(f'  - "{a}"\n' for a in anchors), 1)
    return text


def new_prep(root: Path, course: str, lesson_id: str, chapter: str, apply: bool = False) -> dict[str, Any]:
    """Create a PREP skeleton. Never overwrites an existing PREP."""
    validate_course_name(course)
    path = prep_path(root, course, lesson_id)
    result = {"course": course, "lesson_id": lesson_id, "path": str(path), "exists": path.exists()}
    if path.exists():
        raise ValueError(f"PREP 已存在，拒绝覆盖：{path}")
    text = scaffold_text(root, course, lesson_id, chapter)
    result["dry_run"] = not apply
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    else:
        result["preview"] = text
    return result
