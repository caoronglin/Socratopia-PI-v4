"""Phase 2 · Ontology — contract + negative-test matrix (approval §4.5)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import ontology as onto  # noqa: E402
from scripts.lib import repository  # noqa: E402


class OntologyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="socr-onto-"))
        self.course = "bio"
        onto.init(self.root, self.course)

    def _graph(self):
        return onto.graph_path(self.root, self.course)

    # ---- happy path ----
    def test_upsert_and_relate_and_query(self):
        onto.node_upsert(self.root, self.course, "kp_cell", "KnowledgePoint", {"label": "细胞"})
        onto.node_upsert(self.root, self.course, "kp_divide", "KnowledgePoint", {"label": "分裂"})
        res = onto.edge_relate(self.root, self.course, "kp_divide", "prerequisite", "kp_cell")
        self.assertTrue(res["changed"])
        q = onto.query(self.root, self.course, node_type="KnowledgePoint")
        self.assertEqual(len(q["result"]), 2)
        rel = onto.query(self.root, self.course, related="kp_divide", rel="prerequisite")
        self.assertEqual(rel["result"][0]["to"], "kp_cell")

    # ---- duplicate node/edge are idempotent ----
    def test_duplicate_node_idempotent(self):
        onto.node_upsert(self.root, self.course, "kp1", "Concept", {"a": 1})
        r2 = onto.node_upsert(self.root, self.course, "kp1", "Concept", {"a": 1})
        self.assertFalse(r2["changed"])  # identical -> no new event

    def test_duplicate_edge_idempotent(self):
        onto.node_upsert(self.root, self.course, "a", "Concept")
        onto.node_upsert(self.root, self.course, "b", "Concept")
        onto.edge_relate(self.root, self.course, "a", "related_to", "b")
        r2 = onto.edge_relate(self.root, self.course, "a", "related_to", "b")
        self.assertFalse(r2["changed"])

    # ---- orphan edge ----
    def test_orphan_edge_rejected_on_relate(self):
        with self.assertRaises(ValueError):
            onto.edge_relate(self.root, self.course, "ghost", "related_to", "also_ghost")

    def test_orphan_edge_flagged_on_validate(self):
        onto.node_upsert(self.root, self.course, "a", "Concept")
        onto.append_jsonl(self._graph(), {"kind": "edge", "op": "relate", "from": "a", "rel": "related_to", "to": "missing", "ts": "t"})
        self.assertTrue(any("孤儿边" in e for e in onto.validate(self.root, self.course)))

    # ---- invalid types ----
    def test_invalid_node_type_rejected(self):
        with self.assertRaises(ValueError):
            onto.node_upsert(self.root, self.course, "x", "NotAType")

    def test_invalid_node_type_flagged_on_validate(self):
        onto.append_jsonl(self._graph(), {"kind": "node", "op": "upsert", "id": "x", "type": "Bogus", "props": {}, "ts": "t"})
        self.assertTrue(any("非法类型" in e for e in onto.validate(self.root, self.course)))

    def test_invalid_edge_type_rejected(self):
        onto.node_upsert(self.root, self.course, "a", "Concept")
        onto.node_upsert(self.root, self.course, "b", "Concept")
        with self.assertRaises(ValueError):
            onto.edge_relate(self.root, self.course, "a", "bogus_rel", "b")

    # ---- prerequisite cycle ----
    def test_prerequisite_cycle_rejected(self):
        for nid in ("a", "b", "c"):
            onto.node_upsert(self.root, self.course, nid, "KnowledgePoint")
        onto.edge_relate(self.root, self.course, "a", "prerequisite", "b")
        onto.edge_relate(self.root, self.course, "b", "prerequisite", "c")
        with self.assertRaises(ValueError):
            onto.edge_relate(self.root, self.course, "c", "prerequisite", "a")

    # ---- malformed / interrupted JSONL ----
    def test_malformed_jsonl_reported_not_rewritten(self):
        onto.node_upsert(self.root, self.course, "a", "Concept")
        before = self._graph().read_text(encoding="utf-8")
        with self._graph().open("a", encoding="utf-8") as fh:
            fh.write('{"kind":"node","op":"upsert"')  # partial/interrupted line, no newline
        errors = onto.validate(self.root, self.course)
        self.assertTrue(any("不是合法 JSON" in e for e in errors))
        # history up to the partial line is preserved; validate never rewrites it
        self.assertTrue(self._graph().read_text(encoding="utf-8").startswith(before))

    def test_append_writes_complete_lines(self):
        onto.node_upsert(self.root, self.course, "a", "Concept")
        for raw in self._graph().read_text(encoding="utf-8").splitlines():
            json.loads(raw)  # every persisted line parses

    # ---- cross-course reference ----
    def test_cross_course_props_rejected(self):
        with self.assertRaises(ValueError):
            onto.node_upsert(self.root, self.course, "a", "Concept", {"course": "other"})

    def test_cross_course_flagged_on_validate(self):
        onto.append_jsonl(self._graph(), {"kind": "node", "op": "upsert", "id": "a", "type": "Concept", "props": {"course": "other"}, "ts": "t"})
        self.assertTrue(any("跨课程" in e for e in onto.validate(self.root, self.course)))

    # ---- invalid source anchor ----
    def test_invalid_source_anchor_rejected(self):
        for bad in ["../../etc/passwd", "/abs/path", ""]:
            with self.assertRaises(ValueError):
                onto.node_upsert(self.root, self.course, "a", "Concept", {"source_anchor": bad})

    # ---- mastery field injection ----
    def test_mastery_field_rejected(self):
        for bad in ["mastered", "score", "passed", "current_progress"]:
            with self.assertRaises(ValueError):
                onto.node_upsert(self.root, self.course, "a", "Concept", {bad: True})

    def test_mastery_field_flagged_on_validate(self):
        onto.append_jsonl(self._graph(), {"kind": "node", "op": "upsert", "id": "a", "type": "Concept", "props": {"mastered": True}, "ts": "t"})
        self.assertTrue(any("禁止的权威字段" in e for e in onto.validate(self.root, self.course)))

    # ---- path safety / isolation ----
    def test_course_name_traversal_rejected(self):
        for bad in ["../evil", "..", "a/b"]:
            with self.assertRaises(ValueError):
                onto.validate(self.root, bad)

    def test_symlink_escape_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        link = self.root / "DATA" / "evil"
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(outside, link)
        except OSError:
            self.skipTest("symlink not permitted")
        with self.assertRaises(ValueError):
            repository.course_dir(self.root, "evil")

    # ---- tombstone consistency ----
    def test_tombstone_cascades_edges_and_stays_consistent(self):
        onto.node_upsert(self.root, self.course, "a", "Concept")
        onto.node_upsert(self.root, self.course, "b", "Concept")
        onto.edge_relate(self.root, self.course, "a", "related_to", "b")
        onto.node_tombstone(self.root, self.course, "a")
        self.assertEqual(onto.validate(self.root, self.course), [])  # no orphan left
        self.assertIsNone(onto.node_get(self.root, self.course, "a"))

    # ---- compact consistency + projection contract ----
    def test_compact_matches_rebuild_and_is_derived(self):
        onto.node_upsert(self.root, self.course, "a", "KnowledgePoint", {"label": "x"})
        onto.node_upsert(self.root, self.course, "b", "KnowledgePoint")
        onto.edge_relate(self.root, self.course, "a", "prerequisite", "b")
        proj = onto.compact(self.root, self.course)
        self.assertTrue(proj["derived"])
        self.assertFalse(proj["authoritative"])
        self.assertEqual(proj, onto.rebuild_projection(self.root, self.course))
        # projection node types stay within the schema enum
        schema = json.loads((ROOT / "SYSTEM/schemas/ontology.schema.json").read_text(encoding="utf-8"))
        enum = set(schema["$defs"]["node"]["properties"]["type"]["enum"])
        self.assertEqual(enum, onto.NODE_TYPES)
        for node in proj["nodes"].values():
            self.assertFalse(onto.FORBIDDEN_PROPS & set(node["props"]))

    def test_schema_forbidden_props_match_code(self):
        """Schema and runtime must ban exactly the same mastery fields.

        The schema is not executed by any runtime code, so without this parity
        check the schema's `propertyNames` ban is decorative and can drift
        silently away from `ontology.FORBIDDEN_PROPS`.
        """
        schema = json.loads((ROOT / "SYSTEM/schemas/ontology.schema.json").read_text(encoding="utf-8"))
        banned = set(schema["$defs"]["node"]["properties"]["props"]["propertyNames"]["not"]["enum"])
        self.assertEqual(
            banned, onto.FORBIDDEN_PROPS,
            "SYSTEM/schemas/ontology.schema.json 与 scripts/ontology.py 的禁止字段集合不一致",
        )

    def test_schema_marks_projection_non_authoritative(self):
        schema = json.loads((ROOT / "SYSTEM/schemas/ontology.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["derived"]["const"], True)
        self.assertEqual(schema["properties"]["authoritative"]["const"], False)


if __name__ == "__main__":
    unittest.main()
