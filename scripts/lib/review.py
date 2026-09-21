"""Review-loop state, exit/retrieval practice plans, confusion-driven cards (v4)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.lib.repository import course_dir, read_json, write_json_atomic
from scripts.lib.task_queue import enqueue_task

REVIEW_TASK_KINDS = {
    "exit": "generate_exit_practice",
    "cards": "generate_confusion_cards",
    "retrieval": "prepare_next_lesson_retrieval",
}

CONFUSION_TYPES = {
    "concept_confusion",
    "direction_reversal",
    "causal_error",
    "boundary_error",
    "definition_only",
    "procedure_skip",
    "hint_dependence",
    "transfer_failure",
}

CARD_PLANS = {
    "concept_confusion": ["辨析卡", "错误模型卡"],
    "direction_reversal": ["方向判断卡", "情境判断卡"],
    "causal_error": ["因果链卡", "反例卡"],
    "boundary_error": ["边界反例卡", "适用条件卡"],
    "definition_only": ["深度解释卡"],
    "procedure_skip": ["关键步骤卡", "陷阱卡"],
    "hint_dependence": ["无提示检索卡"],
    "transfer_failure": ["情境迁移卡"],
}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def review_state_path(root: Path, course: str) -> Path:
    return course_dir(root, course) / "runtime" / "review_state.json"


def default_review_state(course: str) -> dict[str, Any]:
    return {"schema_version": 1, "course": course, "confusions": [], "exit_practice": [], "retrieval_log": []}


def load_review_state(root: Path, course: str) -> dict[str, Any]:
    stored = read_json(review_state_path(root, course))
    return stored or default_review_state(course)


def save_review_state(root: Path, course: str, state: Mapping[str, Any]) -> None:
    write_json_atomic(review_state_path(root, course), dict(state))


def validate_review_state(state: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    for key in ("schema_version", "course", "confusions", "exit_practice", "retrieval_log"):
        if key not in state:
            problems.append(f"缺少顶层字段：{key}")
    for key in ("confusions", "exit_practice", "retrieval_log"):
        if not isinstance(state.get(key, []), list):
            problems.append(f"{key} 必须是列表")
    for i, confusion in enumerate(state.get("confusions", [])):
        for field in ("confusion_id", "lesson_id", "knowledge_point", "type", "status"):
            if not str(confusion.get(field) or "").strip():
                problems.append(f"confusions[{i}] 缺少字段：{field}")
        if confusion.get("type") not in CONFUSION_TYPES:
            problems.append(f"confusions[{i}] 非法 type：{confusion.get('type')}")
        if confusion.get("status") not in {"needs_review", "resolved", "needs_reteach"}:
            problems.append(f"confusions[{i}] 非法 status：{confusion.get('status')}")
    return problems


def enqueue_review_task(root: Path, course: str, lesson_id: str, kind: str, summary: str = "") -> dict[str, Any]:
    """Idempotently enqueue an A+ review task (reuses a non-terminal duplicate)."""
    task_kind = REVIEW_TASK_KINDS.get(kind)
    if task_kind is None:
        raise ValueError(f"未知复习任务类型：{kind}（可选：{'/'.join(REVIEW_TASK_KINDS)}）")
    return enqueue_task(
        root,
        course,
        task_kind,
        idempotency_key=f"{task_kind}-{lesson_id}",
        lesson_id=lesson_id,
        payload={"lesson": lesson_id, "summary": summary},
    )


def due_cards_from_file(cards_path: Path, now: datetime | None = None, limit: int = 3) -> list[Mapping[str, Any]]:
    """Select FSRS-due cards (state != 0 and due <= now) for retrieval blending."""
    if not cards_path.exists():
        return []
    data = read_json(cards_path)
    if not data:
        return []
    now_iso = (now or datetime.now(UTC)).isoformat()
    due: list[Mapping[str, Any]] = []
    for card in data.get("cards", []):
        fsrs = card.get("fsrs") or {}
        if fsrs.get("state") in (0, None):
            continue
        due_iso = fsrs.get("due") or ""
        if due_iso and due_iso <= now_iso:
            due.append(card)
    return due[:limit]


def record_confusion(
    root: Path,
    course: str,
    lesson_id: str,
    knowledge_point: str,
    confusion_type: str,
    learner_model: str,
    evidence: str,
    source_anchor: str = "",
    corrective: str = "",
    parallel_retest: str = "",
) -> dict[str, Any]:
    """Append one confusion record, deduplicating on (lesson, knowledge_point, type)."""
    if confusion_type not in CONFUSION_TYPES:
        raise ValueError(f"未知混淆类型：{confusion_type}")
    state = load_review_state(root, course)
    for item in state["confusions"]:
        if (
            item.get("lesson_id") == lesson_id
            and item.get("knowledge_point") == knowledge_point
            and item.get("type") == confusion_type
        ):
            item["learner_model"] = learner_model
            item["evidence"] = evidence
            item["updated_at"] = _now()
            save_review_state(root, course, state)
            return item
    seq = len(state["confusions"]) + 1
    confusion = {
        "confusion_id": f"conf-{datetime.now(UTC).strftime('%Y%m%d')}-{seq:03d}",
        "lesson_id": lesson_id,
        "knowledge_point": knowledge_point,
        "type": confusion_type,
        "learner_model": learner_model,
        "evidence": evidence,
        "source_anchor": source_anchor,
        "corrective": corrective,
        "parallel_retest": parallel_retest,
        "status": "needs_review",
        "created_at": _now(),
        "updated_at": _now(),
    }
    state["confusions"].append(confusion)
    save_review_state(root, course, state)
    return confusion


def _recall_items(chapter: str, knowledge_points: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for i, kp in enumerate(knowledge_points[:3], 1):
        items.append(
            {
                "item_id": f"exit-recall-{i}",
                "type": "recall",
                "prompt": f"用自己的话解释：{kp}（是什么、不是什么、适用条件）。",
                "objective_id": "",
                "source_anchor": "",
                "rubric": "能说清定义、边界和一个例子即通过。",
                "common_mistake": "只背原句、说不出例子或适用条件。",
            }
        )
    return items


def build_exit_plan(
    lesson_id: str,
    chapter: str,
    knowledge_points: list[str],
    confusions: list[Mapping[str, Any]],
    anchors: Mapping[str, str] | None = None,
    extra_items: list[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build an exit plan: recall, main-line, confusion checks, app, transfer.

    `extra_items` are real application/transfer questions; without them the plan
    emits `requires_fill` placeholders that must never be shown to the learner.
    """
    anchors = anchors or {}
    items = _recall_items(chapter, knowledge_points)
    items.append(
        {
            "item_id": "exit-mainline",
            "type": "mainline",
            "prompt": f"用 3–5 句话复述本节（{chapter}）的主线逻辑链。",
            "objective_id": "",
            "source_anchor": anchors.get("mainline", ""),
            "rubric": "能按因果顺序说出核心节点及联系。",
            "common_mistake": "罗列名词但没有因果或顺序。",
        }
    )
    for n, confusion in enumerate(confusions, 1):
        kp = str(confusion.get("knowledge_point") or "本知识点")
        items.append(
            {
                "item_id": f"exit-conf-{n}",
                "type": "confusion",
                "confusion_id": str(confusion.get("confusion_id") or ""),
                "prompt": f"换一个情境判断：围绕 {kp}，先给出正确结论，再说明错误说法错在哪一步。",
                "objective_id": "",
                "source_anchor": str(confusion.get("source_anchor") or ""),
                "rubric": "既答对结论，又能指出原错误模型失效的步骤。",
                "common_mistake": "结论对但说不出错误模型；或错误模型未改变。",
            }
        )
    extra = {str(e.get("type", "")): e for e in (extra_items or [])}
    kp_app = knowledge_points[0] if knowledge_points else "本节核心概念"
    kp_transfer = knowledge_points[-1] if knowledge_points else "本节核心概念"
    app_item: dict[str, Any] = dict(
        extra.get("application")
        or {
            "item_id": "exit-app",
            "type": "application",
            "prompt": f"【待补题】为「{kp_app}」编写一道真实应用情境题（具体情境+问题+参考答案要点+常见误区），由主模型/assessment-designer 完成。",
            "objective_id": "",
            "source_anchor": anchors.get("application", ""),
            "rubric": "步骤正确、使用本节概念、结论与过程一致。",
            "common_mistake": "只写结论无过程；或套用错概念。",
            "requires_fill": True,
        }
    )
    transfer_item: dict[str, Any] = dict(
        extra.get("transfer")
        or {
            "item_id": "exit-transfer",
            "type": "transfer",
            "prompt": f"【待补题】编写一道以「{kp_transfer}」为核心的跨小节/跨章迁移题（说明它能解释什么、不能解释什么）。",
            "objective_id": "",
            "source_anchor": anchors.get("transfer", ""),
            "rubric": "能迁移并说明边界。",
            "common_mistake": "强行套用、忽略适用条件。",
            "requires_fill": True,
        }
    )
    items.append(app_item)
    items.append(transfer_item)
    return items


