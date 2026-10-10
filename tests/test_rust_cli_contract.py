"""Rust CLI adoption contracts: thin adapter, no duplicate course-state engine."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.lib.budget import scenario_costs, soft_threshold_warnings

ROOT = Path(__file__).resolve().parents[1]


class RustLauncherContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rust = (ROOT / "rust/src/main.rs").read_text(encoding="utf-8")
        cls.cargo = (ROOT / "rust/Cargo.toml").read_text(encoding="utf-8")
        cls.prompt = (ROOT / "integrations/cherry-studio/AGENT_PROMPT.md").read_text(encoding="utf-8")
        cls.doc = (ROOT / "docs/RUST_CLI.md").read_text(encoding="utf-8")

    def test_zero_crate_deps_and_single_binary(self):
        self.assertIn("name = \"socratopia-cli\"", self.cargo)
        self.assertIn("name = \"socratopia\"", self.cargo)
        self.assertIn("[dependencies]", self.cargo)
        self.assertTrue((ROOT / "rust/Cargo.lock").is_file())
        self.assertIn("std::process::{Command, ExitCode}", self.rust)

    def test_only_safe_existing_python_entrypoints(self):
        for script in ("initialize.py", "learning_group.py", "lesson_timer.py",
                       "prep.py", "web_article.py", "check.py"):
            self.assertIn(script, self.rust)
            self.assertTrue((ROOT / "scripts" / script).is_file())
        for rule in ("not_symlink", "valid_course", "find_root", "Command::new",
                     "process.args(args)", "status_command"):
            self.assertIn(rule, self.rust)
        self.assertNotIn("sh -c", self.rust)
        self.assertNotIn("shell=True", self.rust)
        self.assertNotIn("std::process::Stdio::null()", self.rust)

    def test_no_duplicate_business_core_or_claimed_readiness(self):
        for false_claim in ("ready_to_teach: true", "mastery = verified",
                            "create_course_state(", "elapsed_seconds += "):
            self.assertNotIn(false_claim, self.rust)
        self.assertIn("ready_to_teach: unverified", self.rust)
        self.assertIn("不是第二套课程引擎", self.doc)
        self.assertIn("SOCRATOPIA_PYTHON", self.doc)

    def test_rust_ci_and_manifest_are_connected(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        for term in ("rust-cli:", "cargo +1.85.1 fmt", "cargo +1.85.1 clippy",
                     "cargo +1.85.1 test", "cargo +1.85.1 build"):
            self.assertIn(term, ci)
        files = set(json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["files"])
        for path in ("rust/Cargo.toml", "rust/Cargo.lock", "rust/src/main.rs",
                     "docs/RUST_CLI.md", "tests/test_rust_cli_contract.py"):
            self.assertIn(path, files)

    def test_prompt_is_more_concise_and_keeps_non_bypass(self):
        self.assertLess(len(self.prompt), 1200)
        for phrase in ("按任务加载", "AGENTS.md", "不是 MCP Server", "当前一位",
                       "socratopia-tutor", "active_tutor", "cherry-tool-guide",
                       "trusted:false", "45 分钟", "verified", "等待回答",
                       "SYSTEM/SPEC/AGENT_LOOP.md"):
            self.assertIn(phrase, self.prompt)
        self.assertIn("不凭空声称 Rust 已安装", self.prompt)

    def test_context_budget_for_new_entrypoints(self):
        costs = scenario_costs(ROOT)
        self.assertGreater(costs["onboarding"], 0)
        self.assertGreater(costs["study-group"], 0)
        self.assertEqual(soft_threshold_warnings(ROOT), [])


if __name__ == "__main__":
    unittest.main()
