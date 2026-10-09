"""Negative tests for pi_arch_doctor.py itself.

plan.md §13 promised ERROR on `canonical state missing/invalid`, but the check
lived only in the per-course CLIs, so `/health` (which runs the doctor) missed
the most damaging corruption class. These tests pin that gate.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def make_repo() -> Path:
    """Copy the control plane into a temp dir so doctor can run in isolation."""
    target = Path(tempfile.mkdtemp()) / "repo"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "DATA", "TEXTBOOK"),
    )
    return target


def run_doctor(root: Path, course: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts/pi_arch_doctor.py"), "--root", str(root)]
        + (["--course", course] if course is not None else []),
        cwd=root,
        text=True,
        capture_output=True,
    )


class DoctorGateTests(unittest.TestCase):
    def setUp(self):
        self._dirs: list[str] = []
        self.work = make_repo()
        self._dirs.append(str(self.work.parent))
        self.runtime = self.work / "DATA/夹具课程/runtime"
        self.runtime.mkdir(parents=True)
        self.write("course_state.json", {
            "schema_version": 1, "course": "夹具课程", "phase": "setup", "lesson_id": None,
            "readiness": {"catalog": "missing", "prep": "missing", "runtime": "ok", "reteach": "clear"},
            "blockers": ["missing_coursebook", "missing_prep"],
            "updated_at": "2026-01-01T00:00:00+00:00",
        })
        self.write("tasks.json", {"schema_version": 1, "tasks": []})
        self.write("handoff.json", {
            "schema_version": 1, "lesson_id": None, "from_tutor": None,
            "to_tutor": None, "carry": [],
        })

    def tearDown(self):
        for path in self._dirs:
            shutil.rmtree(path, ignore_errors=True)

    def write(self, name: str, payload: dict) -> None:
        (self.runtime / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # --- positive -------------------------------------------------------
    def test_missing_authoritative_runtime_file_is_error(self):
        (self.runtime / "handoff.json").unlink()
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("missing runtime file", result.stdout)

    def test_valid_canonical_state_passes(self):
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scoped_doctor_ignores_corrupt_other_course(self):
        other = self.work / "DATA/另一门课/runtime"
        other.mkdir(parents=True)
        (other / "course_state.json").write_text("{broken", encoding="utf-8")
        graph = other.parent / "ontology/graph.jsonl"
        graph.parent.mkdir()
        graph.write_text("{broken", encoding="utf-8")
        result = run_doctor(self.work, "夹具课程")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("另一门课", result.stdout)
        self.assertEqual(run_doctor(self.work).returncode, 1)

    def test_scoped_doctor_rejects_missing_and_unsafe_course(self):
        result = run_doctor(self.work, "不存在")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("missing course", result.stdout)
        result = run_doctor(self.work, "../夹具课程")
        self.assertEqual(result.returncode, 2)
        self.assertIn("非法课程名", result.stderr)

    def test_scoped_doctor_rejects_target_links_before_reading(self):
        other = self.work / "DATA/另一门课"
        other.mkdir(parents=True)
        (other / "bad.json").write_text("{broken", encoding="utf-8")
        (self.runtime / "foreign.json").symlink_to(other / "bad.json")
        result = run_doctor(self.work, "夹具课程")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("cross-course symlink", result.stdout)
        self.assertNotIn("invalid json", result.stdout)

    def test_scoped_doctor_ignores_other_course_symlink(self):
        (self.work / "DATA/异课链接").symlink_to(self.runtime.parent, target_is_directory=True)
        result = run_doctor(self.work, "夹具课程")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(run_doctor(self.work).returncode, 1)

    def test_doctor_rejects_symlinked_containers_before_reading(self):
        for top in ("DATA", "TEXTBOOK"):
            with self.subTest(top=top):
                work = make_repo()
                self._dirs.append(str(work.parent))
                external = work.parent / "external"
                runtime = external / "夹具课程/runtime"
                runtime.mkdir(parents=True)
                (runtime / "course_state.json").write_text("{broken", encoding="utf-8")
                (work / top).symlink_to(external, target_is_directory=True)
                for scope in (None, "夹具课程"):
                    result = run_doctor(work, scope)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn(f"course container is a symlink: {top}", result.stdout)
                    self.assertNotIn("invalid json", result.stdout)

    # --- negative: course_state ----------------------------------------
    def test_corrupt_course_state_is_error(self):
        """The exact corruption the old doctor silently accepted."""
        self.write("course_state.json", {
            "schema_version": 1, "course": "夹具课程", "phase": "NOT_A_PHASE",
            "readiness": {"catalog": "bogus"}, "blockers": "not-a-list", "updated_at": "",
        })
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("ERROR", result.stdout)
        self.assertIn("course_state.json", result.stdout)
        self.assertIn("phase 不在允许集合", result.stdout)

    def test_malformed_course_state_json_does_not_crash(self):
        (self.runtime / "course_state.json").write_text("{not json", encoding="utf-8")
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid json", result.stdout)

    def test_cross_course_state_directory_mismatch_is_error(self):
        self.write("course_state.json", {
            "schema_version": 1, "course": "另一门课", "phase": "setup", "lesson_id": None,
            "readiness": {"catalog": "ok", "prep": "ok", "runtime": "ok", "reteach": "clear"},
            "blockers": [], "updated_at": "2026-01-01T00:00:00+00:00",
        })
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("与所在目录", result.stdout)

    # --- negative: tasks -----------------------------------------------
    def test_invalid_task_status_is_error(self):
        self.write("tasks.json", {
            "schema_version": 1,
            "tasks": [{"id": "a", "idempotency_key": "k", "kind": "review",
                       "course": "夹具课程", "status": "bogus", "attempts": 0}],
        })
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("非法 status", result.stdout)

    def test_task_owned_by_other_course_is_error(self):
        self.write("tasks.json", {
            "schema_version": 1,
            "tasks": [{"id": "a", "idempotency_key": "k", "kind": "review",
                       "course": "另一门课", "status": "pending", "attempts": 0}],
        })
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("跨课程污染", result.stdout)

    # --- negative: handoff ---------------------------------------------
    def test_fabricated_placeholder_handoff_is_error(self):
        self.write("handoff.json", {
            "schema_version": 1, "lesson_id": "lesson_001", "from_tutor": "TUTOR_A",
            "to_tutor": "TUTOR_B", "carry": [],
        })
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("占位伪造", result.stdout)

    # --- negative: manifest --------------------------------------------
    def test_manifest_drift_is_error(self):
        (self.work / "AGENTS.md.unlisted").write_text("drift", encoding="utf-8")
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("file missing from manifest", result.stdout)

    def test_manifest_listing_absent_file_is_error(self):
        manifest = json.loads((self.work / "manifest.json").read_text(encoding="utf-8"))
        manifest["files"].append("scripts/does_not_exist.py")
        (self.work / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("manifest lists missing file", result.stdout)

    def test_missing_manifest_warns_instead_of_crashing(self):
        """Regression: check_manifest referenced an undefined `warnings` (NameError)."""
        (self.work / "manifest.json").unlink()
        result = run_doctor(self.work)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("WARN: missing manifest.json", result.stdout)

    def test_cache_dirs_do_not_trigger_manifest_drift(self):
        cache = self.work / ".pytest_cache"
        cache.mkdir(exist_ok=True)
        (cache / "README.md").write_text("x", encoding="utf-8")
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_oversized_control_file_only_warns(self):
        """plan §10 soft thresholds are WARN, never a hard failure."""
        profile = self.work / ".pi/skills/socratopia-tutor/profiles/TUTOR_D.md"
        profile.write_text(profile.read_text(encoding="utf-8") + "填充内容。" * 400, encoding="utf-8")
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("token soft cap exceeded (profile)", result.stdout)

    def test_pi_system_override_is_error(self):
        """ADR-002 / plan §13: .pi/SYSTEM.md is forbidden, not just discouraged."""
        (self.work / ".pi/SYSTEM.md").write_text("override", encoding="utf-8")
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("forbidden override: .pi/SYSTEM.md", result.stdout)

    def test_machine_specific_paths_in_control_files_are_errors(self):
        for snippet, label in (("C:\\Users\\alice\\x", "Windows user path"), ("/Users/alice/proj", "macOS user path")):
            with self.subTest(snippet=snippet):
                work = make_repo()
                self._dirs.append(str(work.parent))
                agents = work / "AGENTS.md"
                agents.write_text(agents.read_text(encoding="utf-8") + f"\n工具在 {snippet}\n", encoding="utf-8")
                result = run_doctor(work)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(label, result.stdout)

    # --- preserved gates ----------------------------------------------
    def test_fourth_active_skill_still_fails(self):
        rogue = self.work / ".pi/skills/socratopia-rogue"
        rogue.mkdir(parents=True, exist_ok=True)
        (rogue / "SKILL.md").write_text("---\nname: rogue\ndescription: x\n---\n", encoding="utf-8")
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("active skill count must be 3", result.stdout)

    def test_missing_required_runtime_tool_fails(self):
        (self.work / "scripts/task_queue.py").unlink()
        result = run_doctor(self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing required file: scripts/task_queue.py", result.stdout)

    def test_doctor_is_read_only(self):
        """A failing doctor run must not have repaired or rewritten anything."""
        self.write("course_state.json", {"schema_version": 9})
        before = (self.runtime / "course_state.json").read_text(encoding="utf-8")
        run_doctor(self.work)
        self.assertEqual((self.runtime / "course_state.json").read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
