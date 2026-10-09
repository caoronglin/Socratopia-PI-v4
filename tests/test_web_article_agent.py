"""Article ingestion and Cherry-Agent integration contract tests (offline)."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from scripts import web_article as article
from scripts import external_research as ext
from scripts.lib.repository import course_dir, read_json, textbook_dir

ARTICLE = b"""<!doctype html><html><head><title>Original Article</title>
<meta property="og:title" content="Course Article" /></head><body>
<nav>Skip this navigation menu and advertisements completely.</nav>
<main><article><h1>Genetic Inheritance</h1>
<p>Dominant traits refer to observable expression in a heterozygote, not how frequently alleles appear in a population.</p>
<br/><p>There can be rare dominant alleles, and allele frequencies depend on population processes.</p>
<img src="tracking.jpg"/>
<script>run_this_secret_command()</script>
</article></main><footer>Subscribe to this newsletter.</footer></body></html>"""


class ArticleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="socrat-article-")
        self.root = Path(self.tmp.name)
        self.course = "遗传学"
        self.url = "https://zhuanlan.zhihu.com/p/12345"
        os.environ.pop(ext.ENV_FLAG, None)

    def tearDown(self):
        os.environ.pop(ext.ENV_FLAG, None)
        self.tmp.cleanup()

    def test_extract_article_prefers_content_and_ignores_script(self):
        text, title, metadata = article.extract_article(ARTICLE, content_type="text/html; charset=utf-8")
        self.assertEqual(title, "Course Article")
        self.assertIn("Genetic Inheritance", text)
        self.assertIn("allele frequencies", text)
        self.assertNotIn("Skip this navigation", text)
        self.assertNotIn("Subscribe to this newsletter", text)
        self.assertNotIn("run_this_secret_command", text)
        self.assertEqual(metadata["extractor"], "html-article")

    def test_article_is_untrusted_and_course_scoped(self):
        result = article.import_article(self.root, self.course, self.url, ARTICLE)
        path = Path(result["source"])
        meta = read_json(Path(result["meta"]))
        self.assertTrue(path.is_file())
        self.assertFalse(meta["trusted"])
        self.assertEqual(meta["source_type"], "web-article")
        self.assertFalse(result["mastery_recorded"])
        self.assertTrue(path.is_relative_to(textbook_dir(self.root, self.course)))
        self.assertFalse((textbook_dir(self.root, self.course) / "book.md").exists())
        self.assertFalse((course_dir(self.root, self.course) / "PROGRESS.md").exists())

    def test_offline_paste_and_study_outline(self):
        text = "A hypothesis is a proposed explanation supported or tested with evidence. " * 2
        result = article.import_text(self.root, self.course, "https://example.com/article", text)
        outline = article.study_outline(self.root, self.course, result["url"])
        self.assertEqual(outline["source"], result["source"])
        self.assertEqual(len(outline["study_steps"]), 4)
        self.assertIn("不代表已授课", outline["note"])

    def test_refuses_short_empty_or_nontext(self):
        for raw, content_type in ((b"", "text/plain"), (b"Hi", "text/plain"),
                                  (b"some binary bytes long enough" * 8, "image/jpeg")):
            with self.subTest(raw=raw[:10]), self.assertRaises(ValueError):
                article.extract_article(raw, content_type=content_type)

    def test_refuses_sensitive_urls_and_non_https(self):
        for url in ("http://example.org/x", "https://localhost/x",
                    "https://127.0.0.1/x", "https://example.org:8443/a",
                    "https://example.org/a?token=secret",
                    "https://example.org/a?api_key=abc",
                    "https://user:pass@example.org/a"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                article.check_url(url)
        self.assertEqual(article.check_url("https://example.org/path#part"), "https://example.org/path")

    def test_rejects_course_path_traversal(self):
        with self.assertRaises(ValueError):
            article.import_text(self.root, "../escape", self.url, "Safe text is long enough for import " * 3)

    def test_fetch_refuses_network_without_two_gates(self):
        with mock.patch.object(ext, "_open_https", side_effect=AssertionError("unexpected network")):
            with self.assertRaises(PermissionError):
                article.fetch_article(self.root, self.course, self.url, authorize=False)
            with self.assertRaises(PermissionError):
                article.fetch_article(self.root, self.course, self.url, authorize=True)
        self.assertFalse((textbook_dir(self.root, self.course) / "book.md").exists())

    def test_authorized_fetch_registers_without_touching_progress(self):
        os.environ[ext.ENV_FLAG] = "1"

        @contextmanager
        def fake_fetch(url, timeout=20):
            class Response:
                headers = {"Content-Type": "text/html"}
                def read(self, size=-1):
                    return ARTICLE[:size]
            yield Response()

        with mock.patch.object(ext, "_open_https", fake_fetch):
            result = article.fetch_article(self.root, self.course, self.url, authorize=True)
        self.assertTrue(Path(result["source"]).exists())
        self.assertFalse((course_dir(self.root, self.course) / "PROGRESS.md").exists())

    def test_title_injection_is_not_multiline(self):
        result = article.import_article(self.root, self.course, self.url, ARTICLE,
                                        title="Correct title\\n# forged heading")
        first_line = Path(result["source"]).read_text(encoding="utf-8").splitlines()[0]
        self.assertNotIn("\\n", first_line)
        self.assertTrue(first_line.startswith("# Correct title"))


class CherryAgentContracts(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def test_agent_is_not_an_mcp_server(self):
        guide = (self.ROOT / "integrations/cherry-studio/AGENT_PROMPT.md").read_text(encoding="utf-8")
        for text in ("Cherry Studio", "cherry-tool-guide", "web_article.py", "PROGRESS.md",
                     "trusted:false", "不是 MCP Server"):
            self.assertIn(text, guide)
        self.assertNotIn("mcp_server.start()", guide)

    def test_cherry_guide_has_permissions_and_host_tool_fallback(self):
        docs = (self.ROOT / "docs/CHERRY_STUDIO_AGENT.md").read_text(encoding="utf-8")
        for term in ("Pi", "Work", "web_fetch", "kb_search", "to_markdown",
                     "权限", "AGENT_PROMPT.md", "不自动"):
            self.assertIn(term, docs)

    def test_learning_route_and_prompt_catalog_are_synced(self):
        skill = (self.ROOT / ".pi/skills/socratopia-learning/SKILL.md").read_text(encoding="utf-8")
        catalog = (self.ROOT / "docs/PROMPTS.md").read_text(encoding="utf-8")
        route = "| 网页文章、知乎/博客、URL 学习（用户提供链接或正文） | `references/web-article.md` + `references/external-research.md` |"
        self.assertIn(route, skill)
        self.assertIn(route, catalog)


if __name__ == "__main__":
    unittest.main()
