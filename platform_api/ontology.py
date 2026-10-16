"""Reviewed course-only ontology edges and evidence-bound concept diagnosis.

Heading containment != prerequisite. Prerequisites and question mappings
only become active after explicit course-owner submission with a textbook quote.
Metrics describe *recent exercise evidence*, NOT validated learning mastery.
"""
from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from platform_api import course_graph, exercises
from scripts.lib.repository import course_dir, validate_course_name

MAX_RELATIONS = 320
MAX_LINKS = 512
_ID = re.compile(r"^[0-9a-f]{12}$")


class OntologyError(ValueError):
    """An invalid, unsafe or stale source-backed concept relationship."""


def _database(root: Path, course: str) -> Path:
    base = course_dir(root, validate_course_name(course))
    if not base.is_dir() or base.is_symlink():
        raise OntologyError("Course does not exist or is unsafe")
    runtime = base / "runtime"
    if runtime.is_symlink():
        raise OntologyError("Unsafe ontology runtime directory")
    runtime.mkdir(parents=True, exist_ok=True)
    path = runtime / "ontology.sqlite3"
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise OntologyError("Ontology database must be a regular file")
    return path


def _connect(root: Path, course: str) -> sqlite3.Connection:
    db = sqlite3.connect(_database(root, course), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=10000")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS prerequisite_edges (
          source_sha256 TEXT NOT NULL,
          prerequisite_id TEXT NOT NULL,
          concept_id TEXT NOT NULL,
          source_quote TEXT NOT NULL,
          created_at TEXT NOT NULL,
          PRIMARY KEY(source_sha256, prerequisite_id, concept_id)
        );
        CREATE TABLE IF NOT EXISTS question_concepts (
          source_sha256 TEXT NOT NULL,
          question_id TEXT NOT NULL,
          concept_id TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('practice', 'transfer')),
          source_quote TEXT NOT NULL,
          created_at TEXT NOT NULL,
          PRIMARY KEY(source_sha256, question_id, concept_id)
        );
        CREATE INDEX IF NOT EXISTS idx_ontology_relations
          ON prerequisite_edges(source_sha256, concept_id);
        CREATE INDEX IF NOT EXISTS idx_ontology_questions
          ON question_concepts(source_sha256, concept_id);
    """)
    return db


def _source(root: Path, course: str) -> tuple[str, str, dict]:
    course = validate_course_name(course)
    try:
        book, sha = exercises._book(root, course)
        graph = course_graph.build(root, course)
    except (exercises.ExerciseError, ValueError) as exc:
        raise OntologyError(str(exc)) from exc
    if graph["source_sha256"] != sha:
        raise OntologyError("Textbook changed during graph construction")
    return book, sha, graph


def _concept(nodes: dict[str, dict], concept_id: str) -> None:
    if not isinstance(concept_id, str) or not _ID.fullmatch(concept_id):
        raise OntologyError("Invalid concept ID")
    if concept_id not in nodes:
        raise OntologyError("Concept must belong to this textbook version")


def _quote(book: str, evidence: str) -> str:
    if not isinstance(evidence, str):
        raise OntologyError("Textbook evidence must be text")
    evidence = evidence.strip()
    if not 8 <= len(evidence) <= 500 or evidence not in book:
        raise OntologyError("Source quote must occur exactly in the current textbook")
    return evidence


def _reachable(edges: list[tuple[str, str]], source: str, goal: str) -> bool:
    adjacency = defaultdict(set)
    for a, b in edges:
        adjacency[a].add(b)
    pending = [source]
    seen: set[str] = set()
    while pending:
        node = pending.pop()
        if node == goal:
            return True
        if node in seen:
            continue
        seen.add(node)
        pending.extend(adjacency[node] - seen)
    return False


def add_prerequisite(root: Path, course: str, prerequisite_id: str,
                     concept_id: str, source_quote: str) -> dict:
    name = validate_course_name(course)
    book, sha, graph = _source(root, name)
    nodes = {n["id"]: n for n in graph["nodes"]}
    _concept(nodes, prerequisite_id)
    _concept(nodes, concept_id)
    if prerequisite_id == concept_id:
        raise OntologyError("A concept cannot require itself")
    quote = _quote(book, source_quote)
    with closing(_connect(root, name)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        if _source(root, name)[1] != sha:
            raise OntologyError("Textbook changed during ontology update")
        existing = db.execute(
            "SELECT prerequisite_id,concept_id FROM prerequisite_edges WHERE source_sha256=?",
            (sha,),
        ).fetchall()
        if len(existing) >= MAX_RELATIONS:
            raise OntologyError("Ontology prerequisite limit reached")
        edges = [(row["prerequisite_id"], row["concept_id"]) for row in existing]
        if _reachable(edges, concept_id, prerequisite_id):
            raise OntologyError("Prerequisite edge would create a cycle")
        try:
            db.execute("""INSERT INTO prerequisite_edges
                (source_sha256,prerequisite_id,concept_id,source_quote,created_at)
                VALUES (?,?,?,?,?)""",
                (sha, prerequisite_id, concept_id, quote, datetime.now(UTC).isoformat()))
        except sqlite3.IntegrityError as exc:
            raise OntologyError("Prerequisite already exists; no overwrite") from exc
    return {"course": name, "source_sha256": sha,
            "prerequisite_id": prerequisite_id, "concept_id": concept_id,
            "evidence_status": "owner_reviewed_not_scientifically_verified"}


def link_question(root: Path, course: str, question_id: str, concept_id: str,
                  role: str, source_quote: str) -> dict:
    name = validate_course_name(course)
    book, sha, graph = _source(root, name)
    nodes = {n["id"]: n for n in graph["nodes"]}
    _concept(nodes, concept_id)
    if role not in {"practice", "transfer"}:
        raise OntologyError("Link role must be practice or transfer")
    if not isinstance(question_id, str) or not re.fullmatch(r"[a-f0-9]{32}", question_id):
        raise OntologyError("Invalid exercise ID")
    quote = _quote(book, source_quote)
    with closing(exercises._connect(root, name)) as db:
        question = db.execute(
            "SELECT source_sha256 FROM exercises WHERE id=? AND course=?",
            (question_id, name),
        ).fetchone()
    if question is None or question["source_sha256"] != sha:
        raise OntologyError("Exercise must belong to this course and textbook version")
    with closing(_connect(root, name)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        if _source(root, name)[1] != sha:
            raise OntologyError("Textbook changed during ontology update")
        count = db.execute("SELECT COUNT(*) FROM question_concepts WHERE source_sha256=?",
                           (sha,)).fetchone()[0]
        if count >= MAX_LINKS:
            raise OntologyError("Ontology question link limit reached")
        try:
            db.execute("""INSERT INTO question_concepts
                (source_sha256,question_id,concept_id,role,source_quote,created_at)
                VALUES (?,?,?,?,?,?)""",
                (sha, question_id, concept_id, role, quote, datetime.now(UTC).isoformat()))
        except sqlite3.IntegrityError as exc:
            raise OntologyError("Exercise concept link already exists") from exc
    return {"course": name, "source_sha256": sha, "question_id": question_id,
            "concept_id": concept_id, "role": role,
            "evidence_status": "owner_reviewed_not_scientifically_verified"}


def graph(root: Path, course: str) -> dict:
    name = validate_course_name(course)
    _, sha, outline = _source(root, name)
    with closing(_connect(root, name)) as db:
        rows = db.execute(
            "SELECT prerequisite_id,concept_id,source_quote FROM prerequisite_edges "
            "WHERE source_sha256=? ORDER BY prerequisite_id,concept_id", (sha,),
        ).fetchall()
        questions = db.execute(
            "SELECT question_id,concept_id,role FROM question_concepts "
            "WHERE source_sha256=? ORDER BY concept_id,question_id", (sha,),
        ).fetchall()
    return {
        "course": name, "source_sha256": sha, "nodes": outline["nodes"],
        "edges": outline["edges"] + [
            {"source": r["prerequisite_id"], "target": r["concept_id"],
             "type": "prerequisite_owner_reviewed", "derived": False,
             "evidence_quote": r["source_quote"], "fact_verified": False}
            for r in rows
        ],
        "question_links": [dict(r) for r in questions],
        "reviewed_prerequisites": len(rows),
        "relation_policy": "explicit_course_owner_only_no_llm_inference",
        "fact_verified": False, "truncated": outline["truncated"],
    }


def diagnosis(root: Path, course: str) -> dict:
    """Prioritize wrong-linked concepts and flag prerequisites as *checks*.

    A correct transfer exercise is only evidence of that single attempt,
    never sufficient to certify mastery of the concept.
    """
    name = validate_course_name(course)
    knowledge = graph(root, name)
    sha = knowledge["source_sha256"]
    nodes = {n["id"]: n for n in knowledge["nodes"]}
    links = knowledge["question_links"]
    ids = sorted({x["question_id"] for x in links})
    attempts = {}
    if ids:
        with closing(exercises._connect(root, name)) as db:
            params = ",".join("?" for _ in ids)
            rows = db.execute(
                f"""SELECT a.exercise_id,a.is_correct,a.created_at FROM attempts a
                    JOIN (SELECT exercise_id, MAX(rowid) AS last_id
                          FROM attempts WHERE exercise_id IN ({params})
                          GROUP BY exercise_id) latest ON a.rowid=latest.last_id""", ids,
            ).fetchall()
            attempts = {r["exercise_id"]: r for r in rows}
    concepts: dict[str, dict] = {}
    for link in links:
        concept_id = link["concept_id"]
        if concept_id not in nodes:
            continue
        row = concepts.setdefault(concept_id, {
            "concept_id": concept_id, "label": nodes[concept_id]["label"],
            "wrong_practice": 0, "attempted_practice": 0,
            "correct_practice": 0, "transfer_attempted": 0,
            "transfer_correct": 0, "transfer_questions": [],
            "untried_questions": 0,
        })
        result = attempts.get(link["question_id"])
        if result is None:
            row["untried_questions"] += 1
            if link["role"] == "transfer":
                row["transfer_questions"].append(link["question_id"])
            continue
        if link["role"] == "transfer":
            row["transfer_attempted"] += 1
            if result["is_correct"]:
                row["transfer_correct"] += 1
        else:
            row["attempted_practice"] += 1
            if result["is_correct"]:
                row["correct_practice"] += 1
            else:
                row["wrong_practice"] += 1
    backwards = defaultdict(list)
    for edge in knowledge["edges"]:
        if edge["type"] == "prerequisite_owner_reviewed":
            backwards[edge["target"]].append(edge["source"])
    ordered = []
    for concept in concepts.values():
        prerequisite_checks = []
        queue = [(concept["concept_id"], 0)]
        seen: set[str] = {concept["concept_id"]}
        while queue:
            child, depth = queue.pop(0)
            if depth >= 2:
                continue
            for prior in sorted(backwards[child]):
                if prior not in seen and prior in nodes:
                    seen.add(prior)
                    prerequisite_checks.append({
                        "concept_id": prior, "label": nodes[prior]["label"],
                        "depth": depth + 1,
                        "meaning": "prerequisite_to_check_not_proven_weak",
                    })
                    queue.append((prior, depth + 1))
        concept["prerequisite_checks"] = prerequisite_checks[:12] if concept["wrong_practice"] else []
        concept["next_action"] = (
            "review_and_check_prerequisites" if concept["wrong_practice"] else
            "attempt_transfer" if concept["correct_practice"] and not concept["transfer_correct"] else
            "practice_for_diagnosis" if concept["untried_questions"] else
            "review_evidence_without_mastery_claim"
        )
        concept["transfer_evidence"] = "observed_correct_attempt_only" if concept["transfer_correct"] else "missing_or_incorrect"
        ordered.append(concept)
    rank = {"review_and_check_prerequisites": 0, "attempt_transfer": 1,
            "practice_for_diagnosis": 2, "review_evidence_without_mastery_claim": 3}
    ordered.sort(key=lambda c: (rank[c["next_action"]], -c["wrong_practice"],
                                c["label"], c["concept_id"]))
    return {
        "course": name, "source_sha256": sha, "concepts": ordered[:80],
        "linked_questions": len(ids), "reviewed_prerequisites": knowledge["reviewed_prerequisites"],
        "priority_concepts": sum(x["wrong_practice"] > 0 for x in ordered),
        "transfer_verified": False, "mastery_updated": False,
        "note": "只基于已人工关联的客观练习记录排序；前置知识仅建议核查，迁移题答对不等于确认掌握。",
    }
