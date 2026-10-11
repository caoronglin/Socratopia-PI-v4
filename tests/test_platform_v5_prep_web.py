"""v5.0.0-alpha.3 Web PREP API: dry run -> draft, no automatic readiness."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
import pytest

if sys.version_info < (3, 15):
    pytest.skip("v5 API requires Python 3.15", allow_module_level=True)
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from platform_api.app import api

AUTH = {"Authorization": "Bearer alpha3-test-only-token-9876"}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    source = Path(__file__).resolve().parents[1] / "templates"
    shutil.copytree(source, tmp_path / "templates")
    monkeypatch.setenv("SOCRATOPIA_ROOT", str(tmp_path))
    monkeypatch.setenv("SOCRATOPIA_API_TOKEN", "alpha3-test-only-token-9876")
    assert TestClient(api).post("/api/courses", headers=AUTH,
         json={"name": "遗传学"}).status_code == 200
    book = tmp_path / "TEXTBOOK" / "遗传学" / "book.md"
    book.parent.mkdir(parents=True, exist_ok=True)
    book.write_text("# 第一章 遗传学\n## 第一节 减数分裂\nDNA 复制后发生两次分裂。\n", encoding="utf-8")
    return TestClient(api)


def test_prep_dry_run_then_create_never_auto_ready(client: TestClient) -> None:
    base = "/api/courses/遗传学/prep"
    status = client.get(base, headers=AUTH)
    assert status.status_code == 200
    assert status.json()["lessons"] == {}
    assert client.get(base).status_code == 401
    draft = client.post(base + "/chapter/plan", headers=AUTH,
        json={"chapter": "第一章 遗传学"}).json()
    assert draft["dry_run"] is True and draft["draft"] is True
    assert "减数分裂" in draft["preview"]
    assert draft["ready_granted"] is False and draft["mastery_updated"] is False
    assert not Path(draft["path"]).exists()
    created = client.post(base + "/chapter/plan", headers=AUTH,
        json={"chapter": "第一章 遗传学", "apply": True})
    assert created.status_code == 200, created.text
    data = created.json()
    assert data["ready_granted"] is False and data["mastery_updated"] is False
    assert Path(data["path"]).is_file()
    lesson = data["lesson_id"]
    assert client.get(base, headers=AUTH).json()["lessons"][lesson] == "draft"
    checked = client.get(base + "/" + lesson, headers=AUTH).json()
    assert checked["status"] == "draft" and checked["ready_for_class"] is False
    repeated = client.post(base + "/chapter/plan", headers=AUTH,
        json={"chapter": "第一章 遗传学", "apply": True})
    assert repeated.status_code == 200
    assert repeated.json()["exists"] is True
    assert repeated.json()["lesson_id"] == lesson
    assert len(client.get(base, headers=AUTH).json()["lessons"]) == 1
    timer = client.post("/api/courses/遗传学/timer/start", headers=AUTH,
        json={"lesson_id": lesson})
    assert timer.status_code == 409


def test_prep_rejects_invalid_chapter_and_is_course_scoped(client: TestClient) -> None:
    base = "/api/courses/遗传学/prep"
    assert client.post(base + "/chapter/plan", headers=AUTH,
        json={"chapter": "不存在的章节"}).status_code == 409
    assert client.get("/api/courses/不存在/prep", headers=AUTH).status_code == 404
    assert client.get(base + "/../../etc/passwd", headers=AUTH).status_code != 200
    assert client.get(base + "/lesson_abc", headers=AUTH).status_code == 409
