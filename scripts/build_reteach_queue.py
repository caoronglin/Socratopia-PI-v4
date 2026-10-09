#!/usr/bin/env python3
"""新增/重编教材后，生成课程级补讲队列候选项（v4，课程隔离 + 路径安全）。

只生成候选清单，写 RETEACH_QUEUE.md 投影；绝不改写 PROGRESS.md，也不宣称已补讲。
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_stellar import parse_coverage  # noqa: E402
from scripts.lib.repository import course_dir, safe_child_path, textbook_dir, validate_course_name  # noqa: E402


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def strip_md(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "[图片]", text)
    text = re.sub(r"\[[^\]]+\]\([^)]*\)", lambda m: m.group(0).split("](")[0].lstrip("["), text)
    text = re.sub(r"[`*_>#|\-]+", " ", text)
    return re.sub(r"\s+", " ", text)


def load_manifest(cdir: Path) -> dict:
    p = cdir / "manifest.json"
    if p.exists():
        return json.loads(read_text(p))
    chapters: list[dict] = []
    for line in read_text(cdir / "_outline.md").splitlines():
        m = re.match(r"^##\s+(.+)$", line.strip())
        if m:
            chapters.append({"number": len(chapters) + 1, "title": m.group(1).strip()})
    return {"course": cdir.name, "chapters": chapters}


def headings(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if m:
            h = m.group(2).strip()
            if h and h not in out:
                out.append(h)
    return out


def chapter_text(cdir: Path, title: str, next_titles: list[str]) -> str:
    book = read_text(cdir / "book.md")
    i = book.find(title)
    if i < 0:
        return ""
    stops = [book.find(t, i + len(title)) for t in next_titles]
    stops = [x for x in stops if x > i]
    j = min(stops) if stops else len(book)
    return book[i:j]


def covered(heading: str, coverage_text: str) -> bool:
    h0 = strip_md(heading).strip()
    if len(h0) < 2 or h0 in coverage_text:
        return True
    tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", h0)
    return len(tokens) >= 3 and sum(1 for t in tokens if t in coverage_text) >= max(2, len(tokens) // 2)


def build_queue(root: Path, course: str) -> str:
    validate_course_name(course)
    cdir = textbook_dir(root, course)
    if not cdir.exists():
        raise SystemExit(f"课程目录不存在：{cdir}")
    chapters = load_manifest(cdir).get("chapters", [])
    context_dir = course_dir(root, course) / "CONTEXT"
    # A candidate list or PREP is never evidence of a taught, verified item.
    ledger = parse_coverage(read_text(course_dir(root, course) / "PROGRESS.md"))
    verified = [row for row in ledger
                if row.get("status") in {"verified", "intentionally_skipped"}
                and row.get("evidence", "").strip() not in {"", "-"}]
    verified_titles = {strip_md(str(row["item"])).strip() for row in verified}
    coverage_text = strip_md("\n".join(str(row["item"]) + " " + str(row["evidence"]) for row in verified))
    items: list[dict] = []
    all_titles = [str(c.get("title") or f"第{i + 1}章") for i, c in enumerate(chapters)]
    for idx, ch in enumerate(chapters, 1):
        title = str(ch.get("title") or f"第{idx}章")
        txt = chapter_text(cdir, title, all_titles[idx:])
        hs = headings(txt) or [title]
        for h in hs:
            if strip_md(h).strip() not in verified_titles:
                items.append({"chapter": title, "type": "标题/小节", "evidence": h, "reason": "教材或备课包中存在该标题/小节，但既有课堂摘要与进度中未发现明确覆盖痕迹。", "priority": "P1", "status": "pending", "check": "用自己的话复述该小节主线，并完成 1 道辨析/迁移题。"})
        if "[图片]" in strip_md(txt) and not any(x in coverage_text for x in ["图表", "图片", "读图"]):
            items.append({"chapter": title, "type": "图表", "evidence": "本章教材含图片/图表资源", "reason": "既有课堂摘要中未发现图表讲解痕迹。", "priority": "P1", "status": "pending", "check": "说明关键图表的结构/变量、读图陷阱与应用。"})
        if re.search(r"(思考题|习题|练习|例题|案例|讨论题|复习题)", txt) and not re.search(r"(思考题|习题|练习|例题|案例|讨论题|复习题)", coverage_text):
            items.append({"chapter": title, "type": "例题/习题/案例", "evidence": "本章教材含例题/习题/案例线索", "reason": "既有课堂摘要中未发现例题/习题处理痕迹。", "priority": "P1", "status": "pending", "check": "完成代表性题目的思路复述与变式迁移。"})
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# {course} · 新增教材差异补讲队列", "", f"更新时间：{now}", "生成器：`scripts/build_reteach_queue.py`", "",
        "> 说明：本队列是候选补讲清单，不表示课堂已经补讲完成；只有真实授课并通过理解验证后，才能把状态改为 understood。工程生成不会写入课程级 PROGRESS.md。", "", "## 队列", "",
        "| id | 章节 | 类型 | 优先级 | 状态 | 差异证据 | 需要补讲的原因 | 理解验证 |", "|---|---|---|---|---|---|---|---|",
    ]
    if not items:
        lines.append("| 暂无 | - | - | - | - | 未发现明显新增/未覆盖候选项 | 仍需正式上课前人工复核 | - |")
    else:
        for n, item in enumerate(items, 1):
            rid = "RQ-" + hashlib.sha256(
                (course + "|" + item["chapter"] + "|" + item["type"] + "|" + item["evidence"]).encode("utf-8")
            ).hexdigest()[:12]
            row = [rid, item["chapter"], item["type"], item["priority"], item["status"], item["evidence"], item["reason"], item["check"]]
            row = [str(x).replace("|", "/").replace("\n", " ") for x in row]
            lines.append("| " + " | ".join(row) + " |")
    lines += ["", "## 课堂处理规则", "", "- `pending` / `needs_review` 项优先于新章节推进。", "- 每项补讲必须完成：证据定位 → 苏格拉底追问 → 示例/反例 → 理解验证题 → 学习者复述。", "- 未通过理解验证则保持 `needs_review`，并写入下次入口。"]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成新增/重编教材后的补讲队列候选项")
    parser.add_argument("--course", required=True, help="课程名，对应 TEXTBOOK/<课程名>")
    args = parser.parse_args()
    content = build_queue(ROOT, args.course)
    context_dir = course_dir(ROOT, args.course) / "CONTEXT"
    prep_dir = textbook_dir(ROOT, args.course) / "PREP"
    context_dir.mkdir(parents=True, exist_ok=True)
    prep_dir.mkdir(parents=True, exist_ok=True)
    safe_child_path(course_dir(ROOT, args.course), "CONTEXT", "RETEACH_QUEUE.md").write_text(content, encoding="utf-8")
    safe_child_path(textbook_dir(ROOT, args.course), "PREP", "_reteach_queue.md").write_text(content, encoding="utf-8")
    print(f"已生成/更新《{args.course}》补讲队列：{context_dir / 'RETEACH_QUEUE.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
