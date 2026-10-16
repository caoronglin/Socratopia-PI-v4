"""v5 Alpha.2 durable per-course transcript API tests (no real LLM needed)."""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

if sys.version_info < (3, 15):
    pytest.skip("v5 requires Python 3.15", allow_module_level=True)
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient
from platform_api.app import api

TOKEN = "alpha2-test-auth-token-98765"
QUOTE = "减数分裂导致细胞染色体数目减半，最终形成单倍体细胞。"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "templates", tmp_path / "templates")
    monkeypatch.setenv("SOCRATOPIA_ROOT", str(tmp_path))
    monkeypatch.setenv("SOCRATOPIA_API_TOKEN", TOKEN)
    return TestClient(api)


def auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def prepare(client: TestClient, course: str) -> Path:
    created = client.post("/api/courses", json={"name": course}, headers=auth())
    assert created.status_code == 200, created.text
    book = Path(os.environ["SOCRATOPIA_ROOT"]) / "TEXTBOOK" / course / "book.md"
    book.parent.mkdir(parents=True, exist_ok=True)
    book.write_text("# 减数分裂\n" + QUOTE + "\n", encoding="utf-8")
    return book


async def verified_pi(course: str, prompt: str) -> str:
    return json.dumps({"status": "answer", "claims": [
        {"text": "减数分裂导致染色体数目减半。", "source_id": "S1", "quote": QUOTE}
    ]}, ensure_ascii=False)


def transcript(client: TestClient, name: str) -> dict:
    reply = client.get(f"/api/courses/{name}/chat/history", headers=auth())
    assert reply.status_code == 200, reply.text
    return reply.json()


def test_history_is_auth_protected_and_empty_by_default(client: TestClient) -> None:
    prepare(client, "生物课")
    assert client.get("/api/courses/生物课/chat/history").status_code == 401
    assert client.get("/api/courses/生物课/chat/history", headers={
        "Authorization": "Bearer wrong"
    }).status_code == 401
    assert client.get("/api/courses/不存在/chat/history", headers=auth()).status_code == 404
    assert transcript(client, "生物课") == {
        "course": "生物课", "exchanges": 0, "limit": 50, "turns": []
    }


def test_verified_chat_survives_reload_without_updating_mastery(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    book = prepare(client, "遗传学")
    monkeypatch.setattr("platform_api.app.ask_agent", verified_pi)
    progress = Path(os.environ["SOCRATOPIA_ROOT"]) / "DATA" / "遗传学" / "PROGRESS.md"
    original = progress.read_bytes()
    for question in ("什么是减数分裂？", "染色体数目如何变化？"):
        reply = client.post("/api/courses/遗传学/chat", json={"message": question}, headers=auth())
        assert reply.status_code == 200, reply.text
        assert reply.json()["grounding"] == "citation_checked"
    # Re-instantiating TestClient exercises persistent disk storage, not UI memory.
    restored = transcript(TestClient(api), "遗传学")
    assert restored["exchanges"] == 2 and len(restored["turns"]) == 4
    assert restored["turns"][0]["speaker"] == "student"
    assert restored["turns"][0]["text"] == "什么是减数分裂？"
    assert restored["turns"][1]["speaker"] == "course_agent"
    assert restored["turns"][1]["citations"][0]["quote"] == QUOTE
    assert restored["turns"][1]["source_current"] is True
    assert restored["turns"][1]["fact_verified"] is False
    assert restored["turns"][1]["mastery_updated"] is False
    assert progress.read_bytes() == original

    book.write_text("# 减数分裂\n新版教材内容，旧引文不再出现。\n", encoding="utf-8")
    stale = transcript(client, "遗传学")
    assert stale["turns"][1]["source_current"] is False
    assert stale["turns"][1]["citations"][0]["quote"] == QUOTE
    assert stale["turns"][1]["fact_verified"] is False
    assert progress.read_bytes() == original


def test_failed_generation_or_invalid_source_does_not_add_history(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare(client, "细胞学")
    async def invalid(*args):
        return '{"status":"answer","claims":[{"text":"没有引文","source_id":"S404","quote":"完全杜撰的假引文证据。"}]}'
    monkeypatch.setattr("platform_api.app.ask_agent", invalid)
    denied = client.post("/api/courses/细胞学/chat", headers=auth(), json={"message": "减数分裂"})
    assert denied.status_code == 422
    assert transcript(client, "细胞学")["turns"] == []


def test_abstention_is_explicitly_unverified_and_persistent(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare(client, "遗传讨论")
    async def abstain(*args):
        return '{"status":"abstain","reason":"no evidence"}'
    monkeypatch.setattr("platform_api.app.ask_agent", abstain)
    result = client.post("/api/courses/遗传讨论/chat", json={"message": "减数分裂"}, headers=auth())
    assert result.status_code == 200
    turns = transcript(client, "遗传讨论")["turns"]
    assert turns[1]["grounding"] == "insufficient_evidence"
    assert turns[1]["citations"] == []
    assert turns[1]["mastery_updated"] is False


def test_courses_are_isolated_and_database_symlink_refused(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name in ("甲课程", "乙课程"):
        prepare(client, name)
    monkeypatch.setattr("platform_api.app.ask_agent", verified_pi)
    response = client.post("/api/courses/甲课程/chat", json={"message": "减数分裂"}, headers=auth())
    assert response.status_code == 200
    assert transcript(client, "乙课程")["turns"] == []
    database = Path(os.environ["SOCRATOPIA_ROOT"]) / "DATA" / "乙课程" / "runtime" / "chat_history.sqlite3"
    database.unlink()
    outside = tmp_path / "not-a-course.sqlite3"
    outside.write_text("do-not-touch", encoding="utf-8")
    try:
        database.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Filesystem does not allow symlinks")
    blocked = client.get("/api/courses/乙课程/chat/history", headers=auth())
    assert blocked.status_code == 409
    assert outside.read_text(encoding="utf-8") == "do-not-touch"
