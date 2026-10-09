"""Boundary tests for the SkillHub education-pack distillation.

The four `education-*` skillsets were absorbed as references, not installed as
active skills. These tests pin both halves of that decision so a future edit
cannot quietly reintroduce the dross or break the 3-skill freeze.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / ".pi/skills/socratopia-learning"
REFERENCES = LEARNING / "references"

ABSORBED = {
    "education-quiz-generation": "quiz-generation.md",
    "education-lesson-planning": "lesson-planning.md",
    "education-training-program": "course-program.md",
}
FOLDED = "education-student-assessment"
SKILL_NAME = "SKILL.md"

# Rejected content from the source packs. None may reappear as live guidance.
FORBIDDEN = [
    "你已安装以下 Skill",          # orchestrator premise (children NOT installed)
    "一键生成",                     # batch artifact claims
    "自动批改",                     # auto-grading standing in for evidence
    "掌握度图谱",                   # mastery graph -> ontology ban
    "营销文案",                     # S3 external publishing
    "家长沟通",                     # institutional role
    "成绩单",                       # institutional role
    "证书模板",                     # institutional role
    "新课标",                       # K12 binding
    "九大学科",                     # K12 binding
    "Claude Code",                 # host-specific (ARCHITECTURE.md)
    "Codex",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ActiveSkillFreezeTests(unittest.TestCase):
    def test_still_exactly_three_active_skills(self):
        skills = sorted(p.parent.name for p in (ROOT / ".pi/skills").glob("*/SKILL.md"))
        self.assertEqual(
            skills, ["socratopia-engineering", "socratopia-learning", "socratopia-tutor"]
        )

    def test_no_education_pack_installed_as_skill(self):
        for name in (*ABSORBED, FOLDED):
            self.assertFalse((ROOT / ".pi/skills" / name).exists())
            self.assertFalse((ROOT / ".agents/skills" / name).exists())

    def test_kernel_and_skill_frontmatter_unchanged_in_size(self):
        """AGENTS.md must not grow (kernel freeze, plan.md §10)."""
        self.assertLessEqual(len(read(ROOT / "AGENTS.md").split()), 1800)
        text = read(LEARNING / "SKILL.md")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("\nname:", text)
        self.assertIn("\ndescription:", text)


class QuarantineRecordTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(read(ROOT / "quarantine/sources.json"))

    def test_all_four_sources_registered(self):
        slugs = {s["slug"] for s in self.manifest["sources"]}
        for name in (*ABSORBED, FOLDED):
            self.assertIn(name, slugs)

    def test_sources_declare_no_code_and_local_only(self):
        for source in self.manifest["sources"]:
            if source["slug"] in (*ABSORBED, FOLDED):
                self.assertFalse(source["has_code"], source["slug"])
                self.assertFalse(source["network"], source["slug"])
                self.assertEqual(source["runtime_permission"], "local-only (reference)")
                self.assertTrue(source["rejected"])

    def test_active_skill_freeze_still_three(self):
        self.assertEqual(self.manifest["active_skill_freeze"], 3)

    def test_installer_rejection_is_documented(self):
        self.assertIn("skillhub", self.manifest.get("notes_skillhub", "").lower())
        self.assertIn("curl|bash", self.manifest["notes_skillhub"])


class ReferenceDistillationTests(unittest.TestCase):
    def test_absorbed_references_exist(self):
        for name, ref in ABSORBED.items():
            self.assertTrue((REFERENCES / ref).exists(), f"{name} -> {ref}")

    def test_folded_source_lands_in_existing_owner(self):
        text = read(REFERENCES / "assessment.md")
        self.assertIn("错因分类", text)
        self.assertIn("Rubric 维度", text)

    def test_no_second_rule_source_for_assessment(self):
        """student-assessment must not spawn its own parallel assessment doc."""
        self.assertFalse((REFERENCES / "student-assessment.md").exists())

    def test_rejected_content_never_appears_as_guidance(self):
        """Rejected phrases may appear ONLY on ❌ rejection lines, never as advice.

        Naming what is refused is required (see test_rejection_domains_are_declared);
        presenting it as guidance is the regression.
        """
        targets = [REFERENCES / name for name in (*ABSORBED.values(), "assessment.md", "classroom.md")]
        targets.append(LEARNING / SKILL_NAME)
        for path in targets:
            for lineno, line in enumerate(read(path).splitlines(), 1):
                for phrase in FORBIDDEN:
                    if phrase in line:
                        self.assertIn(
                            "❌", line,
                            f"{phrase!r} appears as guidance in {path.name}:{lineno}: {line.strip()}",
                        )

    def test_rejection_domains_are_declared(self):
        """Each distilled reference must state what it refuses, not just what it keeps."""
        for name in ABSORBED.values():
            text = read(REFERENCES / name)
            self.assertIn("明确拒绝", text, name)

    def test_quiz_reference_forbids_mastery_writes(self):
        text = read(REFERENCES / "quiz-generation.md")
        self.assertIn("source_derived", text)
        self.assertIn("ontology", text.lower())

    def test_program_reference_forbids_institutional_scope(self):
        text = read(REFERENCES / "course-program.md")
        for phrase in ("证据检查点", "DIARY.md"):
            self.assertIn(phrase, text)
        self.assertIn("❌", text)


if __name__ == "__main__":
    unittest.main()
