#!/usr/bin/env python3
"""Export Socratopia course state as a Stellar (Hexo theme) notebook tree.

Each course becomes ONE notebook (`source/_data/notebooks/<course>.yml`) and each
lesson becomes ONE note (`source/notes/<course>/lesson_XXX.md`).

Everything written here is a **non-authoritative projection** of
`DATA/<course>/PROGRESS.md`, which stays the sole source of truth. This script
never writes PROGRESS.md, never invents mastery, and never promotes coverage
states (see SYSTEM/SPEC/CLASSROOM_CONTRACT.md).

Default output is `DATA/<course>/stellar/source/` — inside the course boundary
and gitignored. Point `--out` at a Hexo `source/` tree only with intent.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.repository import (  # noqa: E402
    course_dir,
    read_json,
    validate_course_name,
    write_json_atomic,
)

BANNER = (
    "> 本页由 `scripts/export_stellar.py` 从 `DATA/<course>/PROGRESS.md` 导出，"
    "是**只读投影**。掌握事实只以 `PROGRESS.md` 为准；请勿在此页手工编辑课堂事实。"
)

COVERAGE_STATES = {
    "unseen": "unseen",
    "introduced": "introduced",
    "verified": "verified",
    "needs_review": "needs_review",
    "intentionally_skipped": "intentionally_skipped",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def safe(text: str) -> str:
    """Neutralize Hexo/Nunjucks syntax in user-derived text.

    PROGRESS.md is learner/agent-authored data. Hexo executes `{% tag %}` and
    `{{ expr }}` found in note bodies (e.g. file-including tags), so data must
    never be able to open one.
    """
    return text.replace("{%", "{ %").replace("{{", "{ {").replace("{#", "{ #")


def yaml_quote(value: str) -> str:
    """Quote a scalar for YAML front matter without importing a YAML dependency."""
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def parse_coverage(progress_text: str) -> list[dict[str, str]]:
    """Parse the `## Coverage ledger` table. Never invents rows.

    Layout is `item | status | evidence` plus an optional `expected elements`
    column. elements are only read when the header declares that column, so a
    legacy three-column ledger keeps parsing unchanged. Never invents cells.
    """
    rows: list[dict[str, str]] = []
    in_section = False
    header: list[str] = []
    for line in progress_text.splitlines():
        if re.match(r"^#{1,6}\s+", line):
            in_section = bool(re.match(r"^#{1,6}\s+coverage\s+ledger", line, re.I))
            continue
        if not in_section or not line.strip().startswith("|"):
            continue
        # Markdown tables must escape a literal pipe as `\|`; split only on
        # unescaped pipes so math like P(A\|B) survives the round trip.
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        cells = [c.replace("\\|", "|") for c in cells]
        if len(cells) < 2 or set("".join(cells)) <= set("-: "):
            continue
        if cells[0].lower() in {"item", "项目", "条目"}:
            header = [c.lower() for c in cells]
            continue
        if "期望元素" in " ".join(header) and len(cells) > 3:
            # `item | status | evidence | elements` — elements is last.
            evidence, elements = cells[2], "|".join(cells[3:])
        else:
            # `item | status | evidence` — evidence is last and may legitimately
            # contain pipes (math like P(A|B)), so rejoin the tail.
            evidence = "|".join(cells[2:]) if len(cells) > 2 else ""
            elements = ""
        item, status = cells[0], cells[1].lower()
        if item:
            rows.append({"item": item, "status": status, "evidence": evidence, "elements": elements})
    return rows


def parse_checkpoint(progress_text: str) -> dict[str, str]:
    """Parse the `## Current checkpoint` bullet list (the real source of entry/tutor)."""
    out: dict[str, str] = {}
    in_section = False
    for line in progress_text.splitlines():
        if re.match(r"^#{1,6}\s+", line):
            in_section = bool(re.match(r"^#{1,6}\s+current\s+checkpoint", line, re.I))
            continue
        if not in_section:
            continue
        match = re.match(r"^\s*[-*]\s*([A-Za-z_]+)\s*[:：]\s*(.*)$", line)
        if match:
            key, value = match.group(1).strip().lower(), match.group(2).strip()
            if value and value not in {"-", "—"}:
                out[key] = value
    return out


def parse_lessons(progress_text: str) -> list[dict[str, str]]:
    """Parse lesson records. Supports `### lesson_007` headings and `- lesson_id:` lines."""
    lessons: list[dict[str, str]] = []
    seen: set[str] = set()

    headings = list(re.finditer(r"^(#{1,6})\s+(.*)$", progress_text, re.M))
    for match in re.finditer(r"^(#{1,6})\s*(lesson[_\-]\d+)\s*(.*)$", progress_text, re.M | re.I):
        lesson_id = match.group(2).lower().replace("-", "_")
        if lesson_id in seen:
            continue
        seen.add(lesson_id)
        # The lesson's own record: up to the next heading of the same or higher level.
        level = len(match.group(1))
        end = next((h.start() for h in headings
                    if h.start() > match.start() and len(h.group(1)) <= level), len(progress_text))
        body = progress_text[match.end():end].strip()
        lessons.append({"lesson_id": lesson_id, "title": match.group(3).strip(), "body": body})

    for match in re.finditer(r"^\s*[-*]\s*lesson_id\s*[:：]\s*(\S+)\s*$", progress_text, re.M):
        lesson_id = match.group(1).lower().replace("-", "_")
        if lesson_id and lesson_id not in seen and lesson_id not in {"<lesson_id>", "-"}:
            seen.add(lesson_id)
            lessons.append({"lesson_id": lesson_id, "title": "", "body": ""})

    def key(item: dict[str, str]) -> tuple[int, str]:
        digits = re.findall(r"\d+", item["lesson_id"])
        return (int(digits[0]) if digits else 0, item["lesson_id"])

    return sorted(lessons, key=key)


OPEN_STATES = ("needs_review", "unseen", "introduced")


def _lesson_rows(coverage: list[dict[str, str]], lesson_id: str) -> list[dict[str, str]]:
    """Coverage rows whose recorded evidence cites this lesson (never guessed)."""
    pattern = re.compile(re.escape(lesson_id).replace("_", "[_\\-]"), re.I)
    return [row for row in coverage if pattern.search(row["evidence"] or "")]


def _table(rows: list[dict[str, str]]) -> list[str]:
    lines = ["| item | status | evidence |", "|---|---|---|"]
    for row in rows:
        cells = [safe(row["item"]).replace("|", "/"), row["status"] or "-",
                 safe(row["evidence"] or "-").replace("|", "/")]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def render_note(course: str, lesson: dict[str, str], coverage: list[dict[str, str]],
                state: dict, checkpoint: dict[str, str], stamp: str, is_latest: bool = True) -> str:
    """One lesson = one note: this lesson's record + the coverage evidence that cites it.

    The checkpoint ("next entry") describes where the course stands NOW, so it is
    attached only to the latest lesson; older notes never claim it.
    """
    lesson_id = lesson["lesson_id"]
    title = safe(lesson.get("title") or lesson_id)
    own_rows = _lesson_rows(coverage, lesson_id)
    tag_rows = own_rows + ([r for r in coverage if r["status"] in OPEN_STATES] if is_latest else [])
    fm: list[str] = ["---"]
    fm.append(f"title: {yaml_quote(title)}")
    fm.append("collection:")
    fm.append("  profile: notebook")
    fm.append(f"  id: {yaml_quote(course)}")
    fm.append(f"date: {yaml_quote(stamp)}")
    fm.append(f"updated: {yaml_quote(stamp)}")
    fm.append("tags:")
    fm.append("  - socratopia/lesson")
    fm.append(f"  - {course}/{lesson_id}")
    for status in sorted({row["status"] for row in tag_rows if row["status"]}):
        if status in COVERAGE_STATES:
            fm.append(f"  - socratopia/coverage/{status}")
    fm.append("article:")
    fm.append("  style: tech")
    fm.append("render:")
    fm.append("  math: katex")
    fm.append("  diagrams: mermaid")
    fm.append("footer:")
    fm.append("  show_tags: true")
    fm.append("  share: false")
    fm.append("visibility:")
    fm.append("  listed: true")
    fm.append("  searchable: true")
    fm.append("listing:")
    fm.append("  priority: 0")
    fm.append("---")

    body = [f"# {title}", "", BANNER, "", "> 覆盖状态只反映导出时刻 `PROGRESS.md` 的记录。", ""]

    body += ["## 本课记录", ""]
    record = safe(lesson.get("body") or "")
    body.append(record if record else "> `PROGRESS.md` 未记录本课正文；本页不补写。")
    body.append("")

    body += ["## 本课覆盖证据", ""]
    if own_rows:
        body += _table(own_rows)
    else:
        body.append("> 覆盖账本中没有引用本课的证据行；不猜测。")
    body.append("")

    if is_latest:
        open_rows = [r for r in coverage if r["status"] in OPEN_STATES and r not in own_rows]
        counts = {s: sum(1 for r in coverage if r["status"] == s) for s in sorted({r["status"] for r in coverage})}
        body += ["## 课程当前进度", ""]
        body.append("- 覆盖概览：" + ("、".join(f"{s} {n}" for s, n in counts.items()) or "无记录"))
        if open_rows:
            body += ["", "其他未验证项：", ""] + _table(open_rows)
        body += ["", "## 下次入口", ""]
        entry = safe(checkpoint.get("next_entry") or "（`PROGRESS.md` 未记录）")
        tutor = safe(checkpoint.get("tutor") or state.get("active_tutor") or "未设置")
        chapter = safe(checkpoint.get("chapter") or state.get("current_chapter") or "未定位")
        body += [f"- 入口：{entry}", f"- 当前导师：{tutor}", f"- 当前章节：{chapter}", ""]
    return "\n".join(fm + body)


def render_notebook_yaml(course: str, state: dict, lessons: list[dict[str, str]]) -> str:
    name = state.get("course_name") or course
    order = state.get("listing_order") or 1
    return "\n".join([
        f"name: {yaml_quote(name)}",
        f"route:",
        f"  path: /notes/{course}/",
        "listing:",
        f"  order: {int(order)}",
        "  per_page: 0",
        "  sort:",
        "    field: updated",
        "    direction: desc",
        "visibility:",
        "  listed: true",
        "  searchable: true",
        f"description: {yaml_quote('Socratopia 课程笔记本 · 只读投影，事实源为 DATA/' + course + '/PROGRESS.md')}",
        "",
    ])


def build_plan(root: Path, course: str, out: Path) -> dict:
    validate_course_name(course)
    cdir = course_dir(root, course)
    progress = read_text(cdir / "PROGRESS.md")
    runtime = cdir / "runtime"
    state = read_json(runtime / "course_state.json") or {}
    lessons = parse_lessons(progress)
    coverage = parse_coverage(progress)
    checkpoint = parse_checkpoint(progress)
    stamp = dt.datetime.now().isoformat(timespec="seconds")

    files: list[dict] = []
    files.append({
        "path": f"_data/notebooks/{course}.yml",
        "content": render_notebook_yaml(course, state, lessons),
    })
    for index, lesson in enumerate(lessons):
        files.append({
            "path": f"notes/{course}/{lesson['lesson_id']}.md",
            "content": render_note(course, lesson, coverage, state, checkpoint, stamp,
                                   is_latest=index == len(lessons) - 1),
        })
    return {
        "course": course,
        "source_of_truth": f"DATA/{course}/PROGRESS.md",
        "out": str(out),
        "authoritative": False,
        "derived": True,
        "network": False,
        "lessons": len(lessons),
        "coverage_rows": len(coverage),
        "will_not_touch": [
            f"DATA/{course}/PROGRESS.md",
            f"TEXTBOOK/{course}/book.md",
        ],
        "files": files,
    }


_STAMP_LINE = re.compile(r'^(date|updated): ".*"$', re.M)
_DATE_LINE = re.compile(r'^date: ".*"$', re.M)


def strip_stamps(text: str) -> str:
    """Content with the volatile date/updated front-matter lines blanked out."""
    return _STAMP_LINE.sub(lambda m: f'{m.group(1)}: ""', text)


def keep_original_date(new: str, old: str) -> str:
    """A re-export must not change when the lesson was first exported."""
    previous = _DATE_LINE.search(old)
    return _DATE_LINE.sub(lambda _m: previous.group(0), new, count=1) if previous else new


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="导出 Stellar（Hexo 主题）笔记本：一门课程一个 notebook，一节课一篇笔记"
    )
    parser.add_argument("command", choices=["plan", "export", "check"])
    parser.add_argument("--course", required=True)
    parser.add_argument("--out", default=None, help="Hexo source/ 目录（默认 DATA/<course>/stellar/source）")
    parser.add_argument("--apply", action="store_true", help="实际写入（默认只打印计划）")
    args = parser.parse_args(argv)

    out = Path(args.out) if args.out else course_dir(ROOT, args.course) / "stellar/source"
    plan = build_plan(ROOT, args.course, out)

    if args.command == "plan":
        print(json.dumps({k: v for k, v in plan.items() if k != "files"}, ensure_ascii=False, indent=2))
        for item in plan["files"]:
            print(f"  + {item['path']}")
        print("dry-run：未写入任何文件。加 --apply 执行。")
        return 0

    if args.command == "check":
        problems = []
        if not plan["lessons"]:
            problems.append("PROGRESS.md 中没有可解析的 lesson 记录，笔记将为空")
        for item in plan["files"]:
            if item["path"].endswith(".md") and "{{" in item["content"]:
                problems.append(f"未渲染的模板占位符：{item['path']}")
        for problem in problems:
            print(f"ERROR: {problem}")
        print("check 通过" if not problems else f"check 失败：{len(problems)} 项")
        return 0 if not problems else 1

    if not args.apply:
        print("export 需要 --apply。dry-run 计划：")
        for item in plan["files"]:
            print(f"  + {item['path']}")
        return 0

    written = unchanged = 0
    for item in plan["files"]:
        target = out / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        content = item["content"]
        if target.exists():
            old = target.read_text(encoding="utf-8", errors="replace")
            if item["path"].endswith(".md"):
                content = keep_original_date(content, old)
            if strip_stamps(content) == strip_stamps(old):
                unchanged += 1  # same content: do not bump `updated` or rewrite the file
                continue
        target.write_text(content, encoding="utf-8")
        written += 1
    write_json_atomic(out / ".socratopia-export.json", {
        "course": args.course,
        "source_of_truth": plan["source_of_truth"],
        "derived": True,
        "authoritative": False,
        "files": [item["path"] for item in plan["files"]],
    })
    print(f"已导出到 {out}：写入 {written} 个，未变化 {unchanged} 个。")
    print(f"事实源仍是 {plan['source_of_truth']}（导出为只读投影）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
