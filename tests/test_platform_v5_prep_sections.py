"""Alpha.6 typed PREP section edits preserve unrelated fields and refuse stale writes."""
from __future__ import annotations
import sys
import pytest

if sys.version_info < (3, 15):
    pytest.skip("v5 runtime requires Python 3.15", allow_module_level=True)
pytest.importorskip("fastapi")
pytest.importorskip("httpx")
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from platform_api.app import api

AUTH = {"Authorization": "Bearer alpha6-test-secret-987654"}
COURSE = "遗传学"

@pytest.fixture
def sample(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "templates", tmp_path / "templates")
    monkeypatch.setenv("SOCRATOPIA_ROOT", str(tmp_path))
    monkeypatch.setenv("SOCRATOPIA_API_TOKEN", "alpha6-test-secret-987654")
    client = TestClient(api)
    assert client.post("/api/courses", headers=AUTH, json={"name": COURSE}).status_code == 200
    book = tmp_path / "TEXTBOOK" / COURSE / "book.md"
    book.parent.mkdir(parents=True, exist_ok=True)
    book.write_text("# 第一章 遗传学\n## 第一节 减数分裂\n染色体数目减半。\n", encoding="utf-8")
    result = client.post(f"/api/courses/{COURSE}/prep/chapter/plan",
                         headers=AUTH, json={"chapter": "第一章 遗传学", "apply": True})
    assert result.status_code == 200, result.text
    return client, Path(result.json()["path"])

def route():
    return f"/api/courses/{COURSE}/prep/lesson_001/document"


def test_guided_fields_preserve_unrelated_tables(sample):
    client, path = sample
    doc = client.get(route(), headers=AUTH).json()
    assert "问题链" in doc["sections"] and "预期证据" in doc["sections"]
    assert "教研会决议" in doc["sections"]
    before = path.read_text(encoding="utf-8")
    part = "/api/courses/" + COURSE + "/prep/lesson_001/sections"
    result = client.put(part, headers=AUTH, json={
        "expected_sha256": doc["sha256"],
        "updates": {"问题链": "1. 用染色体数目举例。\n2. 哪一步发生减半？",
                    "预期证据": "- 学生能描述关键差异"},
    })
    assert result.status_code == 200, result.text
    saved = result.json()
    assert saved["status"] == "draft" and saved["ready_granted"] is False
    assert saved["mastery_updated"] is False
    assert "哪一步发生减半" in saved["sections"]["问题链"]
    assert "| O1 | TODO |" in saved["body"]
    assert before.split("## 教学评一致性", 1)[1].split("## 问题链", 1)[0] == saved["body"].split("## 教学评一致性", 1)[1].split("## 问题链", 1)[0]
    assert client.post(f"/api/courses/{COURSE}/timer/start",
                       headers=AUTH, json={"lesson_id": "lesson_001"}).status_code == 409


def test_structured_update_requires_fresh_revision(sample):
    client, path = sample
    doc = client.get(route(), headers=AUTH).json()
    endpoint = f"/api/courses/{COURSE}/prep/lesson_001/sections"
    payload = {"expected_sha256": doc["sha256"], "updates": {"问题链": "1. 新的问题"}}
    assert client.put(endpoint, headers=AUTH, json=payload).status_code == 200
    previous = path.read_bytes()
    assert client.put(endpoint, headers=AUTH, json=payload).status_code == 409
    assert path.read_bytes() == previous
    assert client.put(endpoint, json=payload).status_code == 401


@pytest.mark.parametrize("updates", [
    {"不存在的字段": "内容"}, {"问题链": "## 非法新章节"},
    {"教研会决议": "---\nstatus: ready"}, {"问题链": ""},
    {"问题链": "1. 好的\n## 新的小节\n绕过限制"},
])
def test_structured_update_rejects_unsupported_or_injecting_sections(sample, updates):
    client, path = sample
    sha = client.get(route(), headers=AUTH).json()["sha256"]
    before = path.read_bytes()
    result = client.put(f"/api/courses/{COURSE}/prep/lesson_001/sections",
                        headers=AUTH, json={"expected_sha256": sha, "updates": updates})
    assert result.status_code == 409, result.text
    assert path.read_bytes() == before
