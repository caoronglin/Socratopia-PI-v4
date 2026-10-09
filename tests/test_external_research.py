"""Phase 6 · External Capabilities — gating, dry-run, SOURCES-only, no auto-network."""

import io
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import external_research as er  # noqa: E402
from scripts.lib import repository  # noqa: E402


class ExternalResearchTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socr-ext-"))
        self.course = "geo"
        os.environ.pop(er.ENV_FLAG, None)  # ensure disabled by default

    def tearDown(self):
        os.environ.pop(er.ENV_FLAG, None)

    def test_plan_is_offline_and_lists_protected_targets(self):
        p = er.plan(self.root, self.course, "找最新论文")
        self.assertFalse(p["network"])
        self.assertFalse(p["authorized"])
        self.assertIn("book.md", " ".join(p["will_not_touch"]))
        self.assertIn("PROGRESS.md", " ".join(p["will_not_touch"]))

    def test_register_writes_sources_only_not_book(self):
        src = self.root / "note.md"
        src.write_text("外部资料内容", encoding="utf-8")
        res = er.register(self.root, self.course, "https://example.com/x", "示例来源", file=str(src))
        self.assertIn("SOURCES/_external", res["registered"])
        meta = repository.read_json(Path(res["meta"]))
        self.assertFalse(meta["trusted"])
        # never touches book/PROGRESS
        self.assertFalse((repository.textbook_dir(self.root, self.course) / "book.md").exists())
        self.assertFalse((repository.course_dir(self.root, self.course) / "PROGRESS.md").exists())

    def test_fetch_refuses_without_authorize_flag(self):
        with self.assertRaises(SystemExit):
            er.fetch(self.root, self.course, "https://example.com", authorize=False)

    def test_fetch_refuses_when_env_disabled_even_with_flag(self):
        os.environ.pop(er.ENV_FLAG, None)
        with self.assertRaises(SystemExit):
            er.fetch(self.root, self.course, "https://example.com", authorize=True)

    def test_capability_present_is_not_authorization(self):
        # Even if a key exists in env, without the flag it is NOT authorized.
        os.environ["SILICONFLOW_API_KEY"] = "sk-testplaceholder"
        try:
            self.assertFalse(er.authorized())
            with self.assertRaises(SystemExit):
                er.fetch(self.root, self.course, "https://example.com", authorize=True)
        finally:
            os.environ.pop("SILICONFLOW_API_KEY", None)

    def test_authorized_fetch_uses_mocked_urlopen_and_registers(self):
        os.environ[er.ENV_FLAG] = "1"

        @contextmanager
        def fake_urlopen(url, timeout=0):
            buf = io.BytesIO("抓取到的内容".encode("utf-8"))

            class _Resp:
                def read(self, limit=-1):
                    return buf.getvalue()[:limit]
            yield _Resp()

        with mock.patch.object(er, "_open_https", fake_urlopen):
            res = er.fetch(self.root, self.course, "https://example.com/a", "A", authorize=True)
        self.assertIn("SOURCES/_external", res["registered"])
        self.assertTrue(res["sha256"])

    def test_course_traversal_rejected(self):
        with self.assertRaises(ValueError):
            er.plan(self.root, "../evil", "x")


class ExternalFetchSafetyTests(unittest.TestCase):
    def test_disallows_local_and_non_https_targets(self):
        for url in ("file:///etc/passwd", "http://example.com", "https://localhost/x",
                    "https://127.0.0.1/x", "https://192.168.0.1/x"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                er._validate_fetch_url(url)

    def test_same_title_different_source_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = er.register(root, "geo", "https://example.com/a", "相同名称")
            b = er.register(root, "geo", "https://example.com/b", "相同名称")
            self.assertNotEqual(a["registered"], b["registered"])
            self.assertTrue(Path(a["registered"]).exists())
            self.assertTrue(Path(b["registered"]).exists())


if __name__ == "__main__":
    unittest.main()
