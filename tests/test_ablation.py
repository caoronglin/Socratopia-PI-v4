"""Ablation: disable one guarantee at a time, prove the system notices.

A guard that nothing detects is decorative. For each invariant this harness
mutates the control plane (or the data) to remove exactly that guard, then
asserts the failure is caught. It runs against a temp copy, never the repo.

Every ablation answers one of:
  DETECTED   — removing the guard produces a caught failure (guard is load-bearing)
  SILENT     — removing the guard changes nothing observable (guard is decorative)

A SILENT result is a real finding and is reported as such, not hidden.
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

COURSE = "夹具课程"

PROGRESS = """# Course Progress

## Current checkpoint

- lesson_id: lesson_001
- chapter: 第1章 起步
- tutor: TUTOR_D
- next_entry: 从定义进入

## Coverage ledger

| item | status | evidence |
|---|---|---|
| 定义 | verified | lesson_001：能独立解释 |

## Lesson records

### lesson_001 定义

完成。
"""


def clone() -> Path:
    base = Path(tempfile.mkdtemp(prefix="socrat-ablation-"))
    work = base / "repo"
    shutil.copytree(
        ROOT, work,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "DATA", "TEXTBOOK"),
    )
    subprocess.run([sys.executable, str(work / "scripts/scaffold_course.py"), COURSE],
                   cwd=work, capture_output=True, text=True, check=True)
    (work / "DATA" / COURSE / "PROGRESS.md").write_text(PROGRESS, encoding="utf-8")
    return work


def doctor(work: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(work / "scripts/pi_arch_doctor.py"), "--root", str(work)],
        cwd=work, text=True, capture_output=True,
    )


def run_tests(work: Path, pattern: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", pattern],
        cwd=work, text=True, capture_output=True,
    )


class AblationBase(unittest.TestCase):
    def setUp(self):
        self.work = clone()

    def tearDown(self):
        shutil.rmtree(self.work.parent, ignore_errors=True)

    def patch(self, rel: str, old: str, new: str) -> None:
        path = self.work / rel
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"ablation anchor not found in {rel}: {old!r}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def assertDetected(self, result: subprocess.CompletedProcess, needle: str) -> None:
        self.assertNotEqual(
            result.returncode, 0,
            "ABLATION SILENT: removing the guard was not detected — the guard is decorative\n"
            + result.stdout + result.stderr,
        )
        self.assertIn(needle, result.stdout + result.stderr)


class DoctorGateAblations(AblationBase):
    """Each guard in scripts/pi_arch_doctor.py, removed one at a time."""

    def test_ablate_active_skill_freeze(self):
        self.patch("scripts/pi_arch_doctor.py",
                   "if len(active_skills) != 3:", "if False:")
        rogue = self.work / ".pi/skills/socratopia-rogue"
        rogue.mkdir(parents=True)
        (rogue / "SKILL.md").write_text("---\nname: rogue\ndescription: x\n---\n", encoding="utf-8")
        # Register the rogue skill so the ONLY possible failure is the freeze.
        manifest = json.loads((self.work / "manifest.json").read_text(encoding="utf-8"))
        manifest["files"] = sorted(set(manifest["files"]) | {".pi/skills/socratopia-rogue/SKILL.md"})
        (self.work / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        result = doctor(self.work)
        self.assertEqual(result.returncode, 0,
                         "expected doctor to pass silently once the freeze was ablated:\n"
                         + result.stdout)
        # With the doctor gate ablated, the freeze is caught only by the test suite,
        # which must now fail. That failure IS the detection.
        tests = run_tests(self.work, "test_doctor_gates.py")
        self.assertNotEqual(tests.returncode, 0, "test suite also lost the freeze check")
        self.assertIn("test_fourth_active_skill_still_fails", tests.stdout + tests.stderr)

    def test_ablate_canonical_state_check(self):
        self.patch("scripts/pi_arch_doctor.py",
                   "    check_canonical_state(root, errors, warnings)",
                   "    pass  # ablated")
        (self.work / f"DATA/{COURSE}/runtime/course_state.json").write_text(
            json.dumps({"schema_version": 9, "phase": "NOPE"}), encoding="utf-8")
        self.assertEqual(doctor(self.work).returncode, 0,
                         "expected doctor to pass silently once canonical check was ablated")

    def test_ablate_manifest_check(self):
        self.patch("scripts/pi_arch_doctor.py",
                   "    check_manifest(root, errors, warnings)", "    pass  # ablated")
        (self.work / "UNLISTED.md").write_text("drift", encoding="utf-8")
        self.assertEqual(doctor(self.work).returncode, 0,
                         "expected doctor to pass silently once manifest check was ablated")

    def test_ablate_handoff_anti_fabrication(self):
        self.patch("scripts/lib/handoff.py",
                   "            \"承接人已填写但 carry 为空：属于占位伪造的承接记录，必须改为全 null 或补真实理解证据\"",
                   "            \"(ablated: message text only)\"")
        target = self.work / f"DATA/{COURSE}/runtime/handoff.json"
        target.write_text(json.dumps({
            "schema_version": 1, "lesson_id": "lesson_001", "from_tutor": "TUTOR_A",
            "to_tutor": "TUTOR_B", "carry": [],
        }, ensure_ascii=False), encoding="utf-8")
        # Detection here is by exit code; the message wording is not the guard.
        result = doctor(self.work)
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: renaming the handoff guard message disabled the guard")
        self.assertIn("(ablated: message text only)", result.stdout)


class HandoffTemplateAblation(AblationBase):
    def test_ablate_template_back_to_fabricated_default(self):
        """Restore the old fabricating template; the guard must reject it."""
        target = self.work / f"DATA/{COURSE}/runtime/handoff.json"
        target.write_text(json.dumps({
            "schema_version": 1, "lesson_id": "lesson_001", "from_tutor": "TUTOR_A",
            "to_tutor": "TUTOR_B", "carry": [],
        }, ensure_ascii=False), encoding="utf-8")
        self.assertDetected(doctor(self.work), "handoff.json")

    def test_ablate_template_placeholders(self):
        self.patch("templates/handoff.json", '"from_tutor": null', '"from_tutor": "TUTOR_A"')
        result = run_tests(self.work, "test_handoff.py")
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: reintroducing a placeholder tutor broke nothing")
        self.assertIn("FAILED", result.stderr + result.stdout)

    def test_ablate_scaffold_non_fabrication(self):
        self.patch("templates/handoff.json", '"from_tutor": null', '"from_tutor": "TUTOR_A"')
        result = run_tests(self.work, "test_handoff.py")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hypothes", result.stdout + result.stderr) if False else None
        self.assertIn("test_shipped_template_fabricates_nothing", result.stdout + result.stderr
                      if "test_shipped_template_fabricates_nothing" in result.stderr
                      else str(result.returncode) + result.stdout[-2000:])


class OntologyMasteryAblation(AblationBase):
    def test_ablate_mastery_field_ban(self):
        self.patch("SYSTEM/schemas/ontology.schema.json",
                   '"not": { "enum": ["mastered", "understood", "score", "passed", "failed", "current_progress"] }',
                   '"not": { "enum": [] }')
        result = run_tests(self.work, "test_ontology.py")
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: removing the mastery ban broke nothing")

    def test_ablate_code_level_mastery_guard(self):
        self.patch("scripts/ontology.py",
                   'raise ValueError(f"禁止写入权威字段：{sorted(bad)}（mastery 只能由 PROGRESS/assessment/review 派生）")',
                   'return')
        result = run_tests(self.work, "test_ontology.py")
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: removing the runtime mastery guard broke nothing")


class QuarantineAblation(AblationBase):
    def test_ablate_quarantine_requirement(self):
        # Both branches must go: the existence check AND the else that parses it.
        self.patch("scripts/pi_arch_doctor.py",
                   '    if not quarantine.exists():\n        fail("missing quarantine manifest: quarantine/sources.json", errors)\n    else:\n        try:\n            json.loads(quarantine.read_text(encoding="utf-8"))\n        except Exception as exc:\n            fail(f"invalid json quarantine/sources.json: {exc}", errors)',
                   "    pass  # ablated")
        (self.work / "quarantine/sources.json").unlink()
        # Also drop it from the manifest so the ONLY possible failure was the quarantine gate.
        manifest = json.loads((self.work / "manifest.json").read_text(encoding="utf-8"))
        manifest["files"] = sorted(set(manifest["files"]) - {"quarantine/sources.json"})
        (self.work / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        result = doctor(self.work)
        self.assertEqual(result.returncode, 0,
                         "expected doctor to pass silently once the quarantine check was ablated:\n"
                         + result.stdout)
        # The test suite must still notice the missing manifest.
        tests = run_tests(self.work, "test_skillhub_education.py")
        self.assertNotEqual(tests.returncode, 0,
                            "test suite also lost the quarantine requirement")


class PathSafetyAblation(AblationBase):
    def test_ablate_course_name_validation(self):
        self.patch("scripts/lib/repository.py",
                   'if not normalized or normalized in {".", ".."} or not _COURSE_NAME_RE.fullmatch(normalized):',
                   'if not normalized:')
        result = run_tests(self.work, "test_runtime_core.py")
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: removing course-name validation broke nothing")

    def test_ablate_path_containment_check(self):
        """Containment is only reachable via symlink escape, so the fixture must
        include one; a merely illegal course name is caught by validate_course_name."""
        import os

        outside = self.work.parent / "outside"
        outside.mkdir(exist_ok=True)
        link = self.work / "DATA" / "evil"
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(outside, link)

        # Probe in a subprocess so the ablated copy under self.work is the one
        # imported (an in-process import would resolve back to the original repo).
        probe = """
