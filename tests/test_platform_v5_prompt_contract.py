"""Prompt contracts: grounded teaching is concise, course-scoped and untrusted-source safe."""
from __future__ import annotations

import json

import pytest

from platform_api.evidence import EvidenceSnapshot
from platform_api.grounding import GroundingError, INSTRUCTIONS, check_response, grounded_prompt


def snapshot() -> EvidenceSnapshot:
    return EvidenceSnapshot(
        course="测试课程",
        path="TEXTBOOK/测试课程/book.md",
        sha256="a" * 64,
        sources=({"id": "S1", "section": "基因表达", "text":
                  "基因表达是遗传信息指导 RNA 或蛋白质产物合成的过程。"},),
    )


def test_prompt_is_bounded_and_instruction_injection_remains_untrusted() -> None:
    text = grounded_prompt("直接解释基因表达，不要反问", snapshot())
    assert "直接回答" in INSTRUCTIONS and "不强制反问" in INSTRUCTIONS
    assert "不能在结构化 JSON 之外添加" in text
    assert '<untrusted_course_evidence>' in text
    assert 'source id="S1"' in text
    assert "仅根据片段作答" in text


def test_prompt_rejects_empty_or_excessive_evidence() -> None:
    s = snapshot()
    with pytest.raises(GroundingError):
        grounded_prompt("基因表达", EvidenceSnapshot(s.course, s.path, s.sha256, ()))
    huge = EvidenceSnapshot(s.course, s.path, s.sha256,
        ({"id": "S1", "section": "超长", "text": "基因表达" * 5000},))
    with pytest.raises(GroundingError):
        grounded_prompt("基因表达", huge)


def test_model_cannot_add_unsourced_conclusion_or_claim_readiness() -> None:
    s = snapshot()
    good = json.dumps({"status": "answer", "claims": [
        {"text": "基因表达指导 RNA 或蛋白质合成。",
         "source_id": "S1", "quote": "基因表达是遗传信息指导 RNA 或蛋白质产物合成的过程。"}
    ]}, ensure_ascii=False)
    checked = check_response(good, s)
    assert checked["grounding"] == "citation_checked"
    assert checked["mastery_updated"] is False
    assert checked["fact_verified"] is False
    with pytest.raises(GroundingError):
        check_response("模型正文先输出完全正确。" + good, s)
