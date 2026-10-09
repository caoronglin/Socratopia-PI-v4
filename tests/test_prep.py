"""Lesson preparation: scaffold from real state, alignment gate, staleness, isolation."""

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

from scripts.lib import prep  # noqa: E402

COURSE = "夹具课程"

PROGRESS = """# Course Progress

## Current checkpoint

- lesson_id: lesson_002
- chapter: 第2章 导数

## Coverage ledger

| item | status | evidence |
|---|---|---|
| 导数定义 | verified | lesson_001：能独立解释 |
| 链式法则 | needs_review | lesson_002：复合顺序说反 |
| 隐函数求导 | unseen | - |

## Lesson records

### lesson_002 链式法则

出错后纠正。
"""

RETEACH = """# 补讲队列

| id | 章节 | 类型 | 优先级 | 状态 | 差异证据 | 原因 | 验证 |
|---|---|---|---|---|---|---|---|
| RQ-1 | 第2章 | 例题 | P1 | pending | 链式法则例题 | 长原因 | 长验证 |
"""


def good_prep(**front_over) -> str:
    front = {"schema": "prep-1", "course": COURSE, "lesson_id": "lesson_003", "chapter": "第2章 导数",
             "status": "ready", "book_hash": "abc123def456"}
    front.update(front_over)
    lines = ["---"] + [f"{k}: {v}" for k, v in front.items() if v is not None]
    lines += ["anchors:", '  - "## 2.3 链式法则"', "sources: []", "---", "# lesson_003", "",
              "## 教学评一致性", "",
              "| id | 学习目标 | 问题/活动 | 可观察证据 | 支架 |",
              "|---|---|---|---|---|",
              "| O1 | 能说出复合函数求导顺序 | 让学习者先说外层还是内层 | 独立说出并给出一个反例 | B |",
              "| O2 | 能迁移到三层复合 | 给一个三层复合式 | 自行分解并求导 | B→C |",
              "", "## Coverage 种子", "",
              "| item | 计划状态 | 期望元素 |",
              "|---|---|---|",
              "| 链式法则 | introduced | 外层优先、逐层求导、三层迁移 |",
              "",
              "## 预期误概念", "",
              "| 误概念 | 触发条件 | 纠偏问法 |",
              "|---|---|---|",
              "| 内层先求导 | 见到多层复合 | 先问最外层是谁的导数 |",
              "",
              "## 教研会决议", "",
              "- 目标粒度（A）：已拆到可观察",
              "- 期望元素与误概念是否齐（B）：已齐",
              "- 表征与迁移路径（C）：已检查",
              "- 最可能卡点与预案：三层迁移时用具体数例",
              ""]
    return "\n".join(lines)


def run_check(text: str, **kw):
    kw.setdefault("course", COURSE)
    kw.setdefault("lesson_id", "lesson_003")
    kw.setdefault("current_hash", "abc123def456")
    return prep.check_prep_text(text, **kw)


class ReviewGateTests(unittest.TestCase):
    """The prep meeting and the anticipated misconceptions are gates, not suggestions.

    A fluent lesson plan is easy to write and easy to be wrong about; the review
    record is what makes the design auditable before class instead of after.
    """

    def test_ready_requires_prep_meeting_section(self):
        errors, _ = run_check(good_prep().replace("## 教研会决议", "## 别的东西"))
        self.assertTrue(any("教研会决议" in e for e in errors), errors)

    def test_ready_requires_misconception_section(self):
        errors, _ = run_check(good_prep().replace("## 预期误概念", "## 别的东西"))
        self.assertTrue(any("预期误概念" in e for e in errors), errors)

    def test_ready_requires_every_review_field(self):
        """A heading with nothing under it is not a meeting."""
        errors, _ = run_check(good_prep().replace("- 目标粒度（A）：已拆到可观察", ""))
        self.assertTrue(any("目标粒度" in e for e in errors), errors)

    def test_seed_without_elements_blocks_ready(self):
        text = good_prep().replace("| 链式法则 | introduced | 外层优先、逐层求导、三层迁移 |",
                                   "| 链式法则 | introduced | |")
        errors, _ = run_check(text)
        self.assertTrue(any("期望元素" in e for e in errors), errors)

    def test_draft_may_omit_elements(self):
        text = good_prep(status="draft").replace("外层优先、逐层求导、三层迁移", "")
        errors, _ = run_check(text)
        self.assertFalse(any("期望元素" in e for e in errors), errors)

    def test_incomplete_misconception_row_is_error(self):
        text = good_prep().replace(
            "| 内层先求导 | 见到多层复合 | 先问最外层是谁的导数 |",
            "| 内层先求导 | | 先问最外层是谁的导数 |",
        )
        errors, _ = run_check(text)
        self.assertTrue(any("误概念行不完整" in e for e in errors), errors)

    def test_wrong_misconception_header_is_error(self):
        errors, _ = run_check(good_prep().replace("| 误概念 | 触发条件 | 纠偏问法 |", "| a | b | c |"))
        self.assertTrue(any("表头" in e for e in errors), errors)

    def test_wrong_seed_header_is_error(self):
        errors, _ = run_check(good_prep().replace("| item | 计划状态 | 期望元素 |", "| item | 计划状态 |"))
        self.assertTrue(any("表头" in e for e in errors), errors)