def render_practice_markdown(course: str, lesson_id: str, title: str, items: list[Mapping[str, Any]]) -> str:
    """Render questions separated from answers; `requires_fill` stay in a prep-only zone."""
    learner_items = [i for i in items if not i.get("requires_fill")]
    fill_items = [i for i in items if i.get("requires_fill")]
    lines = [f"# {course} · {title}", "", f"生成于 {_now()}；按 `SYSTEM/SPEC/CLASSROOM_CONTRACT.md` 执行。", ""]
    if fill_items:
        lines += [f"> ⚠️ 本计划含 {len(fill_items)} 道待补题（下方「待补题」区）；完成替换前不得发给学习者。", ""]
    lines += ["## 练习", ""]
    for item in learner_items:
        lines += [f"### {item['item_id']} · {item['type']}", "", str(item["prompt"]), ""]
    if learner_items:
        lines += ["---", "", "## 答案与讲解（完成后查看）", ""]
        for item in learner_items:
            lines += [f"### {item['item_id']}", "", f"- 参考标准：{item.get('rubric', '')}", f"- 常见误区：{item.get('common_mistake', '')}"]
            if item.get("source_anchor"):
                lines.append(f"- 锚点：{item['source_anchor']}")
            lines.append("")
    if fill_items:
        lines += ["---", "", "## ⚠️ 待补题（备课用，勿直接发给学习者）", ""]
        for item in fill_items:
            lines += [f"### {item['item_id']} · {item['type']}", "", str(item["prompt"]), "", f"- 参考标准：{item.get('rubric', '')}", f"- 常见误区：{item.get('common_mistake', '')}", ""]
    return "\n".join(lines) + "\n"


