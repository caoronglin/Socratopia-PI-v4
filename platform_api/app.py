"""Local-first FastAPI application, preserving v4 course and timer contracts."""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, Field

from scripts.lib import learning_group, lesson_timer
from scripts.initialize import initialize as initialize_course
from scripts.lib.course_state import load_state, validate_state
from scripts.lib.repository import course_dir, iter_course_paths, validate_course_name

from platform_api.agentscope_tutors import TutorUnavailable, generate_tutor_turn
from platform_api.evidence import EvidenceError, retrieve, is_current
from platform_api.grounding import GroundingError, check_response, grounded_prompt
from platform_api.pi_gateway import PiUnavailable, ask_pi
from platform_api import exercises, books, chat_history
from scripts.lib import chapter_prep
from scripts.lib.prep import prep_status, check_prep, prep_path

api = FastAPI(title="Socratopia API", version="5.0.0-alpha.3", docs_url=None, redoc_url=None)


def root_dir() -> Path:
    return Path(os.environ.get("SOCRATOPIA_ROOT", ".")).resolve()


def require_auth(authorization: Annotated[str | None, Header()] = None) -> None:
    token = os.environ.get("SOCRATOPIA_API_TOKEN", "")
    provided = authorization.removeprefix("Bearer ") if authorization else ""
    if not token:
        raise HTTPException(503, "API token is not configured")
    if not secrets.compare_digest(token, provided):
        raise HTTPException(401, "Unauthorized")


Authenticated = Annotated[None, Depends(require_auth)]


def existing_course(course: str) -> str:
    try:
        name = validate_course_name(course)
        if not course_dir(root_dir(), name).is_dir():
            raise HTTPException(404, "Course does not exist")
        return name
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    tutor: Literal["D", "E", "F"] = "F"


class ChapterPrepRequest(BaseModel):
    chapter: str = Field(min_length=1, max_length=160)
    sources: list[str] = Field(default_factory=list, max_length=16)
    apply: bool = False


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)



class BookImport(BaseModel):
    content: str = Field(min_length=1, max_length=2000000)


class ExerciseCreate(BaseModel):
    kind: Literal["single_select", "multi_select"]
    stem: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=2, max_length=4)
    correct_indices: list[int] = Field(min_length=1, max_length=3)
    explanation: str = Field(min_length=1, max_length=1000)
    source_quote: str = Field(min_length=8, max_length=500)
    lesson_id: str | None = None


class ExerciseSubmission(BaseModel):
    request_id: str = Field(min_length=32, max_length=32)
    selected_indices: list[int] = Field(min_length=1, max_length=4)


class TimerStart(BaseModel):
    lesson_id: str


class TimerTransition(BaseModel):
    action: Literal["heartbeat", "pause", "resume", "finish", "interrupt"]


class GroupConfig(BaseModel):
    members: list[Literal["D", "E", "F"]] = Field(min_length=2, max_length=3)
    lead: Literal["D", "E", "F"]


class GroupStart(BaseModel):
    topic: str = Field(min_length=1, max_length=240)
    rounds: int = Field(default=2, ge=1, le=3)


class GroupContinue(BaseModel):
    question: str = Field(default="", max_length=240)


@api.get("/api/health")
def health() -> dict:
    return {"service": "socratopia", "version": api.version, "ready": bool(os.getenv("SOCRATOPIA_API_TOKEN"))}


@api.get("/api/courses")
def courses(_: Authenticated) -> dict:
    names = []
    for candidate in iter_course_paths(root_dir()):
        try:
            name = validate_course_name(candidate.name)
            if not candidate.is_symlink():
                names.append(name)
        except ValueError:
            continue
    return {"courses": names}


