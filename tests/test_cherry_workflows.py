"""Regression coverage for Cherry Pi integration and source-grounded article flows."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from scripts import cherry_preflight, web_article
from scripts.lib.repository import textbook_dir


class CherryPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="socrat-cherry-check-")
        self.root = Path(self.tmp.name)
        for path in cherry_preflight.REQUIRED:
            dest = self.root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("fixture", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_has_no_host_capability_guess_and_does_not_write(self):
        before = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*"))
        report = cherry_preflight.inspect(self.root)
        after = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*"))
        self.assertTrue(report["ready_to_configure_agent"])
        self.assertIsNone(report["ready_to_teach"])
        self.assertTrue(all("unverified" in status for status in report["cherry_tools"].values()))
        self.assertEqual(before, after)

    def test_warns_on_missing_runtime_in_selected_course_only(self):
        report = cherry_preflight.inspect(self.root, "遗传学")
        self.assertEqual(report["course"]["name"], "遗传学")
        self.assertFalse(report["course"]["runtime_exists"])
        self.assertIn("runtime", " ".join(report["warnings"]))
        self.assertFalse((self.root / "DATA/遗传学").exists())

    def test_missing_project_file_blocks_ready(self):
        (self.root / "AGENTS.md").unlink()
        report = cherry_preflight.inspect(self.root)
        self.assertFalse(report["ready_to_configure_agent"])
        self.assertIn("AGENTS.md", report["missing"])

    def test_traversal_never_reads_other_course(self):
        for course in ("../other", "a/b", ".."):
            with self.subTest(course=course), self.assertRaises(ValueError):
                cherry_preflight.inspect(self.root, course)


class ArticleLearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="socrat-article-flow-")
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_gbk_article_with_heading_and_extractable_excerpts(self):
        raw = ('<html><head><meta charset="gbk"><title>农业科学</title></head>'
               '<body><article><h2>实验设计</h2>'
               '<p>我们先设置不同的实验处理，然后收集数据进行比较与统计检验。</p>'
               '<p>另一段内容用于说明样本重复及数据分析过程，应保留其完整出处。</p>'
               '</article></body></html>').encode("gbk")
        result = web_article.import_article(
            self.root, "遗传学", "https://example.org/articles/gbk", raw,
            content_type="text/html")
        self.assertEqual(result["title"], "农业科学")
        outline = web_article.study_outline(self.root, "遗传学", result["url"])
        self.assertIn("实验设计", outline["headings"])
        self.assertTrue(any("实验处理" in x for x in outline["excerpts"]))
        self.assertTrue(outline["sha256"])
        meta = json.loads(Path(result["meta"]).read_text(encoding="utf-8"))
        self.assertEqual(meta["source_encoding"], "gb18030")
        self.assertFalse(meta["trusted"])
        self.assertFalse((textbook_dir(self.root, "遗传学") / "book.md").exists())

    def test_declared_bad_encoding_and_binary_rejected(self):
        text = "这是测试文本" * 8
        with self.assertRaises(ValueError):
            web_article.extract_article(text.encode(), content_type="text/plain; charset=unsupported")
        with self.assertRaises(ValueError):
            web_article.extract_article((b"hello\x00" + b"text" * 20), content_type="text/plain")

    def test_stdin_import_is_bounded_and_does_not_run_a_shell(self):
        article = ("文档段落含有真实资料信息。 " * 9).encode("utf-8")
        stdin = mock.Mock(buffer=io.BytesIO(article))
        argv = ["web_article.py", "import", "--course", "生物学",
                "--url", "https://example.org/a", "--file", "-"]
        out = io.StringIO()
        with (mock.patch.object(web_article, "ROOT", self.root),
              mock.patch("sys.argv", argv),
              mock.patch("sys.stdin", stdin),
              redirect_stdout(out)):
            self.assertEqual(web_article.main(), 0)
        result = json.loads(out.getvalue())
        self.assertTrue(Path(result["source"]).is_file())
        self.assertFalse((self.root / "DATA/生物学/PROGRESS.md").exists())

    def test_headings_are_from_content_not_metadata_header(self):
        text = "文章原始内容有三个层次，需要对每一项证据分别核验。" * 4
        result = web_article.import_text(self.root, "A", "https://example.com/a", text)
        outline = web_article.study_outline(self.root, "A", result["url"])
        self.assertEqual(outline["headings"], [])
        self.assertEqual(len(outline["excerpts"]), 1)
        self.assertIn("文章原始内容", outline["excerpts"][0])
        self.assertNotIn("source_url", outline["excerpts"][0])


if __name__ == "__main__":
    unittest.main()
