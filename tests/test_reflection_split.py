"""Phase 4 · Reflection / Self-Improving split — separation + boundary guards."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TUTOR = ROOT / ".pi/skills/socratopia-tutor/references"
LEARNING = ROOT / ".pi/skills/socratopia-learning/references"


class ReflectionSplitTests(unittest.TestCase):
    def setUp(self):
        self.self_improving = (TUTOR / "self-improving.md").read_text(encoding="utf-8")
        self.reflection = (LEARNING / "reflection.md").read_text(encoding="utf-8")

    def test_both_references_exist(self):
        self.assertTrue((TUTOR / "self-improving.md").exists())
        self.assertTrue((LEARNING / "reflection.md").exists())

    def test_distinct_state_files(self):
        # tutor self-improving -> DATA/SELF_IMPROVING/<tutor>.jsonl
        # learner reflection -> DATA/<course>/DIARY.md  (per-course)
        self.assertIn("DATA/SELF_IMPROVING/<tutor>.jsonl", self.self_improving)
        self.assertIn("DATA/<course>/DIARY.md", self.reflection)
        # neither file may reference the other's store (no shared state)
        self.assertNotIn("SELF_IMPROVING", self.reflection)
        self.assertNotIn("DIARY.md", self.self_improving)

    def test_self_improving_forbids_mastery_and_course_facts(self):
        for term in ["掌握度", "知识点状态", "考试结果", "课程事实"]:
            self.assertIn(term, self.self_improving)  # listed under 绝不记录
        self.assertIn("绝不记录", self.self_improving)

    def test_reflection_forbids_fabrication_and_mastery_claim(self):
        self.assertIn("不替学习者编造", self.reflection)
        self.assertIn("MEMORY_CONTRACT.md", self.reflection)  # defers to canonical diary rules

    def test_no_heartbeat_or_cron(self):
        for term in ["heartbeat", "cron", "定时任务"]:
            self.assertNotIn(term.lower(), self.self_improving.lower().replace("**不引入 heartbeat/cron/定时任务**", ""))

    def test_routing_wired(self):
        learning = (LEARNING.parent / "SKILL.md").read_text(encoding="utf-8")
        tutor = (TUTOR.parent / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/reflection.md", learning)
        self.assertIn("references/self-improving.md", tutor)


if __name__ == "__main__":
    unittest.main()
