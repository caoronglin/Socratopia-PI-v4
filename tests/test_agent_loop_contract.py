"""Static constraints for a concise, bounded Cherry/Pi Agent Loop.

These assertions verify repository instructions; they do not run a live model
or impose runtime hard limits on Pi's own agent loop.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class AgentLoopPromptContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernel = read("AGENTS.md")
        cls.prompt = read("integrations/cherry-studio/AGENT_PROMPT.md")
        cls.spec = read("SYSTEM/SPEC/AGENT_LOOP.md")
        cls.engineering = read(".pi/skills/socratopia-engineering/SKILL.md")
        cls.doc = read("docs/PROMPTS.md")

    def test_cherry_prompt_is_short_and_does_not_reprint_kernel(self):
        self.assertLessEqual(len(self.prompt), 1400, "Cherry system prompt should stay compact")
        self.assertIn("AGENTS.md", self.prompt)
        self.assertIn("按任务加载", self.prompt)
        self.assertIn("SYSTEM/SPEC/AGENT_LOOP.md", self.prompt)
        self.assertNotIn("## 1. 决策优先级", self.prompt)
        self.assertNotIn("## 3. 权威对象", self.prompt)

    def test_state_machine_exposes_terminal_states(self):
        for state in ("ROUTE", "INSPECT", "ACT", "VERIFY", "DONE", "YIELD", "BLOCKED", "NEXT"):
            with self.subTest(state=state):
                self.assertIn(state, self.spec)
        for concept in ("目标达成", "等待", "无新证据", "拒绝授权", "实际证据",
                        "不同原因", "停止", "并行", "真实"):
            self.assertIn(concept, self.spec)

    def test_stop_rules_do_not_confuse_prompt_and_runtime(self):
        for phrase in ("不是硬性 max-turn/max-tool-call", "prompt-level", "Pi 运行时"):
            self.assertIn(phrase, self.spec)
        self.assertIn("不是 MCP Server", self.prompt)
        self.assertIn("cherry-tool-guide", self.prompt)
        self.assertIn("宿主", self.spec)
        self.assertNotIn("无限循环执行直到完美", self.prompt)

    def test_teaching_waits_instead_of_hallucinating_progress(self):
        for phrase in ("最多一个", "等待回答", "直接讲", "PROGRESS.md", "verified", "不自行下课"):
            self.assertIn(phrase, self.prompt)
        self.assertIn("YIELD", self.spec)
        self.assertIn("PROGRESS.md", self.kernel)

    def test_fallback_does_not_bypass_approval(self):
        for phrase in ("工具", "拒绝", "停止", "trusted:false", "web_article.py"):
            self.assertIn(phrase, self.prompt)
        for phrase in ("审批被拒", "BLOCKED", "不绕", "登录"):
            self.assertIn(phrase, self.doc + self.spec)

    def test_prompt_has_one_canonical_loop_definition(self):
        self.assertIn("SYSTEM/SPEC/AGENT_LOOP.md", self.kernel)
        self.assertIn("SYSTEM/SPEC/AGENT_LOOP.md", self.engineering)
        self.assertIn("SYSTEM/SPEC/AGENT_LOOP.md", self.doc)
        self.assertIn("ROUTE → INSPECT → ACT → VERIFY", self.spec)

    def test_completion_matrix_exposes_failure_and_no_tool_cases(self):
        for scenario in ("简短定义", "开课与追问", "网页打不开", "工具审批被拒",
                         "修复代码", "学生说“懂了”", "本轮目标已完成"):
            self.assertIn(scenario, self.doc)
        self.assertIn("无须依赖工具的任务不调用工具", self.spec)
        self.assertIn("不暗中重试", self.spec)


if __name__ == "__main__":
    unittest.main()
