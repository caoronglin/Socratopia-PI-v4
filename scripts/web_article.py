#!/usr/bin/env python3
"""User-supplied articles (blogs/Zhihu/etc.) -> untrusted, course-scoped SOURCES.

Offline by default. Network fetch requires --authorize AND SOCRATOPIA_EXTERNAL=1.
Never mutates book.md or PROGRESS.md; no login, paywall or anti-bot bypass.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urldefrag, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import external_research as ext  # noqa: E402
from scripts.lib.repository import read_json, safe_child_path, textbook_dir, write_json_atomic  # noqa: E402

MAX_INPUT_BYTES = ext.MAX_FETCH_BYTES
MAX_TEXT_CHARS = 250_000
_BLOCKS = {"p", "div", "section", "h1", "h2", "h3", "h4", "h5", "h6",
           "li", "blockquote", "br", "tr", "pre"}
_OMIT = {"script", "style", "noscript", "svg", "nav", "header", "footer",
         "aside", "form", "button", "iframe"}
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
         "link", "meta", "param", "source", "track", "wbr"}
_SECRET_QUERY = {"token", "access_token", "apikey", "api_key", "secret",
                 "password", "auth", "authorization", "signature", "sig", "key"}


def check_url(url: str) -> str:
    if not isinstance(url, str) or any(ord(ch) < 32 for ch in url):
        raise ValueError("无效网页地址")
    ext._validate_fetch_url(url)
    parsed = urlsplit(url)
    if parsed.port not in (None, 443):
        raise ValueError("只允许默认 HTTPS 端口")
    if any(key.lower() in _SECRET_QUERY for key, _ in parse_qsl(parsed.query)):
        raise ValueError("链接包含可能敏感的认证参数，请提供不含凭据的公开地址")
    return urldefrag(url)[0]


class _Reader(HTMLParser):
    """Collect article/main/body text without executing page instructions."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts = {"article": [], "main": [], "body": []}
        self.depth = {"article": 0, "main": 0, "body": 0}
        self.omit = 0
        self.title_depth = 0
        self.title_parts: list[str] = []
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = dict(attrs)
        if tag == "meta":
            name = (attr.get("property") or attr.get("name") or "").lower()
            if name in {"og:title", "article:published_time", "author", "description"}:
                self.meta[name] = (attr.get("content") or "").strip()[:400]
        if tag in _OMIT:
            self.omit += 1
        if tag == "title":
            self.title_depth += 1
        for region in self.depth:
            if tag == region or self.depth[region]:
                if tag not in _VOID:
                    self.depth[region] += 1
                if not self.omit and tag in _BLOCKS:
                    self.parts[region].append("\n" + ("#" + tag[1] + " " if re.fullmatch(r"h[1-6]", tag) else ""))
        if not self.omit and tag == "br":
            for region in self.depth:
                if self.depth[region]:
                    self.parts[region].append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _VOID:
            return
        if tag == "title" and self.title_depth:
            self.title_depth -= 1
        for region in self.depth:
            if self.depth[region]:
                if not self.omit and tag in _BLOCKS:
                    self.parts[region].append("\n")
                self.depth[region] -= 1
        if tag in _OMIT and self.omit:
            self.omit -= 1

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title_parts.append(data)
        if self.omit:
            return
        value = re.sub(r"[ \t\r\f\v]+", " ", data)
        for region in self.depth:
            if self.depth[region]:
                self.parts[region].append(value)


def extract_article(raw: bytes, *, content_type: str = "") -> tuple[str, str, dict[str, str]]:
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("文章超出 10 MiB 上限")
    if not raw.strip():
        raise ValueError("页面为空")
    if content_type and not any(x in content_type.lower() for x in ("html", "text", "markdown")):
        raise ValueError("该链接不是支持的文本网页；请提供文章正文")
    # Only text, not executable scripts or browser DOM, is ingested.
    text = raw.decode("utf-8-sig", errors="replace")
    if "<html" not in text[:4096].lower() and "<article" not in text[:4096].lower() and "<body" not in text[:4096].lower():
        if re.search(r"<(?:p|h[1-6]|div)\b", text[:4096], re.I):
            pass
        else:
            plain = text.strip()
            if len(plain) < 30:
                raise ValueError("正文过短；请提供可阅读的文章文本")
            return plain[:MAX_TEXT_CHARS], "", {"extractor": "plain-text"}
    reader = _Reader()
    reader.feed(text)
    reader.close()
    for region in ("article", "main", "body"):
        extracted = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n",
                           "".join(reader.parts[region])).strip()
        if len(extracted) >= 40:
            title = reader.meta.get("og:title") or "".join(reader.title_parts).strip()
            return html.unescape(extracted[:MAX_TEXT_CHARS]), title[:200], {
                **reader.meta, "extractor": f"html-{region}"}
    raise ValueError("未提取到可靠的文章正文；知乎登录墙/动态渲染页面请粘贴正文，禁止绕过限制")


