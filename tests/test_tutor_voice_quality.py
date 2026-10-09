"""Static tutor voice-quality contracts: consistency, feedback, routing, and evidence.

These tests check authored instructions and examples, not real model teaching efficacy.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts.lib.budget import soft_threshold_warnings

ROOT = Path(__file__).resolve().parents[1]
TUTOR = ROOT / ".pi/skills/socratopia-tutor"
PROFILES = TUTOR / "profiles"
REFERENCES = TUTOR / "references"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TutorVoiceQualityContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.persona = read(REFERENCES / "persona.md")
        cls.style = read(REFERENCES / "style.md")
        cls.examples = read(REFERENCES / "voice-examples.md")
        cls.profiles = {code: read(PROFILES / f"TUTOR_{code}.md") for code in "DEF"}
        cls.cherry = read(ROOT / "integrations/cherry-studio/AGENT_PROMPT.md")

    def test_each_tutor_is_distinct_without_conflicting_fact_rules(self):
        cues = {
            "D": ("轻快", "具体情境", "元气不等于降低门槛"),
            "E": ("短句", "隐含前提", "换表征"),
            "F": ("温和", "前后章节", "PROGRESS.md"),
        }
        for code, terms in cues.items():
            with self.subTest(tutor=code):
                text = self.profiles[code]
                for term in terms:
                    self.assertIn(term, text)
                self.assertRegex(text, r"直讲|直接解释")
                self.assertIn("## 承接偏好", text)
                self.assertIn("## 盲区护栏", text)
                self.assertIn("默认", text)

    def test_shared_persona_prioritizes_learning_over_performance(self):
        for phrase in ("默认不写动作", "一个主要问题", "等待", "直接讲", "具体认可",
                       "明确纠错", "不猜测情绪", "卡住升级阶梯", "承接共用规则"):
            self.assertIn(phrase, self.persona)
        self.assertIn("pedagogy.md", self.persona)
        self.assertIn("不面向学习者", self.persona)
        self.assertIn("runtime/handoff.json", self.persona)

    def test_style_requires_evidence_and_prevents_canned_voice(self):
        for phrase in ("可核验", "未经核对", "不要假装", "直接进入当前问题",
                       "不强制进入角色", "一个主要问题", "不编造", "不机械", "纠错"):
            self.assertIn(phrase, self.style)
        self.assertNotIn("能省一半时间", self.style)
        self.assertIn("动作", self.style)
        self.assertIn("默认", self.persona)

    def test_roleplay_and_unsupported_relationship_are_not_the_goal(self):
        self.assertIn("亲密关系", self.profiles["D"])
        self.assertIn("不伪造", self.persona)
        self.assertIn("不制造恋爱", read(REFERENCES / "social.md"))
        for profile in self.profiles.values():
            self.assertIn("动作", profile)
            self.assertLess(len(profile), 1100)

    def test_contrastive_examples_show_same_concept_three_ways(self):
        for section in ("场景 1", "场景 2", "场景 3"):
            self.assertIn(section, self.examples)
        for marker in ("D 三月七", "E 丹恒", "F 姬子", "| D |", "| E |", "| F |"):
            self.assertIn(marker, self.examples)
        for concept in ("显性", "频率", "条件概率", "5′→3′"):
            self.assertIn(concept, self.examples)
        self.assertIn("原创", self.examples)
        self.assertIn("不是已通过", self.examples)

    def test_cherry_agent_routes_to_active_single_profile(self):
        for phrase in ("active_tutor", "socratopia-tutor", "persona.md", "当前一位"):
            self.assertIn(phrase, self.cherry)
        tutor_skill = read(TUTOR / "SKILL.md")
        self.assertIn("voice-examples.md", tutor_skill)
        self.assertIn("只有当前导师", tutor_skill)
        self.assertIn("按需", tutor_skill)

    def test_no_unbounded_context_inflation(self):
        warnings = soft_threshold_warnings(ROOT)
        relevant = [x for x in warnings if "socratopia-tutor" in x]
        self.assertEqual(relevant, [], relevant)

    def test_persona_sources_remain_explicit(self):
        sources = read(ROOT / "docs/PERSONA_SOURCES.md")
        self.assertIn("不是角色原台词", sources)
        self.assertIn("教学法映射是本项目的设计", sources)
        self.assertIn("voice-examples.md", sources)
        self.assertIn("词条无此主张", sources)


if __name__ == "__main__":
    unittest.main()
