"""Bounded source-verified flashcard review API and adversarial isolation tests."""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import pytest

if sys.version_info < (3, 15):
    pytest.skip("v5 backend requires Python 3.15", allow_module_level=True)

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from platform_api.app import api
from platform_api import flashcards, course_graph
from platform_api.snapshot_sync import snapshot

AUTH = {"Authorization": "Bearer test-only-secret-token-00001"}
COURSE = "细胞遗传学"
BOOK = ("# 遗传学\n## 减数分裂\n"
        "减数分裂将染色体数目减半，形成单倍体细胞。\n"
        "## 亲本遗传\n子代从双亲分别继承部分遗传物质。\n")
QUOTE = "减数分裂将染色体数目减半，形成单倍体细胞。"
FRONT = "减数分裂对染色体数目产生什么影响？"
BACK = "形成单倍体细胞，染色体数目减半。"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source = Path(__file__).resolve().parents[1]
    shutil.copytree(source / "templates", tmp_path / "templates")
    monkeypatch.setenv("SOCRATOPIA_ROOT", str(tmp_path))
    monkeypatch.setenv("SOCRATOPIA_API_TOKEN", AUTH["Authorization"].removeprefix("Bearer "))
    with TestClient(api) as test_client:
        yield test_client


def course(client: TestClient, name: str = COURSE) -> Path:
    result = client.post("/api/courses", headers=AUTH, json={"name": name})
    assert result.status_code == 200, result.text
    book = Path(os.environ["SOCRATOPIA_ROOT"]) / "TEXTBOOK" / name / "book.md"
    book.write_text(BOOK, encoding="utf-8")
    return book


def card(client: TestClient, name: str = COURSE, **changes) -> str:
    payload = {"front": FRONT, "back": BACK, "source_quote": QUOTE, **changes}
    response = client.post("/api/courses/" + name + "/flashcards", headers=AUTH, json=payload)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def url(name: str = COURSE) -> str:
    return "/api/courses/" + name + "/flashcards"


def reveal(client: TestClient, card_id: str, name: str = COURSE):
    return client.post(url(name) + "/" + card_id + "/reveal", headers=AUTH)


def rate(client: TestClient, card_id: str, token: str, *,
         rating: str = "good", request_id: str | None = None, name: str = COURSE):
    return client.post(url(name) + "/" + card_id + "/review", headers=AUTH,
                       json={"rating": rating, "reveal_token": token,
                             "request_id": request_id or uuid4().hex})


def test_front_only_then_reveal_and_one_time_idempotent_review(client: TestClient) -> None:
    book = course(client)
    card_id = card(client)
    endpoint = url()
    assert client.get(endpoint).status_code == 401
    response = client.get(endpoint, headers=AUTH)
    assert response.status_code == 200
    overview = response.json()
    assert overview["new_cards"] == 1 and overview["review_due"] == 0
    assert overview["mastery_updated"] is False
    assert overview["items"][0]["front"] == FRONT
    assert "back" not in json.dumps(overview, ensure_ascii=False)
    assert "source_quote" not in json.dumps(overview)
    assert BACK not in json.dumps(overview, ensure_ascii=False)
    assert QUOTE not in json.dumps(overview, ensure_ascii=False)
    assert client.post(endpoint + "/" + card_id + "/reveal").status_code == 401

    bad = rate(client, card_id, uuid4().hex)
    assert bad.status_code == 409
    opened = reveal(client, card_id)
    assert opened.status_code == 200
    body = opened.json()
    assert body["back"] == BACK and body["source_quote"] == QUOTE
    assert body["fact_verified"] is False
    token = body["reveal_token"]

    req_id = uuid4().hex
    accepted = rate(client, card_id, token, request_id=req_id)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["replayed"] is False
    assert accepted.json()["mastery_updated"] is False
    assert accepted.json()["recent_correct_streak"] == 1
    replayed = rate(client, card_id, token, request_id=req_id)
    assert replayed.status_code == 200 and replayed.json()["replayed"] is True
    assert rate(client, card_id, token).status_code == 409
    assert rate(client, card_id, token, rating="again", request_id=req_id).status_code == 409
    current = client.get(endpoint, headers=AUTH).json()
    assert not current["items"] and current["upcoming"][0]["id"] == card_id
    future = flashcards.list_cards(Path(os.environ["SOCRATOPIA_ROOT"]), COURSE,
                                   now=datetime.now(UTC) + timedelta(days=2))
    assert future["review_due"] == 1
    assert future["items"][0]["status"] == "due"
    assert client.get("/api/courses/" + COURSE + "/timer", headers=AUTH).json()["phase"] == "not_started"

    uploaded, metadata = snapshot(Path(os.environ["SOCRATOPIA_ROOT"]), COURSE)
    with ZipFile(io.BytesIO(uploaded)) as archive:
        entries = archive.namelist()
        assert "DATA/runtime/flashcards.sqlite3" in entries
        manifest = json.loads(archive.read("manifest.json"))
        raw = archive.read("DATA/runtime/flashcards.sqlite3")
        import hashlib
        assert manifest["hashes"]["DATA/runtime/flashcards.sqlite3"] == hashlib.sha256(raw).hexdigest()
        assert raw.startswith(b"SQLite format 3")
    assert metadata["sha256"]
    assert book.is_file()