def import_article(root: Path, course: str, url: str, raw: bytes, *,
                   title: str = "", content_type: str = "", via: str = "user-article") -> dict:
    url = check_url(url)
    body, detected_title, meta = extract_article(raw, content_type=content_type)
    heading = title or detected_title or urlsplit(url).path.rsplit("/", 1)[-1] or url
    heading = re.sub(r"[\\r\\n\\t]+", " ", heading).strip()[:180] or "Article"
    saved = ext._register(root, course, url, heading, body.encode("utf-8"), via)
    info = read_json(Path(saved["meta"])) or {}
    info.update({"source_type": "web-article", "extraction": meta["extractor"],
                 "published_at": meta.get("article:published_time") or None,
                 "author": meta.get("author") or None, "chars": len(body)})
    write_json_atomic(Path(saved["meta"]), info)
    return {"course": course, "title": heading, "url": url, "chars": len(body),
            "source": saved["registered"], "meta": saved["meta"],
            "trusted": False, "mastery_recorded": False}


def import_text(root: Path, course: str, url: str, text: str, title: str = "") -> dict:
    if not isinstance(text, str):
        raise ValueError("正文必须是文本")
    return import_article(root, course, url, text.encode("utf-8"), title=title,
                          content_type="text/plain", via="user-pasted-article")


def fetch_article(root: Path, course: str, url: str, *,
                  authorize: bool = False, title: str = "") -> dict:
    url = check_url(url)
    if not authorize or not ext.authorized():
        raise PermissionError("联网需要本次操作的明确授权，以及 SOCRATOPIA_EXTERNAL=1")
    # Restricted origins must not be accessed using cookies, login sessions, or browser tricks.
    try:
        with ext._open_https(url, timeout=20) as response:
            raw = response.read(MAX_INPUT_BYTES + 1)
            mime = getattr(getattr(response, "headers", None), "get", lambda k, d="": d)(
                "Content-Type", "")
    except Exception as exc:
        raise ValueError("网页无法直接读取；可复制正文后使用离线导入") from exc
    return import_article(root, course, url, raw, title=title,
                          content_type=mime, via="authorized-web-fetch")


def study_outline(root: Path, course: str, url: str) -> dict:
    url = check_url(url)
    folder = safe_child_path(textbook_dir(root, course), "SOURCES", "_external")
    found = []
    if folder.is_dir():
        for meta_path in folder.glob("*.meta.json"):
            meta = read_json(meta_path)
            if meta and meta.get("url") == url and meta.get("source_type") == "web-article":
                source = safe_child_path(folder, meta_path.name.removesuffix(".meta.json") + ".md")
                if source.is_file():
                    found.append((meta, source))
    if not found:
        raise ValueError("这篇文章尚未导入当前课程")
    info, path = found[-1]
    text = path.read_text(encoding="utf-8")
    headings = [re.sub(r"^#+\s*", "", line).strip() for line in text.splitlines()
                if re.match(r"^#{1,4}\s+\S", line)][:10]
    return {"course": course, "title": info["title"], "url": url,
            "source": str(path), "headings": headings,
            "study_steps": ["指出文章核心论点及来源", "区分事实、观点与证据",
                            "对照当前主教材寻找冲突或补充",
                            "用自己的话解释并回答一题迁移问题"],
            "note": "这是学习提纲，不代表已授课、核验或掌握；需要人工/模型按正文进一步提问。"}


def main() -> int:
    parser = argparse.ArgumentParser(description="导入网页文章到课程 SOURCES（默认不联网）")
    parser.add_argument("command", choices=["plan", "import", "fetch", "study"])
    parser.add_argument("--course", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--authorize", action="store_true")
    args = parser.parse_args()
    if args.command == "plan":
        result = {"course": args.course, "url": check_url(args.url),
                  "offline": True, "target": str(ext._external_dir(ROOT, args.course)),
                  "changes": ["SOURCES/_external"], "not_changed": ["book.md", "PROGRESS.md"]}
    elif args.command == "import":
        if args.file is None:
            parser.error("离线导入必须指定 --file（HTML、Markdown 或纯文本）")
        if args.file.stat().st_size > MAX_INPUT_BYTES:
            parser.error("文件超出 10 MiB 上限")
        result = import_article(ROOT, args.course, args.url, args.file.read_bytes(), title=args.title)
    elif args.command == "fetch":
        result = fetch_article(ROOT, args.course, args.url, authorize=args.authorize, title=args.title)
    else:
        result = study_outline(ROOT, args.course, args.url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
