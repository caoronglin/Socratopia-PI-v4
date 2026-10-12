"""Alpha.6 typed PREP section edits preserve unrelated fields and refuse stale writes."""
from __future__ import annotations
import sys
import pytest

if sys.version_info < (3, 15):
    pytest.skip("v5 runtime requires Python 3.15", allow_module_level=True)
pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from tests.test_platform_v5_prep_editor import sample, AUTH, COURSE, route


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