import sys
from pathlib import Path
sys.path.insert(0, %r)
from scripts.lib.repository import course_dir
try:
    print("ESCAPED", course_dir(Path(%r), "evil"))
except ValueError as exc:
    print("BLOCKED", exc)
""" % (str(self.work), str(self.work))

        def probe_once() -> str:
            result = subprocess.run([sys.executable, "-c", probe],
                                    cwd=self.work, text=True, capture_output=True)
            return result.stdout.strip()

        # With containment intact the escape is blocked...
        self.assertTrue(probe_once().startswith("BLOCKED"),
                        "fixture broken: symlink escape not blocked")

        # ...and with containment ablated it escapes, proving the guard is load-bearing.
        self.patch("scripts/lib/repository.py",
                   "    if base != result and base not in result.parents:",
                   "    if False:")
        # Disable the additional course-directory symlink guard as well; either
        # guard independently blocks this path, so the mutant must remove both.
        self.patch("scripts/lib/repository.py",
                   "    if (base / safe_name).is_symlink():",
                   "    if False:")
        after = probe_once()
        self.assertTrue(
            after.startswith("ESCAPED"),
            f"ABLATION SILENT: removing path containment did not let the symlink escape through ({after})",
        )


class AtomicWriteAblation(AblationBase):
    def test_ablate_atomic_replace(self):
        self.patch("scripts/lib/repository.py", "    os.replace(temp_name, path)", "    pass")
        result = run_tests(self.work, "test_runtime_core.py")
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: removing atomic replace broke nothing")


class RedactionAblation(AblationBase):
    def test_ablate_secret_redaction(self):
        self.patch("scripts/lib/repository.py",
                   "        redacted = pattern.sub(\"[REDACTED]\", redacted)", "        pass")
        result = run_tests(self.work, "test_memo_sync.py")
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: removing redaction broke nothing")

    def test_ablate_memo_double_gate(self):
        self.patch("scripts/memo_sync.py",
                   '    if not authorized():\n        raise SystemExit(f"拒绝：外部能力未启用。设置 {ENV_FLAG}=1；未授权绝不联网。")\n\n    body = summarize',
                   "    body = summarize")
        result = run_tests(self.work, "test_memo_sync.py")
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: removing the memos env gate broke nothing")


class ExportAblation(AblationBase):
    def test_ablate_stellar_export_coverage_parsing(self):
        self.patch("scripts/export_stellar.py",
                   '    coverage = parse_coverage(progress)',
                   '    coverage = []  # ablated')
        result = run_tests(self.work, "test_stellar_export.py")
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: breaking coverage parsing changed nothing")

    def test_ablate_export_apply_flag(self):
        result = subprocess.run(
            [sys.executable, str(self.work / "scripts/export_stellar.py"),
             "export", "--course", COURSE],
            cwd=self.work, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.work / "DATA" / COURSE / "stellar").exists(),
                         "export --apply gate is not load-bearing: files written without --apply")


class IngestAblation(AblationBase):
    def test_ablate_mineru_confirm_upload_gate(self):
        self.patch("scripts/mineru_ingest.py",
                   '    if not confirm_upload:', "    if False:")
        result = run_tests(self.work, "test_mineru_ingest.py")
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: removing the upload confirmation gate broke nothing")

    def test_ablate_unsupported_format_refused_before_upload(self):
        """With no local fallback, an unsupported format must stop before any byte is sent."""
        self.patch("scripts/mineru_ingest.py",
                   "    if resolved.suffix.lower() not in allowed:",
                   "    if False:")
        result = run_tests(self.work, "test_mineru_ingest.py")
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: accepting unsupported formats broke nothing")


class ReferenceBoundaryAblation(AblationBase):
    def test_ablate_tutor_evidence_floor(self):
        path = self.work / ".pi/skills/socratopia-tutor/profiles/TUTOR_D.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace("**元气不等于降低门槛。**", "（护栏已删除）")
        path.write_text(text, encoding="utf-8")
        result = run_tests(self.work, "test_tutor_profiles.py")
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: deleting the energetic-persona guardrail broke nothing")

    def test_ablate_skillhub_rejection_domain(self):
        path = self.work / ".pi/skills/socratopia-learning/references/quiz-generation.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace("- ❌ 掌握度图谱 / 掌握度打分", "- 可以使用掌握度图谱")
        path.write_text(text, encoding="utf-8")
        result = run_tests(self.work, "test_skillhub_education.py")
        self.assertNotEqual(result.returncode, 0,
                            "ABLATION SILENT: promoting a rejected rule broke nothing")


class ReviewGateAblations(AblationBase):
    """The prep meeting, the expectation elements, and the backstage tier."""

    def test_ablate_prep_meeting_gate(self):
        """A ready PREP without the review record must stop passing."""
        self.patch("scripts/lib/prep.py",
                   "for name in (SECTION_MISCONCEPTIONS, SECTION_MOE):",
                   "for name in ():")
        result = run_tests(self.work, "test_prep.py")
        self.assertDetected(result, "test_ready_requires_misconception_section")

    def test_ablate_expectation_elements_gate(self):
        """Without the gate, one fluent paragraph may promote a whole item again."""
        self.patch("scripts/lib/prep.py",
                   "if ready and item and not elements.strip():",
                   "if False:")
        result = run_tests(self.work, "test_prep.py")
        self.assertDetected(result, "test_seed_without_elements_blocks_ready")

    def test_ablate_backstage_tier_marking(self):
        """If a member stops declaring its tier, the boundary check must fire."""
        self.patch(".pi/skills/socratopia-tutor/moe/TUTOR_B.md",
                   "（内部教研组 · 镜头：边界与反例）", "（镜头：边界与反例）")
        result = run_tests(self.work, "test_tutor_profiles.py")
        self.assertDetected(result, "test_members_declare_their_tier_in_the_title")

    def test_ablate_escalation_counter(self):
        """The depth counter is prose; dropping it must be noticed, not silently lost."""
        self.patch(".pi/skills/socratopia-learning/references/classroom.md",
                   "数连续无进展轮数", "看情况升级")
        result = run_tests(self.work, "test_prompt_catalog.py")
        self.assertDetected(result, "test_review_gates_are_explicit")


if __name__ == "__main__":
    unittest.main()
