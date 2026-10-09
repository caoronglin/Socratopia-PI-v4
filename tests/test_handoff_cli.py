"""`scripts/handoff.py` write/validate entrypoint (ADR-006) and state-producer unity."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.course_state import default_state, validate_state  # noqa: E402

COURSE = "夹具课程"
CARRY = [{"knowledge_point": "链式法则", "status": "needs_review", "evidence": "lesson_003：复合函数顺序说反"}]


def clone() -> Path:
    base = Path(tempfile.mkdtemp(prefix="socrat-handoff-"))
    work = base / "repo"
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "__pycache__", "DATA", "TEXTBOOK"))
    subprocess.run([sys.executable, str(work / "scripts/scaffold_course.py"), COURSE],
                   cwd=work, capture_output=True, text=True, check=True)
    return work


def cli(work: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(work / "scripts/handoff.py"), *args],
                          cwd=work, capture_output=True, text=True)


class HandoffCliTests(unittest.TestCase):
    def setUp(self):
        self.work = clone()
        self.path = self.work / "DATA" / COURSE / "runtime/handoff.json"

    def tearDown(self):
        shutil.rmtree(self.work.parent, ignore_errors=True)

    def set_args(self, **over):
        values = {"lesson-id": "lesson_003", "from-tutor": "TUTOR_A", "to-tutor": "TUTOR_E",
                  "carry": json.dumps(CARRY, ensure_ascii=False)}
        values.update(over)
        args = ["set", "--course", COURSE]
        for key, value in values.items():
            args += [f"--{key}", value]
        return args

    def test_fresh_course_validates_as_not_yet_handed_off(self):
        result = cli(self.work, "validate", "--course", COURSE)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("PASS", result.stdout)

    def test_set_requires_apply(self):
        result = cli(self.work, *self.set_args())
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(json.loads(self.path.read_text(encoding="utf-8"))["lesson_id"])

    def test_set_with_evidence_persists_and_validates(self):
        result = cli(self.work, *self.set_args(), "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        stored = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(stored["to_tutor"], "TUTOR_E")
        self.assertEqual(stored["carry"][0]["status"], "needs_review")
        self.assertEqual(cli(self.work, "validate", "--course", COURSE).returncode, 0)

    def test_empty_carry_is_refused_and_nothing_written(self):
        before = self.path.read_text(encoding="utf-8")
        result = cli(self.work, *self.set_args(carry="[]"), "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("占位伪造", result.stdout)
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_invalid_status_is_refused(self):
        bad = json.dumps([{**CARRY[0], "status": "mastered"}], ensure_ascii=False)
        result = cli(self.work, *self.set_args(carry=bad), "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("非法 status", result.stdout)

    def test_same_tutor_is_refused(self):
        result = cli(self.work, *self.set_args(**{"to-tutor": "TUTOR_A"}), "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("不能相同", result.stdout)

    def test_secrets_in_evidence_are_redacted(self):
        leaky = json.dumps([{**CARRY[0], "evidence": "见 token=abc123secret 记录"}], ensure_ascii=False)
        self.assertEqual(cli(self.work, *self.set_args(carry=leaky), "--apply").returncode, 0)
        self.assertNotIn("abc123secret", self.path.read_text(encoding="utf-8"))

    def test_clear_resets_to_no_handoff(self):
        cli(self.work, *self.set_args(), "--apply")
        self.assertEqual(cli(self.work, "clear", "--course", COURSE, "--apply").returncode, 0)
        stored = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual((stored["lesson_id"], stored["carry"]), (None, []))

    def test_rejects_unsafe_course_name(self):
        result = cli(self.work, "show", "--course", "../evil")
        self.assertNotEqual(result.returncode, 0)


class CourseStateProducerTests(unittest.TestCase):
    def test_template_matches_default_state(self):
        """templates/course_state.json is documentation of default_state(); they must not drift."""
        template = json.loads((ROOT / "templates/course_state.json").read_text(encoding="utf-8"))
        produced = default_state("<course>")
        template.pop("updated_at")
        produced.pop("updated_at")
        self.assertEqual(template, produced)

    def test_scaffolded_state_is_valid_and_complete(self):
        work = clone()
        try:
            state = json.loads((work / "DATA" / COURSE / "runtime/course_state.json").read_text(encoding="utf-8"))
            self.assertEqual(validate_state(state), [])
            self.assertEqual(state["course"], COURSE)
            self.assertEqual(set(state), set(default_state(COURSE)))
        finally:
            shutil.rmtree(work.parent, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
