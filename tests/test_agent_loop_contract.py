"""Check agent-loop stop contracts independently of obsolete host-specific prompts."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class AgentLoopPromptContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernel = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        cls.spec = (ROOT / "SYSTEM/SPEC/AGENT_LOOP.md").read_text(encoding="utf-8")
        cls.runtime = (ROOT / "platform_api/agentscope_runtime.py").read_text(encoding="utf-8")

    def test_bounded_state_machine(self):
        for state in ("ROUTE", "INSPECT", "ACT", "VERIFY", "DONE", "YIELD", "BLOCKED", "NEXT"):
            self.assertIn(state, self.spec)
        self.assertIn("ROUTE → INSPECT → ACT → VERIFY", self.spec)

    def test_safety_boundaries_are_backed_by_code(self):
        self.assertIn("AgentScope", self.kernel)
        self.assertIn("FastAPI", self.kernel)
        self.assertIn("MAX_IN_FLIGHT = 4", self.runtime)
        self.assertIn("TIMEOUT_SECONDS = 90", self.runtime)
        self.assertIn("if scope in _active:", self.runtime)
        self.assertIn("asyncio.wait_for", self.runtime)

    def test_model_is_not_final_course_authority(self):
        for term in ("2700", "PROGRESS.md", "SHA", "课程隔离"):
            self.assertIn(term, self.kernel)
        self.assertIn("禁止第二套模型循环", self.kernel)
        self.assertIn("YIELD", self.spec)

if __name__ == "__main__":
    unittest.main()
