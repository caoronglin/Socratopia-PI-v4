"""Persistent course-isolated lesson timer with explicit student-active heartbeats.

A 45-minute completed classroom session requires >=2700 measured active seconds.
Long gaps (>5 minutes), breaks and offline time are not silently counted.
No background process; the Cherry/Pi agent must call heartbeat during each exchange.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from scripts.lib.course_state import state_path, validate_state
from scripts.lib.prep import check_prep, parse_front_matter, prep_path
from scripts.lib.repository import (
    course_dir, read_json, safe_child_path, validate_course_name,
    validate_lesson_id, write_json_atomic,
)

MINIMUM_SECONDS = 45 * 60
MAX_HEARTBEAT_GAP = 5 * 60
SCHEMA = 1
PHASES = {"running", "paused", "interrupted", "completed"}


def _clock(now: datetime | None) -> datetime:
    value = now or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("计时必须使用带时区的真实时间")
    return value.astimezone(UTC)


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("计时记录缺少有效时间")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("计时记录的时间戳非法") from None
    return _clock(result)


def timer_path(root: Path, course: str) -> Path:
    return safe_child_path(course_dir(root, validate_course_name(course)),
                           "runtime", "lesson_timer.json")


@contextmanager
def _mutex(root: Path, course: str):
    runtime = safe_child_path(course_dir(root, course), "runtime")
    runtime.mkdir(parents=True, exist_ok=True)
    path = safe_child_path(runtime, "lesson_timer.lock")
    if path.is_symlink():
        raise ValueError("不允许计时锁是符号链接")
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            if not handle.read(1):
                handle.seek(0)
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _load(root: Path, course: str) -> dict[str, Any] | None:
    state = read_json(timer_path(root, course))
    if state is None:
        return None
    if state.get("schema_version") != SCHEMA or state.get("course") != course:
        raise ValueError("计时记录的 schema 或课程不匹配，不可自动重置")
    if state.get("phase") not in PHASES:
        raise ValueError("计时记录的 phase 非法")
    validate_lesson_id(state.get("lesson_id"))
    if state.get("minimum_seconds") != MINIMUM_SECONDS:
        raise ValueError("计时记录的最低时长配置不匹配")
    value = state.get("elapsed_seconds")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("计时记录的累计秒数非法")
    _parse_time(state.get("started_at"))
    _parse_time(state.get("last_at"))
    if not isinstance(state.get("session_id"), str) or len(state["session_id"]) != 32:
        raise ValueError("计时记录缺少 session_id")
    return state


def _ensure_ready(root: Path, course: str, lesson_id: str) -> str:
    path = state_path(root, course)
    state = read_json(path)
    if state is None:
        raise ValueError("课程 runtime 尚未落盘；不能启动虚构课堂计时")
    errors = validate_state(state)
    if errors or state.get("course") != course:
        raise ValueError("课程 runtime 无效：" + "; ".join(errors))
    ready = state["readiness"]
    if (state.get("phase") not in {"ready", "in_lesson"}
            or any(ready.get(name) != "ok" for name in ("catalog", "prep", "runtime"))
            or ready.get("reteach") != "clear" or state.get("blockers")):
        raise ValueError("课堂 readiness/blockers 尚未放行，不启动正式教学计时")
    if state.get("lesson_id") not in (None, lesson_id):
        raise ValueError("计时课号与课程 runtime 断点不一致")
    errors, warnings = check_prep(root, course, lesson_id)
    if errors or any(w.startswith("stale") for w in warnings):
        raise ValueError("PREP 未通过 ready / 版本检查：" + "; ".join(errors + warnings))
    front, _ = parse_front_matter(prep_path(root, course, lesson_id).read_text(encoding="utf-8"))
    if front.get("status") != "ready":
        raise ValueError("正式课堂计时需要 status: ready 的 PREP")
    chapter = front.get("chapter")
    if not isinstance(chapter, str) or not chapter.strip():
        raise ValueError("PREP 缺少真实章节")
    return chapter


def _accrue(state: dict[str, Any], now: datetime) -> dict[str, Any]:
    if state["phase"] != "running":
        return state
    last = _parse_time(state["last_at"])
    seconds = (now - last).total_seconds()
    if seconds < 0:
        raise ValueError("本机时钟回拨，暂停计时并核对系统时间；不得补算负时长")
    if seconds > MAX_HEARTBEAT_GAP:
        state["elapsed_seconds"] += MAX_HEARTBEAT_GAP
        state["phase"] = "paused"
        state["pause_reason"] = "heartbeat_timeout"
    else:
        state["elapsed_seconds"] += int(seconds)
    state["last_at"] = now.isoformat()
    return state


def _view(state: dict[str, Any], now: datetime) -> dict[str, Any]:
    snapshot = dict(state)
    _accrue(snapshot, now)
    snapshot["remaining_seconds"] = max(0, MINIMUM_SECONDS - snapshot["elapsed_seconds"])
    snapshot["duration_met"] = snapshot["elapsed_seconds"] >= MINIMUM_SECONDS
    snapshot["completed"] = snapshot["phase"] == "completed"
    snapshot["is_active"] = snapshot["phase"] == "running"
    return snapshot


def status(root: Path, course: str, *, now: datetime | None = None) -> dict[str, Any]:
    course = validate_course_name(course)
    clock = _clock(now)
    state = _load(root, course)
    return _view(state, clock) if state else {
        "course": course, "phase": "not_started", "completed": False,
        "remaining_seconds": MINIMUM_SECONDS, "minimum_seconds": MINIMUM_SECONDS,
    }


def _archive(root: Path, course: str, old: dict[str, Any]) -> None:
    dest = safe_child_path(course_dir(root, course), "runtime", "lesson_timer_records",
                           old["session_id"] + ".json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("x", encoding="utf-8") as output:
        json.dump(old, output, ensure_ascii=False, indent=2)
        output.write("\n")


def start(root: Path, course: str, lesson_id: str, *,
          now: datetime | None = None) -> dict[str, Any]:
    course = validate_course_name(course)
    lesson_id = validate_lesson_id(lesson_id)
    clock = _clock(now)
    chapter = _ensure_ready(root, course, lesson_id)
    with _mutex(root, course):
        old = _load(root, course)
        if old and old["phase"] not in {"completed", "interrupted"}:
            if old["lesson_id"] != lesson_id:
                raise ValueError("已有其他课号的计时进行中；先处理当前课堂")
            return _view(old, clock)  # Idempotent; don't reset accumulated time.
        if old:
            _archive(root, course, old)
        state = {
            "schema_version": SCHEMA, "course": course, "lesson_id": lesson_id,
            "chapter": chapter, "session_id": uuid4().hex, "phase": "running",
            "minimum_seconds": MINIMUM_SECONDS, "elapsed_seconds": 0,
            "started_at": clock.isoformat(), "last_at": clock.isoformat(),
            "pause_reason": None,
        }
        write_json_atomic(timer_path(root, course), state)
        return _view(state, clock)


def transition(root: Path, course: str, action: str, *,
               now: datetime | None = None) -> dict[str, Any]:
    course = validate_course_name(course)
    if action not in {"heartbeat", "pause", "resume", "finish", "interrupt"}:
        raise ValueError("未知计时操作")
    clock = _clock(now)
    with _mutex(root, course):
        state = _load(root, course)
        if state is None:
            raise ValueError("本课尚未开始计时")
        if state["phase"] == "completed":
            if action == "finish":
                return _view(state, clock)  # Idempotent finish.
            raise ValueError("已完成的课堂不能再次累计时间")
        state = _accrue(state, clock)
        if action == "heartbeat":
            if state["phase"] != "running":
                write_json_atomic(timer_path(root, course), state)
                result = _view(state, clock)
                result["heartbeat_not_recorded"] = "paused_or_interrupted"
                return result
        elif action == "resume":
            if state["phase"] not in {"paused", "interrupted"}:
                raise ValueError("只有暂停/中断的课堂可恢复")
            state["phase"] = "running"
            state["last_at"] = clock.isoformat()
            state["pause_reason"] = None
        elif action == "pause":
            if state["phase"] != "paused":
                if state["phase"] != "running":
                    raise ValueError("只有运行中的课堂可暂停")
                state["phase"] = "paused"
                state["pause_reason"] = "manual"
        elif action == "interrupt":
            state["phase"] = "interrupted"
            state["pause_reason"] = "early_exit"
        elif action == "finish":
            if state["elapsed_seconds"] < MINIMUM_SECONDS:
                # Persist measured time but DO NOT mark a short lesson complete.
                write_json_atomic(timer_path(root, course), state)
                result = _view(state, clock)
                result["finish_denied"] = "minimum_45_minutes_not_met"
                return result
            state["phase"] = "completed"
            state["pause_reason"] = None
            state["completed_at"] = clock.isoformat()
        write_json_atomic(timer_path(root, course), state)
        return _view(state, clock)
