"""Tutor profile invariants.

Personas are the presentation layer only (ADR-004): they may change tone,
analogy and questioning route, never facts, sources, permissions, course
boundaries, mastery standards or file state.

Two tiers exist and must not blur: `profiles/` face the learner, `moe/` is an
internal review group that only shows up in the prep meeting and the post-class
retrospective (ADR-014).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / ".pi/skills/socratopia-tutor/profiles"

REQUIRED_SECTIONS = ("教学角色", "声音", "追问方式", "典型动作", "强项", "盲区护栏", "承接偏好")

# Internal members deliberate rather than speak: lenses, not stage directions.
MOE_SECTIONS = ("审议镜头", "审议方式", "强项", "盲区护栏", "纪要语气", "侧重场景")

# A profile may reference these concepts but must never assert them as authority.
FORBIDDEN_AUTHORITY = [
    "已掌握", "已学会", "掌握度为", "可以通过考核", "宣布掌握",
]

# Only D/E/F face the learner; A/B/C are the internal review group.
PROFILES_EXPECTED = {"TUTOR_D", "TUTOR_E", "TUTOR_F"}
MOE_EXPECTED = {"TUTOR_A", "TUTOR_B", "TUTOR_C"}

MOE = PROFILES.parent / "moe"
PERSONA = PROFILES.parent / "references/persona.md"
MOE_DOC = PROFILES.parent / "references/moe.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ProfileInventoryTests(unittest.TestCase):
    def test_three_visible_profiles(self):
        found = {p.stem for p in PROFILES.glob("TUTOR_*.md")}
        self.assertEqual(found, PROFILES_EXPECTED)

    def test_three_internal_members(self):
        found = {p.stem for p in MOE.glob("TUTOR_*.md")}
        self.assertEqual(found, MOE_EXPECTED)

    def test_every_profile_has_required_sections(self):
        for path in sorted(PROFILES.glob("TUTOR_*.md")):
            for section in REQUIRED_SECTIONS:
                self.assertIn(f"## {section}", read(path), f"{path.stem} missing {section}")

    def test_every_member_has_lens_sections(self):
        for path in sorted(MOE.glob("TUTOR_*.md")):
            for section in MOE_SECTIONS:
                self.assertIn(f"## {section}", read(path), f"{path.stem} missing {section}")

    def test_profiles_stay_compact(self):
        """plan.md §10 soft cap: compact profile <= 600 汉字；内部成员更短。"""
        for path in sorted(PROFILES.glob("TUTOR_*.md")):
            han = len(re.findall(r"[一-鿿]", read(path)))
            self.assertLessEqual(han, 600, f"{path.stem}: {han} 汉字")
        for path in sorted(MOE.glob("TUTOR_*.md")):
            han = len(re.findall(r"[一-鿿]", read(path)))
            self.assertLessEqual(han, 450, f"{path.stem}: {han} 汉字")

    def test_frontmatter_absent(self):
        """A profile must not carry skill frontmatter; it is not an active skill."""
        for path in [*sorted(PROFILES.glob("TUTOR_*.md")), *sorted(MOE.glob("TUTOR_*.md"))]:
            self.assertFalse(read(path).startswith("---\n"), path.stem)

    def test_members_declare_their_tier_in_the_title(self):
        """Structural fact, not decoration: a member must announce it stays backstage."""
        for path in sorted(MOE.glob("TUTOR_*.md")):
            self.assertIn("内部教研组", read(path).splitlines()[0], path.stem)


class MoeBoundaryTests(unittest.TestCase):
    """The point of the change: A/B/C must never surface as the speaking tutor."""

    def test_moe_protocol_exists_and_forbids_speaking(self):
        text = read(MOE_DOC)
        self.assertIn("不面向学习者", text)
        self.assertIn("备课会", text)
        self.assertIn("下课复盘会", text)

    def test_moe_sinks_are_prep_and_self_improving_only(self):
        text = read(MOE_DOC)
        self.assertIn("PREP", text)
        self.assertIn("SELF_IMPROVING", text)
        self.assertIn("不产生第三份事实源", text)

    def test_persona_routing_table_lists_only_visible_tutors(self):
        text = read(PERSONA)
        for letter in "DEF":
            self.assertRegex(text, rf"\|[^\n]*\| {letter} \|", f"TUTOR_{letter} missing from routing table")
        for letter in "ABC":
            self.assertNotRegex(text, rf"\|\s*[^\n|]+\s*\|\s*{letter}\s*\|",
                                f"TUTOR_{letter} 仍出现在面向学习者的症状表")

    def test_persona_points_to_moe_for_the_internal_group(self):
        text = read(PERSONA)
        self.assertIn("内部教研组", text)
        self.assertIn("moe.md", text)

    def test_contract_declares_two_tiers(self):
        contract = read(ROOT / "SYSTEM/SPEC/TUTOR_CONTRACT.md")
        self.assertIn("moe/", contract)
        self.assertIn("不面向学习者", contract)
        self.assertNotIn("A → B → C 轮换", contract)


class PersonaBoundaryTests(unittest.TestCase):
    def test_no_profile_asserts_mastery(self):
        for path in [*sorted(PROFILES.glob("TUTOR_*.md")), *sorted(MOE.glob("TUTOR_*.md"))]:
            for phrase in FORBIDDEN_AUTHORITY:
                self.assertNotIn(phrase, read(path), f"{phrase!r} in {path.stem}")

    def test_no_profile_claims_to_change_standards(self):
        """The energetic persona must not lower the verification bar."""
        d = read(PROFILES / "TUTOR_D.md")
        self.assertIn("元气不等于降低门槛", d)
        self.assertIn("不取", d)  # explicitly drops the memory-conflict half
        self.assertIn("必须", d)

    def test_dan_heng_guardrail_forbids_endless_probing(self):
        e = read(PROFILES / "TUTOR_E.md")
        self.assertIn("换表征", e)
        self.assertIn("台阶", e)

    def test_himeko_does_not_delegate_mastery(self):
        f = read(PROFILES / "TUTOR_F.md")
        self.assertIn("PROGRESS.md", f)
        self.assertIn("handoff.json", f)


class PersonaProvenanceTests(unittest.TestCase):
    """D/E/F must stay traceable to a recorded source, and deviations must stay explicit."""

    DOC = ROOT / "docs/PERSONA_SOURCES.md"

    def test_each_sourced_tutor_has_page_and_pageid(self):
        text = read(self.DOC)
        for name, pageid in (("三月七", "513926"), ("丹恒", "544559"), ("姬子", "543029")):
            self.assertIn(name, text)
            self.assertIn(pageid, text)
        self.assertIn("zh.moegirl.org.cn", text)

    def test_deliberate_deviation_is_recorded_and_enforced(self):
        text = read(self.DOC)
        self.assertIn("刻意不取", text)
        d = read(PROFILES / "TUTOR_D.md")
        self.assertIn("不取", d)

    def test_teaching_method_is_declared_as_project_design_not_source_claim(self):
        text = read(self.DOC)
        self.assertIn("词条无此主张", text)
        self.assertIn("教学法映射是本项目的设计", text)

    def test_signature_gestures_match_recorded_sources(self):
        self.assertIn("举起相机", read(PROFILES / "TUTOR_D.md"))
        self.assertIn("枪尖", read(PROFILES / "TUTOR_E.md"))
        f = read(PROFILES / "TUTOR_F.md")
        self.assertIn("咖啡", f)
        self.assertNotIn("星图", f)  # unsourced flourish removed

    def test_moved_members_are_recorded_as_internal(self):
        """A move must not silently orphan provenance."""
        self.assertIn("内部教研组", read(self.DOC))


class SharedPersonaRuleTests(unittest.TestCase):
    """Shared rules live once in persona.md; profiles only carry per-tutor angles."""

    def test_escalation_ladder_and_handoff_rule_are_defined_once(self):
        text = read(PERSONA)
        self.assertIn("卡住升级阶梯", text)
        self.assertIn("承接共用规则", text)
        self.assertIn("runtime/handoff.json", text)
        for path in sorted(PROFILES.glob("TUTOR_*.md")):
            self.assertNotIn("不重复上一位导师的原讲法", read(path).split("## 承接偏好")[1], path.stem)

    def test_contract_points_to_routing_table(self):
        contract = read(ROOT / "SYSTEM/SPEC/TUTOR_CONTRACT.md")
        self.assertIn("persona.md", contract)


if __name__ == "__main__":
    unittest.main()
