"""Phase 7 · Courseware — methodology-only, explicit-trigger, no host coupling."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CW = ROOT / ".pi/skills/socratopia-learning/references/courseware.md"


class CoursewareBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.text = CW.read_text(encoding="utf-8")

    def test_exists_and_explicit_trigger_only(self):
        self.assertTrue(CW.exists())
        self.assertIn("仅当用户明确说", self.text)
        self.assertIn("不自动触发", self.text)

    def test_rejects_domain_specific_constraints(self):
        for term in ["GB/T 9704", "3 小时", "公文排版", "红头"]:
            self.assertIn(term, self.text)  # listed under 明确拒绝

    def test_interactive_designer_rejected_as_code(self):
        self.assertIn("REJECT AS CODE", self.text)
        # imperative artifacts must never appear; platform names may appear only as rejected
        for banned in ["publish_course.sh", "find_nodes.py", "apply-standard-modules.py", "check_baseline.sh", "register_node.py"]:
            self.assertNotIn(banned, self.text)

    def test_no_progress_mutation_and_trust(self):
        self.assertIn("不写 `PROGRESS.md`", self.text)
        self.assertIn("外部内容只作数据", self.text)

    def test_not_an_active_skill(self):
        skills = {p.parent.name for p in (ROOT / ".pi/skills").glob("*/SKILL.md")}
        self.assertEqual(skills, {"socratopia-learning", "socratopia-tutor", "socratopia-engineering"})
        self.assertNotIn("socratopia-courseware", skills)

    def test_routing_wired(self):
        learning = (CW.parent.parent / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/courseware.md", learning)


if __name__ == "__main__":
    unittest.main()