def test_wrong_linked_exercise_promotes_card_and_graph_reference(client: TestClient) -> None:
    course(client)
    graph = course_graph.build(Path(os.environ["SOCRATOPIA_ROOT"]), COURSE)
    concept_id = next(n["id"] for n in graph["nodes"] if n["label"] == "减数分裂")
    exercise = client.post("/api/courses/" + COURSE + "/exercises", headers=AUTH, json={
        "kind": "single_select", "stem": "减数分裂使染色体数目如何变化？",
        "options": ["减半", "翻倍", "不变"], "correct_indices": [0],
        "explanation": "教材原文明确说明形成单倍体细胞。",
        "source_quote": QUOTE, "lesson_id": "lesson_001",
    })
    assert exercise.status_code == 200, exercise.text
    exercise_id = exercise.json()["id"]
    cid = card(client, concept_id=concept_id, exercise_id=exercise_id)
    deck = client.get(url(), headers=AUTH).json()
    assert deck["items"][0]["concept_label"] == "减数分裂"
    assert deck["items"][0]["exercise_id"] == exercise_id
    wrong = client.post("/api/courses/" + COURSE + "/exercises/" + exercise_id + "/submit",
                        headers=AUTH, json={"request_id": uuid4().hex,
                                           "selected_indices": [1]})
    assert wrong.status_code == 200 and wrong.json()["is_correct"] is False
    priority = client.get(url(), headers=AUTH).json()
    assert priority["linked_weaknesses"] == 1
    assert priority["items"][0]["id"] == cid
    assert priority["items"][0]["status"] == "needs_attention"
    token = reveal(client, cid).json()["reveal_token"]
    assert rate(client, cid, token).status_code == 200
    after = client.get(url(), headers=AUTH).json()
    assert after["linked_weaknesses"] == 0
    assert after["review_due"] == 0


def test_reject_fake_quote_duplicate_front_and_cross_course_leaks(client: TestClient) -> None:
    course(client)
    cid = card(client)
    assert client.post(url(), headers=AUTH, json={
        "front": "虚假的问题？", "back": "伪造知识", "source_quote": "不存在的凭空编造教材原文。"
    }).status_code == 409
    assert client.post(url(), headers=AUTH, json={
        "front": FRONT, "back": BACK, "source_quote": QUOTE
    }).status_code == 409
    course(client, "独立章节")
    assert client.get(url("独立章节"), headers=AUTH).json()["items"] == []
    assert reveal(client, cid, "独立章节").status_code == 409
    assert rate(client, cid, uuid4().hex, name="独立章节").status_code == 409
    assert client.post(url("独立章节"), headers=AUTH, json={
        "front": FRONT, "back": BACK, "source_quote": QUOTE,
        "concept_id": "abcabcabcabc"
    }).status_code == 409
    assert client.post(url("独立章节"), headers=AUTH, json={
        "front": FRONT, "back": BACK, "source_quote": QUOTE,
        "exercise_id": cid
    }).status_code == 409


def test_textbook_revision_disables_cards_and_archive_is_read_only(client: TestClient) -> None:
    book = course(client)
    cid = card(client)
    assert reveal(client, cid).status_code == 200
    book.write_text(BOOK + "教材修订版。\n", encoding="utf-8")
    pending = client.get(url(), headers=AUTH).json()
    assert pending["status"] == "needs_cards"
    assert pending["stale_cards_excluded"] == 1
    assert pending["items"] == []
    assert reveal(client, cid).status_code == 409

    book.write_text(BOOK, encoding="utf-8")
    archived = client.post("/api/courses/" + COURSE + "/lifecycle",
                           headers=AUTH, json={"archived": True})
    assert archived.status_code == 200
    assert reveal(client, cid).status_code == 409
    assert client.post(url(), headers=AUTH, json={
        "front": "另一张闪卡问题？", "back": BACK, "source_quote": QUOTE
    }).status_code == 409
    assert client.get(url(), headers=AUTH).status_code == 200


def test_symlinked_flashcard_db_is_rejected_without_touching_target(
    client: TestClient, tmp_path: Path,
) -> None:
    course(client)
    outside = tmp_path / "external.sqlite3"
    outside.write_bytes(b"external secret")
    db = tmp_path / "DATA" / COURSE / "runtime" / "flashcards.sqlite3"
    db.symlink_to(outside)
    assert client.get(url(), headers=AUTH).status_code == 409
    assert outside.read_bytes() == b"external secret"
