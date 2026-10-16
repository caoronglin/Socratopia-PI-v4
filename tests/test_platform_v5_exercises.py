"""Authenticated classroom quiz integration and adversarial acceptance tests (Python 3.15)."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from uuid import uuid4

import pytest

if sys.version_info < (3, 15):
    pytest.skip("v5 backend requires Python 3.15", allow_module_level=True)

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from platform_api.app import api

AUTH = {"Authorization": "Bearer test-only-secret-token-00001"}
BOOK = "# 遗传学\n减数分裂将染色体数目减半，形成单倍体细胞。\n"
QUOTE = "减数分裂将染色体数目减半，形成单倍体细胞。"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source = Path(__file__).resolve().parents[1]
    shutil.copytree(source / "templates", tmp_path / "templates")
    monkeypatch.setenv("SOCRATOPIA_ROOT", str(tmp_path))
    monkeypatch.setenv("SOCRATOPIA_API_TOKEN", AUTH["Authorization"].removeprefix("Bearer "))
    with TestClient(api) as test_client:
        yield test_client


def create_course(client: TestClient, name: str = "遗传学") -> Path:
    result = client.post("/api/courses", headers=AUTH, json={"name": name})
    assert result.status_code == 200, result.text
    path = Path(os.environ["SOCRATOPIA_ROOT"]) / "TEXTBOOK" / name / "book.md"
    return path


def question(**overrides) -> dict:
    default = {
        "kind": "single_select",
        "stem": "减数分裂产生的子细胞染色体数目与母细胞相比如何变化？",
        "options": ["减半", "加倍", "保持不变", "随机变化"],
        "correct_indices": [0],
        "explanation": "减数分裂使染色体数目从二倍体减少到单倍体。",
        "source_quote": QUOTE,
        "lesson_id": "lesson_001",
    }
    return {**default, **overrides}


def create_exercise(client: TestClient, course: str = "遗传学", **overrides) -> str:
    response = client.post("/api/courses/" + course + "/exercises", headers=AUTH, json=question(**overrides))
    assert response.status_code == 200, response.text
    return response.json()["id"]


def submit(client: TestClient, qid: str, indices: list[int], *,
           course: str = "遗传学", request_id: str | None = None):
    return client.post(
        "/api/courses/" + course + "/exercises/" + qid + "/submit",
        headers=AUTH,
        json={"selected_indices": indices, "request_id": request_id or uuid4().hex},
    )


def test_manual_source_bound_question_and_grading(client: TestClient) -> None:
    book = create_course(client)
    missing = client.post("/api/courses/遗传学/exercises", headers=AUTH, json=question())
    assert missing.status_code == 409, missing.text
    book.write_text(BOOK, encoding="utf-8")
    qid = create_exercise(client)
    listed = client.get("/api/courses/遗传学/exercises", headers=AUTH)
    assert listed.status_code == 200
    item = listed.json()["questions"][0]
    assert item["id"] == qid and item["source_current"]
    assert "correct_indices" not in item and "explanation" not in item
    assert "source_quote" not in item

    wrong = submit(client, qid, [1]).json()
    assert wrong["is_correct"] is False
    assert wrong["correct_indices"] == [0]
    assert wrong["source_quote"] == QUOTE and wrong["mastery_updated"] is False
    right = submit(client, qid, [0]).json()
    assert right["is_correct"] is True and right["mastery_updated"] is False

    stats = client.get("/api/courses/遗传学/exercise-summary", headers=AUTH).json()
    assert stats["attempts"] == 2 and stats["correct"] == 1 and stats["accuracy"] == 50.0
    assert stats["question_count"] == 1 and stats["mastery_updated"] is False
    # No quiz can forge a 45-minute completed lesson or progress certification.
    timer = client.get("/api/courses/遗传学/timer", headers=AUTH).json()
    assert timer["phase"] == "not_started" and timer["remaining_seconds"] == 2700
    assert (Path(os.environ["SOCRATOPIA_ROOT"]) / "DATA" / "遗传学" / "PROGRESS.md").is_file()


def test_submission_idempotent_and_conflicts(client: TestClient) -> None:
    create_course(client).write_text(BOOK, encoding="utf-8")
    qid = create_exercise(client)
    request_id = uuid4().hex
    first = submit(client, qid, [0], request_id=request_id)
    second = submit(client, qid, [0], request_id=request_id)
    assert first.status_code == 200 and first.json()["replayed"] is False
    assert second.status_code == 200 and second.json()["replayed"] is True
    assert submit(client, qid, [1], request_id=request_id).status_code == 409
    summary = client.get("/api/courses/遗传学/exercise-summary", headers=AUTH).json()
    assert summary["attempts"] == 1 and summary["correct"] == 1


def test_book_version_stale_question_fails_closed(client: TestClient) -> None:
    book = create_course(client)
    book.write_text(BOOK, encoding="utf-8")
    qid = create_exercise(client)
    book.write_text(BOOK + "此处修订了教材。\n", encoding="utf-8")
    assert client.get("/api/courses/遗传学/exercises", headers=AUTH).json()["questions"][0]["source_current"] is False
    assert submit(client, qid, [0]).status_code == 409
    assert client.get("/api/courses/遗传学/exercise-summary", headers=AUTH).json()["attempts"] == 0


def test_multiselect_exact_set_and_lesson_gates(client: TestClient) -> None:
    create_course(client).write_text(BOOK, encoding="utf-8")
    qid = create_exercise(
        client, kind="multi_select",
        stem="下列哪项符合单倍体或减数分裂的特征？（多选）",
        options=["形成单倍体", "染色体数目减半", "染色体数目必定加倍", "一定产生完全相同的细胞"],
        correct_indices=[0, 1],
        explanation="教材指出减数分裂让染色体数目减半，形成单倍体细胞。",
    )
    assert submit(client, qid, [1, 0]).json()["is_correct"] is True
    assert submit(client, qid, [0]).json()["is_correct"] is False
    assert submit(client, qid, [0, 1, 2]).json()["is_correct"] is False


@pytest.mark.parametrize("changes", [
    {"source_quote": "不是教材中的凭空捏造的引用。"},
    {"correct_indices": [0, 0]},
    {"correct_indices": [7]},
    {"kind": "single_select", "correct_indices": [0, 1]},
    {"kind": "multi_select", "correct_indices": [0]},
    {"options": ["重复", "重复", "非重复", "其他"]},
    {"lesson_id": "lesson_../../1"},
])
def test_invalid_or_hallucinated_quiz_key_rejected(client: TestClient, changes: dict) -> None:
    create_course(client).write_text(BOOK, encoding="utf-8")
    result = client.post("/api/courses/遗传学/exercises", headers=AUTH, json=question(**changes))
    assert result.status_code in {409, 422}


def test_course_isolation_and_no_source_key_leak(client: TestClient) -> None:
    create_course(client).write_text(BOOK, encoding="utf-8")
    qid = create_exercise(client)
    second = create_course(client, "生物学")
    second.write_text(BOOK, encoding="utf-8")
    assert client.get("/api/courses/生物学/exercises", headers=AUTH).json()["questions"] == []
    assert submit(client, qid, [0], course="生物学").status_code == 409
    assert client.get("/api/courses/生物学/exercise-summary", headers=AUTH).json()["attempts"] == 0
    assert client.get("/api/courses/生物学/exercises", headers={}).status_code == 401


def test_attempt_validation_before_score(client: TestClient) -> None:
    create_course(client).write_text(BOOK, encoding="utf-8")
    qid = create_exercise(client)
    assert submit(client, qid, [-1]).status_code == 409
    assert submit(client, qid, [0, 0]).status_code == 409
    assert submit(client, qid, [9]).status_code == 409
    assert client.get("/api/courses/遗传学/exercise-summary", headers=AUTH).json()["attempts"] == 0


def test_database_symlink_rejected(client: TestClient, tmp_path: Path) -> None:
    create_course(client).write_text(BOOK, encoding="utf-8")
    target = tmp_path / "target.sqlite"
    target.write_bytes(b"not a database")
    runtime = tmp_path / "DATA" / "遗传学" / "runtime"
    db = runtime / "interactive_exercises.sqlite3"
    db.symlink_to(target)
    assert client.get("/api/courses/遗传学/exercises", headers=AUTH).status_code == 409
    assert target.read_bytes() == b"not a database"



def test_web_textbook_onboarding_and_catalog(client: TestClient) -> None:
    path = create_course(client)
    missing = client.get("/api/courses/遗传学/book", headers=AUTH)
    assert missing.status_code == 200 and missing.json()["can_import"] is True

    # This is the same path a browser paste/file-selection import exercises.
    content = "# 遗传学\n## 第一节 减数分裂\n减数分裂将染色体数目减半，形成单倍体细胞。\n"
    first = client.post("/api/courses/遗传学/book", headers=AUTH, json={"content": content})
    assert first.status_code == 200, first.text
    assert first.json()["ready_for_formal_lesson"] is False
    assert path.read_text(encoding="utf-8") == content
    catalog = client.get("/api/courses/遗传学/book", headers=AUTH).json()
    assert catalog["available"] is True and catalog["can_import"] is False
    assert [part["title"] for part in catalog["chapters"]] == ["遗传学", "第一节 减数分裂"]
    assert len(catalog["sha256"]) == 64
    qid = create_exercise(client)
    assert submit(client, qid, [0]).json()["is_correct"] is True

    previous = path.read_bytes()
    again = client.post("/api/courses/遗传学/book", headers=AUTH,
                        json={"content": "# 伪造新教材\n" + QUOTE + "\n"})
    assert again.status_code == 409
    assert path.read_bytes() == previous


def test_book_upload_course_isolation_and_bad_inputs(client: TestClient) -> None:
    a = create_course(client)
    b = create_course(client, "独立课程")
    book = "# 第一章\n" + QUOTE + "\n"
    assert client.post("/api/courses/遗传学/book", headers=AUTH,
                       json={"content": book}).status_code == 200
    assert client.get("/api/courses/独立课程/book", headers=AUTH).json()["available"] is False
    assert not b.exists()
    assert client.post("/api/courses/独立课程/book", json={"content": book}).status_code == 401
    assert client.post("/api/courses/独立课程/book", headers=AUTH,
                       json={"content": "x" * 2000001}).status_code == 422
    assert client.post("/api/courses/独立课程/book", headers=AUTH,
                       json={"content": "# 小册子\n" + "x" * 35 + "\x00"}).status_code == 409
    assert a.read_text(encoding="utf-8") == book


def test_textbook_symlink_never_overwritten(client: TestClient, tmp_path: Path) -> None:
    book = create_course(client)
    outside = tmp_path / "outside.md"
    outside.write_text("# 外部教材\n" + QUOTE + "\n", encoding="utf-8")
    book.symlink_to(outside)
    result = client.post("/api/courses/遗传学/book", headers=AUTH,
                         json={"content": "# 教材\n" + QUOTE + "\n"})
    assert result.status_code == 409
    assert outside.read_text(encoding="utf-8").startswith("# 外部教材")


def test_study_plan_retrieval_and_spaced_review_are_not_mastery(
    client: TestClient,
) -> None:
    from datetime import UTC, datetime, timedelta
    from platform_api.study_plan import plan

    create_course(client).write_text(BOOK, encoding="utf-8")
    question_id = create_exercise(client)
    url = "/api/courses/遗传学/study-plan"

    assert client.get(url).status_code == 401
    first = client.get(url, headers=AUTH)
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "ready"
    assert body["new_questions"] == 1 and body["review_due"] == 0
    assert body["suggested_minutes"] == 3
    assert body["items"][0]["exercise_id"] == question_id
    assert "correct_indices" not in str(body)
    assert "explanation" not in str(body)
    assert body["mastery_updated"] is False

    assert submit(client, question_id, [1]).status_code == 200
    wrong = client.get(url, headers=AUTH).json()
    assert wrong["review_due"] == 1
    assert wrong["items"][0]["status"] == "retry"

    assert submit(client, question_id, [0]).status_code == 200
    correct = client.get(url, headers=AUTH).json()
    assert correct["review_due"] == 0
    assert correct["items"] == []
    assert correct["upcoming"][0]["status"] == "upcoming"
    tomorrow = plan(
        Path(os.environ["SOCRATOPIA_ROOT"]), "遗传学",
        now=datetime.now(UTC) + timedelta(days=2),
    )
    assert tomorrow["review_due"] == 1
    assert tomorrow["items"][0]["status"] == "due"
    assert tomorrow["mastery_updated"] is False

    assert client.get("/api/courses/遗传学/timer", headers=AUTH).json()["phase"] == "not_started"


def test_study_plan_isolates_courses_and_rejects_stale_book(
    client: TestClient,
) -> None:
    first = create_course(client)
    first.write_text(BOOK, encoding="utf-8")
    qid = create_exercise(client)
    second = create_course(client, "独立遗传学")
    second.write_text(BOOK, encoding="utf-8")

    assert client.get("/api/courses/独立遗传学/study-plan", headers=AUTH).json()["items"] == []
    assert submit(client, qid, [1]).json()["is_correct"] is False
    assert client.get("/api/courses/独立遗传学/study-plan", headers=AUTH).json()["review_due"] == 0

    first.write_text(BOOK + "教材新版说明。", encoding="utf-8")
    stale = client.get("/api/courses/遗传学/study-plan", headers=AUTH).json()
    assert stale["status"] == "needs_questions"
    assert stale["items"] == []
    assert stale["stale_questions_excluded"] == 1
    assert stale["mastery_updated"] is False