class FrontMatterTests(unittest.TestCase):
    def test_parses_scalars_and_lists(self):
        front, body = prep.parse_front_matter(good_prep())
        self.assertEqual(front["course"], COURSE)
        self.assertEqual(front["anchors"], ["## 2.3 链式法则"])
        self.assertEqual(front["sources"], [])
        self.assertTrue(body.startswith("# lesson_003"))

    def test_no_front_matter(self):
        self.assertEqual(prep.parse_front_matter("# only body")[0], {})


class AlignmentGateTests(unittest.TestCase):
    def test_good_prep_passes(self):
        errors, warnings = run_check(good_prep())
        self.assertEqual((errors, warnings), ([], []))

    def test_objective_without_evidence_is_error(self):
        text = good_prep().replace("独立说出并给出一个反例", "")
        errors, _ = run_check(text)
        self.assertTrue(any("缺少可观察证据" in e for e in errors), errors)

    def test_objective_without_activity_is_error(self):
        errors, _ = run_check(good_prep().replace("让学习者先说外层还是内层", ""))
        self.assertTrue(any("缺少问题/活动" in e for e in errors), errors)

    def test_scaffold_spanning_three_levels_is_error(self):
        errors, _ = run_check(good_prep().replace("| B→C |", "| A→B→C |"))
        self.assertTrue(any("跨 3 级" in e for e in errors), errors)

    def test_adjacent_two_levels_ok(self):
        errors, _ = run_check(good_prep())
        self.assertFalse(any("支架" in e for e in errors))

    def test_invalid_scaffold_letter(self):
        errors, _ = run_check(good_prep().replace("| B→C |", "| Z |"))
        self.assertTrue(any("支架必须是 A/B/C" in e for e in errors), errors)

    def test_wrong_table_header_is_error(self):
        errors, _ = run_check(good_prep().replace("| id | 学习目标 |", "| id | 目标 |"))
        self.assertTrue(any("表头必须是" in e for e in errors), errors)

    def test_no_objectives_is_error(self):
        text = good_prep()
        start = text.index("| O1")
        end = text.index("## Coverage 种子")
        errors, _ = run_check(text[:start] + "\n" + text[end:])
        self.assertTrue(any("至少要有一个学习目标" in e for e in errors), errors)

    def test_activity_equal_to_goal_warns(self):
        text = good_prep().replace("让学习者先说外层还是内层", "能说出复合函数求导顺序")
        errors, warnings = run_check(text)
        self.assertEqual(errors, [])
        self.assertTrue(any("复述" in w for w in warnings), warnings)


class BoundaryTests(unittest.TestCase):
    def test_seed_cannot_promote_to_verified(self):
        errors, _ = run_check(good_prep().replace("| 链式法则 | introduced |", "| 链式法则 | verified |"))
        self.assertTrue(any("只能写 unseen/introduced" in e for e in errors), errors)

    def test_mastery_claim_rejected(self):
        errors, _ = run_check(good_prep() + "\n学习者已掌握链式法则。\n")
        self.assertTrue(any("掌握声明" in e for e in errors), errors)

    def test_course_mismatch_is_isolation_error(self):
        errors, _ = run_check(good_prep(course="另一门课"))
        self.assertTrue(any("课程隔离" in e for e in errors), errors)

    def test_lesson_id_mismatch(self):
        errors, _ = run_check(good_prep(lesson_id="lesson_009"))
        self.assertTrue(any("与文件名" in e for e in errors), errors)

    def test_invalid_status(self):
        errors, _ = run_check(good_prep(status="done"))
        self.assertTrue(any("status=" in e for e in errors), errors)


