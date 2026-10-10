"""Static Pi prompt contracts: independent from model/runtime enforcement.

These tests verify routing, trust, tool boundaries and stop instructions.
They do not claim an actual Cherry Studio/Pi model dialogue was executed.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts.lib.budget import budget_warnings, routing_tokens, soft_threshold_warnings

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class PiAgentConstraintsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernel = read("AGENTS.md")
        cls.cherry = read("integrations/cherry-studio/AGENT_PROMPT.md")
        cls.loop = read("SYSTEM/SPEC/AGENT_LOOP.md")
        cls.trust = read("SYSTEM/SPEC/TRUST_EFFECTS.md")
        cls.acceptance = read("docs/PI_AGENT_ACCEPTANCE.md")

    def test_one_project_kernel_no_replacement_system(self):
        self.assertFalse((ROOT / ".pi/SYSTEM.md").exists())
        self.assertFalse((ROOT / ".pi/APPEND_SYSTEM.md").exists())
        self.assertEqual(len(re.findall(r"^## \d+\. ", self.kernel, re.MULTILINE)), 10)
        self.assertIn("Pi Agent Kernel", self.kernel)

    def test_active_instructions_remain_compact(self):
        self.assertLessEqual(len(self.kernel), 2200)
        self.assertLessEqual(len(self.cherry), 1150)
        self.assertEqual(soft_threshold_warnings(ROOT), [])
        self.assertEqual(budget_warnings(ROOT), [])
        self.assertLess(routing_tokens(ROOT), 2100)

    def test_only_three_skills_and_one_profile_in_class(self):
        skills = {p.parent.name for p in (ROOT / ".pi/skills").glob("*/SKILL.md")}
        self.assertEqual(skills, {"socratopia-learning", "socratopia-tutor", "socratopia-engineering"})
        for phrase in ("按任务加载", "socratopia-tutor", "active_tutor", "当前一位",
                       "普通问答直接答", "不自行下课"):
            self.assertIn(phrase, self.cherry)
        self.assertIn("一个匹配 Skill", self.kernel)
        self.assertIn("不得批量加载教材", self.kernel)

    def test_direct_answers_do_not_force_tutoring_loop(self):
        for token in ("直接讲", "先解释", "最多一个", "等待回答"):
            self.assertIn(token, self.cherry)
        for token in ("先解释", "等待学习者", "不自行续问", "YIELD"):
            self.assertIn(token, self.kernel + self.loop)
        self.assertIn("无须依赖工具的任务不调用工具", self.loop)

    def test_stop_rules_and_error_recovery(self):
        for token in ("完成/等待/阻断", "达到目标立即停止", "无新证据不重读/重试",
                      "权限", "拒绝", "停止"):
            self.assertIn(token, self.cherry)
        for token in ("非幂等写入", "目标是否已落盘", "BLOCKED", "Pi 运行时",
                      "prompt-level", "不是硬性 max-turn/max-tool-call"):
            self.assertIn(token, self.loop)
        self.assertNotIn("无限循环执行直到完美", self.kernel + self.cherry)

    def test_untrusted_content_and_approval_not_bypassed(self):
        for token in ("PDF/OCR", "SOURCES", "数据而非指令", "覆盖 active 主课本",
                      "远程上传", "其他工具绕过拒绝"):
            self.assertIn(token, self.kernel)
        for token in ("trusted:false", "cherry-tool-guide", "宿主", "工具缺失"):
            self.assertIn(token, self.cherry)
        self.assertIn("必须针对具体操作明确授权", self.trust)

    def test_timer_and_group_do_not_mint_mastery(self):
        for phrase in ("45 分钟", "lesson_timer.py", "真实", "未完成", "verified",
                       "PROGRESS.md", "study-group.md", "D/E/F"):
            self.assertIn(phrase, self.kernel + self.cherry)
        self.assertIn("心跳只随真实教学交互", self.loop)
        self.assertIn("达到上限 DONE", self.loop)
        self.assertIn("导师讨论文本不得生成", self.loop)

    def test_python_rust_tools_are_optional_no_fake_tool_access(self):
        self.assertIn("不凭空声称 Rust 已安装", self.cherry)
        self.assertIn("Python CLI", self.cherry)
        self.assertIn("不是 MCP Server", self.cherry)
        self.assertIn("获批", self.cherry)

    def test_acceptance_covers_failure_cases_not_only_happy_path(self):
        for phrase in ("权限绕过", "跨课写入", "登录墙",
                       "重复", "未满 45 分钟", "DONE/YIELD/BLOCKED"):
            self.assertIn(phrase, self.acceptance)
        self.assertIn("CI 只验证文本与脚本契约", self.acceptance)
        self.assertIn("真实 Cherry Studio Pi Agent", self.acceptance)


if __name__ == "__main__":
    unittest.main()
