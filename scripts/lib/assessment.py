"""Learning-objective aligned assessment validation (Socratopia v4 contract).

Objective: id, behavior, cognitive_level, source_anchor, expected_evidence.
Item:      id, objective_id, type, difficulty, prompt, answer, rationale, source_anchor.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

OBJECTIVE_REQUIRED = {"id", "behavior", "cognitive_level", "source_anchor", "expected_evidence"}
ITEM_REQUIRED = {
    "id",
    "objective_id",
    "type",
    "difficulty",
    "prompt",
    "answer",
    "rationale",
    "source_anchor",
}
TYPES = {"multiple_choice", "true_false", "fill_blank", "short_answer", "oral_socratic", "performance"}
DIFFICULTIES = {"easy", "medium", "hard"}
_ANCHOR_RE = re.compile(r"[^/\\]+\.(?:md|pdf|docx|pptx)(?:#|:p|\?page=|$)")


def validate_objective(objective: Mapping[str, Any]) -> list[str]:
    """Return names of missing required objective fields."""
    return sorted(key for key in OBJECTIVE_REQUIRED if not str(objective.get(key, "")).strip())


def _anchor_ok(value: Any) -> bool:
    text = str(value or "")
    if not text.strip():
        return False
    # Allow a bare anchor when the objective/source file is recorded elsewhere,
    # but require a file+anchor when a path-like locator is provided.
    return bool(_ANCHOR_RE.search(text)) or text.startswith(("#", "anchor:", "book.md"))


def validate_item(item: Mapping[str, Any], objective_ids: set[str]) -> list[str]:
    """Return quality-gate errors for one assessment item."""
    errors = [f"缺少字段：{key}" for key in sorted(ITEM_REQUIRED) if not str(item.get(key, "")).strip()]
    if str(item.get("objective_id", "")) not in objective_ids:
        errors.append("学习目标不存在")
    if item.get("type") not in TYPES:
        errors.append("题型不受支持")
    if item.get("difficulty") not in DIFFICULTIES:
        errors.append("难度不受支持")
    if not _anchor_ok(item.get("source_anchor")):
        errors.append("来源锚点必须含文件和锚点/页码")
    if item.get("type") == "multiple_choice":
        options = item.get("options", [])
        if not isinstance(options, list) or not 3 <= len(options) <= 5:
            errors.append("选择题选项必须为 3–5 项")
        elif len({str(o).strip() for o in options}) != len(options) or any(
            not str(o).strip() for o in options
        ):
            errors.append("选择题选项必须互异且非空")
        elif sum(str(o) == str(item.get("answer")) for o in options) != 1:
            errors.append("选择题答案必须且只能出现一次")
    return errors


def quality_report(items: Iterable[Mapping[str, Any]], objective_ids: set[str]) -> dict[str, Any]:
    """Summarize validation, coverage, distributions, and duplicate prompts."""
    item_list = list(items)
    coverage = {str(item.get("objective_id", "")) for item in item_list}
    normalized = [re.sub(r"\s+", "", str(item.get("prompt", ""))) for item in item_list]
    duplicates = sorted({p for p, c in Counter(normalized).items() if p and c > 1})
    return {
        "uncovered_objectives": sorted(objective_ids - coverage),
        "type_distribution": dict(Counter(str(i.get("type", "unknown")) for i in item_list)),
        "difficulty_distribution": dict(Counter(str(i.get("difficulty", "unknown")) for i in item_list)),
        "duplicate_prompts": duplicates,
        "errors": {str(i.get("id", "unknown")): validate_item(i, objective_ids) for i in item_list},
    }


def reteach_candidates(items: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Extract failed assessment evidence; never claim mastery automatically."""
    candidates: list[dict[str, str]] = []
    for item in items:
        if (
            item.get("status") == "scored"
            and item.get("result") == "incorrect"
            and item.get("knowledge_point")
        ):
            candidates.append(
                {
                    "objective_id": str(item["objective_id"]),
                    "knowledge_point": str(item["knowledge_point"]),
                    "reason": f"评估题 {item['id']} 作答错误",
                }
            )
    return candidates
