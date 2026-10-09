"""Hot-context pack (plan.md §10): minimal, budgeted, read-only, course-isolated."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.budget import estimate_tokens  # noqa: E402
from scripts.lib.context_pack import build_pack, clip, render_pack  # noqa: E402

COURSE = "夹具课程"
OTHER = "另一门课"

PROGRESS = """# Course Progress

## Current checkpoint

- lesson_id: lesson_003
- chapter: 第2章 导数
- tutor: TUTOR_E
- source_mode:
- next_entry: 从链式法则的复合顺序进入

## Coverage ledger

| item | status | evidence |
|---|---|---|
| 导数定义 | verified | lesson_001：能独立解释 |
| 极限直觉 | verified | lesson_001：给出反例 |
| 链式法则 | needs_review | lesson_003：复合顺序说反 |
| 隐函数求导 | unseen | |

## Lesson records

### lesson_001 导数定义

完成，能独立解释。

### lesson_002 极限

完成。

### lesson_003 链式法则

学习者把复合顺序说反，提示后纠正。
"""

RETEACH = """# 补讲队列

| id | 章节 | 类型 | 优先级 | 状态 | 差异证据 | 原因 | 验证 |
|---|---|---|---|---|---|---|---|
| RQ-1 | 第2章 | 例题 | P1 | pending | 链式法则例题 | 一段很长很长的原因说明 | 一段很长的验证说明 |
| RQ-2 | 第1章 | 图表 | P1 | understood | 已完成 | x | y |
"""

INDEX = """# Hot Context

