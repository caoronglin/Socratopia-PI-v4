"""plan.md §13: duplicate-rule, stale-projection (WARN) and cross-course symlink (ERROR)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib import duplicates  # noqa: E402

SENTENCE = "所有导师共用的卡点处理规则必须只在一个文件里定义一次不能散落"


class DuplicateRuleTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socrat-dup-"))
        (self.root / ".pi/skills/a/references").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def put(self, rel: str, body: str) -> None:
        (self.root / rel).write_text(body, encoding="utf-8")

    def test_repo_is_clean(self):
        self.assertEqual(duplicates.duplicate_rule_warnings(ROOT), [])

    def test_verbatim_sentence_in_two_files_warns(self):
        self.put(".pi/skills/a/references/x.md", f"# X\n\n- {SENTENCE}。\n")
        self.put(".pi/skills/a/references/y.md", f"# Y\n\n{SENTENCE}；其他。\n")
        warnings = duplicates.duplicate_rule_warnings(self.root)
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("x.md", warnings[0])
        self.assertIn("y.md", warnings[0])

    def test_same_sentence_twice_in_one_file_is_fine(self):
        self.put(".pi/skills/a/references/x.md", f"{SENTENCE}。\n{SENTENCE}。\n")
        self.assertEqual(duplicates.duplicate_rule_warnings(self.root), [])

    def test_short_generic_sentences_ignored(self):
        self.put(".pi/skills/a/references/x.md", "先读再改。\n")
        self.put(".pi/skills/a/references/y.md", "先读再改。\n")
        self.assertEqual(duplicates.duplicate_rule_warnings(self.root), [])

    def test_code_fences_tables_and_frontmatter_ignored(self):
        body = f"---\ndescription: {SENTENCE}\n---\n\n```\n{SENTENCE}\n```\n| {SENTENCE} | x |\n"
        self.put(".pi/skills/a/references/x.md", body)
        self.put(".pi/skills/a/references/y.md", body)
        self.assertEqual(duplicates.duplicate_rule_warnings(self.root), [])


class StaleProjectionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socrat-stale-"))
        self.course = self.root / "DATA/课"
        (self.course / "ontology").mkdir(parents=True)
        (self.course / "runtime").mkdir()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def touch(self, rel: str, when: float) -> None:
        path = self.course / rel
        path.write_text("x", encoding="utf-8")
        os.utime(path, (when, when))

    def test_fresh_projection_is_fine(self):
        now = time.time()
        self.touch("ontology/graph.jsonl", now - 100)
        self.touch("ontology/projection.json", now)
        self.assertEqual(duplicates.stale_projection_warnings(self.root), [])

    def test_stale_ontology_projection_warns(self):
        now = time.time()
        self.touch("ontology/projection.json", now - 100)
        self.touch("ontology/graph.jsonl", now)
        warnings = duplicates.stale_projection_warnings(self.root)
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("ontology.py compact", warnings[0])

    def test_sibling_writes_within_tolerance_are_not_stale(self):
        now = time.time()
        self.touch("ontology/projection.json", now)
        self.touch("ontology/graph.jsonl", now + 0.5)
        self.assertEqual(duplicates.stale_projection_warnings(self.root), [])

    def test_missing_optional_projection_is_not_stale(self):
        self.touch("runtime/course_state.json", time.time())
        self.assertEqual(duplicates.stale_projection_warnings(self.root), [])

    def test_stale_state_markdown_warns(self):
        now = time.time()
        self.touch("runtime/course_state.md", now - 100)
        self.touch("runtime/course_state.json", now)
        self.assertTrue(any("course_state.md" in w for w in duplicates.stale_projection_warnings(self.root)))


class StaleCacheTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socrat-cache-"))
        self.index = self.root / "DATA/课/cache/vector/index.json"
        self.book = self.root / "TEXTBOOK/课/book.md"
        self.index.parent.mkdir(parents=True)
        self.book.parent.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def stamp(self, index_age: float, book_age: float) -> None:
        now = time.time()
        for path, age in ((self.index, index_age), (self.book, book_age)):
            path.write_text("x", encoding="utf-8")
            os.utime(path, (now - age, now - age))

    def test_index_older_than_book_warns(self):
        self.stamp(index_age=100, book_age=0)
        warnings = duplicates.stale_cache_warnings(self.root)
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("vector_index.py build", warnings[0])

    def test_fresh_index_is_fine(self):
        self.stamp(index_age=0, book_age=100)
        self.assertEqual(duplicates.stale_cache_warnings(self.root), [])

    def test_missing_index_is_not_reported(self):
        self.book.write_text("x", encoding="utf-8")
        self.assertEqual(duplicates.stale_cache_warnings(self.root), [])


class SymlinkIsolationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socrat-link-"))
        for name in ("甲", "乙"):
            (self.root / "DATA" / name).mkdir(parents=True)
            (self.root / "DATA" / name / "PROGRESS.md").write_text(name, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def link(self, src: Path, dst: Path) -> None:
        try:
            os.symlink(src, dst)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")

    def test_clean_tree_has_no_errors(self):
        self.assertEqual(duplicates.cross_course_symlink_errors(self.root), [])

    def test_symlink_to_other_course_is_error(self):
        self.link(self.root / "DATA/乙/PROGRESS.md", self.root / "DATA/甲/leak.md")
        errors = duplicates.cross_course_symlink_errors(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("cross-course symlink", errors[0])

    def test_symlink_within_same_course_is_fine(self):
        self.link(self.root / "DATA/甲/PROGRESS.md", self.root / "DATA/甲/alias.md")
        self.assertEqual(duplicates.cross_course_symlink_errors(self.root), [])

    def test_course_directory_symlink_is_error(self):
        self.link(self.root / "DATA/乙", self.root / "DATA/丙")
        self.assertTrue(any("course directory is a symlink" in e
                            for e in duplicates.cross_course_symlink_errors(self.root)))


class CheckScriptTests(unittest.TestCase):
    def test_check_script_passes_on_clean_repo(self):
        """check.py (CI entrypoint) must be green on a clean tree, including --strict."""
        work = Path(tempfile.mkdtemp(prefix="socrat-check-")) / "repo"
        try:
            shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(
                ".git", "__pycache__", "DATA", "TEXTBOOK", ".pytest_cache"))
            # Avoid recursion: run only doctor-level behaviour by stubbing the test step.
            result = subprocess.run(
                [sys.executable, "-c",
                 "import sys,subprocess;sys.path.insert(0,'scripts');import check;"
                 "check._run=lambda l,c:subprocess.run(c,cwd=check.ROOT,text=True,capture_output=True) "
                 "if l=='doctor' else subprocess.CompletedProcess(c,0,'','');"
                 "sys.exit(check.main(['--strict']))"],
                cwd=work, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK", result.stdout)
        finally:
            shutil.rmtree(work.parent, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
