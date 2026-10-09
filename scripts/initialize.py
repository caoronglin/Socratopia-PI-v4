"""Safe guided first-run setup for one Socratopia course.

Never replaces existing course files, guesses an active course, marks ready,
creates PREP/book content, or starts a completed lesson.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib import learning_group
from scripts.lib.course_state import state_path, validate_state
from scripts.lib.repository import (
    course_dir, read_json, textbook_dir, validate_course_name, write_json_atomic,
)
from scripts.scaffold_course import scaffold

TUTORS = {"D", "E", "F"}


def inspect(root: Path, course: str) -> dict:
    name = validate_course_name(course)
    data, book = course_dir(root, name), textbook_dir(root, name)
    state = read_json(state_path(root, name))
    errors = validate_state(state) if state else []
    if state and state.get("course") != name:
        errors.append("runtime course 与请求的课程不匹配")
    return {
        "course": name,
        "course_exists": data.is_dir(),
        "runtime_exists": state is not None,
        "runtime_valid": bool(state) and not errors,
        "runtime_errors": errors,
        "active_tutor": state.get("active_tutor") if state else None,
        "book_exists": (book / "book.md").is_file(),
        "outline_exists": (book / "_outline.md").is_file(),
        "progress_exists": (data / "PROGRESS.md").is_file(),
        "group_configured": learning_group.status(root, name)["configured"],
        "readiness": state.get("readiness") if state else None,
        "next_steps": [
            "确认已放入当前课程的合法教材，规范化为 book.md 和 _outline.md",
            "教材检查完成后按章执行 prep.py chapter；填充教案并通过 ready gate",
            "开课前验证 runtime/PREP；正式课堂独立计时至少45分钟",
        ],
        "writes": False,
    }


def initialize(root: Path, course: str, tutor: str = "F",
               members: list[str] | None = None) -> dict:
    name = validate_course_name(course)
    tutor = tutor.strip().upper()
    if tutor not in TUTORS:
        raise ValueError("主导师只能是 D（三月七）、E（丹恒）或 F（姬子）")
    if members:
        members = learning_group._members(members)
        if tutor not in members:
            raise ValueError("主导师必须属于初始化时选择的小组")
    before = inspect(root, name)
    if before["runtime_exists"] and not before["runtime_valid"]:
        raise ValueError("现有课程 runtime 无效；请先诊断，不得在初始化时覆盖")
    # Existing configuration is never reset even when users re-run the wizard.
    if before["group_configured"] and members:
        current = learning_group.status(root, name)
        if current["members"] != members or current["lead"] != tutor:
            raise ValueError("已有学习小组配置；请单独使用 learning_group.py configure 修改")
    created = scaffold(root, name)
    state_pathname = state_path(root, name)
    state = read_json(state_pathname)
    initial_tutor_saved = False
    if not before["runtime_exists"]:
        state["active_tutor"] = tutor
        write_json_atomic(state_pathname, state)
        initial_tutor_saved = True
    group = None
    if members and not before["group_configured"]:
        group = learning_group.configure(root, name, members, tutor)
    return {
        "course": name, "created": created,
        "initial_tutor": (tutor if initial_tutor_saved else state.get("active_tutor")),
        "initial_tutor_saved": initial_tutor_saved,
        "group": group if group else learning_group.status(root, name),
        "ready_for_class": False,
        "next_steps": inspect(root, name)["next_steps"],
        "message": "只初始化缺失骨架；主教材、PREP、课堂计时、掌握状态均未自动生成或放行",
    }


def wizard(root: Path) -> dict:
    print("Socratopia 首次使用引导（本地运行；不联网；现有文件不覆盖）")
    course = input("1/4 课程名：").strip()
    name = validate_course_name(course)
    tutor = input("2/4 主导师 D=三月七 E=丹恒 F=姬子 [F]：").strip().upper() or "F"
    if tutor not in TUTORS:
        raise ValueError("主导师必须是 D/E/F")
    other = input("3/4 学习小组导师（任选2–3位，如 D E F；回车表示不启用）：").strip()
    members = other.upper().replace(",", " ").split() if other else None
    if members and (learning_group._members(members) != members or tutor not in members):
        raise ValueError("学习小组必须包含主导师，成员 D/E/F 且不可重复")
    preview = inspect(root, name)
    print(json.dumps({"plan": preview, "requested_tutor": tutor,
                      "requested_group": members}, ensure_ascii=False, indent=2))
    confirm = input("4/4 只补缺失文件并创建配置？输入 YES 确认：").strip()
    if confirm != "YES":
        return {"applied": False, "reason": "未确认，无文件写入"}
    return {"applied": True, **initialize(root, name, tutor, members)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Socratopia 引导初始化（默认只读 plan）")
    sub = parser.add_subparsers(dest="action", required=True)
    for act in ("plan", "apply", "wizard"):
        cmd = sub.add_parser(act)
        if act != "wizard":
            cmd.add_argument("--course", required=True)
        if act == "apply":
            cmd.add_argument("--tutor", default="F", choices=("D", "E", "F"))
            cmd.add_argument("--members", nargs="+", help="可选 2–3 位学习小组导师 D E F")
    args = parser.parse_args(argv)
    try:
        if args.action == "wizard":
            result = wizard(ROOT)
        elif args.action == "plan":
            result = inspect(ROOT, args.course)
        else:
            result = initialize(ROOT, args.course, args.tutor, args.members)
    except (ValueError, OSError, EOFError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
