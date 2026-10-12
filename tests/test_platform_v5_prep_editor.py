"""Alpha.5: local draft PREP editor is isolated, CAS-safe and never grants ready."""
from __future__ import annotations

import hashlib
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

AUTH = {"Authorization": "Bearer alpha5-tests-secret-6789"}
COURSE = "遗传学"


@pytest.fixture
def sample(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Path]:
    repo = Path(__file__).resolve().parents[1]
    shutil.copytree(repo / "templates", tmp_path / "templates")
    monkeypatch.setenv("SOCRATOPIA_ROOT", str(tmp_path))
    monkeypatch.setenv("SOCRATOPIA_API_TOKEN", "alpha5-tests-secret-6789")
    client = TestClient(api)
    assert client.post("/api/courses", headers=AUTH, json={"name": COURSE}).status_code == 200
    book = tmp_path / "TEXTBOOK" / COURSE / "book.md"
    book.parent.mkdir(parents=True, exist_ok=True)
    book.write_text("# 第一章 遗传学\n## 第一节 减数分裂\n染色体数目减半。\n", encoding="utf-8")
    result = client.post(f"/api/courses/{COURSE}/prep/chapter/plan", headers=AUTH,
                         json={"chapter": "第一章 遗传学", "apply": True})
    assert result.status_code == 200, result.text
    path = Path(result.json()["path"])
    return client, path


def route() -> str:
    return f"/api/courses/{COURSE}/prep/lesson_001/document"


def test_edit_body_keeps_locked_metadata_and_progress(sample: tuple[TestClient, Path], tmp_path: Path) -> None:
    client, path = sample
    progress = tmp_path / "DATA" / COURSE / "PROGRESS.md"
    original_progress = progress.read_bytes()
    book = tmp_path / "TEXTBOOK" / COURSE / "book.md"
    original_book = book.read_bytes()
    before = client.get(route(), headers=AUTH)
    assert before.status_code == 200, before.text
    data = before.json()
    assert data["editable"] is True and data["status"] == "draft"
    assert len(data["sha256"]) == 64
    assert data["body"].startswith("# lesson_001")
    assert client.get(route()).status_code == 401
    original_head = path.read_bytes().split(b"\n---", 1)[0]

    modified = data["body"].replace("TODO", "待人工讨论", 1)
    saved = client.put(route(), headers=AUTH, json={
        "body": modified, "expected_sha256": data["sha256"]
    })
    assert saved.status_code == 200, saved.text
    result = saved.json()
    assert result["body"].rstrip("\n") == modified.rstrip("\n")
    assert result["status"] == "draft" and result["ready_granted"] is False
    assert result["mastery_updated"] is False
    assert result["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert path.read_bytes().split(b"\n---", 1)[0] == original_head
    assert progress.read_bytes() == original_progress
    assert book.read_bytes() == original_book
    assert client.post(f"/api/courses/{COURSE}/timer/start", headers=AUTH,
                       json={"lesson_id": "lesson_001"}).status_code == 409


def test_stale_revision_rejected_without_overwriting_draft(sample: tuple[TestClient, Path]) -> None:
    client, path = sample
    doc = client.get(route(), headers=AUTH).json()
    data = {"body": doc["body"] + "\n追加一条人工备课笔记。\n",
            "expected_sha256": doc["sha256"]}
    assert client.put(route(), headers=AUTH, json=data).status_code == 200
    actual = path.read_bytes()
    denied = client.put(route(), headers=AUTH, json=data)
    assert denied.status_code == 409
    assert path.read_bytes() == actual
    assert "其他窗口" in denied.json()["detail"]
    assert client.put(route(), headers=AUTH,
                      json={"body": "", "expected_sha256": doc["sha256"]}).status_code == 422
    assert client.put(route(), headers=AUTH,
                      json={"body": "hello", "expected_sha256": "invalid"}).status_code == 422


def test_ready_and_legacy_documents_read_only(sample: tuple[TestClient, Path]) -> None:
    client, path = sample
    original = path.read_text(encoding="utf-8")
    path.write_text(original.replace("status: draft", "status: ready"), encoding="utf-8")
    doc = client.get(route(), headers=AUTH)
    assert doc.status_code == 200
    assert doc.json()["editable"] is False
    assert client.put(route(), headers=AUTH, json={
        "body": doc.json()["body"], "expected_sha256": doc.json()["sha256"]
    }).status_code == 409
    assert "status: ready" in path.read_text(encoding="utf-8")

    path.write_text("# Legacy teaching notes\n", encoding="utf-8")
    assert client.get(route(), headers=AUTH).status_code == 409


def test_symlinks_and_mismatched_course_rejected(sample: tuple[TestClient, Path], tmp_path: Path) -> None:
    client, path = sample
    foreign = tmp_path / "foreign.md"
    foreign.write_text("untouched", encoding="utf-8")
    path.unlink()
    try:
        path.symlink_to(foreign)
    except (OSError, NotImplementedError):
        pytest.skip("File symlink unavailable")
    assert client.get(route(), headers=AUTH).status_code == 409
    assert foreign.read_text(encoding="utf-8") == "untouched"
    assert client.get("/api/courses/other-course/prep/lesson_001/document", headers=AUTH).status_code == 404
    assert client.get(f"/api/courses/{COURSE}/prep/lesson_bad/document", headers=AUTH).status_code == 409


def test_existing_lock_refused_and_cleaned_after_success(sample: tuple[TestClient, Path]) -> None:
    client, path = sample
    doc = client.get(route(), headers=AUTH).json()
    lock = path.with_name("." + path.name + ".lock")
    lock.write_text("another editor", encoding="utf-8")
    before = path.read_bytes()
    assert client.put(route(), headers=AUTH, json={
        "body": doc["body"] + "\n新增记录", "expected_sha256": doc["sha256"]
    }).status_code == 409
    assert lock.read_text(encoding="utf-8") == "another editor"
    assert before == path.read_bytes()
    lock.unlink()
    assert client.put(route(), headers=AUTH, json={
        "body": doc["body"] + "\n新增记录", "expected_sha256": doc["sha256"]
    }).status_code == 200
    assert not lock.exists()
