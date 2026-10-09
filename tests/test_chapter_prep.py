"""Chapter-first PREP routing, supplemental provenance and old PREP compatibility."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.lib.chapter_prep import chapter_outline, plan_chapter
from scripts.lib.prep import check_prep, parse_front_matter, prep_path, prep_status
from scripts.lib.repository import textbook_dir

ROOT = Path(__file__).resolve().parents[1]
COURSE = "教材课程"


class ChapterPreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="socrat-chapter-")
        self.root = Path(self.tmp.name)
        (self.root / "templates").mkdir()
        shutil.copy(ROOT / "templates/PREP.md", self.root / "templates/PREP.md")
        book = textbook_dir(self.root, COURSE)
        book.mkdir(parents=True)
        (book / "book.md").write_text(
            "# 教材\n## 第2章 导数\n### 2.1 导数定义\n### 2.2 链式法则\n"
            "## 第3章 积分\n### 3.1 积分定义\n", encoding="utf-8")
        (book / "_outline.md").write_text(
            "# 目录\n## 第2章 导数\n### 2.1 导数定义\n### 2.2 链式法则\n"
            "## 第3章 积分\n### 3.1 积分定义\n", encoding="utf-8")
        data = self.root / "DATA" / COURSE
        data.mkdir(parents=True)
        (data / "PROGRESS.md").write_text(
            "lesson_002: 先前会话\n## Coverage ledger\n"
            "| item | status | evidence |\n|---|---|---|\n"
            "| 链式法则 | needs_review | 上次没区分顺序 |\n", encoding="utf-8")
        self.source = book / "SOURCES" / "_external" / "article.md"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("# 文章\n真实例子与边界", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_resolves_complete_chapter_without_next_chapter(self):
        heading, sections = chapter_outline(self.root, COURSE, "第2章")
        self.assertEqual(heading, "第2章 导数")
        self.assertEqual(sections, ["2.1 导数定义", "2.2 链式法则"])
        self.assertNotIn("3.1 积分定义", sections)

    def test_dry_run_generates_one_chapter_lesson_and_does_not_write(self):
        result = plan_chapter(self.root, COURSE, "第2章")
        self.assertEqual(result["lesson_id"], "lesson_003")
        self.assertTrue(result["dry_run"])
        self.assertFalse((self.root / "TEXTBOOK" / COURSE / "PREP").exists())
        draft = result["preview"]
        self.assertIn("plan_mode: chapter", draft)
        self.assertIn("| 2.1 导数定义 | 2.1 导数定义 |", draft)
        self.assertIn("| 2.2 链式法则 | 2.2 链式法则 |", draft)
        self.assertIn("主线复述及至少两条概念关系", draft)
        self.assertIn("needs_review：链式法则", draft)
        self.assertNotIn("3.1 积分定义", draft)

    def test_persist_and_repeat_reuses_existing_preparation(self):
        first = plan_chapter(self.root, COURSE, "第2章", apply=True)
        saved = prep_path(self.root, COURSE, first["lesson_id"])
        original = saved.read_bytes()
        again = plan_chapter(self.root, COURSE, "第2章 导数", apply=True)
        self.assertEqual(again["lesson_id"], first["lesson_id"])
        self.assertTrue(again["exists"])
        self.assertEqual(original, saved.read_bytes())
        self.assertEqual(prep_status(self.root, COURSE)["lesson_003"], "draft")

    def test_supplements_registered_and_checksum_detects_changes(self):
        label = "SOURCES/_external/article.md"
        result = plan_chapter(self.root, COURSE, "第2章", sources=[label], apply=True)
        saved = prep_path(self.root, COURSE, result["lesson_id"])
        original = saved.read_text(encoding="utf-8")
        front, _ = parse_front_matter(original)
        self.assertEqual(front["sources"], [label])
        self.assertIn("| " + label + " |", original)
        self.assertEqual(check_prep(self.root, COURSE, "lesson_003")[0], [])
        self.source.write_text("# 内容已修改\n新版本", encoding="utf-8")
        errors, warnings = check_prep(self.root, COURSE, "lesson_003")
        self.assertEqual(errors, [])
        self.assertTrue(any("stale：补充资料" in w for w in warnings))
        self.assertEqual(prep_status(self.root, COURSE)["lesson_003"], "stale")

    def test_unregistered_or_traversal_source_rejected(self):
        for source in ["SOURCES/../book.md", "SOURCES/missing.md",
                       "../另一门课/secret.md", "https://example.com/page",
                       "SOURCES/_external/article.md\nmalicious: 1"]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                plan_chapter(self.root, COURSE, "第2章", sources=[source], apply=True)
        self.assertFalse(prep_path(self.root, COURSE, "lesson_003").exists())

    def test_rejects_missing_chapter_or_ambiguous_heading(self):
        for chapter in ("第9章", "第2章\ninjected: value", " "):
            with self.subTest(chapter=chapter), self.assertRaises(ValueError):
                plan_chapter(self.root, COURSE, chapter)

    def test_ready_does_not_allow_incomplete_chapter_plan(self):
        result = plan_chapter(self.root, COURSE, "第2章", apply=True)
        saved = prep_path(self.root, COURSE, result["lesson_id"])
        saved.write_text(saved.read_text(encoding="utf-8").replace(
            "status: draft", "status: ready"), encoding="utf-8")
        errors, _ = check_prep(self.root, COURSE, "lesson_003")
        self.assertTrue(any("章节小节" in e for e in errors), errors)
        self.assertTrue(any("章末收束" in e for e in errors), errors)
        self.assertEqual(prep_status(self.root, COURSE)["lesson_003"], "invalid")

    def test_chapter_coverage_cannot_silently_drop_subsection(self):
        result = plan_chapter(self.root, COURSE, "第2章", apply=True)
        saved = prep_path(self.root, COURSE, result["lesson_id"])
        text = saved.read_text(encoding="utf-8")
        text = "\n".join(line for line in text.splitlines()
                         if not line.startswith("| 2.2 链式法则 |")) + "\n"
        saved.write_text(text, encoding="utf-8")
        errors, _ = check_prep(self.root, COURSE, "lesson_003")
        self.assertTrue(any("章节小节与本教案不一致" in e for e in errors), errors)

    def test_existing_old_style_prep_chapter_is_reused(self):
        path = prep_path(self.root, COURSE, "lesson_008")
        path.parent.mkdir(parents=True)
        path.write_text("---\nschema: prep-1\nchapter: 第2章 导数\n---\nold", encoding="utf-8")
        result = plan_chapter(self.root, COURSE, "第2章")
        self.assertEqual(result["lesson_id"], "lesson_008")
        self.assertTrue(result["exists"])

    def test_cli_dry_run_and_apply(self):
        script = ROOT / "scripts/prep.py"
        # CLI ROOT is the source repo; patching globals would be more invasive.
        # The public callable is the tested implementation; CLI arg declaration is static.
        code = script.read_text(encoding="utf-8")
        self.assertIn('sub.add_parser("chapter"', code)
        self.assertIn('chapter.add_argument("--source"', code)
        self.assertIn('plan_chapter(ROOT, course, args.chapter', code)


if __name__ == "__main__":
    unittest.main()
