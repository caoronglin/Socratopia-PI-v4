#!/usr/bin/env python3
"""Local, network-free search across a Socratopia course.

Scope: book.md sections, outline/manifest anchors, SOURCES/, PREP/, and the
course ontology. Strictly local: no network, no upload, no external API.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import ontology as onto  # noqa: E402
from scripts.lib.repository import course_dir, read_json, textbook_dir, validate_course_name  # noqa: E402

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _terms(query: str) -> list[str]:
    return [t for t in re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]+", query) if t]


def _score(text: str, terms: list[str]) -> int:
    return sum(text.count(t) for t in terms)


def _snippet(text: str, terms: list[str], width: int = 60) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    for t in terms:
        idx = flat.find(t)
        if idx >= 0:
            start = max(0, idx - width // 2)
            return flat[start:start + width]
    return flat[:width]


def _sections(text: str) -> list[dict]:
    """Split markdown into heading-anchored sections."""
    lines = text.splitlines()
    heads: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            heads.append((i, m.group(2).strip()))
    out: list[dict] = []
    for k, (i, title) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        body = "\n".join(lines[i + 1:end])
        out.append({"anchor": title, "text": body})
    if not out and text.strip():
        out.append({"anchor": "", "text": text})
    return out


def _search_markdown(path: Path, terms: list[str], source: str, limit: int) -> list[dict]:
    if not path.exists() or not terms:
        return []
    hits = []
    for sec in _sections(path.read_text(encoding="utf-8", errors="replace")):
        sc = _score(sec["text"] + " " + sec["anchor"], terms)
        if sc > 0:
            hits.append({"source": source, "anchor": sec["anchor"], "score": sc, "snippet": _snippet(sec["text"], terms)})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:limit]


def _search_anchors(root: Path, course: str, terms: list[str], limit: int) -> list[dict]:
    cdir = textbook_dir(root, course)
    hits: list[dict] = []
    manifest = read_json(cdir / "manifest.json") or {}
    for ch in manifest.get("chapters", []):
        title = str(ch.get("title", ""))
        sc = _score(title, terms)
        if sc > 0:
            hits.append({"source": "manifest", "anchor": title, "score": sc, "snippet": title})
    outline = cdir / "_outline.md"
    if outline.exists():
        for line in outline.read_text(encoding="utf-8", errors="replace").splitlines():
            sc = _score(line, terms)
            if sc > 0:
                hits.append({"source": "outline", "anchor": line.strip(), "score": sc, "snippet": line.strip()})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:limit]


def _search_dir(root: Path, base: Path, terms: list[str], source: str, limit: int) -> list[dict]:
    hits: list[dict] = []
    if base.exists():
        for md in sorted(base.rglob("*.md")):
            hits.extend(_search_markdown(md, terms, f"{source}:{md.name}", limit))
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:limit]


def _search_ontology(root: Path, course: str, terms: list[str], limit: int) -> list[dict]:
    if not terms:
        return []
    try:
        nodes, edges = onto.fold(onto.load_events(root, course))
    except ValueError:
        return []
    hits: list[dict] = []
    for nid, node in nodes.items():
        blob = nid + " " + json.dumps(node.get("props", {}), ensure_ascii=False) + " " + str(node.get("type", ""))
        sc = _score(blob, terms)
        if sc > 0:
            hits.append({"source": "ontology", "anchor": nid, "score": sc, "snippet": f"{node.get('type')} {nid}"})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:limit]


def local_search(root: Path, course: str, query: str, scope: str = "all", limit: int = 10) -> list[dict]:
    """Aggregate local hits. Never touches the network."""
    validate_course_name(course)
    terms = _terms(query)
    if not terms:
        return []
    cdir = textbook_dir(root, course)
    hits: list[dict] = []
    if scope in {"all", "book"}:
        hits += _search_markdown(cdir / "book.md", terms, "book", limit)
    if scope in {"all", "sources"}:
        hits += _search_dir(root, cdir / "SOURCES", terms, "sources", limit)
    if scope in {"all", "prep"}:
        hits += _search_dir(root, cdir / "PREP", terms, "prep", limit)
    if scope in {"all", "ontology"}:
        hits += _search_ontology(root, course, terms, limit)
    if scope in {"all", "anchors"}:
        hits += _search_anchors(root, course, terms, limit)
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="课程本地检索（无网络/无上传/无外部 API）")
    parser.add_argument("--course", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--scope", choices=["all", "book", "sources", "prep", "ontology", "anchors"], default="all")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    validate_course_name(args.course)
    hits = local_search(ROOT, args.course, args.query, scope=args.scope, limit=args.limit)
    print(json.dumps({"course": args.course, "query": args.query, "scope": args.scope, "network": False, "hits": hits}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
