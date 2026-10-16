"""AgentScope-only backend contracts, scheduling, provider safety and persona roles."""
from __future__ import annotations

import asyncio
import os
import pytest
from platform_api import agentscope_runtime as rt


def test_runtime_reports_safe_config(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "very-secret-token")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com/v1")
    r = rt.runtime_status()
    assert r["backend"] == "agentscope-course" and r["configured"] is True
    assert not any("secret" in str(v) or "example.com" in str(v) for v in r.values())
    assert r["max_agent_iterations"] == 1 and r["tool_access"] == "course-scoped-readonly-opt-in"


@pytest.mark.parametrize("endpoint", [
    "http://example.com/v1", "https://name:pass@example.com/v1",
    "file:///etc/passwd", "https://example.com/v1#fragment", "https://example.com/v1?q=private"
])
def test_model_endpoint_rejected(monkeypatch, endpoint):
    monkeypatch.setenv("OPENAI_BASE_URL", endpoint)
    with pytest.raises(rt.AgentUnavailable):
        rt._base_url()


def test_missing_key_does_not_call_agent(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(rt.AgentUnavailable):
        asyncio.run(rt.ask_agent("遗传学", "解释减数分裂"))


def test_bounded_per_course_loop_and_cancel_cleanup(monkeypatch):
    started = asyncio.Event()
    unblock = asyncio.Event()

    async def fake_execute(scope, prompt, speaker):
        started.set()
        await unblock.wait()
        return "ok"

    monkeypatch.setattr(rt, "_execute", fake_execute)

    async def exercise():
        a = asyncio.create_task(rt.run_course_turn("遗传学", "问题一", speaker="D"))
        await started.wait()
        with pytest.raises(rt.AgentUnavailable, match="already running"):
            await rt.run_course_turn("遗传学", "问题二", speaker="D")
        b = asyncio.create_task(rt.run_course_turn("植物学", "另一个课程", speaker="E"))
        await asyncio.sleep(0)
        assert len(rt._active) >= 1
        a.cancel()
        with pytest.raises(asyncio.CancelledError):
            await a
        unblock.set()
        assert await b == "ok"
        assert "遗传学" not in rt._active
        assert await rt.run_course_turn("遗传学", "再次执行", speaker="D") == "ok"

    asyncio.run(exercise())


def test_persona_distinctness_and_bounded_history(monkeypatch):
    assert len({v[1] for v in rt.PERSONAS.values()}) == 3
    received = {}
    async def fake(course, prompt, *, speaker=None):
        received.update(course=course, prompt=prompt, speaker=speaker)
        return "严格 JSON 引用"
    monkeypatch.setattr(rt, "run_course_turn", fake)
    history = [{"speaker": "D", "text": "先前内容"} for _ in range(12)]
    assert asyncio.run(rt.generate_tutor_turn("生物", "E", "主题", history)) == "严格 JSON 引用"
    assert received["course"] == "生物" and received["speaker"] == "E"
    assert received["prompt"].count("先前内容") == 6
