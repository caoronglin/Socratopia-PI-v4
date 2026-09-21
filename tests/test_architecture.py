import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArchitectureTests(unittest.TestCase):
    def test_doctor_passes(self):
        p = subprocess.run([sys.executable, str(ROOT / "scripts/pi_arch_doctor.py")], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_schemas_are_json(self):
        for p in (ROOT / "SYSTEM/schemas").glob("*.json"):
            json.loads(p.read_text(encoding="utf-8"))

    def test_exactly_three_active_skills(self):
        skills = list((ROOT / ".pi/skills").glob("*/SKILL.md"))
        self.assertEqual({p.parent.name for p in skills}, {"socratopia-learning", "socratopia-tutor", "socratopia-engineering"})


if __name__ == "__main__":
    unittest.main()
