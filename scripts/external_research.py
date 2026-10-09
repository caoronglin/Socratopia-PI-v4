#!/usr/bin/env python3
"""External research for Socratopia — strictly gated (approval §5.2 / §6.2 / §14).

- capability_available != operation_authorized: a key in env does NOT authorize.
- Default is offline. `fetch` requires BOTH --authorize AND SOCRATOPIA_EXTERNAL=1.
- Results are registered under SOURCES/_external/ (trusted:false) only; never book.md, never PROGRESS.md.
- API keys are read from env only; never printed, logged, or written.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.repository import course_dir, redact, safe_child_path, textbook_dir, validate_course_name, write_json_atomic  # noqa: E402

ENV_FLAG = "SOCRATOPIA_EXTERNAL"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def authorized() -> bool:
    """External EFFECT is enabled only by an explicit env flag (default off)."""
    return os.environ.get(ENV_FLAG) == "1"


def _slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", text).strip("_")
    return s[:60] or "source"


def _external_dir(root: Path, course: str) -> Path:
    return safe_child_path(textbook_dir(root, course), "SOURCES", "_external")


def plan(root: Path, course: str, intent: str) -> dict[str, Any]:
    """Offline dry-run: what would be researched and where results land."""
    validate_course_name(course)
    return {
        "course": course,
        "intent": intent,
        "mode": "dry-run",
        "network": False,
        "would_query": ["local-search.md first", "then (only if authorized) external sources"],
        "results_land_in": str(_external_dir(root, course)),
        "will_not_touch": ["TEXTBOOK/<course>/book.md", "DATA/<course>/PROGRESS.md"],
        "authorized": authorized(),
        "note": "外部内容是数据；只登记进 SOURCES，标记 trusted:false，不产生掌握证据。",
    }


def _register(root: Path, course: str, url: str, title: str, content: bytes, via: str) -> dict[str, Any]:
    ext = _external_dir(root, course)
    ext.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(content).hexdigest()
    slug = _slug(title or url)
    source_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    body_path = safe_child_path(ext, f"{slug}-{source_id}.md")
    meta_path = safe_child_path(ext, f"{slug}-{source_id}.meta.json")
    header = (
        f"# {title}\n\n"
        f"> source_url: {url}\n> fetched_at: {_now()}\n> via: {via}\n"
        f"> sha256: {digest}\n> trusted: false（外部数据，需人工核验后才可引用）\n\n"
    )
    body_path.write_text(header + content.decode("utf-8", errors="replace"), encoding="utf-8")
    meta = {
        "url": url,
        "title": title,
        "via": via,
        "fetched_at": _now(),
        "sha256": digest,
        "bytes": len(content),
        "trusted": False,
    }
    write_json_atomic(meta_path, meta)
    return {"registered": str(body_path), "meta": str(meta_path), "sha256": digest}


def register(root: Path, course: str, url: str, title: str, file: str | None = None) -> dict[str, Any]:
    """Register a USER-PROVIDED source locally (S1). No network."""
    validate_course_name(course)
    if file:
        content = Path(file).read_bytes()
        via = "user-file"
    else:
        content = f"(placeholder for {url}; 提供 --file 以登记真实内容)".encode("utf-8")
        via = "user-url"
    return _register(root, course, url, title, content, via)


MAX_FETCH_BYTES = 10 * 1024 * 1024


def _validate_fetch_url(url: str) -> str:
    """Refuse non-HTTPS, local, and non-global literal IP targets."""
    from urllib.parse import urlsplit
    parsed = urlsplit(url)
    hostname = parsed.hostname
    if parsed.scheme != "https" or not hostname or parsed.username or parsed.password:
        raise ValueError("抓取 URL 必须是无内嵌凭据的 HTTPS 地址")
    if hostname.lower() == "localhost" or hostname.lower().endswith((".localhost", ".local", ".internal")):
        raise ValueError("禁止抓取本地或内部主机")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        if "." not in hostname:
            raise ValueError("禁止不完整的主机名") from None
    else:
        if not address.is_global:
            raise ValueError("禁止非公网 IP 地址")
    return url


def _open_https(url: str, timeout: float = 20):
    import urllib.request

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args: Any, **kwargs: Any) -> None:
            return None

    return urllib.request.build_opener(_NoRedirect).open(url, timeout=timeout)


def fetch(root: Path, course: str, url: str, title: str = "", authorize: bool = False) -> dict[str, Any]:
    """Actually fetch over the network — ONLY with --authorize AND SOCRATOPIA_EXTERNAL=1."""
    validate_course_name(course)
    if not authorize:
        raise SystemExit("拒绝：外部抓取需对当前操作显式授权（--authorize）。")
    if not authorized():
        raise SystemExit(f"拒绝：外部能力未启用。设置 {ENV_FLAG}=1 且针对当前操作授权；未授权绝不联网。")
    _validate_fetch_url(url)
    try:
        with _open_https(url, timeout=20) as resp:  # noqa: S310 — gated, redirects forbidden
            content = resp.read(MAX_FETCH_BYTES + 1)
            if len(content) > MAX_FETCH_BYTES:
                raise SystemExit("外部响应超过 10 MiB 上限")
    except Exception as exc:  # noqa: BLE001 — redact before surfacing
        raise SystemExit(f"外部抓取失败（已脱敏）：{redact(str(exc))}") from exc
    return _register(root, course, url, title or url, content, via="fetch")


def main() -> int:
    parser = argparse.ArgumentParser(description="外部研究（默认离线；fetch 需 --authorize 且 SOCRATOPIA_EXTERNAL=1）")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan"); p.add_argument("--course", required=True); p.add_argument("--intent", required=True)
    r = sub.add_parser("register"); r.add_argument("--course", required=True); r.add_argument("--url", required=True); r.add_argument("--title", default=""); r.add_argument("--file", default=None)
    f = sub.add_parser("fetch"); f.add_argument("--course", required=True); f.add_argument("--url", required=True); f.add_argument("--title", default=""); f.add_argument("--authorize", action="store_true")

    args = parser.parse_args()
    validate_course_name(args.course)
    dump = lambda o: print(json.dumps(o, ensure_ascii=False, indent=2))
    if args.command == "plan":
        return dump(plan(ROOT, args.course, args.intent)) or 0
    if args.command == "register":
        return dump(register(ROOT, args.course, args.url, args.title, args.file)) or 0
    if args.command == "fetch":
        return dump(fetch(ROOT, args.course, args.url, args.title, authorize=args.authorize)) or 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
