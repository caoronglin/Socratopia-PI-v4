#!/usr/bin/env python3
"""Export a course as an Obsidian-flavoured Markdown vault folder (read-only projection).

Output (default `DATA/<course>/obsidian/`, inside the course boundary):

- `00 索引.md`        course index: coverage table, lesson links, open items, prerequisite graph
- `<lesson_id>.md`    one note per lesson: properties, callouts, prev/next wikilinks

Rich syntax used (all core Obsidian, no plugins required): YAML properties, callouts
(`> [!warning]`, foldable `> [!success]-`), `[[wikilinks]]`, ```mermaid fences, `$…$` math.

Everything is derived from `PROGRESS.md` (+ the ontology projection for the graph) and
marked `derived: true`. This script never writes `PROGRESS.md`, never invents status,
and neutralizes executable plugin syntax found in course text (Dataview/Templater).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_stellar import (  # noqa: E402
    OPEN_STATES,
    _lesson_rows,
    parse_checkpoint,
    parse_coverage,
    parse_lessons,
    strip_stamps,
)
from scripts.lib.repository import course_dir, read_json, validate_course_name, write_json_atomic  # noqa: E402

BANNER = "> [!abstract] 只读投影\n> 导出自 `PROGRESS.md`。掌握事实只以 `PROGRESS.md` 为准；请勿在此手改课堂事实。"
CALLOUT = {"verified": "success", "needs_review": "warning", "unseen": "question", "introduced": "info",
           "intentionally_skipped": "note"}
INDEX_NAME = "00 索引"

_DATAVIEW_FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*dataview(js)?\b", re.I | re.M)
_INLINE_DV = re.compile(r"`\s*\$?=")
_LINK_UNSAFE = re.compile(r"[\[\]|#^\\/:*?\"<>]")


def neutral(text: str) -> str:
    """Disable plugin code execution in user-derived text (Dataview/DataviewJS/Templater)."""
    text = _DATAVIEW_FENCE.sub(lambda m: f"{m.group(1)}{m.group(2)} text dataview-disabled", text)
    text = _INLINE_DV.sub("` =", text).replace("<%", "< %")
    return text


def link_name(text: str) -> str:
    """A string safe inside [[...]] and as a filename."""
    return re.sub(r"\s+", " ", _LINK_UNSAFE.sub("-", text)).strip(" .-") or "untitled"


def cell(text: str) -> str:
    return neutral(text).replace("|", "/").replace("\n", " ")


def prop(value: str) -> str:
    """Quote a YAML scalar."""
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def mermaid_graph(projection: dict | None, limit: int = 40) -> str:
    """Prerequisite graph as a mermaid block, or '' when there is no graph (never invented)."""
    if not projection:
        return ""
    nodes = projection.get("nodes") or {}
    edges = [e for e in projection.get("edges") or [] if e.get("rel") == "prerequisite"
             and e.get("from") in nodes and e.get("to") in nodes]
    if not edges:
        return ""
    ids: dict[str, str] = {}

    def nid(key: str) -> str:
        return ids.setdefault(key, f"n{len(ids)}")

    def label(key: str) -> str:
        props = nodes[key].get("props") or {}
        raw = str(props.get("name") or props.get("title") or key)
        return raw.replace('"', "'").replace("\n", " ")[:40]

    lines = ["```mermaid", "graph LR"]
    for edge in edges[:limit]:
        a, b = edge["from"], edge["to"]
        lines.append(f'  {nid(a)}["{label(a)}"] --> {nid(b)}["{label(b)}"]')
    lines.append("```")
    if len(edges) > limit:
        lines.append(f"> 仅显示前 {limit} 条先修关系（共 {len(edges)} 条）。")
    return "\n".join(lines)


def render_lesson(course: str, lesson: dict, coverage: list[dict], checkpoint: dict, state: dict,
                  prev_name: str | None, next_name: str | None, is_latest: bool) -> str:
    lid = lesson["lesson_id"]
    title = lesson.get("title") or lid
    own = _lesson_rows(coverage, lid)
    statuses = sorted({r["status"] for r in own if r["status"]})
    fm = ["---", f"title: {prop(title)}", f"course: {prop(course)}", f"lesson: {prop(lid)}",
          "aliases:", f"  - {prop(title)}", "tags:", "  - socratopia/lesson", f"  - socratopia/course/{link_name(course)}"]
    fm += [f"  - socratopia/{s}" for s in statuses]
    fm += ["derived: true", "authoritative: false", "---"]

    body = [f"# {neutral(title)}", "", BANNER, ""]
    nav = [f"[[{INDEX_NAME}|索引]]"]
    if prev_name:
        nav.insert(0, f"← [[{prev_name}]]")
    if next_name:
        nav.append(f"[[{next_name}]] →")
    body += [" · ".join(nav), ""]

    record = neutral(lesson.get("body") or "")
    body += ["## 本课记录", "", record if record else "> [!missing] 未记录\n> `PROGRESS.md` 没有本课正文；不补写。", ""]

    body += ["## 本课证据", ""]
    if own:
        for status in ("needs_review", "unseen", "introduced", "verified", "intentionally_skipped"):
            rows = [r for r in own if r["status"] == status]
            if not rows:
                continue
            fold = "-" if status in {"verified", "intentionally_skipped"} else ""
            body.append(f"> [!{CALLOUT[status]}]{fold} {status}（{len(rows)}）")
            body += [f"> - **{cell(r['item'])}** — {cell(r['evidence'] or '无证据文字')}" for r in rows]
            body.append("")
    else:
        body += ["> [!missing] 无引用本课的证据行", "> 账本中没有证据列引用本课；不猜测。", ""]

    if is_latest:
        open_rows = [r for r in coverage if r["status"] in OPEN_STATES and r not in own]
        body += ["## 下次入口", ""]
        entry = neutral(checkpoint.get("next_entry") or "（`PROGRESS.md` 未记录）")
        tutor = checkpoint.get("tutor") or state.get("active_tutor") or "未设置"
        chapter = checkpoint.get("chapter") or state.get("current_chapter") or "未定位"
        body += [f"> [!todo] {entry}", f"> 导师：{cell(tutor)} · 章节：{cell(chapter)}", ""]
        if open_rows:
            body.append("> [!question]- 其他未验证项")
            body += [f"> - {cell(r['item'])} [{r['status']}]" for r in open_rows]
            body.append("")
    return "\n".join(fm + [""] + body).rstrip() + "\n"


def render_index(course: str, lessons: list[dict], names: dict[str, str], coverage: list[dict],
                 checkpoint: dict, graph: str) -> str:
    counts: dict[str, int] = {}
    for row in coverage:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    fm = ["---", f"title: {prop(course + ' · 索引')}", f"course: {prop(course)}", "tags:", "  - socratopia/index",
          "derived: true", "authoritative: false", "---"]
    body = [f"# {neutral(course)}", "", BANNER, "", "## 覆盖概览", ""]
    if counts:
        body += ["| 状态 | 数量 |", "|---|---:|"] + [f"| {s} | {n} |" for s, n in sorted(counts.items())]
    else:
        body.append("> [!missing] `PROGRESS.md` 没有覆盖账本行。")
    body += ["", "## 课程", ""]
    body += [f"{n}. [[{names[x['lesson_id']]}]]" + (f" · {cell(x['title'])}" if x.get("title") else "")
             for n, x in enumerate(lessons, 1)] or ["> [!missing] `PROGRESS.md` 没有课时记录。"]
    review = [r for r in coverage if r["status"] == "needs_review"]
    if review:
        body += ["", "## 待复习", "", "> [!warning] needs_review"]
        body += [f"> - **{cell(r['item'])}** — {cell(r['evidence'] or '无证据文字')}" for r in review]
    if checkpoint.get("next_entry"):
        body += ["", "## 下次入口", "", f"> [!todo] {neutral(checkpoint['next_entry'])}"]
    if graph:
        body += ["", "## 先修关系", "", graph]
    return "\n".join(fm + [""] + body).rstrip() + "\n"


def build_plan(root: Path, course: str, out: Path) -> dict:
    validate_course_name(course)
    cdir = course_dir(root, course)
    progress = (cdir / "PROGRESS.md").read_text(encoding="utf-8", errors="replace") if (cdir / "PROGRESS.md").is_file() else ""
    state = read_json(cdir / "runtime" / "course_state.json") or {}
    projection = read_json(cdir / "ontology" / "projection.json")
    lessons, coverage, checkpoint = parse_lessons(progress), parse_coverage(progress), parse_checkpoint(progress)

    names = {x["lesson_id"]: x["lesson_id"] for x in lessons}   # file name == lesson_id: stable, link-safe
    files = [{"path": f"{INDEX_NAME}.md",
              "content": render_index(course, lessons, names, coverage, checkpoint, mermaid_graph(projection))}]
    for i, lesson in enumerate(lessons):
        files.append({"path": f"{names[lesson['lesson_id']]}.md",
                      "content": render_lesson(course, lesson, coverage, checkpoint, state,
                                               names[lessons[i - 1]["lesson_id"]] if i else None,
                                               names[lessons[i + 1]["lesson_id"]] if i + 1 < len(lessons) else None,
                                               i == len(lessons) - 1)})
    return {"course": course, "out": str(out), "source_of_truth": f"DATA/{course}/PROGRESS.md",
            "derived": True, "authoritative": False, "network": False, "lessons": len(lessons),
            "will_not_touch": [f"DATA/{course}/PROGRESS.md", f"TEXTBOOK/{course}/book.md"], "files": files}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导出 Obsidian 风格 Markdown（只读投影）")
    parser.add_argument("command", choices=["plan", "export"])
    parser.add_argument("--course", required=True)
    parser.add_argument("--out", default=None, help="默认 DATA/<course>/obsidian")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        course = validate_course_name(args.course)
    except ValueError as exc:
        print(f"✗ {exc}")
        return 1
    out = Path(args.out) if args.out else course_dir(ROOT, course) / "obsidian"
    plan = build_plan(ROOT, course, out)
    if args.command == "plan" or not args.apply:
        print(json.dumps({k: v for k, v in plan.items() if k != "files"}, ensure_ascii=False, indent=2))
        for item in plan["files"]:
            print(f"  + {item['path']}")
        print("dry-run：未写入任何文件。" + ("" if args.command == "plan" else "加 --apply 执行。"))
        return 0
    out.mkdir(parents=True, exist_ok=True)
    written = unchanged = 0
    for item in plan["files"]:
        target = out / item["path"]
        if target.is_file() and strip_stamps(target.read_text(encoding="utf-8", errors="replace")) == strip_stamps(item["content"]):
            unchanged += 1
            continue
        target.write_text(item["content"], encoding="utf-8")
        written += 1
    write_json_atomic(out / ".socratopia-export.json", {"course": course, "derived": True, "authoritative": False,
                                                        "files": [i["path"] for i in plan["files"]]})
    print(f"已导出到 {out}：写入 {written} 个，未变化 {unchanged} 个。事实源仍是 {plan['source_of_truth']}。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
