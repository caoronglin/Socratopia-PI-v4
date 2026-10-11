"""Course-bound, read-only evidence retrieval; no LLM or network trust in this layer."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from scripts.lib.repository import safe_child_path, textbook_dir, validate_course_name

MAX_BOOK_BYTES = 2_000_000
MAX_EXCERPT = 1300
MAX_RESULTS = 3


class EvidenceError(ValueError):
    """Source data unavailable or invalid; fail closed instead of guessing."""


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    course: str
    path: str
    sha256: str
    sources: tuple[dict[str, str], ...]

    def for_client(self) -> dict:
        return {
            "course": self.course,
            "source": self.path,
            "sha256": self.sha256,
            "excerpts": list(self.sources),
            "ready": bool(self.sources),
            "fact_verified": False,
        }


def _book_path(root: Path, course: str) -> Path:
    name = validate_course_name(course)
    book_root = textbook_dir(root, name)
    # Resolve only after checking the link; a symlinked textbook cannot cross
    # course boundaries or silently change the authoritative content.
    path = book_root / "book.md"
    if path.is_symlink():
        raise EvidenceError("Active coursebook cannot be a symlink")
    return safe_child_path(book_root, "book.md")


def _read_book(root: Path, course: str) -> tuple[str, str]:
    path = _book_path(root, course)
    if not path.is_file():
        raise EvidenceError("Active book.md is missing; add the textbook before grounded teaching")
    if path.stat().st_size > MAX_BOOK_BYTES:
        raise EvidenceError("Active textbook exceeds the bounded evidence size")
    raw = path.read_bytes()
    if len(raw) > MAX_BOOK_BYTES:
        raise EvidenceError("Active textbook changed during reading")
    try:
        content = raw.decode("utf-8")
    except UnicodeError as exc:
        raise EvidenceError("Active textbook is not valid UTF-8") from exc
    return content, hashlib.sha256(raw).hexdigest()


def _tokens(s: str) -> set[str]:
    text = s.casefold()
    latin = re.findall(r"[a-z0-9][a-z0-9_+-]{1,}", text)
    han = re.findall(r"[\u3400-\u9fff]+", text)
    return set(latin) | {word[i:i + 2] for word in han for i in range(len(word) - 1)}


def _sections(book: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading = "正文"
    pieces: list[str] = []
    for line in book.splitlines():
        if re.match(r"^#{1,4}\s+\S", line):
            if pieces:
                sections.append((heading, "\n".join(pieces).strip()))
            heading = line.lstrip("# ").strip()[:120]
            pieces = [line]
        else:
            pieces.append(line)
    if pieces:
        sections.append((heading, "\n".join(pieces).strip()))
    return [(heading, text) for heading, text in sections if text]


def retrieve(root: Path, course: str, question: str) -> EvidenceSnapshot:
    name = validate_course_name(course)
    book, fingerprint = _read_book(root, name)
    if not question.strip():
        raise EvidenceError("Question must not be empty")
    tokens = _tokens(question)
    ranked = []
    for i, (heading, body) in enumerate(_sections(book)):
        overlap = tokens & _tokens(heading + "\n" + body[:3500])
        if overlap:
            ranked.append((len(overlap), i, heading, body))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    snippets = []
    for _, _, heading, body in ranked[:MAX_RESULTS]:
        snippets.append({
            "id": f"S{len(snippets) + 1}",
            "section": heading,
            "text": body[:MAX_EXCERPT],
        })
    return EvidenceSnapshot(
        course=name,
        path=f"TEXTBOOK/{name}/book.md",
        sha256=fingerprint,
        sources=tuple(snippets),
    )


def is_current(root: Path, snapshot: EvidenceSnapshot) -> bool:
    try:
        return _read_book(root, snapshot.course)[1] == snapshot.sha256
    except EvidenceError:
        return False
