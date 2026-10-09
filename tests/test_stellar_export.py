"""Socratopia -> Stellar (Hexo theme) export invariants.

A course is one notebook; a lesson is one note. Everything written is a
non-authoritative projection of PROGRESS.md, so these tests pin both the layout
and the "never invent state" boundary.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_stellar import (  # noqa: E402
    build_plan,
    parse_checkpoint,
    parse_coverage,
    parse_lessons,
)

COURSE = "夹具课程"

PROGRESS = """# Course Progress

## Current checkpoint

- lesson_id: lesson_002
- chapter: 第2章 贝叶斯推断
- tutor: TUTOR_A
- next_entry: 从"先验如何被似然更新"进入

## Coverage ledger

| item | status | evidence |
|---|---|---|
| 贝叶斯公式 | verified | lesson_001：能独立推导 |
| 概率与似然的区别 | needs_review | lesson_002：把 P(A|B) 与 P(B|A) 弄反 |
| 条件独立 | unseen | - |

## Lesson records

### lesson_001 条件概率

完成条件概率与全概率公式。

### lesson_002 先验与后验

讲过贝叶斯直觉；学习者出错，已纠正未复测。
"""


def make_repo(progress: str = PROGRESS) -> Path:
    base = Path(tempfile.mkdtemp())
    work = base / "repo"
    shutil.copytree(
        ROOT, work,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "DATA", "TEXTBOOK"),
    )
    subprocess.run([sys.executable, str(work / "scripts/scaffold_course.py"), COURSE],
                   cwd=work, capture_output=True, text=True, check=True)
    (work / "DATA" / COURSE / "PROGRESS.md").write_text(progress, encoding="utf-8")
    return work


class ParserTests(unittest.TestCase):
    def test_parses_coverage_rows(self):
        rows = parse_coverage(PROGRESS)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["status"], "verified")

    def test_math_pipe_in_evidence_is_rejoined(self):
        """`P(A|B)` must not truncate the evidence cell."""
        rows = parse_coverage(PROGRESS)
        evidence = next(r["evidence"] for r in rows if "似然" in r["item"])
        self.assertIn("P(A|B)", evidence)
        self.assertIn("P(B|A)", evidence)

    def test_never_invents_status(self):
        rows = parse_coverage(PROGRESS)
        self.assertEqual(rows[-1]["evidence"], "-")

    def test_parses_lessons_sorted(self):
        lessons = parse_lessons(PROGRESS)
        self.assertEqual([l["lesson_id"] for l in lessons], ["lesson_001", "lesson_002"])
        self.assertEqual(lessons[0]["title"], "条件概率")

    def test_parses_checkpoint(self):
        checkpoint = parse_checkpoint(PROGRESS)
        self.assertEqual(checkpoint["next_entry"], '从"先验如何被似然更新"进入')
        self.assertEqual(checkpoint["tutor"], "TUTOR_A")

    def test_empty_progress_yields_nothing(self):
        self.assertEqual(parse_coverage(""), [])
        self.assertEqual(parse_lessons(""), [])


class PlanShapeTests(unittest.TestCase):
    def setUp(self):
        self.work = make_repo()
        self.plan = build_plan(self.work, COURSE, self.work / "out")

    def tearDown(self):
        shutil.rmtree(self.work.parent, ignore_errors=True)

    def test_one_notebook_per_course(self):
        yml = [f for f in self.plan["files"] if f["path"].endswith(".yml")]
        self.assertEqual(len(yml), 1)
        self.assertEqual(yml[0]["path"], f"_data/notebooks/{COURSE}.yml")

    def test_one_note_per_lesson(self):
        notes = sorted(f["path"] for f in self.plan["files"] if f["path"].endswith(".md"))
        self.assertEqual(notes, [
            f"notes/{COURSE}/lesson_001.md",
            f"notes/{COURSE}/lesson_002.md",
        ])

    def test_plan_declares_non_authoritative(self):
        self.assertFalse(self.plan["authoritative"])
        self.assertTrue(self.plan["derived"])
        self.assertFalse(self.plan["network"])
        self.assertIn("PROGRESS.md", self.plan["source_of_truth"])
        self.assertTrue(any("PROGRESS.md" in p for p in self.plan["will_not_touch"]))
        self.assertTrue(any("book.md" in p for p in self.plan["will_not_touch"]))

    def test_note_carries_required_stellar_fields(self):
        note = next(f for f in self.plan["files"] if f["path"].endswith("lesson_002.md"))
        content = note["content"]
        self.assertTrue(content.startswith("---\n"))
        for field in ("title:", "collection:", "  profile: notebook", "  id:", "tags:", "visibility:", "listing:"):
            self.assertIn(field, content)
        self.assertIn("socratopia/lesson", content)
        self.assertIn("socratopia/coverage/needs_review", content)

    def test_note_states_it_is_a_projection(self):
        note = next(f for f in self.plan["files"] if f["path"].endswith(".md"))
        self.assertIn("只读投影", note["content"])
        self.assertIn("PROGRESS.md", note["content"])

    def test_no_unrendered_placeholders(self):
        for item in self.plan["files"]:
            self.assertNotIn("{{", item["content"], item["path"])


class PerLessonSummaryTests(unittest.TestCase):
    """A note is THIS lesson's post-class summary, not a copy of the whole course."""

    def setUp(self):
        self.work = make_repo()
        plan = build_plan(self.work, COURSE, self.work / "out")
        self.notes = {Path(f["path"]).stem: f["content"] for f in plan["files"] if f["path"].endswith(".md")}

    def tearDown(self):
        shutil.rmtree(self.work.parent, ignore_errors=True)

    def test_each_note_contains_its_own_lesson_record(self):
        self.assertIn("完成条件概率与全概率公式", self.notes["lesson_001"])
        self.assertIn("讲过贝叶斯直觉", self.notes["lesson_002"])

    def test_notes_do_not_leak_other_lessons(self):
        self.assertNotIn("讲过贝叶斯直觉", self.notes["lesson_001"])
        self.assertNotIn("完成条件概率", self.notes["lesson_002"])

    def test_coverage_rows_are_only_those_citing_the_lesson(self):
        self.assertIn("贝叶斯公式", self.notes["lesson_001"])
        self.assertNotIn("概率与似然的区别", self.notes["lesson_001"])
        self.assertIn("概率与似然的区别", self.notes["lesson_002"])

    def test_next_entry_only_on_latest_lesson(self):
        self.assertNotIn("下次入口", self.notes["lesson_001"])
        self.assertIn("下次入口", self.notes["lesson_002"])
        self.assertIn("先验如何被似然更新", self.notes["lesson_002"])

    def test_older_note_tags_do_not_claim_later_states(self):
        self.assertIn("socratopia/coverage/verified", self.notes["lesson_001"])
        self.assertNotIn("needs_review", self.notes["lesson_001"])

    def test_no_invalid_tabs_wrapper(self):
        for stem, content in self.notes.items():
            self.assertNotIn("{% tabs", content, stem)
            self.assertNotIn("{% endtabs", content, stem)

    def test_lesson_without_record_body_is_not_invented(self):
        progress = PROGRESS.replace("完成条件概率与全概率公式。", "")
        work = make_repo(progress)
        try:
            plan = build_plan(work, COURSE, work / "out")
            note = next(f for f in plan["files"] if f["path"].endswith("lesson_001.md"))
            self.assertIn("未记录本课正文", note["content"])
        finally:
            shutil.rmtree(work.parent, ignore_errors=True)

    def test_template_syntax_in_progress_is_neutralized(self):
        """PROGRESS.md is data; Hexo would execute `{% include_code %}` / `{{ }}` in a note body."""
        evil = PROGRESS.replace("完成条件概率与全概率公式。",
                                "{% include_code ../../secret.txt %} {{ site.config }} {# c #}")
        work = make_repo(evil)
        try:
            plan = build_plan(work, COURSE, work / "out")
            for item in plan["files"]:
                if item["path"].endswith(".md"):
                    self.assertNotIn("{%", item["content"], item["path"])
                    self.assertNotIn("{{", item["content"], item["path"])
                    self.assertNotIn("{#", item["content"], item["path"])
        finally:
            shutil.rmtree(work.parent, ignore_errors=True)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.work = make_repo()

    def tearDown(self):
        shutil.rmtree(self.work.parent, ignore_errors=True)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.work / "scripts/export_stellar.py"), *args],
            cwd=self.work, text=True, capture_output=True,
        )

    def test_plan_is_dry_run(self):
        result = self.run_cli("plan", "--course", COURSE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.work / "DATA" / COURSE / "stellar").exists())
        self.assertIn("dry-run", result.stdout)

    def test_export_without_apply_writes_nothing(self):
        result = self.run_cli("export", "--course", COURSE)
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.work / "DATA" / COURSE / "stellar").exists())
        self.assertIn("--apply", result.stdout)

    def test_export_apply_writes_only_stellar_tree(self):
        before = (self.work / "DATA" / COURSE / "PROGRESS.md").read_text(encoding="utf-8")
        result = self.run_cli("export", "--course", COURSE, "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        out = self.work / "DATA" / COURSE / "stellar/source"
        self.assertTrue((out / f"_data/notebooks/{COURSE}.yml").exists())
        self.assertTrue((out / f"notes/{COURSE}/lesson_001.md").exists())
        marker = json.loads((out / ".socratopia-export.json").read_text(encoding="utf-8"))
        self.assertFalse(marker["authoritative"])
        self.assertTrue(marker["derived"])
        self.assertEqual((self.work / "DATA" / COURSE / "PROGRESS.md").read_text(encoding="utf-8"), before)

    def test_export_is_idempotent(self):
        self.run_cli("export", "--course", COURSE, "--apply")
        first = (self.work / "DATA" / COURSE / f"stellar/source/notes/{COURSE}/lesson_001.md").read_text(encoding="utf-8")
        self.run_cli("export", "--course", COURSE, "--apply")
        second = (self.work / "DATA" / COURSE / f"stellar/source/notes/{COURSE}/lesson_001.md").read_text(encoding="utf-8")
        self.assertEqual(first, second)

    def test_reexport_without_changes_rewrites_nothing(self):
        """Truly idempotent: unchanged lessons keep their file (and `updated`) untouched."""
        self.run_cli("export", "--course", COURSE, "--apply")
        note = self.work / "DATA" / COURSE / f"stellar/source/notes/{COURSE}/lesson_001.md"
        import os
        os.utime(note, (1_000_000_000, 1_000_000_000))
        result = self.run_cli("export", "--course", COURSE, "--apply")
        self.assertIn("未变化 3 个", result.stdout)  # notebook yml + 2 notes
        self.assertEqual(int(note.stat().st_mtime), 1_000_000_000)

    def test_changed_lesson_is_rewritten_but_keeps_first_export_date(self):
        import re
        self.run_cli("export", "--course", COURSE, "--apply")
        note = self.work / "DATA" / COURSE / f"stellar/source/notes/{COURSE}/lesson_001.md"
        first_date = re.search(r'^date: (.*)$', note.read_text(encoding="utf-8"), re.M).group(1)
        progress = self.work / "DATA" / COURSE / "PROGRESS.md"
        progress.write_text(progress.read_text(encoding="utf-8").replace(
            "完成条件概率与全概率公式。", "完成条件概率，并补了一个反例。"), encoding="utf-8")
        result = self.run_cli("export", "--course", COURSE, "--apply")
        text = note.read_text(encoding="utf-8")
        self.assertIn("补了一个反例", text)
        self.assertEqual(re.search(r'^date: (.*)$', text, re.M).group(1), first_date)
        self.assertIn("写入 1 个", result.stdout)

    def test_path_traversal_rejected(self):
        result = self.run_cli("plan", "--course", "../etc")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
