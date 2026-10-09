"""45-minute classroom timer: no short completion, idle cap, course isolation."""
from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.lib.course_state import default_state, state_path
from scripts.lib.lesson_timer import MINIMUM_SECONDS, start, status, timer_path, transition
from scripts.lib.prep import book_hash, prep_path
from scripts.lib.repository import course_dir, textbook_dir, write_json_atomic

COURSE = "遗传学"
LESSON = "lesson_001"
T0 = datetime(2026, 10, 9, 1, 0, tzinfo=UTC)


class LessonTimerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="socrat-timer-")
        self.root = Path(self.tmp.name)
        book = textbook_dir(self.root, COURSE)
        book.mkdir(parents=True)
        (book / "book.md").write_text("# 教材\n## 第1章\n", encoding="utf-8")
        hash_value = book_hash(self.root, COURSE)
        prep = prep_path(self.root, COURSE, LESSON)
        prep.parent.mkdir(parents=True)
        prep.write_text(
            "---\nschema: prep-1\ncourse: 遗传学\nlesson_id: lesson_001\n"
            "chapter: 第1章\nstatus: ready\nbook_hash: " + hash_value +
            '\nanchors:\n  - "## 第1章"\nsources: []\n---\n'
            "# 第1章\n\n## 教学评一致性\n\n"
            "| id | 学习目标 | 问题/活动 | 可观察证据 | 支架 |\n"
            "|---|---|---|---|---|\n"
            "| O1 | 理解基本概念 | 举一个具体例子 | 独立解释 | B |\n\n"
            "## Coverage 种子\n\n| item | 计划状态 | 期望元素 |\n"
            "|---|---|---|\n| 定义 | unseen | 定义、条件 |\n\n"
            "## 预期误概念\n\n| 误概念 | 触发条件 | 纠偏问法 |\n"
            "|---|---|---|\n| 混淆概念 | 特殊例子 | 核对定义 |\n\n"
            "## 教研会决议\n\n"
            "- 目标粒度（A）：已拆分\n"
            "- 期望元素与误概念是否齐（B）：已评估\n"
            "- 表征与迁移路径（C）：已检查\n"
            "- 最可能卡点与预案：使用具体例子\n",
            encoding="utf-8")
        state = default_state(COURSE)
        state["phase"] = "ready"
        state["lesson_id"] = LESSON
        state["readiness"] = {"catalog": "ok", "prep": "ok", "runtime": "ok", "reteach": "clear"}
        state["blockers"] = []
        write_json_atomic(state_path(self.root, COURSE), state)
        self.progress = course_dir(self.root, COURSE) / "PROGRESS.md"
        self.progress.write_text("课堂事实未写入", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def at(self, minutes: float) -> datetime:
        return T0 + timedelta(minutes=minutes)

    def _accumulate_44(self):
        start(self.root, COURSE, LESSON, now=T0)
        for minute in range(4, 45, 4):
            outcome = transition(self.root, COURSE, "heartbeat", now=self.at(minute))
            self.assertEqual(outcome["phase"], "running")
        self.assertEqual(outcome["elapsed_seconds"], 44 * 60)

    def test_no_short_lesson_can_finish(self):
        self._accumulate_44()
        result = transition(self.root, COURSE, "finish", now=self.at(44))
        self.assertFalse(result["completed"])
        self.assertEqual(result["remaining_seconds"], 60)
        self.assertIn("finish_denied", result)
        result = transition(self.root, COURSE, "heartbeat", now=self.at(45))
        self.assertEqual(result["remaining_seconds"], 0)
        completed = transition(self.root, COURSE, "finish", now=self.at(45))
        self.assertTrue(completed["completed"])
        self.assertEqual(completed["elapsed_seconds"], MINIMUM_SECONDS)
        self.assertEqual(transition(self.root, COURSE, "finish", now=self.at(45))["session_id"],
                         completed["session_id"])
        self.assertEqual(self.progress.read_text(encoding="utf-8"), "课堂事实未写入")

    def test_long_idle_gap_auto_pauses_and_is_not_credited(self):
        start(self.root, COURSE, LESSON, now=T0)
        result = transition(self.root, COURSE, "heartbeat", now=self.at(20))
        self.assertEqual(result["phase"], "paused")
        self.assertEqual(result["elapsed_seconds"], 5 * 60)
        self.assertIn("heartbeat_not_recorded", result)
        self.assertFalse(result["completed"])
        transition(self.root, COURSE, "resume", now=self.at(25))
        resumed = transition(self.root, COURSE, "heartbeat", now=self.at(29))
        self.assertEqual(resumed["elapsed_seconds"], 9 * 60)

    def test_explicit_break_not_counted_and_status_readonly(self):
        start(self.root, COURSE, LESSON, now=T0)
        before = timer_path(self.root, COURSE).read_bytes()
        shown = status(self.root, COURSE, now=self.at(2))
        self.assertEqual(shown["elapsed_seconds"], 120)
        self.assertEqual(timer_path(self.root, COURSE).read_bytes(), before)
        transition(self.root, COURSE, "pause", now=self.at(3))
        self.assertEqual(status(self.root, COURSE, now=self.at(30))["elapsed_seconds"], 180)
        transition(self.root, COURSE, "resume", now=self.at(30))
        self.assertEqual(transition(self.root, COURSE, "heartbeat", now=self.at(34))["elapsed_seconds"], 420)

    def test_early_exit_allowed_but_never_completed(self):
        start(self.root, COURSE, LESSON, now=T0)
        interrupted = transition(self.root, COURSE, "interrupt", now=self.at(1))
        self.assertEqual(interrupted["phase"], "interrupted")
        self.assertFalse(interrupted["completed"])
        resumed = transition(self.root, COURSE, "resume", now=self.at(20))
        self.assertEqual(resumed["elapsed_seconds"], 60)

    def test_restart_is_idempotent_and_completed_sessions_archived(self):
        initial = start(self.root, COURSE, LESSON, now=T0)
        again = start(self.root, COURSE, LESSON, now=self.at(1))
        self.assertEqual(initial["session_id"], again["session_id"])
        self._accumulate_from(0, 45)
        transition(self.root, COURSE, "finish", now=self.at(45))
        new = start(self.root, COURSE, LESSON, now=self.at(46))
        self.assertNotEqual(new["session_id"], initial["session_id"])
        self.assertEqual(new["elapsed_seconds"], 0)
        archived = course_dir(self.root, COURSE) / "runtime/lesson_timer_records" / (initial["session_id"] + ".json")
        self.assertTrue(archived.is_file())

    def _accumulate_from(self, from_minute: int, through: int):
        for m in range(from_minute + 5, through + 1, 5):
            transition(self.root, COURSE, "heartbeat", now=self.at(m))

    def test_bad_clock_does_not_credit_negative_duration(self):
        start(self.root, COURSE, LESSON, now=T0)
        with self.assertRaises(ValueError):
            transition(self.root, COURSE, "heartbeat", now=T0 - timedelta(seconds=1))
        self.assertEqual(status(self.root, COURSE, now=T0)["elapsed_seconds"], 0)

    def test_runtime_or_prep_not_ready_refuses_start(self):
        state = default_state(COURSE)
        write_json_atomic(state_path(self.root, COURSE), state)
        with self.assertRaises(ValueError):
            start(self.root, COURSE, LESSON, now=T0)
        self.assertFalse(timer_path(self.root, COURSE).exists())

    def test_course_isolation_and_wrong_lesson(self):
        start(self.root, COURSE, LESSON, now=T0)
        self.assertEqual(status(self.root, "另一门课", now=T0)["phase"], "not_started")
        with self.assertRaises(ValueError):
            start(self.root, COURSE, "lesson_002", now=T0)
        with self.assertRaises(ValueError):
            start(self.root, "../other", LESSON, now=T0)

    def test_persisted_state_survives_process_like_reloads(self):
        start(self.root, COURSE, LESSON, now=T0)
        transition(self.root, COURSE, "heartbeat", now=self.at(4))
        self.assertEqual(status(self.root, COURSE, now=self.at(4))["elapsed_seconds"], 240)


if __name__ == "__main__":
    unittest.main()
