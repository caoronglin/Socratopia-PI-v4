"""Local snapshot guarantees: no cross-course files, no secrets and stable checksums."""
import io
import json
from zipfile import ZipFile
import pytest
from platform_api.snapshot_sync import snapshot, _secure_url, SyncError

def test_snapshot_includes_only_curated_course_files(tmp_path):
    for course in ("甲课", "乙课"):
        (tmp_path / "DATA" / course / "runtime").mkdir(parents=True)
        (tmp_path / "TEXTBOOK" / course).mkdir(parents=True)
        (tmp_path / "TEXTBOOK" / course / "book.md").write_text(
            "# " + course + "\n## 概念\n这是教材。\n", encoding="utf-8")
    (tmp_path / "DATA" / "甲课" / ".env").write_text("secret=private")
    content, info = snapshot(tmp_path, "甲课")
    assert info["sha256"] and info["files"] == 1
    with ZipFile(io.BytesIO(content)) as zf:
        assert sorted(zf.namelist()) == ["TEXTBOOK/book.md", "manifest.json"]
        text = zf.read("TEXTBOOK/book.md").decode()
        assert "甲课" in text and "乙课" not in text
        assert ".env" not in "\n".join(zf.namelist())
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["restore_mode"] == "manual-review-only"

@pytest.mark.parametrize("address", ["http://storage.invalid/path",
    "https://user:secret@example.com", "https://example.com/?token=a"])
def test_remote_endpoint_must_be_secure(address):
    with pytest.raises(SyncError):
        _secure_url(address)
