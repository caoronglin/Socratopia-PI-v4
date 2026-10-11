"""Local-first FastAPI application, preserving v4 course and timer contracts."""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from scripts.lib import learning_group, lesson_timer
from scripts.initialize import initialize as initialize_course
from scripts.lib.course_state import load_state, validate_state
from scripts.lib.repository import course_dir, iter_course_paths, validate_course_name

from platform_api.agentscope_tutors import TutorUnavailable, generate_tutor_turn
from platform_api.pi_gateway import PiUnavailable, ask_pi

api = FastAPI(title="Socratopia API", version="5.0.0-alpha.1", docs_url=None, redoc_url=None)


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


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


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


@api.post("/api/courses/{course}/chat")
async def chat(course: str, payload: ChatRequest, _: Authenticated) -> dict:
    name = existing_course(course)
    # A normal chat never marks a lesson complete or updates mastery.
    try:
        text = await ask_pi(name, payload.message)
    except PiUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    # Only an actual learner interaction can heartbeat an existing active lesson.
    if lesson_timer.status(root_dir(), name).get("is_active"):
        lesson_timer.transition(root_dir(), name, "heartbeat")
    return {"course": name, "speaker": "pi", "text": text, "mastery_updated": False}


@api.get("/api/courses/{course}/group")
def group_status(course: str, _: Authenticated) -> dict:
    return learning_group.status(root_dir(), existing_course(course))


@api.post("/api/courses/{course}/group/configure")
def group_configure(course: str, payload: GroupConfig, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return learning_group.configure(root_dir(), name, payload.members, payload.lead)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@api.post("/api/courses/{course}/group/start")
def group_start(course: str, payload: GroupStart, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return learning_group.start(root_dir(), name, payload.topic, payload.rounds)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@api.post("/api/courses/{course}/group/continue")
def group_continue(course: str, payload: GroupContinue, _: Authenticated) -> dict:
    name = existing_course(course)
    try:
        return learning_group.continue_round(root_dir(), name, payload.question)
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
        text = await generate_tutor_turn(speaker, session["topic"], session["turns"])
        return learning_group.record(root_dir(), name, speaker, text)
    except TutorUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


app = api
