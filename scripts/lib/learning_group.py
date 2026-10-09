"""Bounded learner-facing multi-tutor discussion (one Pi Agent, multiple voices).

The CLI controls participants, speaker order and observable transcript. It does
not invoke other models/agents or change formal lesson progress or timer.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from scripts.lib.course_state import state_path, validate_state
from scripts.lib.lesson_timer import _mutex
from scripts.lib.repository import (
    course_dir, read_json, safe_child_path, textbook_dir, validate_course_name,
    write_json_atomic,
)

VALID_TUTORS = {"D": "三月七", "E": "丹恒", "F": "姬子"}
MAX_ROUNDS = 3
MAX_UTTERANCE = 2500


def group_path(root: Path, course: str) -> Path:
    return safe_child_path(course_dir(root, validate_course_name(course)),
                           "runtime", "learning_group.json")


def _read(root: Path, course: str) -> dict[str, Any] | None:
    state = read_json(group_path(root, course))
    if state is None:
        return None
    if state.get("schema_version") != 1 or state.get("course") != course:
        raise ValueError("学习小组记录与课程/schema 不一致")
    members = state.get("members")
    if (not isinstance(members, list) or not 2 <= len(members) <= 3
            or len(set(members)) != len(members)
            or any(m not in VALID_TUTORS for m in members)
            or state.get("lead") not in members):
        raise ValueError("学习小组的导师配置无效")
    session = state.get("session")
    if session is not None:
        if not isinstance(session, dict) or session.get("phase") not in {
                "speaking", "awaiting_user", "finished", "stopped"}:
            raise ValueError("学习小组当前讨论状态无效")
        rounds = session.get("max_rounds")
        if type(rounds) is not int or not 1 <= rounds <= MAX_ROUNDS:
            raise ValueError("讨论轮次超出有效范围")
        if (type(session.get("round")) is not int or not 1 <= session["round"] <= rounds
                or type(session.get("index")) is not int
                or not 0 <= session["index"] <= len(members)):
            raise ValueError("讨论发言游标无效")
        turns = session.get("turns")
        if not isinstance(turns, list) or len(turns) > len(members) * rounds:
            raise ValueError("讨论记录超出受限范围")
    return state


def _emit(state: dict[str, Any], root: Path) -> dict[str, Any]:
    view = {
        "course": state["course"], "members": state["members"],
        "lead": state["lead"], "names": {m: VALID_TUTORS[m] for m in state["members"]},
        "session": state["session"], "single_agent_simulation": True,
        "writes_mastery": False, "lesson_timer_unchanged": True,
    }
    session = state["session"]
    if session:
        i = session["index"]
        view["next_speaker"] = (state["members"][i] if session["phase"] == "speaking"
                                and i < len(state["members"]) else None)
        view["requires_user_turn"] = session["phase"] == "awaiting_user"
        view["may_continue"] = (session["phase"] == "awaiting_user"
                                and session["round"] < session["max_rounds"])
        view["book_exists"] = (textbook_dir(root, state["course"]) / "book.md").is_file()
    return view


def status(root: Path, course: str) -> dict[str, Any]:
    name = validate_course_name(course)
    value = _read(root, name)
    if not value:
        return {"course": name, "configured": False, "session": None}
    return {"configured": True, **_emit(value, root)}


def _members(members: list[str]) -> list[str]:
    result = [v.strip().upper() for v in members]
    if not 2 <= len(result) <= 3 or len(set(result)) != len(result):
        raise ValueError("学习小组必须有 2–3 位不同导师")
    if any(v not in VALID_TUTORS for v in result):
        raise ValueError("仅支持学习者可见导师 D/E/F；A/B/C 为内部教研组")
    return result


def configure(root: Path, course: str, members: list[str], lead: str) -> dict[str, Any]:
    course = validate_course_name(course)
    members = _members(members)
    lead = lead.upper().strip()
    if lead not in members:
        raise ValueError("主持导师必须在小组成员中")
    persisted = read_json(state_path(root, course))
    if not persisted or persisted.get("course") != course or validate_state(persisted):
        raise ValueError("请先完成本课程引导初始化；缺少合法落盘 runtime")
    with _mutex(root, course):
        previous = _read(root, course)
        if previous and previous["session"] and previous["session"]["phase"] in {
                "speaking", "awaiting_user"}:
            raise ValueError("讨论进行中，请先 stop，再修改成员")
        if previous and previous["members"] == members and previous["lead"] == lead:
            return _emit(previous, root)
        state = {"schema_version": 1, "course": course, "members": members,
                 "lead": lead, "session": None}
        write_json_atomic(group_path(root, course), state)
        return _emit(state, root)


def _topic(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 240 or any(ch in value for ch in "\r\n\x00"):
        raise ValueError("请提供单行、明确且不超过 240 字的讨论问题")
    return value


def start(root: Path, course: str, topic: str, rounds: int = 2) -> dict[str, Any]:
    course, topic = validate_course_name(course), _topic(topic)
    if type(rounds) is not int or not 1 <= rounds <= MAX_ROUNDS:
        raise ValueError("一场讨论最多 3 轮")
    with _mutex(root, course):
        state = _read(root, course)
        if not state:
            raise ValueError("请先配置 2–3 位导师")
        old = state.get("session")
        if old and old["phase"] in {"speaking", "awaiting_user"}:
            if old["topic"] != topic or old["max_rounds"] != rounds:
                raise ValueError("已有进行中的讨论，先 stop 或继续")
            return _emit(state, root)
        state["session"] = {"id": uuid4().hex, "topic": topic, "phase": "speaking",
                            "max_rounds": rounds, "round": 1, "index": 0,
                            "turns": [], "started_at": datetime.now(UTC).isoformat()}
        write_json_atomic(group_path(root, course), state)
        return _emit(state, root)


def record(root: Path, course: str, speaker: str, statement: str) -> dict[str, Any]:
    course = validate_course_name(course)
    speaker = speaker.upper().strip()
    statement = statement.strip()
    if not statement or len(statement) > MAX_UTTERANCE or "\x00" in statement:
        raise ValueError("发言必须是非空的实际生成内容，且不超过 2500 字")
    with _mutex(root, course):
        state = _read(root, course)
        if not state or not state["session"] or state["session"]["phase"] != "speaking":
            raise ValueError("当前没有等待导师发言的讨论")
        session = state["session"]
        expected = state["members"][session["index"]]
        if speaker != expected:
            raise ValueError(f"发言顺序错误，当前应为导师 {expected}")
        session["turns"].append({"round": session["round"], "speaker": speaker,
                                 "text": statement})
        session["index"] += 1
        if session["index"] == len(state["members"]):
            session["phase"] = ("finished" if session["round"] == session["max_rounds"]
                                else "awaiting_user")
        write_json_atomic(group_path(root, course), state)
        return _emit(state, root)


def continue_round(root: Path, course: str, question: str = "") -> dict[str, Any]:
    course = validate_course_name(course)
    with _mutex(root, course):
        state = _read(root, course)
        if not state or not state["session"]:
            raise ValueError("没有可继续的讨论")
        session = state["session"]
        if session["phase"] != "awaiting_user" or session["round"] >= session["max_rounds"]:
            raise ValueError("只能在上一轮完成、用户继续之后开启下一轮")
        if question:
            session["topic"] = _topic(question)
        session["round"] += 1
        session["index"] = 0
        session["phase"] = "speaking"
        write_json_atomic(group_path(root, course), state)
        return _emit(state, root)


def stop(root: Path, course: str) -> dict[str, Any]:
    course = validate_course_name(course)
    with _mutex(root, course):
        state = _read(root, course)
        if not state or not state["session"]:
            raise ValueError("当前没有小组讨论")
        if state["session"]["phase"] not in {"finished", "stopped"}:
            state["session"]["phase"] = "stopped"
            write_json_atomic(group_path(root, course), state)
        return _emit(state, root)
