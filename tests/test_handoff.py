"""Anti-fabrication rules for runtime/handoff.json (ADR-006).

A course that has not taught yet must be able to say "no handoff yet". The
regression these tests guard against is a scaffold template that invents a
TUTOR_A -> TUTOR_B carry-over for every fresh course.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.handoff import validate_handoff  # noqa: E402


def record(**overrides: object) -> dict:
    base = {
        "schema_version": 1,
        "lesson_id": None,
        "from_tutor": None,
        "to_tutor": None,
        "carry": [],
        "opening_anchor": "",
        "tone_note": "",
    }
    base.update(overrides)
    return base


class HandoffTemplateTests(unittest.TestCase):
    def test_shipped_template_fabricates_nothing(self):
        template = json.loads((ROOT / "templates/handoff.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_handoff(template), [])

    def test_template_names_no_tutor_and_no_lesson(self):
        template = json.loads((ROOT / "templates/handoff.json").read_text(encoding="utf-8"))
        for key in ("lesson_id", "from_tutor", "to_tutor"):
            self.assertIsNone(template[key], f"{key} 不得预填占位值")
        self.assertEqual(template["carry"], [])

    def test_legacy_fabricated_template_is_now_rejected(self):
        """The pre-fix template must be invalid, or the fix is cosmetic."""
        fabricated = record(
            lesson_id="lesson_001",
            from_tutor="TUTOR_A",
            to_tutor="TUTOR_B",
            carry=[],
        )
        errors = validate_handoff(fabricated)
        self.assertTrue(errors)
        self.assertTrue(any("占位伪造" in e for e in errors), errors)


class HandoffConsistencyTests(unittest.TestCase):
    def test_null_handoff_with_empty_carry_is_valid(self):
        self.assertEqual(validate_handoff(record()), [])

    def test_real_carry_over_is_valid(self):
        ok = record(
            lesson_id="lesson_007",
            from_tutor="TUTOR_A",
            to_tutor="TUTOR_B",
            carry=[
                {
                    "knowledge_point": "TCP 三次握手",
                    "status": "needs_review",
                    "evidence": "PROGRESS.md lesson_007：能复述但说不出 SYN-ACK 丢失的后果",
                    "recommended_angle": "用抓包实例切入",
                }
            ],
        )
        self.assertEqual(validate_handoff(ok), [])

    def test_partial_parties_rejected(self):
        errors = validate_handoff(record(from_tutor="TUTOR_A"))
        self.assertTrue(any("同时为 null 或同时有值" in e for e in errors), errors)

    def test_null_party_with_carry_rejected(self):
        errors = validate_handoff(
            record(carry=[{"knowledge_point": "x", "status": "introduced", "evidence": "e"}])
        )
        self.assertTrue(any("carry 必须为空" in e for e in errors), errors)

    def test_carry_item_requires_evidence(self):
        errors = validate_handoff(
            record(
                lesson_id="lesson_001",
                from_tutor="TUTOR_A",
                to_tutor="TUTOR_B",
                carry=[{"knowledge_point": "x", "status": "verified"}],
            )
        )
        self.assertTrue(any("evidence" in e for e in errors), errors)

    def test_carry_status_enum_enforced(self):
        errors = validate_handoff(
            record(
                lesson_id="lesson_001",
                from_tutor="TUTOR_A",
                to_tutor="TUTOR_B",
                carry=[{"knowledge_point": "x", "status": "mastered", "evidence": "e"}],
            )
        )
        self.assertTrue(any("非法 status" in e for e in errors), errors)

    def test_extra_field_rejected(self):
        self.assertTrue(validate_handoff(record(surprise=1)))


class HandoffSchemaParityTests(unittest.TestCase):
    """The shipped schema must express the same two legal shapes."""

    def test_schema_requires_carry_and_forbids_extras(self):
        schema = json.loads((ROOT / "SYSTEM/schemas/handoff.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["additionalProperties"], False)
        self.assertIn("carry", schema["required"])
        self.assertEqual(len(schema["oneOf"]), 2)

    def test_schema_party_fields_are_nullable(self):
        schema = json.loads((ROOT / "SYSTEM/schemas/handoff.schema.json").read_text(encoding="utf-8"))
        for key in ("lesson_id", "from_tutor", "to_tutor"):
            self.assertEqual(schema["properties"][key]["type"], ["string", "null"])


class ScaffoldHandoffTests(unittest.TestCase):
    def test_fresh_course_handoff_is_schema_and_validator_clean(self):
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "repo"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "DATA", "TEXTBOOK"),
            )
            course = "夹具课程"
            run = subprocess.run(
                [sys.executable, str(work / "scripts/scaffold_course.py"), course],
                cwd=work,
                text=True,
                capture_output=True,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            created = json.loads(
                (work / "DATA" / course / "runtime/handoff.json").read_text(encoding="utf-8")
            )
            self.assertEqual(validate_handoff(created), [])
            self.assertIsNone(created["from_tutor"])


if __name__ == "__main__":
    unittest.main()
