"""Deterministic release packaging: manifest allowlist, no private course data."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.package_release import make_zip


class PackageReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="socrat-zip-")
        self.root = Path(self.tmp.name)
        (self.root / ".pi/prompts").mkdir(parents=True)
        (self.root / ".pi/prompts/start-class.md").write_text("lesson", encoding="utf-8")
        (self.root / "AGENTS.md").write_text("project rules", encoding="utf-8")
        (self.root / "release").mkdir()
        (self.root / "release/VERSION").write_text("v4.1.0-rc.1\n", encoding="utf-8")
        (self.root / "release/NOTES.md").write_text("release note", encoding="utf-8")
        (self.root / "manifest.json").write_text(
            json.dumps({"files": ["AGENTS.md", ".pi/prompts/start-class.md"]}), encoding="utf-8")
        (self.root / "DATA/私有课堂").mkdir(parents=True)
        (self.root / "DATA/私有课堂/PROGRESS.md").write_text("secret academic record", encoding="utf-8")
        (self.root / "TEXTBOOK/私人教材").mkdir(parents=True)
        (self.root / "TEXTBOOK/私人教材/book.md").write_text("private textbook", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_archives_verified_allowlist_and_two_identical_builds(self):
        a = make_zip(self.root, self.root / "out1", "v4.1.0-rc.1")
        b = make_zip(self.root, self.root / "out2", "v4.1.0-rc.1")
        self.assertEqual(a["sha256"], b["sha256"])
        self.assertEqual(Path(a["archive"]).read_bytes(), Path(b["archive"]).read_bytes())
        content = Path(a["archive"]).read_bytes()
        self.assertNotIn(b"secret academic record", content)
        self.assertNotIn(b"private textbook", content)
        self.assertEqual(hashlib.sha256(content).hexdigest(), a["sha256"])
        with zipfile.ZipFile(a["archive"]) as stream:
            names = stream.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertIn("Socratopia-PI-v4-v4.1.0-rc.1/AGENTS.md", names)
            self.assertIn("Socratopia-PI-v4-v4.1.0-rc.1/manifest.json", names)
            self.assertTrue(all("/DATA/" not in n and "/TEXTBOOK/" not in n for n in names))
        self.assertIn(a["sha256"], Path(a["checksum"]).read_text(encoding="utf-8"))

    def test_manifest_traversal_and_secrets_are_rejected(self):
        for invalid in ("../secret.md", "DATA/x.md", "TEXTBOOK/book.md", ".env",
                        ".git/config", "scripts/../../hidden", "C:\\secrets"):
            with self.subTest(path=invalid):
                (self.root / "manifest.json").write_text(
                    json.dumps({"files": ["AGENTS.md", invalid]}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    make_zip(self.root, self.root / "out", "v4.1.0-rc.1")

    def test_missing_or_symlink_in_manifest_rejected(self):
        (self.root / "manifest.json").write_text(
            json.dumps({"files": ["missing.md"]}), encoding="utf-8")
        with self.assertRaises(ValueError):
            make_zip(self.root, self.root / "out", "v4.1.0-rc.1")
        try:
            (self.root / "alias.md").symlink_to(self.root / "AGENTS.md")
        except OSError:
            self.skipTest("symlinks unavailable")
        (self.root / "manifest.json").write_text(
            json.dumps({"files": ["alias.md"]}), encoding="utf-8")
        with self.assertRaises(ValueError):
            make_zip(self.root, self.root / "out", "v4.1.0-rc.1")

    def test_linux_bundle_contains_real_executable_path_and_checksum(self):
        binary = self.root / "rust/target/release/socratopia"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"\x7fELF" + b"FAKE-NATIVE-LINUX-CLI")
        result = make_zip(self.root, self.root / "out", "v4.2.0-rc.1",
                          platform="linux-x86_64",
                          cli_binary=Path("rust/target/release/socratopia"))
        self.assertTrue(result["archive"].endswith("-linux-x86_64.zip"))
        self.assertEqual(result["files"], 6)
        with zipfile.ZipFile(result["archive"]) as stream:
            entry = "Socratopia-PI-v4-v4.2.0-rc.1/bin/socratopia"
            self.assertEqual(stream.read(entry), binary.read_bytes())
            self.assertEqual(stream.getinfo(entry).external_attr >> 16 & 0o111, 0o111)
        repeated = make_zip(self.root, self.root / "again", "v4.2.0-rc.1",
                            platform="linux-x86_64",
                            cli_binary=binary)
        self.assertEqual(result["sha256"], repeated["sha256"])

    def test_platform_and_binary_must_match(self):
        path = self.root / "rust/target/release/socratopia.exe"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"MZ" + b"TEST-WINDOWS-CLI")
        with self.assertRaises(ValueError):
            make_zip(self.root, self.root / "out", "v4.2.0-rc.1",
                     platform="windows-x86_64")
        with self.assertRaises(ValueError):
            make_zip(self.root, self.root / "out", "v4.2.0-rc.1",
                     cli_binary=path)
        with self.assertRaises(ValueError):
            make_zip(self.root, self.root / "out", "v4.2.0-rc.1",
                     platform="linux-x86_64", cli_binary=path)
        result = make_zip(self.root, self.root / "out", "v4.2.0-rc.1",
                          platform="windows-x86_64", cli_binary=path)
        with zipfile.ZipFile(result["archive"]) as stream:
            self.assertIn("Socratopia-PI-v4-v4.2.0-rc.1/bin/socratopia.exe", stream.namelist())

    def test_macos_binary_header_validation(self):
        path = self.root / "rust/target/release/socratopia"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"BAD-NON-MACHO")
        with self.assertRaises(ValueError):
            make_zip(self.root, self.root / "out", "v4.2.0-rc.1",
                     platform="macos-x86_64", cli_binary=path)
        path.write_bytes(b"\xcf\xfa\xed\xfe" + b"FAKE-MACHO-CLI")
        self.assertEqual(
            make_zip(self.root, self.root / "out", "v4.2.0-rc.1",
                     platform="macos-x86_64", cli_binary=path)["files"], 6)

    def test_binary_symlink_or_external_source_rejected(self):
        outside = self.root.parent / (self.root.name + "-external.bin")
        outside.write_bytes(b"\x7fELF" + b"EXTERNAL")
        with self.assertRaises(ValueError):
            make_zip(self.root, self.root / "out", "v4.2.0-rc.1",
                     platform="linux-x86_64", cli_binary=outside)
        outside.unlink()
        external = self.root / "rust/target/release/socratopia"
        external.parent.mkdir(parents=True)
        try:
            external.symlink_to(self.root / "AGENTS.md")
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError):
            make_zip(self.root, self.root / "out", "v4.2.0-rc.1",
                     platform="linux-x86_64", cli_binary=external)

    def test_invalid_version_rejected(self):
        with self.assertRaises(ValueError):
            make_zip(self.root, self.root / "out", "../not-a-version")


if __name__ == "__main__":
    unittest.main()
