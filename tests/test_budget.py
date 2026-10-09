"""Token-budget helpers (plan.md §10): CJK-aware estimate + soft caps."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib import budget  # noqa: E402


class EstimateTests(unittest.TestCase):
    def test_cjk_costs_more_than_word_count_suggests(self):
        text = "导师人格只改变表达方式" * 10
        self.assertEqual(len(text.split()), 1)  # wc -w would say 1 "word"
        self.assertGreater(budget.estimate_tokens(text), 100)

    def test_ascii_is_cheaper_per_char(self):
        self.assertLess(budget.estimate_tokens("a" * 100), budget.estimate_tokens("汉" * 100))

    def test_empty(self):
        self.assertEqual(budget.estimate_tokens(""), 0)


class RepositoryBudgetTests(unittest.TestCase):
    def test_repo_has_no_soft_cap_warnings(self):
        """Guards against silent growth of always-loaded / per-task context."""
        self.assertEqual(budget.soft_threshold_warnings(ROOT), [])

    def test_repo_fits_plan_proportions_at_default_window(self):
        self.assertEqual(budget.budget_warnings(ROOT), [])

    def test_small_window_flags_classroom_scenario(self):
        warnings = budget.budget_warnings(ROOT, window=16_000)
        self.assertTrue(any("classroom" in w for w in warnings), warnings)

    def test_every_scenario_file_exists(self):
        for name, parts in budget.SCENARIOS.items():
            for part in parts:
                if part != "profile:max":
                    self.assertTrue((ROOT / part).exists(), f"{name}: {part}")

    def test_oversized_file_is_reported_per_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("规" * 3000, encoding="utf-8")
            skill = root / ".pi/skills/s"
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: s\ndescription: d\n---\n" + "技" * 1500, encoding="utf-8")
            (skill / "references/r.md").write_text("参" * 1500, encoding="utf-8")
            warnings = budget.soft_threshold_warnings(root)
            self.assertEqual(len(warnings), 3, warnings)
            self.assertTrue(any("(kernel)" in w for w in warnings))
            self.assertTrue(any("(skill)" in w for w in warnings))
            self.assertTrue(any("(reference)" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
