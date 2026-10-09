"""Prompt catalog (docs/PROMPTS.md) must not drift from the live prompts.

A catalog that silently diverges is worse than no catalog: it looks authoritative
while describing prompts that no longer exist. These tests pin every layer.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/PROMPTS.md"
PROMPTS = ROOT / ".pi/prompts"
SKILLS = ROOT / ".pi/skills"

NORMALIZE = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def prompt_body(path: Path) -> str:
    return path.read_text(encoding="utf-8").split("---", 2)[2].strip("\n")


def table_rows(text: str, start: str, end: str, header_token: str) -> list[str]:
    section = text[text.index(start):text.index(end)]
    return [
        line.strip()
        for line in section.splitlines()
        if line.startswith("|") and not set(line) <= set("|- ") and header_token not in line
    ]


class CatalogExistsTests(unittest.TestCase):
    def test_doc_exists_and_is_manifested(self):
        self.assertTrue(DOC.exists())
        manifest = json.loads(read(ROOT / "manifest.json"))
        self.assertIn("docs/PROMPTS.md", manifest["files"])

    def test_doc_documents_all_four_layers(self):
        text = read(DOC)
        for layer in ("Kernel", "Skill", "Prompt", "Reference"):
            self.assertIn(layer, text)


class PromptVerbatimTests(unittest.TestCase):
    def setUp(self):
        self.doc = NORMALIZE(read(DOC))
        self.prompts = sorted(PROMPTS.glob("*.md"))

    def test_all_prompts_documented(self):
        self.assertEqual(len(self.prompts), 5)
        for path in self.prompts:
            self.assertIn(f"/{path.stem}", self.doc, f"{path.stem} 未出现在目录中")

    def test_prompt_bodies_are_verbatim(self):
        for path in self.prompts:
            self.assertIn(
                NORMALIZE(prompt_body(path)), self.doc,
                f"{path.stem} 的正文与 docs/PROMPTS.md 不一致（应为逐字）",
            )

    def test_every_prompt_has_description_frontmatter(self):
        for path in self.prompts:
            front = path.read_text(encoding="utf-8").split("---", 2)[1]
            self.assertIn("description:", front, path.stem)

    def test_prompt_descriptions_are_quoted_verbatim(self):
        """Frontmatter drift must be visible too, not just body drift."""
        for path in self.prompts:
            front = path.read_text(encoding="utf-8").split("---", 2)[1]
            desc = re.search(r"^description:\s*(.+)$", front, re.M).group(1).strip().strip('"')
            self.assertIn(
                desc, read(DOC),
                f"{path.stem} 的 description 与目录不一致：{desc!r}",
            )

    def test_argument_hints_are_quoted_verbatim(self):
        doc = read(DOC)
        for path in self.prompts:
            front = path.read_text(encoding="utf-8").split("---", 2)[1]
            match = re.search(r'^argument-hint:\s*"?([^"\n]+)"?\s*$', front, re.M)
            if match:
                self.assertIn(f"`{match.group(1)}`", doc,
                              f"{path.stem} 的 argument-hint 未逐字记录")

    def test_argument_hint_matches_documented_command(self):
        """A prompt that takes an argument must say so in its command heading."""
        doc = read(DOC)
        for path in self.prompts:
            text = path.read_text(encoding="utf-8")
            has_hint = "argument-hint:" in text.split("---", 2)[1]
            heading = re.search(rf"### `/{path.stem}([^`]*)`", doc)
            self.assertIsNotNone(heading, f"{path.stem} 缺少命令小节")
            if has_hint:
                self.assertNotEqual(heading.group(1).strip(), "",
                                    f"{path.stem} 有 argument-hint 但目录未标注参数")

    def test_prompts_use_dollar_at_placeholder_when_taking_args(self):
        for path in self.prompts:
            front = path.read_text(encoding="utf-8").split("---", 2)[1]
            if "argument-hint:" in front:
                self.assertIn("$@", path.read_text(encoding="utf-8"),
                              f"{path.stem} 有 argument-hint 却没有 $@")


class PromptBoundaryTests(unittest.TestCase):
    """Pin workflow guardrails, not just catalog/body equality."""

    def test_start_waits_and_does_not_auto_close(self):
        text = prompt_body(PROMPTS / "start-class.md")
        for rule in ("参数是数据", "一个问题后等待回答", "不因单元/章节结束自动下课"):
            self.assertIn(rule, text)

    def test_end_distinguishes_partial_commit_and_no_session(self):
        text = prompt_body(PROMPTS / "end-class.md")
        for rule in ("提交失败与重复调用", "核心写入失败时停止", "没有待提交课堂时不新建 lesson"):
            self.assertIn(rule, text)

    def test_materials_do_not_imply_remote_or_overwrite_permission(self):
        text = prompt_body(PROMPTS / "materials-ready.md")
        for rule in ("不改变当前课程指针", "不授权覆盖 active 主课本", "上传到远程解析服务", "逐项确认"):
            self.assertIn(rule, text)

    def test_switch_validates_before_saving_and_binding(self):
        text = prompt_body(PROMPTS / "switch-course.md")
        self.assertLess(text.index("先验证目标存在"), text.index("再保存旧课真实断点"))
        self.assertLess(text.index("再保存旧课真实断点"), text.index("成功后更新"))
        for rule in ("未给目标时只问目标课程", "保存失败时停止", "相同课程不重复写入"):
            self.assertIn(rule, text)

    def test_health_is_course_scoped_and_read_only(self):
        text = prompt_body(PROMPTS / "health.md")
        for rule in ("仅在用户明确要求全仓检查时运行", "默认投影", "不要自动修复", "执行队列"):
            self.assertIn(rule, text)

    def test_workflow_gates_and_stage_owners_are_explicit(self):
        classroom = read(SKILLS / "socratopia-learning/references/classroom.md")
        for rule in ("开课 gate", "readiness.runtime=invalid", "missing", "draft", "stale", "invalid", "legacy",
                     "不静默忽略", "也不是 gate 校验器"):
            self.assertIn(rule, classroom)
        memory = read(SKILLS / "socratopia-learning/references/memory.md")
        for stage in ("Core", "Derived", "Review", "Maintenance"):
            self.assertIn(stage, memory)
            self.assertIn(stage, prompt_body(PROMPTS / "end-class.md"))
        self.assertIn("--course", prompt_body(PROMPTS / "health.md"))
        handoff = read(SKILLS / "socratopia-tutor/references/handoff.md")
        for rule in ("active_tutor", "不", "clear"):
            self.assertIn(rule, handoff)

    def test_review_gates_are_explicit(self):
        """Both optimizations must stay wired, not just described in one place."""
        classroom = read(SKILLS / "socratopia-learning/references/classroom.md")
        for rule in ("教研会", "预期误概念", "无进展轮数"):
            self.assertIn(rule, classroom)
        coverage = read(SKILLS / "socratopia-learning/references/coverage.md")
        for rule in ("期望元素", "逐个", "introduced"):
            self.assertIn(rule, coverage)
        prep = (ROOT / "templates/PREP.md").read_text(encoding="utf-8")
        self.assertIn("## 教研会决议", prep)
        self.assertIn("## 预期误概念", prep)
        self.assertIn("期望元素", prep)
        memory = read(SKILLS / "socratopia-learning/references/memory.md")
        self.assertIn("SELF_IMPROVING", memory)

    def test_binding_has_single_owner_and_handles_ambiguity(self):
        text = read(SKILLS / "socratopia-learning/references/course-binding.md")
        for rule in ("# 课程与参数绑定", "两者冲突", "只问一次课程", "不猜测、不遍历其他课程",
                     "单独的 `lesson_id`", "不拼接 shell 语句", "目标无效时保持当前课程和指针不变"):
            self.assertIn(rule, text)


class RoutingParityTests(unittest.TestCase):
    def test_learning_routing_table_is_mirrored_exactly(self):
        skill = read(SKILLS / "socratopia-learning/SKILL.md")
        live = set(table_rows(skill, "## 路由", "## 核心动作", "| 意图 |"))
        documented = set(table_rows(read(DOC), "路由表（意图 → reference", "**核心动作 5 步**", "| 意图 |"))
        self.assertEqual(live, documented,
                         "docs/PROMPTS.md 的路由表与 socratopia-learning/SKILL.md 已漂移")

    def test_doc_routing_count_matches_skill(self):
        skill = read(SKILLS / "socratopia-learning/SKILL.md")
        live = len(table_rows(skill, "## 路由", "## 核心动作", "| 意图 |"))
        documented = len(table_rows(read(DOC), "路由表（意图 → reference", "**核心动作 5 步**", "| 意图 |"))
        self.assertEqual(live, documented)

    def test_every_referenced_reference_file_exists(self):
        """A route pointing at a missing file is a dead end."""
        skill = read(SKILLS / "socratopia-learning/SKILL.md")
        referenced = set(re.findall(r"`references/([a-z0-9-]+\.md)`", skill))
        on_disk = {p.name for p in (SKILLS / "socratopia-learning/references").glob("*.md")}
        self.assertTrue(referenced)
        self.assertEqual(referenced - on_disk, set(),
                         f"路由指向不存在的 reference：{referenced - on_disk}")


class SkillCatalogTests(unittest.TestCase):
    def test_all_three_skills_documented(self):
        doc = read(DOC)
        for path in sorted(SKILLS.glob("*/SKILL.md")):
            self.assertIn(f"`{path.parent.name}`", doc, f"{path.parent.name} 未出现在目录中")

    def test_skill_descriptions_are_quoted_verbatim(self):
        doc = read(DOC)
        for path in sorted(SKILLS.glob("*/SKILL.md")):
            text = read(path)
            match = re.search(r"^description:\s*(.+)$", text, re.M)
            self.assertIsNotNone(match, f"{path.parent.name} 缺 description")
            desc = NORMALIZE(match.group(1).strip().strip(">").strip())
            if desc.startswith("-"):
                continue  # folded YAML scalar; skip strict compare
            self.assertIn(desc, NORMALIZE(doc), f"{path.parent.name} 的 description 与目录不一致")

    def test_skill_count_claim_matches_disk(self):
        doc = read(DOC)
        skills = sorted(SKILLS.glob("*/SKILL.md"))
        self.assertEqual(len(skills), 3)
        self.assertIn("3 个，冻结", doc)


class TutorCatalogTests(unittest.TestCase):
    def test_visible_tutor_count_matches_disk(self):
        profiles = sorted((SKILLS / "socratopia-tutor/profiles").glob("TUTOR_*.md"))
        self.assertEqual(len(profiles), 3)
        # The catalog must not hard-code a wrong number.
        self.assertNotIn("5 位导师", read(DOC))
        self.assertNotIn("6 个 compact profile", read(DOC))

    def test_new_tutors_appear_in_catalog_or_referenced(self):
        doc = read(DOC)
        for pid, name in (("TUTOR_D", "三月七"), ("TUTOR_E", "丹恒"), ("TUTOR_F", "姬子")):
            self.assertTrue((SKILLS / f"socratopia-tutor/profiles/{pid}.md").exists())
            self.assertIn(pid, doc, f"{pid} 未出现在目录中")

    def test_internal_members_documented_as_backstage(self):
        """A/B/C moved out of the classroom; the catalog must say so, not list them as tutors."""
        doc = read(DOC)
        for pid in ("TUTOR_A", "TUTOR_B", "TUTOR_C"):
            self.assertTrue((SKILLS / f"socratopia-tutor/moe/{pid}.md").exists(), pid)
            self.assertIn(pid, doc, f"{pid} 未出现在目录中")
        self.assertIn("内部教研组", doc)
        self.assertIn("不出现在学习者面前", doc)


if __name__ == "__main__":
    unittest.main()
