#!/usr/bin/env python3
"""Local, per-course vector-ish index for Socratopia (network-free).

- Store: DATA/<course>/cache/vector/index.json  (regenerable, non-authoritative)
- Engine: local lexical tokens (ASCII words + CJK char bigrams). No network, no upload.
- Remote embeddings (e.g. SiliconFlow BGE-M3) are a separate, gated capability
  (approval §6.2 / Phase 6) and are intentionally NOT wired here.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.repository import course_dir, read_json, textbook_dir, validate_course_name, write_json_atomic  # noqa: E402

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def index_path(root: Path, course: str) -> Path:
    return course_dir(root, course) / "cache" / "vector" / "index.json"


def _tokens(text: str) -> list[str]:
    words = _WORD_RE.findall(text.lower())
    cjk = "".join(_CJK_RE.findall(text))
    bigrams = [cjk[i:i + 2] for i in range(len(cjk) - 1)]
    return words + bigrams


def _sections(text: str) -> list[dict]:
    lines = text.splitlines()
    heads: list[tuple[int, str]] = [(i, m.group(2).strip()) for i, line in enumerate(lines) if (m := _HEADING_RE.match(line))]
    out: list[dict] = []
    for k, (i, title) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        out.append({"anchor": title, "text": "\n".join(lines[i + 1:end])})
    if not out and text.strip():
        out.append({"anchor": "", "text": text})
    return out


def _collect_docs(root: Path, course: str) -> list[dict]:
    cdir = textbook_dir(root, course)
    docs: list[dict] = []
    book = cdir / "book.md"
    if book.exists():
        for sec in _sections(book.read_text(encoding="utf-8", errors="replace")):
            docs.append({"source": "book", "anchor": sec["anchor"], "text": sec["text"]})
    for base, label in ((cdir / "SOURCES", "sources"), (cdir / "PREP", "prep")):
        if base.exists():
            for md in sorted(base.rglob("*.md")):
                docs.append({"source": f"{label}:{md.name}", "anchor": md.stem, "text": md.read_text(encoding="utf-8", errors="replace")})
    for doc in docs:
        counts: dict[str, int] = {}
        for tok in _tokens(doc["text"] + " " + doc["anchor"]):
            counts[tok] = counts.get(tok, 0) + 1
        doc["tf"] = counts
        doc.pop("text", None)
    return docs


def build(root: Path, course: str) -> dict[str, Any]:
    validate_course_name(course)
    docs = _collect_docs(root, course)
    index = {
        "schema_version": 1,
        "course": course,
        "engine": "local-lexical",
        "network": False,
        "derived": True,
        "authoritative": False,
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "docs": docs,
    }
    write_json_atomic(index_path(root, course), index)
    return {"course": course, "docs": len(docs), "path": str(index_path(root, course))}


def search(root: Path, course: str, query: str, limit: int = 10) -> dict[str, Any]:
    validate_course_name(course)
    index = read_json(index_path(root, course))
    if index is None:
        return {"available": False, "hits": [], "hint": "索引不存在，先 build（本地，无网络）。"}
    q = set(_tokens(query))
    hits: list[dict] = []
    for doc in index.get("docs", []):
        tf = doc.get("tf", {})
        score = sum(tf.get(t, 0) for t in q)
        if score > 0:
            hits.append({"source": doc.get("source"), "anchor": doc.get("anchor"), "score": score})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return {"available": True, "engine": index.get("engine"), "network": False, "hits": hits[:limit]}


def status(root: Path, course: str) -> dict[str, Any]:
    validate_course_name(course)
    index = read_json(index_path(root, course))
    if index is None:
        return {"course": course, "available": False}
    return {"course": course, "available": True, "engine": index.get("engine"), "docs": len(index.get("docs", [])), "built_at": index.get("built_at")}


def main() -> int:
    parser = argparse.ArgumentParser(description="课程本地向量索引（无网络/可再生/非权威）")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build"); b.add_argument("--course", required=True); b.add_argument("--apply", action="store_true")
    s = sub.add_parser("search"); s.add_argument("--course", required=True); s.add_argument("--query", required=True); s.add_argument("--limit", type=int, default=10)
    st = sub.add_parser("status"); st.add_argument("--course", required=True)
    args = parser.parse_args()
    validate_course_name(args.course)
    dump = lambda o: print(json.dumps(o, ensure_ascii=False, indent=2))
    if args.command == "build":
        if not args.apply:
            raise SystemExit("build 需要 --apply（写入可再生缓存，非权威）。")
        return dump(build(ROOT, args.course)) or 0
    if args.command == "search":
        return dump(search(ROOT, args.course, args.query, limit=args.limit)) or 0
    if args.command == "status":
        return dump(status(ROOT, args.course)) or 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
