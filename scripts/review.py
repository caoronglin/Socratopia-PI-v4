#!/usr/bin/env python3
"""Review-loop CLI: exit practice, retrieval practice, confusion cards, results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib import review as review_lib  # noqa: E402
from scripts.lib.repository import course_dir, validate_course_name  # noqa: E402


def _write_plan(root: Path, course: str, lesson_id: str, kind: str, items: list) -> Path:
    d = course_dir(root, course) / "PRACTICE"
    d.mkdir(parents=True, exist_ok=True)
    json_path = d / f"{lesson_id}_{kind}.json"
    md_path = d / f"{lesson_id}_{kind}.md"
    title = "本节结束练习" if kind == "exit" else "前课检索练习"
    json_path.write_text(
        json.dumps({"lesson_id": lesson_id, "kind": kind, "items": items}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(review_lib.render_practice_markdown(course, lesson_id, title, items), encoding="utf-8")
    return md_path


def cmd_exit(args: argparse.Namespace) -> int:
    validate_course_name(args.course)
    kps = [k.strip() for k in args.knowledge_points.split(";") if k.strip()]
    extra_items: list = []
    if args.items:
        data = json.loads(Path(args.items).read_text(encoding="utf-8"))
        extra_items = data if isinstance(data, list) else [data]
    state = review_lib.load_review_state(ROOT, args.course)
    lesson_confusions = [c for c in state.get("confusions", []) if c.get("lesson_id") == args.lesson_id]
    items = review_lib.build_exit_plan(args.lesson_id, args.chapter, kps, lesson_confusions, extra_items=extra_items)
    path = _write_plan(ROOT, args.course, args.lesson_id, "exit", items)
    state.setdefault("exit_practice", []).append({"lesson_id": args.lesson_id, "items": items, "completed": False})
    review_lib.save_review_state(ROOT, args.course, state)
    print(f"已生成本节结束练习：{path}")
    fill = [i for i in items if i.get("requires_fill")]
    if fill:
        print(f"⚠️ 含 {len(fill)} 道待补题（application/transfer）：使用前必须用 --items 传入真实题目。")
    return 0


def cmd_retrieval(args: argparse.Namespace) -> int:
    validate_course_name(args.course)
    from_lessons = [x.strip() for x in args.from_lessons.split(",") if x.strip()]
    state = review_lib.load_review_state(ROOT, args.course)
    due_cards = review_lib.due_cards_from_file(course_dir(ROOT, args.course) / "cards.json")
    prerequisites = [x.strip() for x in args.prerequisites.split(";") if x.strip()]
    items = review_lib.build_retrieval_plan(args.lesson_id, from_lessons, state, limit=args.limit, due_cards=due_cards, prerequisites=prerequisites)
    path = _write_plan(ROOT, args.course, args.lesson_id, "retrieval", items)
    print(f"已生成前课检索练习：{path}")
    print(f"（含到期卡 {len(due_cards)} 张、前置知识点 {len(prerequisites)} 个）")
    return 0


def cmd_cards(args: argparse.Namespace) -> int:
    validate_course_name(args.course)
    state = review_lib.load_review_state(ROOT, args.course)
    drafts: list = []
    for confusion in state.get("confusions", []):
        if confusion.get("lesson_id") != args.lesson_id:
            continue
        drafts.extend(review_lib.card_drafts_for_confusion(confusion, chapter=args.chapter, section=args.section))
    if not drafts:
        print(f"课程 {args.course} 第 {args.lesson_id} 课暂无已记录混淆，未生成卡片。")
        return 0
    pending = course_dir(ROOT, args.course) / "_pending_cards.md"
    blocks = review_lib.render_pending_cards(args.course, drafts)
    if pending.exists():
        pending.write_text(review_lib.merge_pending_cards(pending.read_text(encoding="utf-8"), blocks), encoding="utf-8")
    else:
        pending.write_text(blocks, encoding="utf-8")
    print(f"已生成待导入卡片草案：{pending}（导入为独立步骤，不影响课堂事实）")
    return 0


def cmd_confusion(args: argparse.Namespace) -> int:
    validate_course_name(args.course)
    confusion = review_lib.record_confusion(
        ROOT, args.course, args.lesson_id, args.knowledge_point, args.type,
        args.learner_model, args.evidence, source_anchor=args.source_anchor,
        corrective=args.corrective, parallel_retest=args.parallel_retest,
    )
    print(json.dumps(confusion, ensure_ascii=False, indent=2))
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    if not args.apply:
        print("结果写入需要 --apply。")
        return 1
    validate_course_name(args.course)
    state = review_lib.record_retrieval_result(ROOT, args.course, args.lesson_id, args.item_id, args.result, note=args.note)
    print(f"已记录 {args.lesson_id} / {args.item_id} → {args.result}")
    open_count = sum(1 for c in state["confusions"] if c.get("status") in {"needs_review", "needs_reteach"})
    print(f"当前 needs_review/needs_reteach 混淆：{open_count}")
    return 0


def cmd_enqueue(args: argparse.Namespace) -> int:
    validate_course_name(args.course)
    kinds = [k.strip() for k in args.kinds.split(",") if k.strip()]
    if not kinds:
        print("--kinds 不能为空（可选：exit,cards,retrieval）。")
        return 1
    for kind in kinds:
        task = review_lib.enqueue_review_task(ROOT, args.course, args.lesson_id, kind, summary=args.summary)
        print(f"已入队：{task['kind']}（{task['id'][:8]}，status={task['status']}）")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    validate_course_name(args.course)
    state = review_lib.load_review_state(ROOT, args.course)
    print(f"课程：{args.course}")
    print(f"混淆记录：{len(state.get('confusions', []))}")
    for c in state.get("confusions", []):
        print(f"- {c.get('confusion_id')} | {c.get('lesson_id')} | {c.get('knowledge_point')} | {c.get('type')} | {c.get('status')}")
    print(f"退出练习：{len(state.get('exit_practice', []))}")
    print(f"检索记录：{len(state.get('retrieval_log', []))}")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="复习闭环：退出练习/检索练习/混淆闪卡")
    sub = parser.add_subparsers(dest="command", required=True)

    p_exit = sub.add_parser("exit")
    p_exit.add_argument("--course", required=True)
    p_exit.add_argument("--lesson-id", required=True)
    p_exit.add_argument("--chapter", default="")
    p_exit.add_argument("--knowledge-points", default="")
    p_exit.add_argument("--items", default="")
    p_exit.set_defaults(func=cmd_exit)

    p_retr = sub.add_parser("retrieval")
    p_retr.add_argument("--course", required=True)
    p_retr.add_argument("--lesson-id", required=True)
    p_retr.add_argument("--from-lessons", required=True)
    p_retr.add_argument("--prerequisites", default="")
    p_retr.add_argument("--limit", type=int, default=6)
    p_retr.set_defaults(func=cmd_retrieval)

    p_cards = sub.add_parser("cards")
    p_cards.add_argument("--course", required=True)
    p_cards.add_argument("--lesson-id", required=True)
    p_cards.add_argument("--chapter", default="")
    p_cards.add_argument("--section", default="")
    p_cards.set_defaults(func=cmd_cards)

    p_conf = sub.add_parser("confusion")
    p_conf.add_argument("--course", required=True)
    p_conf.add_argument("--lesson-id", required=True)
    p_conf.add_argument("--knowledge-point", required=True)
    p_conf.add_argument("--type", required=True, choices=sorted(review_lib.CONFUSION_TYPES))
    p_conf.add_argument("--learner-model", required=True)
    p_conf.add_argument("--evidence", required=True)
    p_conf.add_argument("--source-anchor", default="")
    p_conf.add_argument("--corrective", default="")
    p_conf.add_argument("--parallel-retest", default="")
    p_conf.set_defaults(func=cmd_confusion)

    p_rec = sub.add_parser("record")
    p_rec.add_argument("--course", required=True)
    p_rec.add_argument("--lesson-id", required=True)
    p_rec.add_argument("--item-id", required=True)
    p_rec.add_argument("--result", choices=["passed", "hint_correct", "failed"], required=True)
    p_rec.add_argument("--note", default="")
    p_rec.add_argument("--apply", action="store_true")
    p_rec.set_defaults(func=cmd_record)

    p_st = sub.add_parser("status")
    p_st.add_argument("--course", required=True)
    p_st.set_defaults(func=cmd_status)

    p_enq = sub.add_parser("enqueue")
    p_enq.add_argument("--course", required=True)
    p_enq.add_argument("--lesson-id", required=True)
    p_enq.add_argument("--kinds", required=True)
    p_enq.add_argument("--summary", default="")
    p_enq.set_defaults(func=cmd_enqueue)

    args = parser.parse_args()
    lesson_id = getattr(args, "lesson_id", "")
    kind = getattr(args, "command", "")
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001
        print(f"✗ {kind} 执行失败：{exc}")
        if lesson_id and kind in review_lib.REVIEW_TASK_KINDS:
            task = review_lib.enqueue_review_task(ROOT, args.course, lesson_id, kind, summary=f"自动入队（{kind} 失败待重跑）")
            print(f"已自动入队待重跑：{task['kind']}（{task['id'][:8]}）")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
