"""Deterministic retrieval-practice queue from real course quiz attempts.

This is a *study suggestion*, not an assessment of mastery. No model calls,
secret prompts, global student profile, or authoritative course state writes.
Only questions tied to the course's CURRENT textbook are eligible.
"""
from __future__ import annotations

from collections import defaultdict
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from platform_api import exercises
from scripts.lib.repository import validate_course_name

# Heuristic intervals, not a validated learning/ability estimate.
INTERVAL_DAYS = (1, 3, 7, 14, 30)
QUESTION_LIMIT = 200
QUEUE_LIMIT = 5


def plan(root: Path, course: str, *, now: datetime | None = None) -> dict:
    """Return a bounded, answer-key-free plan for the specified course."""
    course = validate_course_name(course)
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("Study plan requires a timezone-aware clock")
    now = now.astimezone(UTC)

    try:
        _, book_sha = exercises._book(root, course)
    except exercises.ExerciseError:
        book_sha = None

    with closing(exercises._connect(root, course)) as db:
        total = db.execute(
            "SELECT COUNT(*) FROM exercises WHERE course=?", (course,)
        ).fetchone()[0]
        if book_sha is None:
            questions = []
        else:
            questions = db.execute(
                """SELECT id, stem, lesson_id, created_at
                   FROM exercises WHERE course=? AND source_sha256=?
                   ORDER BY created_at DESC, id DESC LIMIT ?""",
                (course, book_sha, QUESTION_LIMIT),
            ).fetchall()
        history = defaultdict(list)
        if questions:
            # One query, five latest records per question; no 1+N round trips.
            # SQLite window functions are available in every supported Python.
            rows = db.execute(
                """WITH target AS (
                     SELECT id FROM exercises
                     WHERE course=? AND source_sha256=?
                     ORDER BY created_at DESC, id DESC LIMIT ?
                   ), ranked AS (
                     SELECT a.exercise_id, a.is_correct, a.created_at,
                       ROW_NUMBER() OVER (
                         PARTITION BY a.exercise_id
                         ORDER BY a.created_at DESC, a.request_id DESC
                       ) AS rn
                     FROM attempts a JOIN target ON target.id=a.exercise_id
                   )
                   SELECT exercise_id, is_correct, created_at FROM ranked
                   WHERE rn <= 5 ORDER BY exercise_id, rn""",
                (course, book_sha, QUESTION_LIMIT),
            ).fetchall()
            for attempt in rows:
                history[attempt["exercise_id"]].append(attempt)

    suggested = []
    for question in questions:
        attempts = history[question["id"]]
        streak = 0
        for attempt in attempts:
            if attempt["is_correct"]:
                streak += 1
            else:
                break
        latest = attempts[0] if attempts else None
        if latest is None:
            status, due = "new", now
            reason = "还没有做过，先尝试独立作答"
        elif not latest["is_correct"]:
            status = "retry"
            due = now
            reason = "上次回答不正确，优先复习相关教材后再试"
        else:
            last_at = datetime.fromisoformat(latest["created_at"]).astimezone(UTC)
            due = last_at + timedelta(days=INTERVAL_DAYS[min(streak, 5) - 1])
            status = "due" if due <= now else "upcoming"
            reason = "间隔复习已到期" if status == "due" else "稍后进行间隔复习"
        suggested.append({
            "exercise_id": question["id"],
            "stem": question["stem"],
            "lesson_id": question["lesson_id"],
            "status": status,
            "reason": reason,
            "next_review_at": due.isoformat(),
            "recent_correct_streak": streak,
        })

    priority = {"retry": 0, "due": 1, "new": 2, "upcoming": 3}
    suggested.sort(key=lambda item: (
        priority[item["status"]], item["next_review_at"], item["exercise_id"]
    ))
    ready = [x for x in suggested if x["status"] != "upcoming"]
    upcoming = [x for x in suggested if x["status"] == "upcoming"]
    available = len(questions)
    return {
        "course": course,
        "textbook_sha256": book_sha,
        "status": ("needs_textbook" if book_sha is None else
                   "needs_questions" if available == 0 else "ready"),
        "review_due": sum(x["status"] in {"retry", "due"} for x in ready),
        "new_questions": sum(x["status"] == "new" for x in ready),
        "stale_questions_excluded": max(0, total - available),
        "shown": min(len(ready), QUEUE_LIMIT),
        "suggested_minutes": min(15, 3 * min(len(ready), QUEUE_LIMIT)),
        "items": ready[:QUEUE_LIMIT],
        "upcoming": upcoming[:3],
        "mastery_updated": False,
        "note": "依据真实练习记录排序；不代表知识掌握，亦不改变正式课程状态。",
    }
