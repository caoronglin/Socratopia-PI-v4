"""Course-isolated, textbook-verified retrieval flashcards.

Only owner-authored cards. GET never exposes the back, key or textbook quote.
Reveal produces a short-lived single-use token for explicitly self-rated recall.
No model calls and no claims of verified mastery.
"""
from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from platform_api import course_graph, exercises
from scripts.lib.repository import course_dir, validate_course_name

CARD_LIMIT = 200
QUEUE_LIMIT = 8
INTERVAL_DAYS = (1, 3, 7, 14, 30)
RATINGS = {"again", "hard", "good", "easy"}
_ID = re.compile(r"^[a-f0-9]{32}$")


class FlashcardError(ValueError):
    """An unsafe, stale or inconsistent flashcard operation."""


def _database(root: Path, course: str) -> Path:
    base = course_dir(root, validate_course_name(course))
    if not base.is_dir() or base.is_symlink():
        raise FlashcardError("Course does not exist or is unsafe")
    runtime = base / "runtime"
    if runtime.is_symlink():
        raise FlashcardError("Course runtime cannot be a symlink")
    runtime.mkdir(parents=True, exist_ok=True)
    db_path = runtime / "flashcards.sqlite3"
    if db_path.is_symlink():
        raise FlashcardError("Flashcard database cannot be a symlink")
    if db_path.exists() and not db_path.is_file():
        raise FlashcardError("Flashcard database must be a regular file")
    return db_path


