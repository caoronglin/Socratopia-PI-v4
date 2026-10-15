"""Deterministic concept graph from current-course textbook headings only."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path
from platform_api.evidence import _read_book
from scripts.lib.repository import validate_course_name

MAX_NODES = 160

def build(root: Path, course: str) -> dict:
    name = validate_course_name(course)
    book, sha = _read_book(root, name)
    nodes: list[dict] = []
    edges: list[dict] = []
    parents: list[tuple[int, str]] = []
    for line_number, line in enumerate(book.splitlines(), 1):
        match = re.match(r"^(#{1,4})\s+(.{1,140}?)\s*$", line)
        if not match:
            continue
        if len(nodes) >= MAX_NODES:
            break
        level, title = len(match.group(1)), match.group(2)
        nid = hashlib.sha256(f"{line_number}:{title}".encode()).hexdigest()[:12]
        nodes.append({"id": nid, "label": title, "line": line_number,
                      "level": level, "source": "book.md", "fact_verified": False})
        while parents and parents[-1][0] >= level:
            parents.pop()
        if parents:
            edges.append({"source": parents[-1][1], "target": nid,
                          "type": "heading_contains", "derived": True})
        parents.append((level, nid))
    return {"course": name, "source_sha256": sha, "nodes": nodes,
            "edges": edges, "derivation": "markdown_headings",
            "fact_verified": False, "truncated": len(nodes) == MAX_NODES}
