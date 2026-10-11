"""Local API integration smoke gates for v5; legacy tests run separately."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

if sys.version_info < (3, 15):
    pytest.skip("v5 API requires Python 3.15", allow_module_level=True)

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient
from platform_api.app import api
from platform_api.pi_gateway import PiUnavailable, ask_pi


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "templates", tmp_path / "templates")
    monkeypatch.setenv("SOCRATOPIA_ROOT", str(tmp_path))
    monkeypatch.setenv("SOCRATOPIA_API_TOKEN", "test-only-secret-token-00001")
    return TestClient(api)


def auth() -> dict:
    return {"Authorization": "Bearer test-only-secret-token-00001"}


def test_auth_fails_closed(client: TestClient) -> None:
    assert client.get("/api/courses").status_code == 401
    assert client.get("/api/courses", headers={"Authorization": "Bearer incorrect"}).status_code == 401
    assert client.get("/api/health").status_code == 200


def test_create_and_read_course_without_mastery(client: TestClient) -> None:
    created = client.post("/api/courses", json={"name": "遗传学", "tutor": "F"}, headers=auth())
    assert created.status_code == 200, created.text
    assert created.json()["ready_for_class"] is False
    assert "遗传学" in client.get("/api/courses", headers=auth()).json()["courses"]
    state = client.get("/api/courses/遗传学/state", headers=auth()).json()
    assert state["phase"] == "setup"
    assert state["blockers"]
    timer = client.get("/api/courses/遗传学/timer", headers=auth()).json()
    assert timer["remaining_seconds"] == 2700
    # A newly initialized course cannot claim a completed lesson.
    start = client.post("/api/courses/遗传学/timer/start",
                        headers=auth(), json={"lesson_id": "lesson_001"})
    assert start.status_code == 409
    assert client.post("/api/courses", json={"name": "../escape"}, headers=auth()).status_code == 409


def test_chat_preserves_progress(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    client.post("/api/courses", json={"name": "生物信息学"}, headers=auth())

    async def fake_pi(course: str, message: str) -> str:
        assert course == "生物信息学"
        return "这是对 " + message + " 的教学解释"

    monkeypatch.setattr("platform_api.app.ask_pi", fake_pi)
    reply = client.post("/api/courses/生物信息学/chat", headers=auth(), json={"message": "什么是 RNA-seq?"})
    assert reply.status_code == 200, reply.text
    assert reply.json()["mastery_updated"] is False
    timer = client.get("/api/courses/生物信息学/timer", headers=auth()).json()
    assert timer["phase"] == "not_started"


def test_real_group_state_machine_with_stubbed_llm(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    client.post("/api/courses", json={"name": "学习小组课程"}, headers=auth())
    config = client.post("/api/courses/学习小组课程/group/configure",
                         headers=auth(), json={"members": ["D", "E"], "lead": "D"})
    assert config.status_code == 200, config.text
    started = client.post("/api/courses/学习小组课程/group/start",
                          headers=auth(), json={"topic": "基因表达", "rounds": 2})
    assert started.json()["next_speaker"] == "D"

    async def fake_tutor(speaker: str, topic: str, prior: list[dict]) -> str:
        assert topic == "基因表达"
        return "导师 " + speaker + " 的解释"

    monkeypatch.setattr("platform_api.app.generate_tutor_turn", fake_tutor)
    first = client.post("/api/courses/学习小组课程/group/next", headers=auth())
    assert first.status_code == 200, first.text
    second = client.post("/api/courses/学习小组课程/group/next", headers=auth())
    assert second.json()["requires_user_turn"] is True
    blocked = client.post("/api/courses/学习小组课程/group/next", headers=auth())
    assert blocked.status_code == 409
    continued = client.post("/api/courses/学习小组课程/group/continue", headers=auth(), json={})
    assert continued.json()["next_speaker"] == "D"


def test_gateway_rejects_non_loopback_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    monkeypatch.setenv("SOCRATOPIA_API_TOKEN", "test-only-secret-token-00001")
    for url in ["http://127.0.0.1:8787@evil.example", "https://127.0.0.1:8787", "http://localhost:8787/move"]:
        monkeypatch.setenv("SOCRATOPIA_PI_URL", url)
        with pytest.raises(PiUnavailable):
            asyncio.run(ask_pi("课程", "你好"))