def _connect(root: Path, course: str) -> sqlite3.Connection:
    db = sqlite3.connect(_database(root, course), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=10000")
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS cards (
          id TEXT PRIMARY KEY,
          course TEXT NOT NULL,
          front TEXT NOT NULL,
          back TEXT NOT NULL,
          source_quote TEXT NOT NULL,
          source_sha256 TEXT NOT NULL,
          concept_id TEXT,
          exercise_id TEXT,
          created_at TEXT NOT NULL,
          UNIQUE(course, source_sha256, front)
        );
        CREATE TABLE IF NOT EXISTS reveals (
          token TEXT PRIMARY KEY,
          card_id TEXT NOT NULL REFERENCES cards(id),
          created_at TEXT NOT NULL,
          used_request_id TEXT
        );
        CREATE TABLE IF NOT EXISTS reviews (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          request_id TEXT NOT NULL UNIQUE,
          card_id TEXT NOT NULL REFERENCES cards(id),
          token TEXT NOT NULL UNIQUE REFERENCES reveals(token),
          rating TEXT NOT NULL,
          streak INTEGER NOT NULL,
          due_at TEXT NOT NULL,
          reviewed_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_flashcard_course_source
          ON cards(course, source_sha256, created_at);
        CREATE INDEX IF NOT EXISTS idx_flashcard_reviews
          ON reviews(card_id, id DESC);
        CREATE INDEX IF NOT EXISTS idx_flashcard_reveals
          ON reveals(card_id, created_at DESC);
    """)
    return db


def _current_book(root: Path, course: str) -> tuple[str, str]:
    try:
        return exercises._book(root, course)
    except exercises.ExerciseError as exc:
        raise FlashcardError(str(exc)) from exc


def create(root: Path, course: str, front: str, back: str, source_quote: str,
           *, concept_id: str | None = None,
           exercise_id: str | None = None) -> dict:
    course = validate_course_name(course)
    if not all(isinstance(x, str) for x in (front, back, source_quote)):
        raise FlashcardError("Flashcard fields must be text")
    front, back, quote = front.strip(), back.strip(), source_quote.strip()
    if not 3 <= len(front) <= 240 or not 1 <= len(back) <= 800:
        raise FlashcardError("Flashcard front or back exceeds length bounds")
    if not 8 <= len(quote) <= 500:
        raise FlashcardError("Source quote must have 8–500 characters")
    book, fingerprint = _current_book(root, course)
    if quote not in book:
        raise FlashcardError("Quote must occur exactly in the current textbook")
    if concept_id is not None:
        if not isinstance(concept_id, str) or not re.fullmatch(r"[a-f0-9]{12}", concept_id):
            raise FlashcardError("Invalid graph concept ID")
        graph = course_graph.build(root, course)
        if (graph["source_sha256"] != fingerprint
                or concept_id not in {node["id"] for node in graph["nodes"]}):
            raise FlashcardError("Concept must exist in this textbook version")
    if exercise_id is not None:
        if not isinstance(exercise_id, str) or not _ID.fullmatch(exercise_id):
            raise FlashcardError("Invalid linked exercise ID")
        with closing(exercises._connect(root, course)) as exercise_db:
            question = exercise_db.execute(
                "SELECT source_sha256 FROM exercises WHERE id=? AND course=?",
                (exercise_id, course),
            ).fetchone()
        if question is None or question["source_sha256"] != fingerprint:
            raise FlashcardError("Linked exercise must belong to this course and book")
    card_id = uuid4().hex
    with closing(_connect(root, course)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        if _current_book(root, course)[1] != fingerprint:
            raise FlashcardError("Textbook changed while creating the flashcard")
        try:
            db.execute(
                """INSERT INTO cards
                   (id,course,front,back,source_quote,source_sha256,concept_id,
                    exercise_id,created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
                (card_id, course, front, back, quote, fingerprint, concept_id,
                 exercise_id, datetime.now(UTC).isoformat()),
            )
        except sqlite3.IntegrityError as exc:
            raise FlashcardError("A card with this front already exists in this book") from exc
    return {"course": course, "id": card_id, "created": True,
            "source_sha256": fingerprint, "mastery_updated": False}


def _card(db: sqlite3.Connection, course: str, card_id: str) -> sqlite3.Row:
    if not isinstance(card_id, str) or not _ID.fullmatch(card_id):
        raise FlashcardError("Invalid flashcard identifier")
    row = db.execute("SELECT * FROM cards WHERE id=? AND course=?",
                     (card_id, course)).fetchone()
    if row is None:
        raise FlashcardError("Flashcard not found in this course")
    return row


def list_cards(root: Path, course: str, *, now: datetime | None = None) -> dict:
    course = validate_course_name(course)
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise FlashcardError("Review time must contain timezone")
    now = now.astimezone(UTC)
    try:
        _, fingerprint = _current_book(root, course)
    except FlashcardError:
        fingerprint = None
    with closing(_connect(root, course)) as db:
        total = db.execute("SELECT COUNT(*) FROM cards WHERE course=?", (course,)).fetchone()[0]
        if fingerprint is None:
            cards = []
        else:
            cards = db.execute(
                """SELECT * FROM cards WHERE course=? AND source_sha256=?
                   ORDER BY created_at DESC, id DESC LIMIT ?""",
                (course, fingerprint, CARD_LIMIT),
            ).fetchall()
        # Reuse ONE query per batch, not per flashcard.
        last_reviews: dict[str, sqlite3.Row] = {}
        wrong_questions: dict[str, str] = {}
        if cards:
            ids = [card["id"] for card in cards]
            placeholders = ",".join("?" for _ in ids)
            reviews = db.execute(
                f"""SELECT r.* FROM reviews r
                     JOIN (SELECT card_id, MAX(id) AS max_id FROM reviews
                           WHERE card_id IN ({placeholders}) GROUP BY card_id) latest
                     ON r.id=latest.max_id""", ids,
            ).fetchall()
            last_reviews = {r["card_id"]: r for r in reviews}
        linked = sorted({card["exercise_id"] for card in cards if card["exercise_id"]})
        if linked:
            with closing(exercises._connect(root, course)) as exdb:
                placeholders = ",".join("?" for _ in linked)
                rows = exdb.execute(
                    f"""SELECT a.exercise_id, a.is_correct, a.created_at
                        FROM attempts a JOIN (
                          SELECT exercise_id, MAX(rowid) AS newest
                          FROM attempts WHERE exercise_id IN ({placeholders})
                          GROUP BY exercise_id
                        ) latest ON a.rowid=latest.newest""", linked,
                ).fetchall()
                wrong_questions = {
                    r["exercise_id"]: r["created_at"] for r in rows if not r["is_correct"]
                }
    graph_labels = {}
    if fingerprint is not None and any(card["concept_id"] for card in cards):
        graph = course_graph.build(root, course)
        if graph["source_sha256"] == fingerprint:
            graph_labels = {n["id"]: n["label"] for n in graph["nodes"]}
    prepared = []
    for card in cards:
        last = last_reviews.get(card["id"])
        due = last["due_at"] if last else None
        last_bad = wrong_questions.get(card["exercise_id"])
        missed_after_review = bool(last_bad and (
            last is None or last_bad > last["reviewed_at"]))
        if missed_after_review:
            status = "needs_attention"
        elif last is None:
            status = "new"
        elif datetime.fromisoformat(due).astimezone(UTC) <= now:
            status = "due"
        else:
            status = "upcoming"
        prepared.append({
            "id": card["id"], "front": card["front"],
            "concept_id": card["concept_id"],
            "concept_label": graph_labels.get(card["concept_id"]),
            "exercise_id": card["exercise_id"],
            "status": status, "due_at": due,
            "recent_correct_streak": int(last["streak"]) if last else 0,
            "source_current": True,
            # Never return answer/back/source_quote before an explicit reveal.
        })
    priority = {"needs_attention": 0, "due": 1, "new": 2, "upcoming": 3}
    prepared.sort(key=lambda item: (priority[item["status"]],
                                    item["due_at"] or "", item["id"]))
    ready = [card for card in prepared if card["status"] != "upcoming"]
    upcoming = [card for card in prepared if card["status"] == "upcoming"]
    return {"course": course, "textbook_sha256": fingerprint,
            "status": "needs_textbook" if fingerprint is None else
                      "needs_cards" if not cards else "ready",
            "total_cards": total, "active_cards": len(cards),
            "stale_cards_excluded": max(0, total - len(cards)),
            "limited": max(0, total - len(cards)) > 0 and len(cards) == CARD_LIMIT,
            "review_due": sum(c["status"] in {"needs_attention", "due"} for c in ready),
            "new_cards": sum(c["status"] == "new" for c in ready),
            "linked_weaknesses": sum(c["status"] == "needs_attention" for c in ready),
            "items": ready[:QUEUE_LIMIT], "upcoming": upcoming[:3],
            "suggested_minutes": min(16, len(ready[:QUEUE_LIMIT]) * 2),
            "mastery_updated": False,
            "note": "记忆卡根据自评和练习记录建议复习；不代表正式知识掌握。"}


def reveal(root: Path, course: str, card_id: str) -> dict:
    course = validate_course_name(course)
    _, fingerprint = _current_book(root, course)
    with closing(_connect(root, course)) as db, db:
        row = _card(db, course, card_id)
        if row["source_sha256"] != fingerprint:
            raise FlashcardError("Flashcard belongs to an older textbook version")
        token = uuid4().hex
        db.execute("INSERT INTO reveals(token,card_id,created_at) VALUES (?,?,?)",
                   (token, card_id, datetime.now(UTC).isoformat()))
    return {"course": course, "id": card_id, "back": row["back"],
            "source_quote": row["source_quote"],
            "source_sha256": row["source_sha256"], "reveal_token": token,
            "fact_verified": False, "mastery_updated": False}


def review(root: Path, course: str, card_id: str, rating: str,
           token: str, request_id: str) -> dict:
    course = validate_course_name(course)
    if rating not in RATINGS or not all(
        isinstance(x, str) and _ID.fullmatch(x) for x in (token, request_id)
    ):
        raise FlashcardError("Invalid review rating or identifier")
    now = datetime.now(UTC)
    with closing(_connect(root, course)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        card = _card(db, course, card_id)
        if _current_book(root, course)[1] != card["source_sha256"]:
            raise FlashcardError("Flashcard textbook version is stale")
        existing = db.execute("SELECT * FROM reviews WHERE request_id=?", (request_id,)).fetchone()
        if existing:
            if (existing["card_id"] != card_id or existing["rating"] != rating
                    or existing["token"] != token):
                raise FlashcardError("Request ID already used for another flashcard review")
            return _public_review(existing, replayed=True)
        active = db.execute(
            "SELECT * FROM reveals WHERE token=? AND card_id=?",
            (token, card_id),
        ).fetchone()
        if active is None or active["used_request_id"]:
            raise FlashcardError("Reveal token missing or already used")
        if now - datetime.fromisoformat(active["created_at"]).astimezone(UTC) > timedelta(minutes=30):
            raise FlashcardError("Reveal token expired; reveal again")
        prior = db.execute(
            "SELECT streak FROM reviews WHERE card_id=? ORDER BY id DESC LIMIT 1",
            (card_id,),
        ).fetchone()
        previous_streak = int(prior["streak"]) if prior else 0
        streak = previous_streak + 1 if rating in {"good", "easy"} else 0
        if rating == "again":
            due = now + timedelta(minutes=10)
        elif rating == "hard":
            due = now + timedelta(days=1)
        else:
            index = min(streak - 1 + (1 if rating == "easy" else 0),
                        len(INTERVAL_DAYS) - 1)
            due = now + timedelta(days=INTERVAL_DAYS[index])
        db.execute(
            """INSERT INTO reviews(request_id,card_id,token,rating,streak,due_at,reviewed_at)
               VALUES (?,?,?,?,?,?,?)""",
            (request_id, card_id, token, rating, streak,
             due.isoformat(), now.isoformat()),
        )
        db.execute("UPDATE reveals SET used_request_id=? WHERE token=?",
                   (request_id, token))
        stored = db.execute("SELECT * FROM reviews WHERE request_id=?", (request_id,)).fetchone()
        return _public_review(stored, replayed=False)


def _public_review(row: sqlite3.Row, *, replayed: bool) -> dict:
    return {"exercise_completion": False, "mastery_updated": False,
            "card_id": row["card_id"], "rating": row["rating"],
            "reviewed_at": row["reviewed_at"], "next_review_at": row["due_at"],
            "recent_correct_streak": row["streak"], "replayed": replayed}
