"""Dependency and self-contained executable release contracts."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (".github/workflows/ci.yml", ".github/workflows/release.yml")


class DependencyAndStandaloneContracts(unittest.TestCase):
    def test_all_external_actions_use_immutable_commit_sha(self):
        for name in FILES:
            with self.subTest(workflow=name):
                content = (ROOT / name).read_text(encoding="utf-8")
                actions = re.findall(r"^\s*- uses:\s*([^\s#]+)", content, re.MULTILINE)
                self.assertTrue(actions)
                for action in actions:
                    self.assertRegex(action, r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+@[0-9a-f]{40}$")
                self.assertNotIn("pull_request_target:", content)

    def test_updated_official_action_families_present(self):
        ci = (ROOT / FILES[0]).read_text(encoding="utf-8")
        release = (ROOT / FILES[1]).read_text(encoding="utf-8")
        for action in ("3d3c42e5aac5ba805825da76410c181273ba90b1",
                       "5fda3b95a4ea91299a34e894583c3862153e4b97"):
            self.assertIn(action, ci)
            self.assertIn(action, release)
        for action in ("cf430e030ddbb5b0abf93d22962f4752f3646cd9",
                       "9000827ccba6bdab643e8b6fd33ac0654aef8333"):
            self.assertIn(action, release)

    def test_dependencies_explicitly_pinned_and_dependabot_configured(self):
        self.assertEqual((ROOT / "requirements-build.txt").read_text(encoding="utf-8").strip(),
                         "pyinstaller==6.22.3")
        self.assertEqual((ROOT / "requirements-ci.txt").read_text(encoding="utf-8").strip(),
                         "pytest==9.1.1")
        config = (ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
        for term in ("package-ecosystem: github-actions", "package-ecosystem: pip",
                     "interval: weekly"):
            self.assertIn(term, config)

    def test_frozen_backend_cannot_ignore_selected_workspace(self):
        source = (ROOT / "scripts/frozen_backend.py").read_text(encoding="utf-8")
        rust = (ROOT / "rust/src/main.rs").read_text(encoding="utf-8")
        smoke = (ROOT / "scripts/smoke_standalone.py").read_text(encoding="utf-8")
        self.assertIn('process.env("SOCRATOPIA_WORKSPACE_ROOT", root);', rust)
        self.assertIn('os.environ.get("SOCRATOPIA_WORKSPACE_ROOT")', source)
        self.assertIn("installed_bin.is_some() && !use_bundle", rust)
        self.assertIn("缺少 bin/socratopia-backend", rust)
        self.assertIn("alternate-workspace", smoke)
        self.assertIn("安装包不完整", smoke)
        self.assertIn("SOCRATOPIA_REQUIRE_BUNDLED", smoke)


if __name__ == "__main__":
    unittest.main()
