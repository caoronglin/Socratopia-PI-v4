"""Deterministic, persistent interactive classroom questions.

Questions are authored by the local course owner, NEVER keyed by an LLM.
Answers are graded by an immutable answer key tied to an exact textbook SHA.
Attempts are instructional records, not authoritative mastery evaluations.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from platform_api.evidence import EvidenceError, _read_book
from scripts.lib.repository import course_dir, safe_child_path, validate_course_name, validate_lesson_id


class ExerciseError(ValueError):
    """Invalid question, source or attempt. Do not update learning progress."""


def _db_path(root: Path, course: str) -> Path:
    runtime = safe_child_path(course_dir(root, validate_course_name(course)), "runtime")
    runtime.mkdir(parents=True, exist_ok=True)
    target = safe_child_path(runtime, "interactive_exercises.sqlite3")
    if target.is_symlink():
        raise ExerciseError("Exercise database cannot be a symlink")
    return target


def _connect(root: Path, course: str) -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path(root, course), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=10000")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS exercises (
            id TEXT PRIMARY KEY,
            course TEXT NOT NULL,
            lesson_id TEXT,
            kind TEXT NOT NULL,
            stem TEXT NOT NULL,
            options_json TEXT NOT NULL,
            answer_json TEXT NOT NULL,
            explanation TEXT NOT NULL,
            source_quote TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attempts (
            request_id TEXT PRIMARY KEY,
            exercise_id TEXT NOT NULL REFERENCES exercises(id),
            selected_json TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    return connection


def _book(root: Path, course: str) -> tuple[str, str]:
    try:
        return _read_book(root, course)
    except EvidenceError as exc:
        raise ExerciseError(str(exc)) from exc


def _valid_question(question: dict[str, Any]) -> None:
    kind = question.get("kind")
    options = question.get("options")
    answers = question.get("correct_indices")
    if kind not in {"single_select", "multi_select"}:
        raise ExerciseError("Question kind must be single_select or multi_select")
    if not isinstance(options, list) or not 2 <= len(options) <= 4:
        raise ExerciseError("Question must have 2–4 choices")
    if any(not isinstance(s, str) or not 1 <= len(s.strip()) <= 180 for s in options):
        raise ExerciseError("Each choice must have 1–180 visible characters")
    if len({s.strip().casefold() for s in options}) != len(options):
        raise ExerciseError("Choices must not be duplicated")
    if (not isinstance(answers, list) or not answers
            or any(type(n) is not int or n < 0 or n >= len(options) for n in answers)
            or len(set(answers)) != len(answers)):
        raise ExerciseError("Answer key must contain unique valid choice indices")
    if kind == "single_select" and len(answers) != 1:
        raise ExerciseError("Single-select question must have exactly one correct answer")
    if kind == "multi_select" and not 2 <= len(answers) < len(options):
        raise ExerciseError("Multi-select needs 2+ but not all correct choices")
    if not 1 <= len(question.get("stem", "").strip()) <= 500:
        raise ExerciseError("Question must have a 1–500 character stem")
    if not 1 <= len(question.get("explanation", "").strip()) <= 1000:
        raise ExerciseError("Explanation is required and must be 1–1000 characters")
    if not 8 <= len(question.get("source_quote", "").strip()) <= 500:
        raise ExerciseError("Textbook evidence quote must have 8–500 characters")
    lesson_id = question.get("lesson_id")
    if lesson_id is not None:
        validate_lesson_id(lesson_id)


def create(root: Path, course: str, question: dict[str, Any]) -> dict:
    course = validate_course_name(course)
    _valid_question(question)
    book, fingerprint = _book(root, course)
    quote = question["source_quote"].strip()
    if quote not in book:
        raise ExerciseError("Evidence quote must exactly occur in this course's current book.md")
    key = sorted(question["correct_indices"])
    record = {
        "id": uuid4().hex,
        "course": course,
        "lesson_id": question.get("lesson_id"),
        "kind": question["kind"],
        "stem": question["stem"].strip(),
        "options": [value.strip() for value in question["options"]],
        "correct_indices": key,
        "explanation": question["explanation"].strip(),
        "source_quote": quote,
        "source_sha256": fingerprint,
        "created_at": datetime.now(UTC).isoformat(),
    }
    with _connect(root, course) as db:
        # A textbook revision during authoring must not activate an old question.
        if _book(root, course)[1] != fingerprint:
            raise ExerciseError("Book changed during question creation; retry")
        db.execute(
            """INSERT INTO exercises (id,course,lesson_id,kind,stem,options_json,
               answer_json,explanation,source_quote,source_sha256,created_at)
               VALUES (:id,:course,:lesson_id,:kind,:stem,:options_json,
               :answer_json,:explanation,:source_quote,:source_sha256,:created_at)""",
            {
                **{k: record[k] for k in (
                    "id", "course", "lesson_id", "kind", "stem", "explanation",
                    "source_quote", "source_sha256", "created_at"
                )},
                "options_json": json.dumps(record["options"], ensure_ascii=False),
                "answer_json": json.dumps(key),
            },
        )
    return {"id": record["id"], "created": True, "source_sha256": fingerprint}


def _public(row: sqlite3.Row, current_sha: str | None) -> dict:
    return {
        "id": row["id"], "lesson_id": row["lesson_id"], "kind": row["kind"],
        "stem": row["stem"], "options": json.loads(row["options_json"]),
        "source_sha256": row["source_sha256"],
        "source_current": row["source_sha256"] == current_sha,
        "created_at": row["created_at"],
        # Answer key, explanation and quote are not delivered before submission.
    }


def list_questions(root: Path, course: str) -> dict:
    try:
        fingerprint = _book(root, course)[1]
    except ExerciseError:
        fingerprint = None
    with _connect(root, course) as db:
        rows = db.execute(
            "SELECT * FROM exercises WHERE course=? ORDER BY created_at DESC, id DESC",
            (course,),
        ).fetchall()
    return {"course": course, "questions": [_public(row, fingerprint) for row in rows]}


def _read_attempt(row: sqlite3.Row, question: sqlite3.Row) -> dict:
    return {
        "request_id": row["request_id"],
        "exercise_id": row["exercise_id"],
        "selected_indices": json.loads(row["selected_json"]),
        "correct_indices": json.loads(question["answer_json"]),
        "is_correct": bool(row["is_correct"]),
        "explanation": question["explanation"],
        "source_quote": question["source_quote"],
        "source_sha256": question["source_sha256"],
        "created_at": row["created_at"],
        "mastery_updated": False,
    }


def submit(root: Path, course: str, exercise_id: str,
           request_id: str, selected: list[int]) -> tuple[dict, bool]:
    course = validate_course_name(course)
    if not re.fullmatch(r"[0-9a-f]{32}", exercise_id):
        raise ExerciseError("Invalid exercise ID")
    if not re.fullmatch(r"[0-9a-f]{32}", request_id):
        raise ExerciseError("Invalid request ID")
    if (not isinstance(selected, list) or not selected or len(selected) > 4
            or any(type(n) is not int for n in selected)
            or len(set(selected)) != len(selected)):
        raise ExerciseError("Selected choices must contain unique valid indices")
    selected = sorted(selected)
    with _connect(root, course) as db:
        db.execute("BEGIN IMMEDIATE")
        question = db.execute(
            "SELECT * FROM exercises WHERE id=? AND course=?", (exercise_id, course),
        ).fetchone()
        if question is None:
            raise ExerciseError("Question not found in this course")
        prior = db.execute("SELECT * FROM attempts WHERE request_id=?", (request_id,)).fetchone()
        if prior is not None:
            if prior["exercise_id"] != exercise_id or json.loads(prior["selected_json"]) != selected:
                raise ExerciseError("Request ID already used for a different submission")
            return _read_attempt(prior, question), False
        options = json.loads(question["options_json"])
        if any(n < 0 or n >= len(options) for n in selected):
            raise ExerciseError("Selected choice is out of range")
        _, fingerprint = _book(root, course)
        if fingerprint != question["source_sha256"]:
            raise ExerciseError("Question textbook revision is stale; reauthor against the current book")
        answer = json.loads(question["answer_json"])
        is_correct = selected == answer
        db.execute(
            """INSERT INTO attempts (request_id, exercise_id, selected_json,
               is_correct, created_at) VALUES (?,?,?,?,?)""",
            (request_id, exercise_id, json.dumps(selected), int(is_correct),
             datetime.now(UTC).isoformat()),
        )
        row = db.execute("SELECT * FROM attempts WHERE request_id=?", (request_id,)).fetchone()
        return _read_attempt(row, question), True


def summary(root: Path, course: str) -> dict:
    course = validate_course_name(course)
    with _connect(root, course) as db:
        stats = db.execute("""
            SELECT COUNT(*) AS total, COALESCE(SUM(is_correct), 0) AS correct
            FROM attempts JOIN exercises ON exercises.id=attempts.exercise_id
            WHERE exercises.course=?
        """, (course,)).fetchone()
        days = db.execute("""
            SELECT substr(attempts.created_at, 1, 10) AS day,
                   COUNT(*) AS attempts, SUM(attempts.is_correct) AS correct
            FROM attempts JOIN exercises ON exercises.id=attempts.exercise_id
            WHERE exercises.course=?
            GROUP BY day ORDER BY day DESC LIMIT 14
        """, (course,)).fetchall()
        total_questions = db.execute(
            "SELECT COUNT(*) FROM exercises WHERE course=?", (course,),
        ).fetchone()[0]
    total, correct = stats["total"], stats["correct"]
    return {
        "course": course, "question_count": total_questions,
        "attempts": total, "correct": correct,
        "accuracy": round(correct * 100 / total, 1) if total else None,
        "trend": [
            {"day": d["day"], "correct": d["correct"], "incorrect": d["attempts"] - d["correct"]}
            for d in reversed(days)
        ],
        "mastery_updated": False,
        "meaning": "practice_attempt_accuracy_not_verified_mastery",
    }
