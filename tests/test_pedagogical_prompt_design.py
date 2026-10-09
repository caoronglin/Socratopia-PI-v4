"""Static regression checks for adaptive pedagogy, prompt routing, and evidence gates.

These tests verify written contracts, not live model learning outcomes.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / ".pi/skills/socratopia-learning/references"
TUTOR = ROOT / ".pi/skills/socratopia-tutor/references"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class AdaptivePedagogyContracts(unittest.TestCase):
    def setUp(self):
        self.pedagogy = read(LEARNING / "pedagogy.md")
        self.examples = read(LEARNING / "pedagogy-examples.md")
        self.classroom = read(LEARNING / "classroom.md")
        self.persona = read(TUTOR / "persona.md")
        self.style = read(TUTOR / "style.md")
        self.start = read(ROOT / ".pi/prompts/start-class.md")

    def test_response_sensitive_not_question_count_driven(self):
        for signal in ("独立正确", "部分正确", "自信但错误", "卡住", "只说“懂了”"):
            self.assertIn(signal, self.pedagogy)
        for action in ("反例", "换表征", "最小台阶", "直接解释", "迁移"):
            self.assertIn(action, self.pedagogy)
        self.assertIn("无进展轮数", self.classroom)

    def test_direct_answer_is_authoritative_at_entry(self):
        for layer in (self.pedagogy, self.classroom, self.persona, self.start):
            self.assertIn("直接讲", layer)
            self.assertIn("解释", layer)
        self.assertIn("不先用提问拖延", self.start)
        self.assertIn("可选", self.pedagogy)
        self.assertIn("一个问题后等待回答", self.start)

    def test_no_mastery_from_confidence_or_prep(self):
        self.assertIn("不直接升级 coverage", self.pedagogy)
        self.assertIn("verified", self.pedagogy)
        self.assertIn("PROGRESS.md", read(ROOT / "AGENTS.md"))
        self.assertIn("introduced", read(LEARNING / "coverage.md"))

    def test_three_contrasting_examples(self):
        for example in ("自信但错误", "卡住两轮", "明确直讲"):
            self.assertIn(example, self.examples)
        self.assertIn("不是必须复读的导师台词", self.examples)

    def test_style_does_not_invent_measurements_or_thoughts(self):
        self.assertNotIn("能省一半时间", self.style)
        for phrase in ("可核验", "未经核对", "不要假装", "直接进入当前问题"):
            self.assertIn(phrase, self.style)

    def test_single_owner_and_reference_boundaries(self):
        self.assertIn("references/pedagogy.md", self.start)
        self.assertIn("references/pedagogy.md", self.persona)
        self.assertIn("pedagogy.md", self.classroom)
        self.assertNotIn("Pedagogy ·", read(ROOT / "AGENTS.md"))

    def test_research_and_evaluation_not_confused_with_test_success(self):
        catalog = read(ROOT / "docs/PROMPTS.md")
        for source in ("GuideEval", "StratL", "Tutor CoPilot", "Pi Prompt Templates"):
            self.assertIn(source, catalog)
        for scenario in ("自信但错误", "明确要求直讲", "教材未给出精确数值"):
            self.assertIn(scenario, catalog)
        self.assertIn("静态测试通过不表示实际教学效果已改进", catalog)


if __name__ == "__main__":
    unittest.main()
