"""Guided initialization and course-isolated multi-tutor discussion tests."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import initialize
from scripts.lib import learning_group as group
from scripts.lib.course_state import state_path
from scripts.lib.repository import course_dir, textbook_dir

ROOT = Path(__file__).resolve().parents[1]


class FirstRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="socrat-first-run-")
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / "templates", self.root / "templates")
        self.course = "遗传学"

    def tearDown(self):
        self.tmp.cleanup()

    def test_plan_read_only_and_not_ready(self):
        before = list(self.root.iterdir())
        result = initialize.inspect(self.root, self.course)
        self.assertFalse(result["runtime_exists"])
        self.assertFalse(result["writes"])
        self.assertEqual(before, list(self.root.iterdir()))
        self.assertFalse((self.root / "DATA").exists())

    def test_first_setup_and_idempotent_rerun(self):
        first = initialize.initialize(self.root, self.course, "E", ["E", "F"])
        self.assertTrue(first["created"])
        self.assertTrue(first["initial_tutor_saved"])
        self.assertFalse(first["ready_for_class"])
        self.assertEqual(first["group"]["members"], ["E", "F"])
        state_pathname = state_path(self.root, self.course)
        self.assertEqual(json.loads(state_pathname.read_text(encoding="utf-8"))["active_tutor"], "E")
        progress = course_dir(self.root, self.course) / "PROGRESS.md"
        progress.write_text("user's saved work", encoding="utf-8")
        previous = state_pathname.read_bytes()
        again = initialize.initialize(self.root, self.course, "E", ["E", "F"])
        self.assertEqual(again["created"], [])
        self.assertFalse(again["initial_tutor_saved"])
        self.assertEqual(progress.read_text(encoding="utf-8"), "user's saved work")
        self.assertEqual(state_pathname.read_bytes(), previous)
        self.assertFalse((textbook_dir(self.root, self.course) / "book.md").exists())

    def test_existing_user_tutor_and_group_not_overwritten(self):
        initialize.initialize(self.root, self.course, "D", ["D", "E"])
        with self.assertRaises(ValueError):
            initialize.initialize(self.root, self.course, "F", ["E", "F"])
        state = json.loads(state_path(self.root, self.course).read_text(encoding="utf-8"))
        self.assertEqual(state["active_tutor"], "D")
        self.assertEqual(group.status(self.root, self.course)["members"], ["D", "E"])

    def test_invalid_course_and_configuration_do_not_write(self):
        for name in ("..", "../bad", "x/y"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                initialize.initialize(self.root, name)
        with self.assertRaises(ValueError):
            initialize.initialize(self.root, self.course, "A")
        with self.assertRaises(ValueError):
            initialize.initialize(self.root, self.course, "D", ["D", "D"])
        self.assertFalse((self.root / "DATA").exists())

    def test_corrupt_existing_runtime_fails_closed(self):
        initialize.initialize(self.root, self.course)
        file = state_path(self.root, self.course)
        data = json.loads(file.read_text(encoding="utf-8"))
        data["phase"] = "not_valid"
        file.write_text(json.dumps(data), encoding="utf-8")
        before = file.read_bytes()
        with self.assertRaises(ValueError):
            initialize.initialize(self.root, self.course)
        self.assertEqual(file.read_bytes(), before)

    def test_wizard_requires_explicit_yes(self):
        with patch("builtins.input", side_effect=["生物学", "F", "D E F", "no"]):
            result = initialize.wizard(self.root)
        self.assertFalse(result["applied"])
        self.assertFalse((self.root / "DATA").exists())

    def test_wizard_yes_creates_course_group(self):
        with patch("builtins.input", side_effect=["生物学", "F", "D E F", "YES"]):
            result = initialize.wizard(self.root)
        self.assertTrue(result["applied"])
        self.assertEqual(group.status(self.root, "生物学")["members"], ["D", "E", "F"])


class GroupDiscussionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="socrat-panel-")
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / "templates", self.root / "templates")
        self.course = "遗传学"
        initialize.initialize(self.root, self.course, "F")
        self.progress = course_dir(self.root, self.course) / "PROGRESS.md"
        self.before = self.progress.read_bytes()

    def tearDown(self):
        self.tmp.cleanup()

    def test_configure_multiple_tutors_without_changing_active_tutor(self):
        status = group.configure(self.root, self.course, ["D", "E", "F"], "F")
        self.assertEqual(status["lead"], "F")
        self.assertEqual(status["members"], ["D", "E", "F"])
        state = json.loads(state_path(self.root, self.course).read_text(encoding="utf-8"))
        self.assertEqual(state["active_tutor"], "F")
        self.assertEqual(self.progress.read_bytes(), self.before)

    def test_invalid_members_and_internal_tutors_rejected(self):
        for members, lead in [(["A", "D"], "D"), (["D", "D"], "D"),
                              (["D"], "D"), (["D", "E", "F", "D"], "D"),
                              (["D", "E"], "F")]:
            with self.subTest(members=members), self.assertRaises(ValueError):
                group.configure(self.root, self.course, members, lead)

    def test_discussion_order_waits_for_user_and_finishes(self):
        group.configure(self.root, self.course, ["D", "F"], "F")
        one = group.start(self.root, self.course, "显性一定常见吗？", rounds=2)
        self.assertTrue(one["single_agent_simulation"])
        self.assertEqual(one["next_speaker"], "D")
        self.assertFalse(one["book_exists"])
        with self.assertRaises(ValueError):
            group.record(self.root, self.course, "F", "不能跳过 D")
        two = group.record(self.root, self.course, "D", "显性只描述表现型")
        self.assertEqual(two["next_speaker"], "F")
        three = group.record(self.root, self.course, "F", "显性并不代表高频")
        self.assertEqual(three["session"]["phase"], "awaiting_user")
        self.assertTrue(three["requires_user_turn"])
        advanced = group.continue_round(self.root, self.course, "稀有显性例子")
        self.assertEqual(advanced["next_speaker"], "D")
        group.record(self.root, self.course, "D", "补充具体例子")
        final = group.record(self.root, self.course, "F", "归纳与前提")
        self.assertEqual(final["session"]["phase"], "finished")
        self.assertFalse(final["may_continue"])
        self.assertEqual(len(final["session"]["turns"]), 4)
        with self.assertRaises(ValueError):
            group.continue_round(self.root, self.course)
        self.assertEqual(self.progress.read_bytes(), self.before)

    def test_repeated_start_and_stop(self):
        group.configure(self.root, self.course, ["E", "F"], "F")
        first = group.start(self.root, self.course, "问题")
        second = group.start(self.root, self.course, "问题")
        self.assertEqual(first["session"]["id"], second["session"]["id"])
        with self.assertRaises(ValueError):
            group.start(self.root, self.course, "不同主题")
        ended = group.stop(self.root, self.course)
        self.assertEqual(ended["session"]["phase"], "stopped")
        self.assertEqual(group.stop(self.root, self.course)["session"]["phase"], "stopped")
        restarted = group.start(self.root, self.course, "新主题")
        self.assertNotEqual(restarted["session"]["id"], first["session"]["id"])

    def test_config_during_active_session_rejected(self):
        group.configure(self.root, self.course, ["D", "E"], "D")
        group.start(self.root, self.course, "讨论")
        with self.assertRaises(ValueError):
            group.configure(self.root, self.course, ["E", "F"], "E")

    def test_bounded_rounds_and_utterance(self):
        group.configure(self.root, self.course, ["D", "E"], "D")
        for rounds in (0, 4, -1):
            with self.subTest(rounds=rounds), self.assertRaises(ValueError):
                group.start(self.root, self.course, "主题", rounds=rounds)
        group.start(self.root, self.course, "主题", rounds=1)
        for text in ("", "z" * 2501):
            with self.assertRaises(ValueError):
                group.record(self.root, self.course, "D", text)
        group.record(self.root, self.course, "D", "说法一")
        result = group.record(self.root, self.course, "E", "说法二")
        self.assertEqual(result["session"]["phase"], "finished")

    def test_course_and_progress_isolation(self):
        group.configure(self.root, self.course, ["D", "E"], "D")
        group.start(self.root, self.course, "话题")
        self.assertFalse(group.status(self.root, "另一门课")["configured"])
        with self.assertRaises(ValueError):
            group.configure(self.root, "../other", ["D", "E"], "D")
        self.assertEqual(self.progress.read_bytes(), self.before)
        self.assertFalse((course_dir(self.root, self.course) / "runtime/lesson_timer.json").exists())


if __name__ == "__main__":
    unittest.main()
