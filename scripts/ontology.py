#!/usr/bin/env python3
"""Socratopia v4 course ontology: typed knowledge graph over append-only JSONL.

Contract (SYSTEM/SPEC + approval §4):
- Store: DATA/<course>/ontology/graph.jsonl (append-only, authoritative history)
         DATA/<course>/ontology/projection.json (derived, non-authoritative, rebuildable)
- Node types: Course/Chapter/KnowledgePoint/Concept/Example/Method/Equation/Experiment
- Edge types: contains/prerequisite/related_to/contrast_with/derived_from/example_of/applies_to
- Forbidden authoritative props: mastered/understood/score/passed/failed/current_progress
  (mastery is derived from PROGRESS/assessment/review, never stored here).
- Mutations require --apply; get/query/validate/stats are read-only.
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

from scripts.lib.repository import (  # noqa: E402
    append_jsonl,
    course_dir,
    read_json,
    validate_course_name,
    write_json_atomic,
)

NODE_TYPES = {"Course", "Chapter", "KnowledgePoint", "Concept", "Example", "Method", "Equation", "Experiment"}
EDGE_TYPES = {"contains", "prerequisite", "related_to", "contrast_with", "derived_from", "example_of", "applies_to"}
FORBIDDEN_PROPS = {"mastered", "understood", "score", "passed", "failed", "current_progress"}
_ID_RE = re.compile(r"^[A-Za-z0-9_.\-\u4e00-\u9fff]{1,128}$")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID_RE.match(value)) and ".." not in value


def _valid_ref(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    if "\x00" in value or value.startswith("/") or ".." in value:
        return False
    return True


def graph_path(root: Path, course: str) -> Path:
    return course_dir(root, course) / "ontology" / "graph.jsonl"


def projection_path(root: Path, course: str) -> Path:
    return course_dir(root, course) / "ontology" / "projection.json"


# ---------- event loading / folding ----------

def load_events(root: Path, course: str) -> list[dict[str, Any]]:
    """Parse append-only JSONL; raise ValueError on a malformed line (no rewrite)."""
    path = graph_path(root, course)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8", errors="strict").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"graph.jsonl 第 {lineno} 行不是合法 JSON：{exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"graph.jsonl 第 {lineno} 行必须是 object")
        events.append(obj)
    return events


def fold(events: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str, str], dict[str, Any]]]:
    """Fold events into current active nodes and edges."""
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    for ev in events:
        kind = ev.get("kind")
        op = ev.get("op")
        if kind == "node":
            nid = ev.get("id")
            if op in {"upsert", "supersede"} and _valid_id(nid):
                nodes[nid] = {"id": nid, "type": ev.get("type"), "props": dict(ev.get("props") or {}), "updated_at": ev.get("ts", "")}
            elif op == "tombstone" and _valid_id(nid):
                nodes.pop(nid, None)
        elif kind == "edge":
            key = (str(ev.get("from")), str(ev.get("rel")), str(ev.get("to")))
            if op == "relate":
                edges[key] = {"from": key[0], "rel": key[1], "to": key[2], "props": dict(ev.get("props") or {}), "ts": ev.get("ts", "")}
            elif op == "tombstone":
                edges.pop(key, None)
    return nodes, edges


def _prereq_adjacency(edges: dict[tuple[str, str, str], dict[str, Any]]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {}
    for (frm, rel, to) in edges:
        if rel == "prerequisite":
            adj.setdefault(frm, set()).add(to)
    return adj


def _reachable(adj: dict[str, set[str]], start: str, target: str) -> bool:
    stack = [start]
    seen: set[str] = set()
    while stack:
        cur = stack.pop()
        if cur == target:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(adj.get(cur, ()))
    return False


# ---------- validation ----------

def validate(root: Path, course: str) -> list[str]:
    """Return constraint violations; never mutates history."""
    validate_course_name(course)
    try:
        events = load_events(root, course)
    except ValueError as exc:
        return [str(exc)]
    errors: list[str] = []
    nodes, edges = fold(events)
    active = set(nodes)
    for ev in events:
        kind, op = ev.get("kind"), ev.get("op")
        if kind == "node" and op in {"upsert", "supersede"}:
            nid = ev.get("id")
            if not _valid_id(nid):
                errors.append(f"非法节点 id：{nid!r}")
                continue
            if ev.get("type") not in NODE_TYPES:
                errors.append(f"节点 {nid} 非法类型：{ev.get('type')}")
            props = ev.get("props") or {}
            bad = FORBIDDEN_PROPS.intersection(props)
            if bad:
                errors.append(f"节点 {nid} 含禁止的权威字段：{sorted(bad)}")
            if "course" in props and props["course"] != course:
                errors.append(f"节点 {nid} 跨课程引用：course={props['course']!r} != {course!r}")
            for ref_key in ("source_anchor", "evidence_ref", "book_anchor"):
                if ref_key in props and not _valid_ref(props[ref_key]):
                    errors.append(f"节点 {nid} 非法 {ref_key}：{props[ref_key]!r}")
        elif kind == "edge":
            frm, rel, to = ev.get("from"), ev.get("rel"), ev.get("to")
            if not (_valid_id(frm) and _valid_id(to)):
                errors.append(f"边含非法端点：{frm!r} -> {to!r}")
                continue
            if rel not in EDGE_TYPES:
                errors.append(f"边 {frm}->{to} 非法关系：{rel}")
    # Orphan check on ACTIVE (folded) edges only: a legitimately created edge whose
    # endpoint was later tombstoned (cascade) must not be flagged.
    for (frm, rel, to) in edges:
        if frm not in active or to not in active:
            errors.append(f"孤儿边：{frm} -[{rel}]-> {to}（端点不存在或已删除）")
    adj = _prereq_adjacency(edges)
    for (frm, rel, to) in edges:
        if rel == "prerequisite" and _reachable(adj, to, frm):
            errors.append(f"prerequisite 成环：{frm} <-> {to}")
    return errors


def rebuild_projection(root: Path, course: str) -> dict[str, Any]:
    nodes, edges = fold(load_events(root, course))
    return {
        "schema_version": 1,
        "course": course,
        "generated_at": _now(),
        "derived": True,
        "authoritative": False,
        "nodes": nodes,
        "edges": list(edges.values()),
    }


# ---------- mutations ----------

def _check_writable(node_id: str, ntype: str, props: dict[str, Any], course: str) -> None:
    if not _valid_id(node_id):
        raise ValueError(f"非法节点 id：{node_id!r}")
    if ntype not in NODE_TYPES:
        raise ValueError(f"非法节点类型：{ntype}（允许：{sorted(NODE_TYPES)}）")
    bad = FORBIDDEN_PROPS.intersection(props)
    if bad:
        raise ValueError(f"禁止写入权威字段：{sorted(bad)}（mastery 只能由 PROGRESS/assessment/review 派生）")
    if "course" in props and props["course"] != course:
        raise ValueError(f"跨课程引用被拒：{props['course']!r} != {course!r}")
    for ref_key in ("source_anchor", "evidence_ref", "book_anchor"):
        if ref_key in props and not _valid_ref(props[ref_key]):
            raise ValueError(f"非法 {ref_key}：{props[ref_key]!r}")


def node_upsert(root: Path, course: str, node_id: str, ntype: str, props: dict[str, Any] | None = None) -> dict[str, Any]:
    """Idempotent upsert: no-op if unchanged; supersede event if props changed."""
    validate_course_name(course)
    props = dict(props or {})
    _check_writable(node_id, ntype, props, course)
    nodes, _ = fold(load_events(root, course))
    current = nodes.get(node_id)
    if current and current.get("type") == ntype and current.get("props") == props:
        return {"changed": False, "node": current}
    op = "supersede" if current else "upsert"
    event = {"kind": "node", "op": op, "id": node_id, "type": ntype, "props": props, "ts": _now()}
    append_jsonl(graph_path(root, course), event)
    return {"changed": True, "op": op, "node": {"id": node_id, "type": ntype, "props": props, "updated_at": event["ts"]}}


def node_tombstone(root: Path, course: str, node_id: str) -> dict[str, Any]:
    """Tombstone a node and cascade-remove edges touching it (keeps graph consistent)."""
    validate_course_name(course)
    if not _valid_id(node_id):
        raise ValueError(f"非法节点 id：{node_id!r}")
    nodes, edges = fold(load_events(root, course))
    if node_id not in nodes:
        return {"changed": False}
    append_jsonl(graph_path(root, course), {"kind": "node", "op": "tombstone", "id": node_id, "ts": _now()})
    removed = 0
    for (frm, rel, to) in list(edges):
        if frm == node_id or to == node_id:
            append_jsonl(graph_path(root, course), {"kind": "edge", "op": "tombstone", "from": frm, "rel": rel, "to": to, "ts": _now()})
            removed += 1
    return {"changed": True, "edges_removed": removed}


def edge_relate(root: Path, course: str, frm: str, rel: str, to: str, props: dict[str, Any] | None = None) -> dict[str, Any]:
    """Idempotent relate; rejects unknown rel, orphan endpoints, and prerequisite cycles."""
    validate_course_name(course)
    props = dict(props or {})
    if rel not in EDGE_TYPES:
        raise ValueError(f"非法关系：{rel}（允许：{sorted(EDGE_TYPES)}）")
    if not (_valid_id(frm) and _valid_id(to)):
        raise ValueError(f"非法边端点：{frm!r} -> {to!r}")
    nodes, edges = fold(load_events(root, course))
    if frm not in nodes or to not in nodes:
        raise ValueError(f"孤儿边被拒：{frm} -[{rel}]-> {to}（端点不存在或已删除）")
    key = (frm, rel, to)
    if key in edges and edges[key].get("props") == props:
        return {"changed": False, "edge": edges[key]}
    if rel == "prerequisite":
        adj = _prereq_adjacency(edges)
        if _reachable(adj, to, frm):
            raise ValueError(f"prerequisite 成环被拒：{frm} -> {to}")
    append_jsonl(graph_path(root, course), {"kind": "edge", "op": "relate", "from": frm, "rel": rel, "to": to, "props": props, "ts": _now()})
    return {"changed": True, "edge": {"from": frm, "rel": rel, "to": to, "props": props}}


def node_get(root: Path, course: str, node_id: str) -> dict[str, Any] | None:
    nodes, edges = fold(load_events(root, course))
    node = nodes.get(node_id)
    if node is None:
        return None
    rel_edges = [e for (f, _r, t), e in edges.items() if f == node_id or t == node_id]
    return {"node": node, "edges": rel_edges}


def query(root: Path, course: str, node_type: str | None = None, node_id: str | None = None,
          related: str | None = None, rel: str | None = None) -> dict[str, Any]:
    nodes, edges = fold(load_events(root, course))
    if node_id is not None:
        got = node_get(root, course, node_id)
        return {"result": got}
    if related is not None:
        out = []
        for (f, r, t), e in edges.items():
            if f == related or t == related:
                if rel is None or r == rel:
                    out.append(e)
        return {"result": out}
    if node_type is not None:
        if node_type not in NODE_TYPES:
            raise ValueError(f"非法节点类型：{node_type}")
        return {"result": [n for n in nodes.values() if n.get("type") == node_type]}
    return {"result": list(nodes.values())}


def compact(root: Path, course: str) -> dict[str, Any]:
    projection = rebuild_projection(root, course)
    write_json_atomic(projection_path(root, course), projection)
    return projection


def stats(root: Path, course: str) -> dict[str, Any]:
    nodes, edges = fold(load_events(root, course))
    by_type: dict[str, int] = {}
    for n in nodes.values():
        by_type[n.get("type", "?")] = by_type.get(n.get("type", "?"), 0) + 1
    by_rel: dict[str, int] = {}
    for (_f, r, _t) in edges:
        by_rel[r] = by_rel.get(r, 0) + 1
    return {"course": course, "nodes": len(nodes), "edges": len(edges), "nodes_by_type": by_type, "edges_by_rel": by_rel}


def init(root: Path, course: str) -> dict[str, Any]:
    validate_course_name(course)
    gp = graph_path(root, course)
    gp.parent.mkdir(parents=True, exist_ok=True)
    created = []
    if not gp.exists():
        gp.write_text("", encoding="utf-8")
        created.append(str(gp))
    projection = rebuild_projection(root, course)
    write_json_atomic(projection_path(root, course), projection)
    created.append(str(projection_path(root, course)))
    return {"course": course, "created": created}


# ---------- CLI ----------

def _parse_props(pairs: list[str] | None, props_json: str | None) -> dict[str, Any]:
    props: dict[str, Any] = {}
    if props_json:
        loaded = json.loads(props_json)
        if not isinstance(loaded, dict):
            raise SystemExit("--props 必须是 JSON object")
        props.update(loaded)
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"--prop 需为 k=v：{pair}")
        k, v = pair.split("=", 1)
        props[k.strip()] = v
    return props


def main() -> int:
    parser = argparse.ArgumentParser(description="课程知识图谱（append-only JSONL，mastery 不入库）")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init"); p.add_argument("--course", required=True); p.add_argument("--apply", action="store_true")

    p = sub.add_parser("node", help="node upsert|get|tombstone")
    node_sub = p.add_subparsers(dest="node_command", required=True)
    up = node_sub.add_parser("upsert"); up.add_argument("--course", required=True); up.add_argument("--id", required=True); up.add_argument("--type", required=True); up.add_argument("--prop", action="append"); up.add_argument("--props", default=None); up.add_argument("--source-anchor", default=None); up.add_argument("--apply", action="store_true")
    get = node_sub.add_parser("get"); get.add_argument("--course", required=True); get.add_argument("--id", required=True)
    tomb = node_sub.add_parser("tombstone"); tomb.add_argument("--course", required=True); tomb.add_argument("--id", required=True); tomb.add_argument("--apply", action="store_true")

    p = sub.add_parser("edge"); edge_sub = p.add_subparsers(dest="edge_command", required=True)
    rel = edge_sub.add_parser("relate"); rel.add_argument("--course", required=True); rel.add_argument("--from", dest="frm", required=True); rel.add_argument("--rel", required=True); rel.add_argument("--to", required=True); rel.add_argument("--props", default=None); rel.add_argument("--apply", action="store_true")

    p = sub.add_parser("query"); p.add_argument("--course", required=True); p.add_argument("--type", default=None); p.add_argument("--id", default=None); p.add_argument("--related", default=None); p.add_argument("--rel", default=None)

    p = sub.add_parser("validate"); p.add_argument("--course", required=True)
    p = sub.add_parser("compact"); p.add_argument("--course", required=True); p.add_argument("--apply", action="store_true")
    p = sub.add_parser("stats"); p.add_argument("--course", required=True)

    args = parser.parse_args()
    validate_course_name(args.course)
    dump = lambda obj: print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))

    if args.command == "init":
        if not args.apply:
            raise SystemExit("init 需要 --apply。")
        return dump(init(ROOT, args.course)) or 0
    if args.command == "node":
        if args.node_command == "upsert":
            if not args.apply:
                raise SystemExit("node upsert 需要 --apply。")
            props = _parse_props(args.prop, args.props)
            if args.source_anchor:
                props["source_anchor"] = args.source_anchor
            return dump(node_upsert(ROOT, args.course, args.id, args.type, props)) or 0
        if args.node_command == "get":
            return dump(node_get(ROOT, args.course, args.id) or {"result": None}) or 0
        if args.node_command == "tombstone":
            if not args.apply:
                raise SystemExit("node tombstone 需要 --apply。")
            return dump(node_tombstone(ROOT, args.course, args.id)) or 0
    if args.command == "edge":
        if not args.apply:
            raise SystemExit("edge relate 需要 --apply。")
        props = _parse_props(None, args.props)
        return dump(edge_relate(ROOT, args.course, args.frm, args.rel, args.to, props)) or 0
    if args.command == "query":
        return dump(query(ROOT, args.course, node_type=args.type, node_id=args.id, related=args.related, rel=args.rel)) or 0
    if args.command == "validate":
        errors = validate(ROOT, args.course)
        print("有效" if not errors else "\n".join(errors))
        return 0 if not errors else 1
    if args.command == "compact":
        if not args.apply:
            raise SystemExit("compact 需要 --apply。")
        return dump(compact(ROOT, args.course)) or 0
    if args.command == "stats":
        return dump(stats(ROOT, args.course)) or 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
