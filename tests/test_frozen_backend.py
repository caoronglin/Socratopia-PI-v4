"""Frozen CPython runner preserves script permissions and exact exit codes."""
from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from scripts.frozen_backend import ALLOWED, main


class FrozenBackendTests(unittest.TestCase):
    def test_known_entrypoints_and_no_doctor_side_effects(self):
        for name in ("initialize.py", "learning_group.py", "lesson_timer.py",
                     "prep.py", "cherry_preflight.py", "web_article.py"):
            self.assertIn(name, ALLOWED)
        self.assertNotIn("check.py", ALLOWED)
        self.assertNotIn("pi_arch_doctor.py", ALLOWED)

    def test_unrecognized_executable_never_runs(self):
        for args in ([], ["../other.py"], ["../../SECRET"], ["no.py"], ["check.py"]):
            with self.subTest(args=args), patch("runpy.run_path") as run:
                self.assertEqual(main(args), 2)
                run.assert_not_called()

    def test_supported_module_uses_real_project_script_and_exact_arguments(self):
        with patch("runpy.run_path", side_effect=SystemExit(0)) as run, \
             patch.object(sys, "argv", ["frozen-backend"]):
            self.assertEqual(main(["initialize.py", "plan", "--course", "遗传学"]), 0)
            executed = run.call_args.args[0]
            self.assertTrue(executed.endswith("scripts/initialize.py") or
                            executed.endswith("scripts\\initialize.py"))
            self.assertEqual(sys.argv[1:], ["plan", "--course", "遗传学"])
            self.assertEqual(run.call_args.kwargs["run_name"], "__main__")

    def test_nonzero_status_propagates(self):
        with patch("runpy.run_path", side_effect=SystemExit(2)):
            self.assertEqual(main(["lesson_timer.py", "finish", "--course", "遗传学"]), 2)


if __name__ == "__main__":
    unittest.main()
