"""Phase 5 · Local Search / Ingestion — positive hits + network-free & isolation guards."""

import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import local_search as ls  # noqa: E402
from scripts import vector_index as vi  # noqa: E402
from scripts import ontology as onto  # noqa: E402
from scripts.lib import repository  # noqa: E402


class LocalSearchTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socr-ls-"))
        self.course = "phys"
        book = repository.textbook_dir(self.root, self.course)
        book.mkdir(parents=True, exist_ok=True)
        (book / "book.md").write_text(
            "# 第1章 力学\n## 牛顿第二定律\n力等于质量乘加速度，F=ma。\n## 动量\n动量守恒在孤立系统中成立。\n",
            encoding="utf-8",
        )
        (book / "_outline.md").write_text("## 第1章 力学\n- 牛顿第二定律\n", encoding="utf-8")
        (book / "SOURCES").mkdir(exist_ok=True)
        (book / "SOURCES" / "note.md").write_text("补充：动量守恒的边界条件。\n", encoding="utf-8")

    def test_book_section_hit(self):
        hits = ls.local_search(self.root, self.course, "加速度")
        self.assertTrue(any(h["anchor"] == "牛顿第二定律" for h in hits))

    def test_sources_hit(self):
        hits = ls.local_search(self.root, self.course, "边界", scope="sources")
        self.assertTrue(any("note.md" in h["source"] for h in hits))

    def test_anchor_hit(self):
        hits = ls.local_search(self.root, self.course, "力学", scope="anchors")
        self.assertTrue(hits)

    def test_empty_query_returns_nothing(self):
        self.assertEqual(ls.local_search(self.root, self.course, "   "), [])

    def test_course_traversal_rejected(self):
        with self.assertRaises(ValueError):
            ls.local_search(self.root, "../evil", "x")

    def test_ontology_passthrough(self):
        onto.node_upsert(self.root, self.course, "kp_fma", "KnowledgePoint", {"label": "牛顿第二定律"})
        hits = ls.local_search(self.root, self.course, "牛顿", scope="ontology")
        self.assertTrue(any(h["source"] == "ontology" for h in hits))


class VectorIndexTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socr-vec-"))
        self.course = "chem"
        book = repository.textbook_dir(self.root, self.course)
        book.mkdir(parents=True, exist_ok=True)
        (book / "book.md").write_text("# 第1章 原子\n## 电子云\n电子云描述电子出现概率。\n", encoding="utf-8")

    def test_build_search_status_roundtrip(self):
        info = vi.build(self.root, self.course)
        self.assertGreaterEqual(info["docs"], 1)
        st = vi.status(self.root, self.course)
        self.assertTrue(st["available"])
        self.assertFalse(vi.search(self.root, self.course, "电子")["available"] is False)
        res = vi.search(self.root, self.course, "电子云")
        self.assertTrue(res["hits"])
        self.assertFalse(res["network"])

    def test_search_before_build_unavailable(self):
        res = vi.search(self.root, self.course, "电子")
        self.assertFalse(res["available"])

    def test_index_is_derived_non_authoritative(self):
        vi.build(self.root, self.course)
        idx = repository.read_json(vi.index_path(self.root, self.course))
        self.assertTrue(idx["derived"])
        self.assertFalse(idx["authoritative"])
        self.assertFalse(idx["network"])

    def test_index_lives_under_cache(self):
        vi.build(self.root, self.course)
        self.assertIn("cache/vector", str(vi.index_path(self.root, self.course)))


class NoNetworkGuardTests(unittest.TestCase):
    def test_phase5_scripts_have_no_network_imports(self):
        for name in ("local_search.py", "vector_index.py"):
            src = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            for bad in ("import socket", "import requests", "urllib", "http.client", "httpx"):
                self.assertNotIn(bad, src, f"{name} 含网络依赖：{bad}")


if __name__ == "__main__":
    unittest.main()
