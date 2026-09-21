"""Phase 1 · Runtime Core Restore — positive + negative tests."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib import assessment, course_state, repository, review  # noqa: E402
from scripts.lib import task_queue as tq  # noqa: E402


class RepositorySafetyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socr-"))

    def test_course_name_traversal_rejected(self):
        for bad in ["../evil", "..", ".", "a/b", "a\\b", ""]:
            with self.assertRaises(ValueError):
                repository.validate_course_name(bad)

    def test_course_dir_isolated_under_data(self):
        d = repository.course_dir(self.root, "python")
        self.assertEqual(d, (self.root / "DATA" / "python").resolve())

    def test_course_dir_blocks_escape(self):
        with self.assertRaises(ValueError):
            repository.course_dir(self.root, "../outside")

    def test_write_json_atomic_leaves_no_tmp(self):
        target = self.root / "DATA" / "c" / "runtime" / "x.json"
        repository.write_json_atomic(target, {"a": 1})
        self.assertTrue(target.exists())
        self.assertEqual(list(target.parent.glob("*.tmp")), [])

    def test_malformed_json_raises(self):
        p = self.root / "bad.json"
        p.write_text("{not json", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            repository.read_json(p)

    def test_redact_masks_secrets(self):
        out = repository.redact("Authorization: Bearer sk-abcdef123456 and api_key=topsecret")
        self.assertNotIn("sk-abcdef123456", out)
        self.assertNotIn("topsecret", out)
        self.assertIn("[REDACTED]", out)


class CourseStateTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socr-"))

    def test_default_state_valid(self):
        state = course_state.default_state("c")
        self.assertEqual(course_state.validate_state(state), [])

    def test_migrate_v3_lifecycle_to_v4(self):
        legacy = {"schema_version": 1, "course": "c", "lifecycle": "needs_reteach", "lesson_number": 2, "current_chapter": "第3章"}
        state = course_state.to_v4(legacy, "c")
        self.assertEqual(state["phase"], "ready")
        self.assertEqual(state["readiness"]["reteach"], "pending")
        self.assertEqual(state["blockers"], ["pending_reteach"])
        self.assertEqual(state["lesson_id"], "lesson_002")

    def test_validate_rejects_bad_phase(self):
        state = course_state.default_state("c")
        state["phase"] = "bogus"
        self.assertTrue(course_state.validate_state(state))

    def test_validate_rejects_bad_readiness(self):
        state = course_state.default_state("c")
        state["readiness"]["catalog"] = "weird"
        self.assertTrue(course_state.validate_state(state))

    def test_validate_rejects_duplicate_blockers(self):
        state = course_state.default_state("c")
        state["blockers"] = ["x", "x"]
        self.assertTrue(any("重复" in e for e in course_state.validate_state(state)))

    def test_migrate_writes_json_and_backup(self):
        course_state.migrate_state(self.root, "c")
        path = course_state.state_path(self.root, "c")
        self.assertTrue(path.exists())
        course_state.migrate_state(self.root, "c")  # second migrate should back up
        self.assertTrue(path.with_suffix(path.suffix + ".bak").exists())


class TaskQueueTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socr-"))

    def test_enqueue_idempotent(self):
        t1 = tq.enqueue_task(self.root, "c", "kind_a", "key1", lesson_id="lesson_001")
        t2 = tq.enqueue_task(self.root, "c", "kind_a", "key1", lesson_id="lesson_001")
        self.assertEqual(t1["id"], t2["id"])
        self.assertEqual(len(tq._load(self.root, "c")["tasks"]), 1)

    def test_legal_and_illegal_transitions(self):
        t = tq.enqueue_task(self.root, "c", "k", "key")
        tq.transition_task(self.root, "c", t["id"], "running")
        self.assertEqual(tq.transition_task(self.root, "c", t["id"], "completed")["status"], "completed")
        with self.assertRaises(ValueError):
            tq.transition_task(self.root, "c", t["id"], "running")  # terminal -> illegal

    def test_running_increments_attempts(self):
        t = tq.enqueue_task(self.root, "c", "k", "key")
        tq.transition_task(self.root, "c", t["id"], "running")
        tq.transition_task(self.root, "c", t["id"], "failed")
        tq.transition_task(self.root, "c", t["id"], "pending")
        t2 = tq.transition_task(self.root, "c", t["id"], "running")
        self.assertEqual(t2["attempts"], 2)

    def test_error_is_redacted(self):
        t = tq.enqueue_task(self.root, "c", "k", "key")
        tq.transition_task(self.root, "c", t["id"], "running")
        done = tq.transition_task(self.root, "c", t["id"], "failed", error="token=sk-abcdef123456 leaked")
        self.assertNotIn("sk-abcdef123456", done["last_error"])

    def test_schema_rejects_top_level_course_and_bad_status(self):
        bad = {"schema_version": 1, "course": "c", "tasks": [{"id": "1", "idempotency_key": "k", "kind": "x", "course": "c", "status": "weird", "attempts": 0}]}
        errors = tq.validate_queue(bad)
        self.assertTrue(any("额外字段" in e for e in errors))
        self.assertTrue(any("非法 status" in e for e in errors))

    def test_schema_rejects_duplicate_id(self):
        dup = {"schema_version": 1, "tasks": [
            {"id": "1", "idempotency_key": "a", "kind": "x", "course": "c", "status": "pending", "attempts": 0},
            {"id": "1", "idempotency_key": "b", "kind": "x", "course": "c", "status": "pending", "attempts": 0},
        ]}
        self.assertTrue(any("重复 id" in e for e in tq.validate_queue(dup)))


class AssessmentTests(unittest.TestCase):
    def test_multiple_choice_rules(self):
        obj = {"1"}
        good = {"id": "q1", "objective_id": "1", "type": "multiple_choice", "difficulty": "easy",
                "prompt": "p", "answer": "A", "rationale": "r", "source_anchor": "book.md#s", "options": ["A", "B", "C"]}
        self.assertEqual(assessment.validate_item(good, obj), [])
        few = dict(good, options=["A", "B"])
        self.assertTrue(any("3–5" in e for e in assessment.validate_item(few, obj)))
        dup = dict(good, options=["A", "A", "B"])
        self.assertTrue(any("互异" in e for e in assessment.validate_item(dup, obj)))
        absent = dict(good, options=["A", "B", "C"], answer="Z")
        self.assertTrue(any("只能出现一次" in e for e in assessment.validate_item(absent, obj)))

    def test_missing_required_and_bad_objective(self):
        errors = assessment.validate_item({"id": "q", "objective_id": "nope"}, set())
        self.assertTrue(any("学习目标不存在" in e for e in errors))
        self.assertTrue(len(errors) > 3)

    def test_quality_report_coverage_and_duplicates(self):
        obj = {"1", "2"}
        items = [
            {"id": "a", "objective_id": "1", "type": "recall", "difficulty": "easy", "prompt": "same", "answer": "x", "rationale": "r", "source_anchor": "book.md#a"},
            {"id": "b", "objective_id": "1", "type": "recall", "difficulty": "easy", "prompt": "same", "answer": "x", "rationale": "r", "source_anchor": "book.md#a"},
        ]
        rep = assessment.quality_report(items, obj)
        self.assertEqual(rep["uncovered_objectives"], ["2"])
        self.assertTrue(rep["duplicate_prompts"])

    def test_reteach_only_on_scored_incorrect(self):
        items = [
            {"id": "a", "objective_id": "1", "status": "scored", "result": "incorrect", "knowledge_point": "kp"},
            {"id": "b", "objective_id": "1", "status": "scored", "result": "correct", "knowledge_point": "kp"},
            {"id": "c", "objective_id": "1", "status": "draft", "result": "incorrect", "knowledge_point": "kp"},
        ]
        cands = assessment.reteach_candidates(items)
        self.assertEqual([c["objective_id"] for c in cands], ["1"])
        self.assertEqual(len(cands), 1)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socr-"))

    def test_record_confusion_dedup(self):
        review.record_confusion(self.root, "c", "L1", "kp", "causal_error", "model", "evid")
        review.record_confusion(self.root, "c", "L1", "kp", "causal_error", "model2", "evid2")
        state = review.load_review_state(self.root, "c")
        self.assertEqual(len(state["confusions"]), 1)
        self.assertEqual(state["confusions"][0]["learner_model"], "model2")

    def test_exit_plan_has_fill_placeholders(self):
        items = review.build_exit_plan("L1", "第1章", ["kp1"], [])
        self.assertTrue(any(i.get("requires_fill") for i in items))

    def test_retrieval_plan_prioritizes_needs_reteach(self):
        state = {"confusions": [{"confusion_id": "conf-x", "lesson_id": "L0", "knowledge_point": "kp", "status": "needs_reteach"}],
                 "exit_practice": [], "retrieval_log": []}
        items = review.build_retrieval_plan("L1", ["L0"], state)
        self.assertEqual(items[0]["type"], "confusion")

    def test_failed_retrieval_escalates_to_needs_reteach(self):
        review.record_confusion(self.root, "c", "L1", "kp", "causal_error", "m", "e")
        cid = review.load_review_state(self.root, "c")["confusions"][0]["confusion_id"]
        review.record_retrieval_result(self.root, "c", "L1", f"retr-conf-{cid}", "failed")
        conf = next(c for c in review.load_review_state(self.root, "c")["confusions"] if c["confusion_id"] == cid)
        self.assertEqual(conf["status"], "needs_reteach")

    def test_review_enqueue_idempotent(self):
        t1 = review.enqueue_review_task(self.root, "c", "L1", "exit")
        t2 = review.enqueue_review_task(self.root, "c", "L1", "exit")
        self.assertEqual(t1["id"], t2["id"])


if __name__ == "__main__":
    unittest.main()