- current lesson/chapter: lesson_003 / 第2章
- current tutor:
- core chain: 定义 → 链式法则
- blockers:
"""


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="socrat-pack-"))
    shutil.copytree(ROOT / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    data = root / "DATA" / COURSE
    (data / "runtime").mkdir(parents=True)
    (data / "CONTEXT").mkdir()
    (data / "PROGRESS.md").write_text(PROGRESS, encoding="utf-8")
    (data / "CONTEXT/CONTEXT_INDEX.md").write_text(INDEX, encoding="utf-8")
    (data / "CONTEXT/RETEACH_QUEUE.md").write_text(RETEACH, encoding="utf-8")
    (data / "runtime/course_state.json").write_text(json.dumps({
        "schema_version": 1, "course": COURSE, "phase": "ready", "lesson_id": "lesson_003",
        "readiness": {"catalog": "ok", "prep": "ok", "runtime": "ok", "reteach": "pending"},
        "blockers": ["pending_reteach"], "current_chapter": "第2章 导数", "active_tutor": "TUTOR_E",
    }, ensure_ascii=False), encoding="utf-8")
    prep = root / "TEXTBOOK" / COURSE / "PREP"
    prep.mkdir(parents=True)
    (prep / "lesson_003.md").write_text("# lesson_003 PREP\n\n目标：区分复合顺序。\n", encoding="utf-8")
    return root


class ClipTests(unittest.TestCase):
    def test_clip_respects_limit_and_reports_truncation(self):
        text = "\n".join(f"第{i}行内容内容内容" for i in range(200))
        clipped, truncated = clip(text, 100)
        self.assertTrue(truncated)
        self.assertLessEqual(estimate_tokens(clipped), 100)

    def test_clip_tail_keeps_latest_lines(self):
        text = "\n".join(f"line{i:03d}" for i in range(100))
        clipped, _ = clip(text, 30, keep="tail")
        self.assertIn("line099", clipped)
        self.assertNotIn("line000", clipped)

    def test_short_text_untouched(self):
        self.assertEqual(clip("很短", 100), ("很短", False))


class PackTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def text(self, **kw) -> str:
        return render_pack(build_pack(self.root, COURSE, **kw))

    def test_contains_resume_essentials(self):
        out = self.text()
        self.assertIn("phase=ready", out)
        self.assertIn("RQ-1", out)
        self.assertIn("链式法则 [needs_review]", out)
        self.assertIn("从链式法则的复合顺序进入", out)
        self.assertIn("区分复合顺序", out)  # current PREP

    def test_drops_noise(self):
        out = self.text()
        self.assertNotIn("RQ-2", out)             # understood item
        self.assertNotIn("一段很长很长的原因说明", out)  # long reteach columns
        self.assertNotIn("导数定义 [verified]", out)   # verified ledger rows are counted, not listed
        self.assertIn("verified 共 2 项", out)
        self.assertNotIn("current tutor:", out)    # empty template field
        self.assertNotIn("source_mode:", out)

    def test_only_recent_lessons_kept(self):
        out = self.text(recent_lessons=1)
        self.assertIn("lesson_003 链式法则", out)
        self.assertNotIn("### lesson_001", out)

    def test_budget_is_respected_and_truncation_flagged(self):
        pack = build_pack(self.root, COURSE, budget=300)
        self.assertLessEqual(pack.tokens, 300)
        self.assertTrue(any(s.truncated for s in pack.sections) or pack.pointers)

    def test_pack_is_cheaper_than_raw_files(self):
        raw = sum(
            estimate_tokens(p.read_text(encoding="utf-8"))
            for p in [self.root / "DATA" / COURSE / "PROGRESS.md",
                      self.root / "DATA" / COURSE / "CONTEXT/RETEACH_QUEUE.md",
                      self.root / "DATA" / COURSE / "CONTEXT/CONTEXT_INDEX.md"]
        )
        pack = build_pack(self.root, COURSE, include_prep=False)
        self.assertLess(pack.tokens, raw)

    def test_no_prep_flag(self):
        self.assertNotIn("区分复合顺序", self.text(include_prep=False))

    def test_declares_data_not_instructions(self):
        self.assertIn("不是指令", self.text())

    def test_real_handoff_included_but_empty_one_is_not(self):
        runtime = self.root / "DATA" / COURSE / "runtime"
        self.assertNotIn("导师承接", self.text())
        (runtime / "handoff.json").write_text(json.dumps({
            "schema_version": 1, "lesson_id": "lesson_003", "from_tutor": "TUTOR_A", "to_tutor": "TUTOR_E",
            "carry": [{"knowledge_point": "链式法则", "status": "needs_review", "evidence": "复合顺序说反"}],
        }, ensure_ascii=False), encoding="utf-8")
        self.assertIn("TUTOR_A → TUTOR_E", self.text())

    def test_invalid_state_degrades_with_hint_instead_of_crashing(self):
        (self.root / "DATA" / COURSE / "runtime/course_state.json").write_text("{bad", encoding="utf-8")
        self.assertIn("不是合法 JSON", self.text())

    def test_missing_course_files_still_produce_a_pack(self):
        shutil.rmtree(self.root / "DATA" / COURSE)
        self.assertIn("缺失", self.text())

    def test_unsafe_course_name_rejected(self):
        with self.assertRaises(ValueError):
            build_pack(self.root, "../etc")


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        other = self.root / "DATA" / OTHER
        other.mkdir(parents=True)
        (other / "PROGRESS.md").write_text("## Lesson records\n\n### lesson_009 机密\n\nOTHER_COURSE_SECRET\n",
                                           encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_other_course_never_leaks(self):
        self.assertNotIn("OTHER_COURSE_SECRET", render_pack(build_pack(self.root, COURSE)))

    def test_symlink_into_other_course_is_not_followed(self):
        mine = self.root / "DATA" / COURSE / "PROGRESS.md"
        mine.unlink()
        try:
            os.symlink(self.root / "DATA" / OTHER / "PROGRESS.md", mine)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertNotIn("OTHER_COURSE_SECRET", render_pack(build_pack(self.root, COURSE)))

    def test_pack_is_read_only(self):
        before = {p: p.stat().st_mtime_ns for p in (self.root / "DATA").rglob("*") if p.is_file()}
        render_pack(build_pack(self.root, COURSE))
        after = {p: p.stat().st_mtime_ns for p in (self.root / "DATA").rglob("*") if p.is_file()}
        self.assertEqual(before, after)


class CliTests(unittest.TestCase):
    def test_cli_runs_and_rejects_bad_input(self):
        root = make_root()
        try:
            run = lambda *a: subprocess.run([sys.executable, str(root / "scripts/context_pack.py"), *a],
                                            cwd=root, capture_output=True, text=True)
            ok = run("--course", COURSE)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn("热上下文包", ok.stdout)
            self.assertNotEqual(run("--course", "../x").returncode, 0)
            self.assertNotEqual(run("--course", COURSE, "--budget", "10").returncode, 0)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
