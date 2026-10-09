"""Memory layers: deterministic hot index, evidence-backed summaries, compression invariants."""

from __future__ import annotations

import json
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

from scripts.lib import memory as mem  # noqa: E402

COURSE = "夹具课程"

PROGRESS = """# Course Progress

## Current checkpoint

- lesson_id: lesson_002
- chapter: 第2章 导数
- tutor: TUTOR_E
- next_entry: 从链式法则的复合顺序进入

## Coverage ledger

| item | status | evidence |
|---|---|---|
| 导数定义 | verified | lesson_001：能独立解释 |
| 链式法则 | needs_review | lesson_002：复合顺序说反，提示后纠正 |
| 隐函数求导 | unseen | - |

## Lesson records

### lesson_001 导数定义

完成，能独立解释。

### lesson_002 链式法则

学习者把复合顺序说反，提示后纠正，未复测。
"""

RETEACH = """# 补讲队列

| id | 章节 | 类型 | 优先级 | 状态 | 差异证据 | 原因 | 验证 |
|---|---|---|---|---|---|---|---|
| RQ-1 | 第2章 | 例题 | P1 | pending | 链式法则例题 | 原因 | 验证 |
| RQ-2 | 第1章 | 图表 | P1 | understood | 已完成 | x | y |
"""


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="socrat-mem-"))
    shutil.copytree(ROOT / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    data = root / "DATA" / COURSE
    (data / "CONTEXT").mkdir(parents=True)
    (data / "runtime").mkdir()
    (data / "PROGRESS.md").write_text(PROGRESS, encoding="utf-8")
    (data / "CONTEXT/RETEACH_QUEUE.md").write_text(RETEACH, encoding="utf-8")
    (data / "runtime/course_state.json").write_text(json.dumps({
        "schema_version": 1, "course": COURSE, "phase": "ready", "lesson_id": "lesson_002",
        "readiness": {"catalog": "ok", "prep": "ok", "runtime": "ok", "reteach": "pending"},
        "blockers": ["pending_reteach"]}, ensure_ascii=False), encoding="utf-8")
    return root


class HotLayerTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.index = self.root / "DATA" / COURSE / "CONTEXT/CONTEXT_INDEX.md"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def build(self, apply=True):
        return mem.build_hot(self.root, COURSE, apply=apply)

    def test_hot_contains_every_required_fact(self):
        self.build()
        text = self.index.read_text(encoding="utf-8")
        for needle in ("lesson_002", "第2章 导数", "TUTOR_E", "链式法则", "复合顺序说反", "RQ-1",
                       "pending_reteach", "从链式法则的复合顺序进入", "隐函数求导"):
            self.assertIn(needle, text)

    def test_resolved_reteach_and_verified_rows_are_not_listed(self):
        self.build()
        text = self.index.read_text(encoding="utf-8")
        self.assertNotIn("RQ-2", text)
        self.assertNotIn("导数定义 —", text)

    def test_dry_run_writes_nothing(self):
        result = self.build(apply=False)
        self.assertEqual(result["outcome"], "would_write")
        self.assertFalse(self.index.exists())

    def test_rebuild_is_idempotent_and_has_no_timestamp(self):
        self.assertEqual(self.build()["outcome"], "written")
        first = self.index.read_text(encoding="utf-8")
        mtime = self.index.stat().st_mtime_ns
        self.assertEqual(self.build()["outcome"], "unchanged")
        self.assertEqual(self.index.read_text(encoding="utf-8"), first)
        self.assertEqual(self.index.stat().st_mtime_ns, mtime)
        self.assertNotRegex(first, r"\d{4}-\d{2}-\d{2}T")

    def test_handwritten_notes_outside_markers_survive_rebuild(self):
        self.index.write_text("# Hot Context\n\n我的手写备注：别忘了讲反例。\n", encoding="utf-8")
        self.build()
        PROGRESS_PATH = self.root / "DATA" / COURSE / "PROGRESS.md"
        PROGRESS_PATH.write_text(PROGRESS.replace("TUTOR_E", "TUTOR_A"), encoding="utf-8")
        self.build()
        text = self.index.read_text(encoding="utf-8")
        self.assertIn("我的手写备注：别忘了讲反例。", text)
        self.assertIn("TUTOR_A", text)
        self.assertNotIn("TUTOR_E", text)
        self.assertEqual(text.count(mem.HOT_BEGIN), 1)

    def test_within_character_budget(self):
        result = self.build()
        self.assertFalse(result["over_budget"], result)

    def test_no_facts_means_no_invention(self):
        shutil.rmtree(self.root / "DATA" / COURSE)
        (self.root / "DATA" / COURSE).mkdir()
        self.build()
        text = self.index.read_text(encoding="utf-8")
        self.assertIn("未定位", text)
        self.assertIn("无账本记录", text)
        self.assertNotIn("needs_review（", text)

    def test_other_course_is_never_read(self):
        other = self.root / "DATA" / "另一门课"
        other.mkdir(parents=True)
        (other / "PROGRESS.md").write_text(PROGRESS.replace("链式法则", "机密条目"), encoding="utf-8")
        self.build()
        self.assertNotIn("机密条目", self.index.read_text(encoding="utf-8"))

    def test_never_modifies_progress(self):
        before = (self.root / "DATA" / COURSE / "PROGRESS.md").read_bytes()
        self.build()
        mem.build_summaries(self.root, COURSE, apply=True)
        self.assertEqual((self.root / "DATA" / COURSE / "PROGRESS.md").read_bytes(), before)


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.path = self.root / "DATA" / COURSE / "CONTEXT/LESSON_SUMMARIES.md"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_each_lesson_gets_its_own_evidence_backed_block(self):
        mem.build_summaries(self.root, COURSE, apply=True)
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("## lesson_001 · 导数定义", text)
        self.assertIn("## lesson_002 · 链式法则", text)
        block2 = text.split("<!-- lesson:lesson_002:begin -->")[1].split("<!-- lesson:lesson_002:end -->")[0]
        self.assertIn("链式法则 [needs_review]", block2)
        self.assertIn("未解决：链式法则", block2)
        block1 = text.split("<!-- lesson:lesson_001:begin -->")[1].split("<!-- lesson:lesson_001:end -->")[0]
        self.assertNotIn("链式法则", block1)

    def test_lesson_without_cited_evidence_says_so(self):
        progress = self.root / "DATA" / COURSE / "PROGRESS.md"
        progress.write_text(PROGRESS.replace("lesson_001：能独立解释", "口头确认"), encoding="utf-8")
        mem.build_summaries(self.root, COURSE, "lesson_001", apply=True)
        self.assertIn("没有引用本课的行", self.path.read_text(encoding="utf-8"))

    def test_single_lesson_only_touches_that_block(self):
        mem.build_summaries(self.root, COURSE, apply=True)
        text = self.path.read_text(encoding="utf-8").replace("完成，能独立解释", "手改过的旧文字")
        self.path.write_text(text, encoding="utf-8")
        mem.build_summaries(self.root, COURSE, "lesson_002", apply=True)
        self.assertIn("手改过的旧文字", self.path.read_text(encoding="utf-8"))

    def test_unknown_lesson_is_refused_not_invented(self):
        with self.assertRaises(ValueError):
            mem.build_summaries(self.root, COURSE, "lesson_099", apply=True)
        self.assertFalse(self.path.exists())

    def test_bad_lesson_id_refused(self):
        with self.assertRaises(ValueError):
            mem.build_summaries(self.root, COURSE, "../x", apply=True)

    def test_rebuild_idempotent(self):
        mem.build_summaries(self.root, COURSE, apply=True)
        self.assertEqual(mem.build_summaries(self.root, COURSE, apply=True)["outcome"], "unchanged")

    def test_long_records_are_clipped_not_dropped(self):
        progress = self.root / "DATA" / COURSE / "PROGRESS.md"
        progress.write_text(PROGRESS.replace("完成，能独立解释。", "很长的记录" * 200), encoding="utf-8")
        mem.build_summaries(self.root, COURSE, "lesson_001", apply=True)
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("很长的记录", text)
        self.assertIn("…", text)
        self.assertLess(len(text), 1200)


class InvariantTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        mem.build_hot(self.root, COURSE, apply=True)
        mem.build_summaries(self.root, COURSE, apply=True)
        self.index = self.root / "DATA" / COURSE / "CONTEXT/CONTEXT_INDEX.md"
        future = time.time() + 5
        os.utime(self.index, (future, future))  # keep the hot layer clearly newer than PROGRESS

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_fresh_build_passes(self):
        errors, warnings = mem.check(self.root, COURSE)
        self.assertEqual((errors, warnings), ([], []))

    def test_dropping_needs_review_is_an_error(self):
        self.index.write_text(self.index.read_text(encoding="utf-8").replace("链式法则", "某个点"), encoding="utf-8")
        errors, _ = mem.check(self.root, COURSE)
        self.assertTrue(any("needs_review「链式法则」" in e for e in errors), errors)

    def test_dropping_pending_reteach_is_an_error(self):
        self.index.write_text(self.index.read_text(encoding="utf-8").replace("RQ-1", "RQ-X"), encoding="utf-8")
        errors, _ = mem.check(self.root, COURSE)
        self.assertTrue(any("RQ-1" in e for e in errors), errors)

    def test_losing_next_entry_is_an_error(self):
        self.index.write_text(self.index.read_text(encoding="utf-8").replace("从链式法则的复合顺序进入", "继续"), encoding="utf-8")
        errors, _ = mem.check(self.root, COURSE)
        self.assertTrue(any("next_entry" in e for e in errors), errors)

    def test_oversized_hot_layer_warns(self):
        text = self.index.read_text(encoding="utf-8").replace(mem.HOT_END, "填充" * 1700 + "\n" + mem.HOT_END)
        self.index.write_text(text, encoding="utf-8")
        _, warnings = mem.check(self.root, COURSE)
        self.assertTrue(any("超过约定上限" in w for w in warnings), warnings)

    def test_stale_hot_layer_warns(self):
        past = time.time() - 100
        os.utime(self.index, (past, past))
        _, warnings = mem.check(self.root, COURSE)
        self.assertTrue(any("stale" in w for w in warnings), warnings)

    def test_missing_hot_layer_is_warning_not_error(self):
        self.index.unlink()
        errors, warnings = mem.check(self.root, COURSE)
        self.assertEqual(errors, [])
        self.assertTrue(warnings)

    def test_missing_summary_warns(self):
        (self.root / "DATA" / COURSE / "CONTEXT/LESSON_SUMMARIES.md").write_text("# Lesson Summaries\n", encoding="utf-8")
        _, warnings = mem.check(self.root, COURSE)
        self.assertTrue(any("尚无温层摘要" in w for w in warnings), warnings)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(self.root / "scripts/memory.py"), *args],
                              cwd=self.root, capture_output=True, text=True)

    def test_build_requires_apply_to_write(self):
        self.assertEqual(self.cli("build", "--course", COURSE).returncode, 0)
        self.assertFalse((self.root / "DATA" / COURSE / "CONTEXT/CONTEXT_INDEX.md").exists())

    def test_check_exit_code_reflects_invariants(self):
        self.cli("build", "--course", COURSE, "--apply")
        self.assertEqual(self.cli("check", "--course", COURSE).returncode, 0)
        index = self.root / "DATA" / COURSE / "CONTEXT/CONTEXT_INDEX.md"
        index.write_text(index.read_text(encoding="utf-8").replace("链式法则", "某点"), encoding="utf-8")
        self.assertEqual(self.cli("check", "--course", COURSE).returncode, 1)

    def test_unsafe_course_rejected(self):
        self.assertNotEqual(self.cli("build", "--course", "../etc").returncode, 0)

    def test_unknown_lesson_exit_code(self):
        self.assertEqual(self.cli("summarize", "--course", COURSE, "--lesson-id", "lesson_099", "--apply").returncode, 1)


if __name__ == "__main__":
    unittest.main()
