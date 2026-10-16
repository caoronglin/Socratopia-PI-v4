"""Ontology acceptance: reviewed prerequisites, evidence-anchored diagnosis, isolation."""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import pytest

if sys.version_info < (3, 15):
    pytest.skip("V5 API requires Python 3.15", allow_module_level=True)

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient
from platform_api.app import api
from platform_api.snapshot_sync import snapshot

AUTH = {"Authorization": "Bearer ontology-only-test-token"}
BOOK = ("# 生物学\n## DNA 复制\nDNA复制以亲代DNA为模板合成新的DNA链。\n"
        "## 减数分裂\n减数分裂使染色体数目减半，形成单倍体细胞。\n"
        "## 遗传分离\n减数分裂使等位基因在配子形成过程中分离。\n")
QUOTE = "减数分裂使染色体数目减半，形成单倍体细胞。"
OTHER_QUOTE = "减数分裂使等位基因在配子形成过程中分离。"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "templates", tmp_path / "templates")
    monkeypatch.setenv("SOCRATOPIA_ROOT", str(tmp_path))
    monkeypatch.setenv("SOCRATOPIA_API_TOKEN", AUTH["Authorization"].removeprefix("Bearer "))
    with TestClient(api) as test_client:
        yield test_client


def create(client: TestClient, name: str):
    result = client.post("/api/courses", headers=AUTH, json={"name": name})
    assert result.status_code == 200, result.text
    book = Path(os.environ["SOCRATOPIA_ROOT"]) / "TEXTBOOK" / name / "book.md"
    book.write_text(BOOK, encoding="utf-8")
    return book


def concept_ids(client: TestClient, name: str) -> dict[str, str]:
    r = client.get("/api/courses/" + name + "/graph", headers=AUTH)
    assert r.status_code == 200
    return {x["label"]: x["id"] for x in r.json()["nodes"]}