@api.post("/api/courses")
def create_course(payload: CourseCreate, _: Authenticated) -> dict:
    try:
        return initialize_course(root_dir(), payload.name, payload.tutor)
    except (ValueError, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc


@api.get("/api/courses/{course}/state")
def course_state(course: str, _: Authenticated) -> dict:
    state = load_state(root_dir(), existing_course(course))
    errors = validate_state(state)
    if errors:
        raise HTTPException(409, "Invalid course state: " + "; ".join(errors))
    return state



@api.get("/api/courses/{course}/evidence")
def course_evidence(course: str, q: str, _: Authenticated) -> dict:
    name = existing_course(course)
    if not 1 <= len(q.strip()) <= 2000:
        raise HTTPException(422, "Query must have 1–2000 characters")
    try:
        return retrieve(root_dir(), name, q).for_client()
    except EvidenceError as exc:
        raise HTTPException(409, str(exc)) from exc


@api.get("/api/courses/{course}/overview")
def overview(course: str, _: Authenticated) -> dict:
    name = existing_course(course)
    state = load_state(root_dir(), name)
    errors = validate_state(state)
    timer = lesson_timer.status(root_dir(), name)
    group = learning_group.status(root_dir(), name)
    book_present = False
    try:
        # The source must be readable, not merely present on disk.
        from platform_api.evidence import _read_book
        _, _ = _read_book(root_dir(), name)
        book_present = True
    except EvidenceError:
        pass
    return {
        "course": name, "state_valid": not errors, "course_phase": state.get("phase"),
        "readiness": state.get("readiness"), "blockers": list(state.get("blockers", [])) + errors,
        "book_available": book_present, "grounded_chat_ready": book_present,
        "formal_lesson_ready": bool(
            not errors and not state.get("blockers")
            and all(state.get("readiness", {}).get(k) == "ok" for k in ("catalog", "prep", "runtime"))
            and state.get("readiness", {}).get("reteach") == "clear"
            and state.get("phase") in {"ready", "in_lesson"}
        ),
        "timer_phase": timer["phase"],
        "group_phase": (group.get("session") or {}).get("phase", "not_started"),
        "mastery_automatically_updated": False,
    }



@api.get("/api/courses/{course}/prep")
def course_prep_status(course: str, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return {"course": name, "lessons": prep_status(root_dir(), name)}
    except (ValueError, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc


@api.get("/api/courses/{course}/prep/{lesson_id}")
def course_prep_check(course: str, lesson_id: str, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        from scripts.lib.repository import validate_lesson_id
        validate_lesson_id(lesson_id)
        errors, warnings = check_prep(root_dir(), name, lesson_id)
        status = prep_status(root_dir(), name).get(lesson_id, "missing")
        return {"course": name, "lesson_id": lesson_id, "status": status,
                "ready_for_class": status == "ready" and not errors and
                    not any(w.startswith("stale") for w in warnings),
                "errors": errors, "warnings": warnings}
    except (ValueError, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc


@api.post("/api/courses/{course}/prep/chapter/plan")
def course_prep_chapter(course: str, payload: ChapterPrepRequest, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        result = chapter_prep.plan_chapter(
            root_dir(), name, payload.chapter,
            sources=payload.sources, apply=payload.apply
        )
        # No automatic ready promotion. Newly created plans remain drafts.
        return {**result, "ready_granted": False, "mastery_updated": False}
    except (ValueError, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc


@api.get("/api/courses/{course}/book")
def book_info(course: str, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return books.info(root_dir(), name)
    except (books.BookError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@api.post("/api/courses/{course}/book")
def import_course_book(course: str, payload: BookImport, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return books.import_markdown(root_dir(), name, payload.content)
    except (books.BookError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@api.get("/api/courses/{course}/exercises")
def exercise_list(course: str, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return exercises.list_questions(root_dir(), name)
    except (exercises.ExerciseError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@api.post("/api/courses/{course}/exercises")
def exercise_create(course: str, payload: ExerciseCreate, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return exercises.create(root_dir(), name, payload.model_dump())
    except (exercises.ExerciseError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@api.post("/api/courses/{course}/exercises/{exercise_id}/submit")
def exercise_submit(course: str, exercise_id: str,
                    payload: ExerciseSubmission, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        result, inserted = exercises.submit(
            root_dir(), name, exercise_id, payload.request_id, payload.selected_indices
        )
    except (exercises.ExerciseError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc
    # Existing 45min timer remains authoritative. Count only *new* learner
    # attempts, never a repeated idempotent network retry.
    if inserted and lesson_timer.status(root_dir(), name).get("is_active"):
        try:
            lesson_timer.transition(root_dir(), name, "heartbeat")
        except ValueError:
            pass  # A quiz attempt does not grant or reset formal lesson time.
    return {**result, "replayed": not inserted}


@api.get("/api/courses/{course}/exercise-summary")
def exercise_summary(course: str, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return exercises.summary(root_dir(), name)
    except (exercises.ExerciseError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@api.get("/api/courses/{course}/timer")
def timer_status(course: str, _: Authenticated) -> dict:
    return lesson_timer.status(root_dir(), existing_course(course))


@api.post("/api/courses/{course}/timer/start")
def timer_start(course: str, payload: TimerStart, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return lesson_timer.start(root_dir(), name, payload.lesson_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@api.post("/api/courses/{course}/timer/transition")
def timer_transition(course: str, payload: TimerTransition, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return lesson_timer.transition(root_dir(), name, payload.action)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@api.get("/api/courses/{course}/chat/history")
def read_chat_history(course: str, response: Response, _: Authenticated) -> dict:
    response.headers["Cache-Control"] = "no-store"
    name = existing_course(course)
    try:
        return chat_history.recent(root_dir(), name)
    except (chat_history.HistoryError, OSError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@api.post("/api/courses/{course}/chat")
async def chat(course: str, payload: ChatRequest, _: Authenticated) -> dict:
    name = existing_course(course)
    # Grounded mode is the only course-chat mode. Missing sources are NOT
    # replaced with model world knowledge, and cannot tick the lesson clock.
    try:
        snapshot = retrieve(root_dir(), name, payload.message)
        prompt = grounded_prompt(payload.message, snapshot)
    except (EvidenceError, GroundingError) as exc:
        raise HTTPException(409, str(exc)) from exc
    try:
        raw = await ask_pi(name, prompt)
    except PiUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    if not is_current(root_dir(), snapshot):
        raise HTTPException(409, "Textbook changed during generation; retry against current sources")
    try:
        outcome = check_response(raw, snapshot)
    except GroundingError as exc:
        raise HTTPException(422, str(exc)) from exc
    response = {"course": name, "speaker": "pi", "source_sha256": snapshot.sha256, **outcome}
    # A model rejection, invalid citation or textbook revision above never
    # creates a transcript. Accepted abstentions remain explicitly unverified.
    try:
        chat_history.record(root_dir(), name, payload.message, response)
    except (chat_history.HistoryError, OSError, ValueError) as exc:
        raise HTTPException(409, "Could not save validated chat: " + str(exc)) from exc
    if outcome["grounding"] == "citation_checked" and lesson_timer.status(root_dir(), name).get("is_active"):
        lesson_timer.transition(root_dir(), name, "heartbeat")
    return response


def public_group(payload: dict) -> dict:
    """v4 CLI simulates tutor voices; v5 HTTP executes independent Agents."""
    return {**payload, "single_agent_simulation": False, "execution_backend": "agentscope"}


@api.get("/api/courses/{course}/group")
def group_status(course: str, _: Authenticated) -> dict:
    return public_group(learning_group.status(root_dir(), existing_course(course)))


@api.post("/api/courses/{course}/group/configure")
def group_configure(course: str, payload: GroupConfig, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return public_group(learning_group.configure(root_dir(), name, payload.members, payload.lead))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@api.post("/api/courses/{course}/group/start")
def group_start(course: str, payload: GroupStart, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return public_group(learning_group.start(root_dir(), name, payload.topic, payload.rounds))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@api.post("/api/courses/{course}/group/continue")
def group_continue(course: str, payload: GroupContinue, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return public_group(learning_group.continue_round(root_dir(), name, payload.question))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@api.post("/api/courses/{course}/group/next")
async def group_next(course: str, _: Authenticated) -> dict:
    name = existing_course(course)
    state = learning_group.status(root_dir(), name)
    speaker = state.get("next_speaker")
    session = state.get("session")
    if not speaker or not session:
        raise HTTPException(409, "No tutor turn available; wait for the learner")
    try:
        snapshot = retrieve(root_dir(), name, session["topic"])
        prompt = grounded_prompt(session["topic"], snapshot)
    except (EvidenceError, GroundingError) as exc:
        raise HTTPException(409, str(exc)) from exc
    try:
        raw = await generate_tutor_turn(speaker, prompt, session["turns"])
    except TutorUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    if not is_current(root_dir(), snapshot):
        raise HTTPException(409, "Textbook changed during tutor generation")
    try:
        outcome = check_response(raw, snapshot)
    except GroundingError as exc:
        raise HTTPException(422, str(exc)) from exc
    if outcome["grounding"] != "citation_checked":
        raise HTTPException(409, "Tutor abstained; discussion did not advance")
    try:
        result = learning_group.record(
            root_dir(), name, speaker, outcome["text"],
            expected_session_id=session["id"],
            expected_turns=len(session["turns"]),
            expected_topic=session["topic"],
            evidence={"sha256": snapshot.sha256, "citations": outcome["citations"]},
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {**public_group(result), "source_sha256": snapshot.sha256,
            "last_turn_evidence": outcome["citations"],
            "grounding": outcome["grounding"], "fact_verified": False,
            "single_agent_simulation": False, "execution_backend": "agentscope"}


app = api