class ReadinessTests(unittest.TestCase):
    def test_ready_with_todo_is_error(self):
        errors, _ = run_check(good_prep().replace("能迁移到三层复合", "TODO"))
        self.assertTrue(any("TODO" in e for e in errors), errors)

    def test_draft_may_contain_todo(self):
        errors, _ = run_check(good_prep(status="draft").replace("能迁移到三层复合", "TODO"))
        self.assertEqual(errors, [])

    def test_ready_requires_anchors(self):
        text = good_prep().replace('anchors:\n  - "## 2.3 链式法则"\n', "anchors:\n")
        errors, _ = run_check(text)
        self.assertTrue(any("anchors" in e for e in errors), errors)

    def test_ready_requires_book_hash(self):
        errors, _ = run_check(good_prep(book_hash="none"))
        self.assertTrue(any("book_hash" in e for e in errors), errors)

    def test_generic_angle_brackets_are_not_placeholders(self):
        text = good_prep().replace("先说外层还是内层", "写出 List<int> 的类型")
        errors, _ = run_check(text)
        self.assertEqual(errors, [])

    def test_stale_when_book_changed(self):
        _, warnings = run_check(good_prep(), current_hash="999999999999")
        self.assertTrue(any(w.startswith("stale") for w in warnings), warnings)


class FileLevelTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socrat-prep-"))
        shutil.copytree(ROOT / "scripts", self.root / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "templates", self.root / "templates")
        data = self.root / "DATA" / COURSE
        (data / "CONTEXT").mkdir(parents=True)
        (data / "PROGRESS.md").write_text(PROGRESS, encoding="utf-8")
        (data / "CONTEXT/RETEACH_QUEUE.md").write_text(RETEACH, encoding="utf-8")
        book = self.root / "TEXTBOOK" / COURSE
        book.mkdir(parents=True)
        (book / "book.md").write_text("# 书\n\n## 2.3 链式法则\n", encoding="utf-8")
        (book / "_outline.md").write_text("# 大纲\n\n## 第2章 导数\n\n### 2.3 链式法则\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(self.root / "scripts/prep.py"), *args],
                              cwd=self.root, capture_output=True, text=True)

    def test_scaffold_uses_only_real_state(self):
        text = prep.scaffold_text(self.root, COURSE, "lesson_003", "第2章 导数")
        self.assertIn("needs_review：链式法则", text)
        self.assertIn("RQ-1", text)
        self.assertNotIn("导数定义", text.split("## Coverage 种子")[1])   # verified items are not seeded
        self.assertIn("| 隐函数求导 | unseen |", text)
        self.assertIn(f"book_hash: {prep.book_hash(self.root, COURSE)}", text)
        self.assertIn("第2章 导数", text.split("anchors:")[1].split("sources")[0])

    def test_scaffold_carries_expectation_elements_column(self):
        """Elements must be planned, not improvised: the column has to exist in the skeleton."""
        text = prep.scaffold_text(self.root, COURSE, "lesson_004", "第2章")
        self.assertIn("| item | 计划状态 | 期望元素 |", text)
        self.assertIn("## 预期误概念", text)
        self.assertIn("## 教研会决议", text)

    def test_fresh_scaffold_is_a_valid_draft_not_ready(self):
        text = prep.scaffold_text(self.root, COURSE, "lesson_003", "第2章 导数")
        errors, _ = run_check(text, current_hash=prep.book_hash(self.root, COURSE))
        self.assertEqual(errors, [])
        self.assertIn("status: draft", text)

    def test_ready_gate_blocks_unfilled_scaffold(self):
        text = prep.scaffold_text(self.root, COURSE, "lesson_003", "x").replace("status: draft", "status: ready")
        errors, _ = run_check(text, current_hash=prep.book_hash(self.root, COURSE))
        self.assertTrue(any("TODO" in e for e in errors))

    def test_no_carry_is_stated_not_invented(self):
        (self.root / "DATA" / COURSE / "PROGRESS.md").write_text("# p\n", encoding="utf-8")
        (self.root / "DATA" / COURSE / "CONTEXT/RETEACH_QUEUE.md").unlink()
        text = prep.scaffold_text(self.root, COURSE, "lesson_003", "")
        self.assertIn("无 needs_review 与待补讲", text)

    def test_cli_new_dry_run_then_apply_then_refuses_overwrite(self):
        dry = self.cli("new", "--course", COURSE, "--lesson-id", "lesson_003")
        self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
        target = self.root / "TEXTBOOK" / COURSE / "PREP/lesson_003.md"
        self.assertFalse(target.exists())
        self.assertEqual(self.cli("new", "--course", COURSE, "--lesson-id", "lesson_003", "--apply").returncode, 0)
        self.assertTrue(target.exists())
        again = self.cli("new", "--course", COURSE, "--lesson-id", "lesson_003", "--apply")
        self.assertEqual(again.returncode, 1)
        self.assertIn("拒绝覆盖", again.stdout)

    def test_cli_check_exit_codes(self):
        self.cli("new", "--course", COURSE, "--lesson-id", "lesson_003", "--apply")
        self.assertEqual(self.cli("check", "--course", COURSE, "--lesson-id", "lesson_003").returncode, 0)
        target = self.root / "TEXTBOOK" / COURSE / "PREP/lesson_003.md"
        target.write_text(target.read_text(encoding="utf-8").replace("status: draft", "status: ready"), encoding="utf-8")
        self.assertEqual(self.cli("check", "--course", COURSE, "--lesson-id", "lesson_003").returncode, 1)

    def test_cli_rejects_bad_ids_and_courses(self):
        self.assertEqual(self.cli("new", "--course", COURSE, "--lesson-id", "../x").returncode, 1)
        self.assertNotEqual(self.cli("status", "--course", "../etc").returncode, 0)

    def test_status_distinguishes_ready_draft_stale_invalid_legacy(self):
        folder = self.root / "TEXTBOOK" / COURSE / "PREP"
        folder.mkdir(exist_ok=True)
        real = prep.book_hash(self.root, COURSE)
        (folder / "lesson_001.md").write_text(good_prep(lesson_id="lesson_001", book_hash=real), encoding="utf-8")
        (folder / "lesson_002.md").write_text(good_prep(lesson_id="lesson_002", status="draft", book_hash=real), encoding="utf-8")
        (folder / "lesson_003.md").write_text(good_prep(book_hash="000000000000"), encoding="utf-8")
        (folder / "lesson_004.md").write_text(good_prep(lesson_id="lesson_004", book_hash=real).replace("独立说出并给出一个反例", ""), encoding="utf-8")
        (folder / "lesson_005.md").write_text("# 旧式自由格式 PREP\n", encoding="utf-8")
        status = prep.prep_status(self.root, COURSE)
        self.assertEqual(status, {"lesson_001": "ready", "lesson_002": "draft", "lesson_003": "stale",
                                  "lesson_004": "invalid", "lesson_005": "legacy"})

    def test_legacy_prep_is_never_judged(self):
        folder = self.root / "TEXTBOOK" / COURSE / "PREP"
        folder.mkdir(exist_ok=True)
        (folder / "lesson_001.md").write_text("无 front matter，且写着已掌握。", encoding="utf-8")
        self.assertEqual(prep.prep_status(self.root, COURSE), {"lesson_001": "legacy"})

    def test_other_course_is_never_read(self):
        other = self.root / "DATA" / "另一门课"
        other.mkdir(parents=True)
        (other / "PROGRESS.md").write_text(
            "## Coverage ledger\n\n| item | status | evidence |\n|---|---|---|\n| 机密项 | needs_review | x |\n", encoding="utf-8")
        self.assertNotIn("机密项", prep.scaffold_text(self.root, COURSE, "lesson_003", ""))

    def test_scaffold_never_writes_progress_or_book(self):
        before = {p: p.read_bytes() for p in [self.root / "DATA" / COURSE / "PROGRESS.md",
                                              self.root / "TEXTBOOK" / COURSE / "book.md"]}
        self.cli("new", "--course", COURSE, "--lesson-id", "lesson_003", "--apply")
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)


class TemplateTests(unittest.TestCase):
    def test_template_is_not_ready_and_declares_plan_only(self):
        text = (ROOT / "templates/PREP.md").read_text(encoding="utf-8")
        self.assertIn("status: draft", text)
        self.assertIn("不代表已授课", text)
        for claim in prep.MASTERY_CLAIMS:
            self.assertNotIn(claim, text)


if __name__ == "__main__":
    unittest.main()
