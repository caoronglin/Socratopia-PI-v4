"""Claude Code adapter must stay a thin, non-divergent view of `.pi/`.

The project keeps one authoritative control plane under `.pi/`. Claude Code
reads `AGENTS.md` natively but discovers skills under `.claude/skills/` and
commands under `.claude/commands/`, so this branch adds thin pointers there.

Two failure modes matter and are pinned below:
1. a stale duplicate rule body in `.claude/` that drifts from `.pi/`
2. a pointer that names a `.pi/` target which no longer exists
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / ".claude"
PI_SKILLS = ROOT / ".pi/skills"
PI_PROMPTS = ROOT / ".pi/prompts"

# `.pi/` is the single owner; `.claude/` may only point at it.
PI_TARGET = re.compile(r"\.pi/(?:prompts|skills)/[A-Za-z0-9_./-]+\.md")


def frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text.split("---", 2)[1] if text.startswith("---") else ""


def description_of(path: Path) -> str:
    match = re.search(r"^description:\s*(.+)$", frontmatter(path), re.M)
    return match.group(1).strip().strip('"') if match else ""


class KernelTests(unittest.TestCase):
    def test_no_root_claude_md_duplicate(self):
        """ADR-001: one kernel only. Claude Code reads AGENTS.md natively."""
        self.assertFalse(
            (ROOT / "CLAUDE.md").exists(),
            "根 CLAUDE.md 会与 AGENTS.md 形成第二份常驻规则（doctor 也会告警）",
        )
        self.assertTrue((ROOT / "AGENTS.md").is_file())

    def test_no_claude_system_override(self):
        """ADR-002 parity: never replace the host system prompt."""
        for forbidden in (CLAUDE / "SYSTEM.md", ROOT / ".pi/SYSTEM.md"):
            self.assertFalse(forbidden.exists(), f"禁止的宿主覆盖：{forbidden}")


class SkillPointerTests(unittest.TestCase):
    def setUp(self):
        self.skills = sorted(p.parent.name for p in CLAUDE.glob("skills/*/SKILL.md"))
        self.pi = sorted(p.parent.name for p in PI_SKILLS.glob("*/SKILL.md"))

    def test_skill_sets_match(self):
        self.assertEqual(self.skills, self.pi)
        self.assertEqual(len(self.skills), 3)

    def test_every_pointer_names_an_existing_target(self):
        for name in self.skills:
            body = (CLAUDE / f"skills/{name}/SKILL.md").read_text(encoding="utf-8")
            targets = PI_TARGET.findall(body)
            self.assertTrue(targets, f"{name} 入口未指向任何 .pi/ 权威文件")
            for rel in targets:
                self.assertTrue((ROOT / rel).is_file(), f"{name} 指向不存在的 {rel}")

    def test_pointer_does_not_duplicate_rule_body(self):
        """A pointer must stay short; a copied body is a second rule source."""
        for name in self.skills:
            body = (CLAUDE / f"skills/{name}/SKILL.md").read_text(encoding="utf-8")
            self.assertLess(
                len(body), 700,
                f"{name} 的 Claude 入口过长，疑似复制了 .pi/ 正文",
            )

    def test_frontmatter_description_matches_pi(self):
        for name in self.skills:
            self.assertEqual(
                description_of(CLAUDE / f"skills/{name}/SKILL.md"),
                description_of(PI_SKILLS / f"{name}/SKILL.md"),
                f"{name} 的 description 已与 .pi/ 漂移",
            )


class CommandPointerTests(unittest.TestCase):
    def setUp(self):
        self.commands = sorted(p.stem for p in CLAUDE.glob("commands/*.md"))
        self.prompts = sorted(p.stem for p in PI_PROMPTS.glob("*.md"))

    def test_command_sets_match(self):
        self.assertEqual(self.commands, self.prompts)
        self.assertEqual(len(self.commands), 7)

    def test_every_command_points_at_existing_prompt(self):
        for name in self.commands:
            body = (CLAUDE / f"commands/{name}.md").read_text(encoding="utf-8")
            rel = f".pi/prompts/{name}.md"
            self.assertIn(rel, body, f"/{name} 未指向权威提示词")
            self.assertTrue((ROOT / rel).is_file())

    def test_commands_taking_args_use_claude_placeholder(self):
        """Pi uses `$@`; Claude Code substitutes `$ARGUMENTS`, not `$@`."""
        for name in self.commands:
            body = (CLAUDE / f"commands/{name}.md").read_text(encoding="utf-8")
            pi_body = (PI_PROMPTS / f"{name}.md").read_text(encoding="utf-8")
            takes_args = "argument-hint:" in frontmatter(PI_PROMPTS / f"{name}.md")
            self.assertNotIn("$@", body, f"/{name} 残留 Pi 的 $@ 占位符")
            self.assertEqual(
                "argument-hint:" in frontmatter(CLAUDE / f"commands/{name}.md"),
                takes_args,
                f"/{name} 的 argument-hint 与 .pi/ 不一致",
            )
            if takes_args:
                self.assertIn("$ARGUMENTS", body, f"/{name} 接受参数但未使用 $ARGUMENTS")

    def test_frontmatter_description_matches_pi(self):
        for name in self.commands:
            self.assertEqual(
                description_of(CLAUDE / f"commands/{name}.md"),
                description_of(PI_PROMPTS / f"{name}.md"),
                f"/{name} 的 description 已与 .pi/ 漂移",
            )


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.settings = json.loads(
            (CLAUDE / "settings.json").read_text(encoding="utf-8")
        )

    def test_settings_are_valid_and_scoped(self):
        perms = self.settings.get("permissions", {})
        self.assertIsInstance(perms.get("deny"), list)
        self.assertIsInstance(perms.get("ask"), list)
        for rule in perms["deny"] + perms["ask"]:
            self.assertIsInstance(rule, str)

    def test_remote_and_destructive_actions_need_confirmation(self):
        perms = self.settings.get("permissions", {})
        guarded = set(perms.get("deny", [])) | set(perms.get("ask", []))
        for required in (
            "Bash(git push:*)",
            "Bash(rm -rf:*)",
            "Bash(python scripts/mineru_ingest.py remote:*)",
            "Bash(python scripts/memo_sync.py push:*)",
        ):
            self.assertIn(required, guarded, f"未设门控：{required}")

    def test_secrets_are_never_readable(self):
        denied = " ".join(self.settings["permissions"]["deny"])
        self.assertIn(".env", denied)


class ManifestTests(unittest.TestCase):
    def test_claude_files_are_registered(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        listed = set(manifest["files"])
        for rel in (
            ".claude/settings.json",
            ".claude/skills/socratopia-learning/SKILL.md",
            ".claude/skills/socratopia-tutor/SKILL.md",
            ".claude/skills/socratopia-engineering/SKILL.md",
            ".claude/commands/start-class.md",
            ".claude/commands/end-class.md",
            ".claude/commands/initialize.md",
            ".claude/commands/study-group.md",
            ".claude/commands/health.md",
            ".claude/commands/materials-ready.md",
            ".claude/commands/switch-course.md",
        ):
            self.assertIn(rel, listed, f"{rel} 未登记到 manifest.json")
            self.assertTrue((ROOT / rel).is_file())


if __name__ == "__main__":
    unittest.main()