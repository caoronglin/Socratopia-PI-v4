"""Opt-in, immutable WebDAV/S3 course snapshot export, never auto-restore.

Secrets are configured only in the local server's environment. Snapshots can
contain private course notes and chat; require trusted remote storage. This is
backup transport, NOT an authoritative course-state synchronization protocol.
"""
from __future__ import annotations
import base64
import hashlib
import io
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

from platform_api.course_agents import identity
from scripts.lib.repository import course_dir, textbook_dir, validate_course_name

MAX_TOTAL = 24 * 1024 * 1024
FILES = [
    ("DATA", "PROGRESS.md"),
    ("DATA", "runtime/course_state.json"),
    ("DATA", "runtime/agent_features.json"),
    ("DATA", "runtime/model_roles.json"),
    ("DATA", "runtime/archive_state.json"),
    ("DATA", "runtime/tasks.json"),
    ("DATA", "CONTEXT/CONTEXT_INDEX.md"),
    ("DATA", "CONTEXT/LESSON_SUMMARIES.md"),
    ("TEXTBOOK", "book.md"),
]

class SyncError(ValueError):
    pass

def _location(root: Path, course: str, top: str, name: str) -> Path:
    parent = course_dir(root, course) if top == "DATA" else textbook_dir(root, course)
    candidate = parent / name
    if any(p.is_symlink() for p in (parent, *candidate.parents, candidate)):
        raise SyncError("Refusing symlinked snapshot content")
    if parent.resolve() not in candidate.resolve().parents:
        raise SyncError("Snapshot source outside course")
    return candidate

def _entry(name: str, content: bytes, archive: ZipFile) -> None:
    info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    archive.writestr(info, content)

def snapshot(root: Path, course: str) -> tuple[bytes, dict]:
    course = validate_course_name(course)
    if not course_dir(root, course).is_dir():
        raise SyncError("Course does not exist")
    buf = io.BytesIO()
    hashes = {}
    total = 0
    with ZipFile(buf, "w") as archive:
        for top, name in FILES:
            source = _location(root, course, top, name)
            if not source.is_file():
                continue
            length = source.stat().st_size
            if length > MAX_TOTAL or total + length > MAX_TOTAL:
                raise SyncError("Snapshot exceeds the bounded size limit")
            content = source.read_bytes()
            if len(content) != length:
                raise SyncError("Snapshot source changed during reading")
            entry = top + "/" + name
            _entry(entry, content, archive)
            hashes[entry] = hashlib.sha256(content).hexdigest()
            total += len(content)
        for database_name in ("chat_history.sqlite3", "interactive_exercises.sqlite3", "flashcards.sqlite3", "ontology.sqlite3"):
            db = _location(root, course, "DATA", "runtime/" + database_name)
            if not db.is_file():
                continue
            if db.stat().st_size + total > MAX_TOTAL:
                raise SyncError("Course SQLite data exceeds snapshot limit")
            with tempfile.TemporaryDirectory(prefix="socratopia-snapshot-") as tmp:
                target = Path(tmp) / "consistent.sqlite3"
                # sqlite backup includes WAL data without copying uncheckpointed -wal files.
                src = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
                dst = sqlite3.connect(target)
                try:
                    src.backup(dst)
                finally:
                    dst.close()
                    src.close()
                content = target.read_bytes()
            if total + len(content) > MAX_TOTAL:
                raise SyncError("Consistent course SQLite data exceeds snapshot limit")
            entry = "DATA/runtime/" + database_name
            _entry(entry, content, archive)
            hashes[entry] = hashlib.sha256(content).hexdigest()
            total += len(content)
        if not hashes:
            raise SyncError("No course data to synchronize")
        manifest = {"schema_version": 1, "course_hash": identity(course),
                    "hashes": hashes, "restore_mode": "manual-review-only"}
        _entry("manifest.json", json.dumps(manifest, sort_keys=True).encode(), archive)
    payload = buf.getvalue()
    return payload, {"course": course, "sha256": hashlib.sha256(payload).hexdigest(),
                     "files": len(hashes), "bytes": len(payload), "contains_personal_notes": True}

def _secure_url(raw: str) -> str:
    p = urlsplit(raw)
    if p.scheme != "https" or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise SyncError("WebDAV and S3 endpoints require an HTTPS URL without inline credentials")
    return raw.rstrip("/")

def upload(root: Path, course: str, backend: str) -> dict:
    if backend not in {"webdav", "s3"}:
        raise SyncError("Only WebDAV and S3 are supported")
    content, meta = snapshot(root, course)
    filename = identity(course) + "-" + meta["sha256"] + ".zip"
    if backend == "webdav":
        import httpx
        base = _secure_url(os.environ.get("SOCRATOPIA_WEBDAV_URL", ""))
        username = os.environ.get("SOCRATOPIA_WEBDAV_USERNAME", "")
        password = os.environ.get("SOCRATOPIA_WEBDAV_PASSWORD", "")
        if not username or not password:
            raise SyncError("WebDAV credentials missing")
        try:
            with httpx.Client(timeout=30, follow_redirects=False) as client:
                res = client.put(base + "/" + filename, content=content,
                                 auth=(username, password),
                                 headers={"Content-Type": "application/zip",
                                          "If-None-Match": "*"})
                if res.status_code == 412:
                    return {**meta, "backend": backend, "already_exists": True}
                if res.status_code not in (200, 201, 204):
                    raise SyncError("WebDAV upload failed (HTTP " + str(res.status_code) + ")")
        except httpx.HTTPError as exc:
            raise SyncError("WebDAV is unavailable") from exc
    else:
        bucket = os.environ.get("SOCRATOPIA_S3_BUCKET", "")
        if not bucket:
            raise SyncError("S3 bucket not configured")
        endpoint = os.environ.get("SOCRATOPIA_S3_ENDPOINT", "").strip()
        if endpoint:
            _secure_url(endpoint)
        try:
            import boto3
        except ImportError as exc:
            raise SyncError("S3 requires the optional socratopia-platform[sync] extra") from exc
        client = boto3.client("s3", **({"endpoint_url": endpoint} if endpoint else {}))
        try:
            client.put_object(Bucket=bucket, Key="socratopia/" + filename,
                              Body=content, ContentType="application/zip",
                              ServerSideEncryption="AES256", IfNoneMatch="*",
                              ChecksumSHA256=base64.b64encode(hashlib.sha256(content).digest()).decode())
        except Exception as exc:
            # Never expose potentially sensitive provider error messages.
            raise SyncError("S3 upload rejected (verify credentials and bucket policy)") from exc
    return {**meta, "backend": backend, "already_exists": False}
