"""Contract checks for stable, version-consistent multi-platform GitHub releases."""
from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StableReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tag = (ROOT / "release/VERSION").read_text(encoding="utf-8").strip()
        cls.toml = tomllib.loads((ROOT / "rust/Cargo.toml").read_text(encoding="utf-8"))
        cls.lock = tomllib.loads((ROOT / "rust/Cargo.lock").read_text(encoding="utf-8"))
        cls.workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        cls.notes = (ROOT / "release/NOTES.md").read_text(encoding="utf-8")

    def test_version_is_stable_semver_and_matches_cargo_lock(self):
        self.assertRegex(self.tag, r"^v[0-9]+\.[0-9]+\.[0-9]+$")
        version = self.tag.removeprefix("v")
        self.assertEqual(self.toml["package"]["version"], version)
        self.assertTrue(any(package.get("name") == "socratopia-cli"
                            and package.get("version") == version
                            for package in self.lock["package"]))
        self.assertIn(self.tag, self.notes)
        self.assertIn("正式版", self.notes)

    def test_release_is_latest_not_prerelease_and_never_overwritten(self):
        self.assertIn("RELEASE_FLAGS+=(--latest)", self.workflow)
        self.assertIn("RELEASE_FLAGS+=(--prerelease)", self.workflow)
        self.assertIn('if [[ "$TAG" == *-* ]]', self.workflow)
        self.assertIn('gh release view "$TAG"', self.workflow)
        self.assertIn('refusing to overwrite', self.workflow)
        self.assertIn('test "$LATEST" = "$TAG"', self.workflow)
        self.assertIn('select(.isLatest)', self.workflow)

    def test_all_native_architectures_and_sha256_are_publish_gated(self):
        for platform in ("linux-x86_64", "windows-x86_64",
                         "macos-x86_64", "macos-arm64"):
            self.assertIn(f"platform: {platform}", self.workflow)
            self.assertIn(f"-{platform}.zip", self.notes)
        self.assertIn("sha256sum --check *.sha256", self.workflow)
        self.assertIn("assert executed.stdout.strip()", self.workflow)
        self.assertIn('not any("/DATA/" in n or "/TEXTBOOK/" in n for n in names)', self.workflow)

    def test_release_describes_python_requirement_and_unverified_ui(self):
        for phrase in ("无需自行安装 Rust 或 Python", "PyInstaller", "Cherry Studio", "尚未宣称通过"):
            self.assertIn(phrase, self.notes)
        self.assertIn("scripts/check.py --strict", self.workflow)
        self.assertIn("socratopia-backend", self.workflow)
        self.assertIn("--require-backend", self.workflow)
        self.assertIn("SOCRATOPIA_REQUIRE_BUNDLED", self.workflow)


if __name__ == "__main__":
    unittest.main()