def select_retrieval_targets(
    state: Mapping[str, Any],
    from_lessons: list[str],
    limit: int = 6,
    due_cards: list[Mapping[str, Any]] | None = None,
    prerequisites: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Select retrieval items by priority: reteach > needs_review > due cards > mainline > exit > prereq."""
    lessons = set(from_lessons)
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(item: dict[str, Any]) -> None:
        key = item.get("item_id") or item.get("confusion_id") or f"{item.get('lesson_id', '')}-{len(seen)}"
        if key not in seen:
            seen.add(key)
            items.append(item)

    for confusion in state.get("confusions", []):
        status = confusion.get("status")
        in_recent = confusion.get("lesson_id") in lessons
        if status == "needs_reteach" or (status == "needs_review" and in_recent):
            add(
                {
                    "item_id": f"retr-conf-{confusion.get('confusion_id', '')}",
                    "type": "confusion",
                    "lesson_id": confusion.get("lesson_id", ""),
                    "knowledge_point": confusion.get("knowledge_point", ""),
                    "prompt": f"无提示回答：围绕「{confusion.get('knowledge_point', '')}」给出正确结论，并指出错误模型错在哪。",
                    "rubric": "独立给出正确结论并说清错误原因。",
                    "common_mistake": "结论对但错误模型未纠正。",
                }
            )
    for card in due_cards or []:
        add(
            {
                "item_id": f"retr-card-{card.get('id', '')}",
                "type": "card",
                "lesson_id": "",
                "knowledge_point": card.get("knowledge_point", ""),
                "prompt": f"无提示检索（到期卡）：{card.get('front', '')}",
                "rubric": "能独立完整作答，无需提示。",
                "common_mistake": "只能部分回忆或需要提示。",
            }
        )
    for lesson_id in from_lessons:
        add(
            {
                "item_id": f"retr-mainline-{lesson_id}",
                "type": "mainline",
                "lesson_id": lesson_id,
                "knowledge_point": "",
                "prompt": f"无提示复述 {lesson_id} 的主线逻辑链。",
                "rubric": "能按因果顺序复述核心节点。",
                "common_mistake": "只能回忆名词，说不出关系。",
            }
        )
    for entry in state.get("exit_practice", []):
        if entry.get("lesson_id") in lessons and not entry.get("completed"):
            for item in entry.get("items", []):
                if item.get("type") in {"recall", "application"} and not item.get("requires_fill"):
                    add(
                        {
                            "item_id": f"retr-exit-{item.get('item_id', '')}",
                            "type": item.get("type", "recall"),
                            "lesson_id": entry.get("lesson_id", ""),
                            "prompt": f"（退出练习未完成）{item.get('prompt', '')}",
                            "rubric": item.get("rubric", ""),
                            "common_mistake": item.get("common_mistake", ""),
                        }
                    )
    for kp in prerequisites or []:
        add(
            {
                "item_id": f"retr-pre-{kp}",
                "type": "prerequisite",
                "lesson_id": "",
                "knowledge_point": kp,
                "prompt": f"（本节前置）用自己的话解释：{kp}（是什么、适用条件）。",
                "rubric": "能说清定义与适用条件。",
                "common_mistake": "只背名词或说不清适用条件。",
            }
        )
    return items[:limit]


def build_retrieval_plan(
    lesson_id: str,
    from_lessons: list[str],
    state: Mapping[str, Any],
    limit: int = 6,
    due_cards: list[Mapping[str, Any]] | None = None,
    prerequisites: list[str] | None = None,
) -> list[dict[str, Any]]:
    items = select_retrieval_targets(state, from_lessons, limit=limit, due_cards=due_cards, prerequisites=prerequisites)
    if not items:
        items = [
            {
                "item_id": "retr-default-1",
                "type": "recall",
                "lesson_id": from_lessons[0] if from_lessons else "",
                "prompt": "用自己的话复述上一课最核心的一个知识点，并给出一个例子。",
                "rubric": "定义、边界、例子齐备。",
                "common_mistake": "只有定义没有例子或边界。",
            }
        ]
    return items


def _card_front(confusion: Mapping[str, Any], card_type: str) -> str:
    kp = str(confusion.get("knowledge_point") or "本知识点")
    model = str(confusion.get("learner_model") or "常见错误模型")
    table = {
        "辨析卡": f"【辨析卡】与「{kp}」最易混淆的另一个概念是什么？用一句反例区分它们。",
        "错误模型卡": f"【错误模型卡】为什么「{model}」不成立？正确的表述是什么？",
        "方向判断卡": f"【方向判断卡】关于 {kp}，判断方向/正负/大小关系时最容易反在哪一步？给出正确判断。",
        "情境判断卡": f"【情境判断卡】{kp} 在什么条件下成立、什么条件下失效？",
        "因果链卡": f"【因果链卡】复述 {kp} 的因果链，并指出哪一步最容易被误认为理所当然。",
        "反例卡": f"【反例卡】给出 {kp} 的一个反例或边界案例，并说明为什么它不适用。",
        "边界反例卡": f"【边界反例卡】{kp} 的适用条件是什么？给出一个越界会出错的例子。",
        "适用条件卡": f"【适用条件卡】{kp} 在什么条件下才能使用？哪些条件下必须换方法？",
        "深度解释卡": f"【深度解释卡】不用背定义：解释 {kp} 为什么是这样、一个例子、一个反例。",
        "关键步骤卡": f"【关键步骤卡】完成 {kp} 相关流程/推导时，最关键的一步是什么？跳步会错在哪？",
        "陷阱卡": f"【陷阱卡】针对 {kp} 的常见陷阱是什么？如何避免？",
        "无提示检索卡": f"【无提示检索卡】合上笔记回答：{kp} 的核心结论、适用条件和典型例子。",
    }
    return table.get(card_type, f"【复习卡】用自己的话解释 {kp}，并说明它的边界。")


def _card_back(confusion: Mapping[str, Any]) -> str:
    corrective = str(confusion.get("corrective") or "已按课堂纠正重新解释")
    parts = [corrective]
    if confusion.get("parallel_retest"):
        parts.append(f"平行再测：{confusion['parallel_retest']}")
    return "；".join(parts)


def card_drafts_for_confusion(confusion: Mapping[str, Any], chapter: str = "", section: str = "") -> list[dict[str, Any]]:
    """Build 2–4 flashcard drafts for one confusion record."""
    plans = CARD_PLANS.get(str(confusion.get("type")), ["无提示检索卡"])
    drafts: list[dict[str, Any]] = []
    for card_type in plans[:4]:
        drafts.append(
            {
                "id": "",
                "type": "qa",
                "chapter": chapter or "",
                "section": section or "",
                "knowledge_point": str(confusion.get("knowledge_point") or ""),
                "front": _card_front(confusion, card_type),
                "back": _card_back(confusion),
                "confusion_id": str(confusion.get("confusion_id") or ""),
                "lesson_id": str(confusion.get("lesson_id") or ""),
                "source_anchor": str(confusion.get("source_anchor") or ""),
            }
        )
    return drafts


def render_pending_cards(course: str, drafts: list[Mapping[str, Any]]) -> str:
    blocks: list[str] = []
    for draft in drafts:
        meta_lines = [f"chapter: {draft.get('chapter') or ''}", f"knowledge_point: {draft.get('knowledge_point') or ''}"]
        if draft.get("id"):
            meta_lines.insert(0, f"id: {draft['id']}")
        if draft.get("section"):
            meta_lines.append(f"section: {draft['section']}")
        blocks.append("\n".join(["````", *meta_lines, "---", "", "## 正面", str(draft["front"]), "", "## 反面", str(draft["back"]), "````"]))
    header = f"# {course} · 混淆记忆卡待导入\n\n> 来源：课堂混淆证据；导入由卡片流程处理，未导入前不影响课堂事实。\n\n"
    return header + "\n\n".join(blocks) + "\n"


def merge_pending_cards(existing: str, new_blocks: str) -> str:
    new_text = new_blocks.strip()
    if new_text in existing:
        return existing
    return (existing.rstrip() + "\n\n" + new_blocks).strip() + "\n"


def record_retrieval_result(root: Path, course: str, lesson_id: str, item_id: str, result: str, note: str = "") -> dict[str, Any]:
    """Record one retrieval outcome (requires caller --apply); failed may escalate to needs_reteach."""
    if result not in {"passed", "hint_correct", "failed"}:
        raise ValueError(f"非法结果：{result}")
    state = load_review_state(root, course)
    state["retrieval_log"].append({"lesson_id": lesson_id, "item_id": item_id, "result": result, "note": note, "recorded_at": _now()})
    if result == "failed":
        for confusion in state["confusions"]:
            if confusion.get("confusion_id") == item_id.replace("retr-conf-", ""):
                confusion["status"] = "needs_reteach"
    save_review_state(root, course, state)
    return state