def question(client: TestClient, course: str, *, stem: str = "减数分裂如何影响染色体数目？"):
    payload = {
        "stem": stem, "kind": "single_select",
        "options": ["减半", "加倍", "不变"], "correct_indices": [0],
        "source_quote": QUOTE, "explanation": "请核对教材中减数分裂的定义。",
    }
    r = client.post("/api/courses/" + course + "/exercises", headers=AUTH, json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def link(client, course: str, question_id: str, concept_id: str, role="practice"):
    return client.post("/api/courses/" + course + "/ontology/questions", headers=AUTH,
                       json={"question_id": question_id, "concept_id": concept_id,
                             "role": role, "source_quote": QUOTE})


def edge(client, course: str, from_id: str, to_id: str, quote=QUOTE):
    return client.post("/api/courses/" + course + "/ontology/prerequisites", headers=AUTH,
                       json={"prerequisite_id": from_id, "concept_id": to_id,
                             "source_quote": quote})


def test_correctly_labels_untested_prerequisites_and_transfer_evidence(client):
    name = "精准学习"
    create(client, name)
    nodes = concept_ids(client, name)
    p = nodes["DNA 复制"]
    c = nodes["减数分裂"]
    t = nodes["遗传分离"]
    assert edge(client, name, p, c).status_code == 200
    assert edge(client, name, c, t, OTHER_QUOTE).status_code == 200
    # Heading hierarchy does not create implied prerequisite edges.
    kg = client.get("/api/courses/" + name + "/ontology", headers=AUTH)
    assert kg.status_code == 200
    data = kg.json()
    assert data["reviewed_prerequisites"] == 2
    assert data["fact_verified"] is False
    assert len([e for e in data["edges"] if e["type"] == "prerequisite_owner_reviewed"]) == 2
    assert edge(client, name, t, p).status_code == 409   # cycle
    assert edge(client, name, p, c).status_code == 409   # duplicate
    assert edge(client, name, p, p).status_code == 409
    assert edge(client, name, p, t, quote="凭空捏造的假引文，肯定找不到。").status_code == 409

    practice = question(client, name)
    transfer = question(client, name, stem="换一个生物情境，单倍体细胞如何形成？")
    assert link(client, name, practice, c).status_code == 200
    assert link(client, name, transfer, c, role="transfer").status_code == 200
    assert link(client, name, practice, c).status_code == 409
    assert client.get("/api/courses/" + name + "/diagnosis").status_code == 401

    r = client.post("/api/courses/" + name + "/exercises/" + practice + "/submit",
                    headers=AUTH, json={"request_id": uuid4().hex, "selected_indices": [1]})
    assert r.status_code == 200 and not r.json()["is_correct"]
    diagnosis = client.get("/api/courses/" + name + "/diagnosis", headers=AUTH)
    assert diagnosis.status_code == 200
    body = diagnosis.json()
    assert body["priority_concepts"] == 1
    assert body["mastery_updated"] is False and body["transfer_verified"] is False
    concept = next(d for d in body["concepts"] if d["concept_id"] == c)
    assert concept["wrong_practice"] == 1
    assert concept["next_action"] == "review_and_check_prerequisites"
    assert [x["label"] for x in concept["prerequisite_checks"]] == ["DNA 复制"]
    assert concept["prerequisite_checks"][0]["meaning"] == "prerequisite_to_check_not_proven_weak"
    assert concept["transfer_questions"] == [transfer]
    assert "correct_indices" not in json.dumps(body)

    r = client.post("/api/courses/" + name + "/exercises/" + transfer + "/submit",
                    headers=AUTH, json={"request_id": uuid4().hex, "selected_indices": [0]})
    assert r.status_code == 200 and r.json()["is_correct"]
    concept2 = next(d for d in client.get(
        "/api/courses/" + name + "/diagnosis", headers=AUTH).json()["concepts"]
        if d["concept_id"] == c)
    assert concept2["transfer_correct"] == 1
    assert concept2["transfer_evidence"] == "observed_correct_attempt_only"

    zipped, _ = snapshot(Path(os.environ["SOCRATOPIA_ROOT"]), name)
    with ZipFile(io.BytesIO(zipped)) as z:
        assert "DATA/runtime/ontology.sqlite3" in z.namelist()
        manifest = json.loads(z.read("manifest.json"))
        import hashlib
        binary = z.read("DATA/runtime/ontology.sqlite3")
        assert hashlib.sha256(binary).hexdigest() == manifest["hashes"][
            "DATA/runtime/ontology.sqlite3"]


def test_course_and_textbook_fences(client):
    book = create(client, "课程甲")
    create(client, "课程乙")
    a = concept_ids(client, "课程甲")
    b = concept_ids(client, "课程乙")
    qid = question(client, "课程甲")
    assert link(client, "课程乙", qid, b["减数分裂"]).status_code == 409
    assert client.get("/api/courses/课程乙/diagnosis", headers=AUTH).json()["concepts"] == []
    assert link(client, "课程甲", qid, a["减数分裂"]).status_code == 200
    book.write_text(BOOK + "\n新版附注。\n", encoding="utf-8")
    got = client.get("/api/courses/课程甲/ontology", headers=AUTH).json()
    assert got["question_links"] == []
    assert client.get("/api/courses/课程甲/diagnosis", headers=AUTH).json()["priority_concepts"] == 0
    assert link(client, "课程甲", qid, a["减数分裂"]).status_code == 409


def test_archived_course_and_symlink_rejected(client, tmp_path: Path):
    create(client, "档案课程")
    nodes = concept_ids(client, "档案课程")
    archived = client.post("/api/courses/档案课程/lifecycle", headers=AUTH, json={"archived": True})
    assert archived.status_code == 200
    assert edge(client, "档案课程", nodes["DNA 复制"], nodes["减数分裂"]).status_code == 409
    assert client.get("/api/courses/档案课程/ontology", headers=AUTH).status_code == 200

    create(client, "不安全课程")
    db = tmp_path / "DATA" / "不安全课程" / "runtime" / "ontology.sqlite3"
    outside = tmp_path / "outside"
    outside.write_text("do not touch", encoding="utf-8")
    db.symlink_to(outside)
    assert client.get("/api/courses/不安全课程/ontology", headers=AUTH).status_code == 409
    assert outside.read_text(encoding="utf-8") == "do not touch"
