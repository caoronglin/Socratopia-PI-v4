"""Obsidian export: rich Markdown, plugin-code neutralization, honesty about missing data."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import export_obsidian as ob  # noqa: E402

COURSE = "夹具课程"

PROGRESS = """# Course Progress

## Current checkpoint

- lesson_id: lesson_002
- chapter: 第2章 导数
- tutor: TUTOR_E
- next_entry: 从复合顺序进入

## Coverage ledger

| item | status | evidence |
|---|---|---|
| 导数定义 | verified | lesson_001：能独立解释 |
| 链式法则 | needs_review | lesson_002：把 P(A\\|B) 说反 |
| 隐函数求导 | unseen | - |

## Lesson records

### lesson_001 导数定义

完成，能独立解释 $f'(x)$。

### lesson_002 链式法则

出错后纠正，未复测。
"""

PROJECTION = {"nodes": {"极限": {"props": {"name": "极限"}}, "导数": {"props": {"name": 'f"(x)\n导数'}}, "链式法则": {"props": {}}},
              "edges": [{"from": "极限", "rel": "prerequisite", "to": "导数"},
                        {"from": "导数", "rel": "prerequisite", "to": "链式法则"},
                        {"from": "极限", "rel": "related_to", "to": "链式法则"}]}


def make_repo(progress: str = PROGRESS, projection: dict | None = PROJECTION) -> Path:
    base = Path(tempfile.mkdtemp(prefix="socrat-obs-"))
    work = base / "repo"
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "__pycache__", "DATA", "TEXTBOOK", ".pytest_cache"))
    subprocess.run([sys.executable, str(work / "scripts/scaffold_course.py"), COURSE], cwd=work,
                   capture_output=True, text=True, check=True)
    data = work / "DATA" / COURSE
    (data / "PROGRESS.md").write_text(progress, encoding="utf-8")
    if projection is not None:
        (data / "ontology/projection.json").write_text(json.dumps(projection, ensure_ascii=False), encoding="utf-8")
    return work


def plan_files(work: Path) -> dict[str, str]:
    plan = ob.build_plan(work, COURSE, work / "out")
    return {f["path"]: f["content"] for f in plan["files"]}


class NeutralizeTests(unittest.TestCase):
    def test_dataviewjs_fence_is_disabled(self):
        text = "```dataviewjs\ndv.pages().file.delete()\n```"
        out = ob.neutral(text)
        self.assertNotRegex(out, r"```dataview")
        self.assertIn("dataview-disabled", out)

    def test_dataview_fence_variants(self):
        for fence in ("```dataview", "~~~dataviewjs", "  ````DATAVIEW", "```dataview "):
            self.assertNotRegex(ob.neutral(fence + "\nTABLE x\n"), r"(?i)(`{3,}|~{3,})\s*dataview(js)?\b", fence)

    def test_inline_dataview_and_templater_disabled(self):
        out = ob.neutral("a `=this.file.name` b `$=dv.span(1)` c <% tp.system.prompt() %>")
        self.assertNotIn("`=", out)
        self.assertNotIn("`$=", out)
        self.assertNotIn("<%", out)

    def test_ordinary_code_untouched(self):
        self.assertEqual(ob.neutral("`x = 1` 与 ```python\nprint(1)\n```"), "`x = 1` 与 ```python\nprint(1)\n```")

    def test_link_names_are_safe(self):
        self.assertNotRegex(ob.link_name("a[b]|c#d^e/f\\g"), r"[\[\]|#^/\\]")
        self.assertEqual(ob.link_name("///"), "untitled")


class LessonNoteTests(unittest.TestCase):
    def setUp(self):
        self.work = make_repo()
        self.files = plan_files(self.work)

    def tearDown(self):
        shutil.rmtree(self.work.parent, ignore_errors=True)

    def test_layout(self):
        self.assertEqual(sorted(self.files), ["00 索引.md", "lesson_001.md", "lesson_002.md"])

    def test_properties_block(self):
        note = self.files["lesson_002.md"]
        self.assertTrue(note.startswith("---\n"))
        for field in ('course: "夹具课程"', 'lesson: "lesson_002"', "derived: true", "authoritative: false",
                      "aliases:", "socratopia/needs_review"):
            self.assertIn(field, note)

    def test_callouts_by_status(self):
        note = self.files["lesson_002.md"]
        self.assertIn("> [!warning] needs_review（1）", note)
        self.assertIn("> [!todo] 从复合顺序进入", note)
        self.assertIn("> [!success]- verified", self.files["lesson_001.md"])   # verified is foldable

    def test_wikilink_navigation(self):
        self.assertIn("[[00 索引|索引]]", self.files["lesson_001.md"])
        self.assertIn("[[lesson_002]] →", self.files["lesson_001.md"])
        self.assertIn("← [[lesson_001]]", self.files["lesson_002.md"])
        self.assertNotIn("← [[", self.files["lesson_001.md"])      # first lesson has no previous link
        nav_line = next(line for line in self.files["lesson_002.md"].splitlines() if "[[00 索引" in line)
        self.assertNotIn("→", nav_line)                            # last lesson has no next link

    def test_math_and_pipes_survive(self):
        self.assertIn("$f'(x)$", self.files["lesson_001.md"])
        self.assertIn("P(A/B)", self.files["lesson_002.md"])      # pipe in a table cell is escaped, not truncated

    def test_next_entry_only_on_latest(self):
        self.assertNotIn("下次入口", self.files["lesson_001.md"])
        self.assertIn("下次入口", self.files["lesson_002.md"])

    def test_other_lessons_do_not_leak(self):
        self.assertNotIn("出错后纠正", self.files["lesson_001.md"])
        self.assertNotIn("导数定义 — lesson", self.files["lesson_002.md"].split("## 下次入口")[0])

    def test_missing_body_and_evidence_are_stated(self):
        work = make_repo(PROGRESS.replace("完成，能独立解释 $f'(x)$。", "").replace("lesson_001：能独立解释", "口头"))
        try:
            note = plan_files(work)["lesson_001.md"]
            self.assertIn("[!missing] 未记录", note)
            self.assertIn("无引用本课的证据行", note)
        finally:
            shutil.rmtree(work.parent, ignore_errors=True)

    def test_banner_declares_projection(self):
        for name, text in self.files.items():
            self.assertIn("[!abstract] 只读投影", text, name)


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.work = make_repo()
        self.index = plan_files(self.work)["00 索引.md"]

    def tearDown(self):
        shutil.rmtree(self.work.parent, ignore_errors=True)

    def test_overview_links_and_open_items(self):
        self.assertIn("| needs_review | 1 |", self.index)
        self.assertIn("1. [[lesson_001]] · 导数定义", self.index)
        self.assertIn("2. [[lesson_002]] · 链式法则", self.index)
        self.assertIn("> [!warning] needs_review", self.index)

    def test_mermaid_prerequisite_graph(self):
        self.assertIn("```mermaid\ngraph LR", self.index)
        self.assertEqual(self.index.count("-->"), 2)             # only `prerequisite` edges, not related_to
        self.assertNotRegex(self.index, r"n\d\[\"[^\"]*\"[^\]]")  # labels are quoted and closed

    def test_mermaid_labels_are_escaped(self):
        label_line = next(line for line in self.index.splitlines() if "导数" in line and "-->" in line)
        self.assertNotIn("\n", label_line)
        self.assertEqual(label_line.count('"') % 2, 0, label_line)

    def test_no_graph_means_no_section(self):
        work = make_repo(projection=None)
        try:
            index = plan_files(work)["00 索引.md"]
            self.assertNotIn("mermaid", index)
            self.assertNotIn("先修关系", index)
        finally:
            shutil.rmtree(work.parent, ignore_errors=True)

    def test_graph_with_no_prerequisite_edges_is_omitted(self):
        self.assertEqual(ob.mermaid_graph({"nodes": {"a": {}}, "edges": [{"from": "a", "rel": "related_to", "to": "a"}]}), "")

    def test_dangling_edges_ignored(self):
        self.assertEqual(ob.mermaid_graph({"nodes": {"a": {}}, "edges": [{"from": "a", "rel": "prerequisite", "to": "zz"}]}), "")

    def test_large_graph_is_capped_and_says_so(self):
        nodes = {f"k{i}": {"props": {}} for i in range(60)}
        edges = [{"from": f"k{i}", "rel": "prerequisite", "to": f"k{i + 1}"} for i in range(59)]
        out = ob.mermaid_graph({"nodes": nodes, "edges": edges}, limit=10)
        self.assertEqual(out.count("-->"), 10)
        self.assertIn("共 59 条", out)


class SafetyTests(unittest.TestCase):
    def test_executable_plugin_syntax_in_progress_is_neutralized_everywhere(self):
        evil = (PROGRESS.replace("出错后纠正，未复测。", "```dataviewjs\ndv.view('x')\n```\n`=this.file` <% tp.x %>")
                .replace("从复合顺序进入", "`$=dv.span(1)`"))
        work = make_repo(evil)
        try:
            for name, text in plan_files(work).items():
                self.assertNotRegex(text, r"(?i)`{3}\s*dataview", name)
                self.assertNotIn("`=this", text, name)
                self.assertNotIn("`$=", text, name)
                self.assertNotIn("<%", text, name)
        finally:
            shutil.rmtree(work.parent, ignore_errors=True)

    def test_empty_course_is_honest(self):
        work = make_repo("# p\n", projection=None)
        try:
            index = plan_files(work)["00 索引.md"]
            self.assertIn("没有覆盖账本行", index)
            self.assertIn("没有课时记录", index)
        finally:
            shutil.rmtree(work.parent, ignore_errors=True)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.work = make_repo()

    def tearDown(self):
        shutil.rmtree(self.work.parent, ignore_errors=True)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(self.work / "scripts/export_obsidian.py"), *args],
                              cwd=self.work, capture_output=True, text=True)

    def test_export_without_apply_writes_nothing(self):
        result = self.cli("export", "--course", COURSE)
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.work / "DATA" / COURSE / "obsidian").exists())

    def test_apply_writes_only_obsidian_tree_and_not_progress(self):
        before = (self.work / "DATA" / COURSE / "PROGRESS.md").read_bytes()
        self.assertEqual(self.cli("export", "--course", COURSE, "--apply").returncode, 0)
        out = self.work / "DATA" / COURSE / "obsidian"
        self.assertTrue((out / "00 索引.md").is_file())
        self.assertTrue((out / "lesson_001.md").is_file())
        marker = json.loads((out / ".socratopia-export.json").read_text(encoding="utf-8"))
        self.assertFalse(marker["authoritative"])
        self.assertEqual((self.work / "DATA" / COURSE / "PROGRESS.md").read_bytes(), before)

    def test_reexport_is_idempotent(self):
        self.cli("export", "--course", COURSE, "--apply")
        again = self.cli("export", "--course", COURSE, "--apply")
        self.assertIn("写入 0 个，未变化 3 个", again.stdout)

    def test_unsafe_course_rejected(self):
        self.assertEqual(self.cli("plan", "--course", "../etc").returncode, 1)


if __name__ == "__main__":
    unittest.main()
