"""Thin authenticated bridge to Pi SDK: Pi alone owns the native model loop.

The Python course supervisor owns the source checks and persistent memory.
Nothing in this module initiates a parallel tool or autonomous agent loop.
"""
from __future__ import annotations

import os
from threading import Lock
from urllib.parse import urlsplit

import httpx

from scripts.lib.repository import validate_course_name

MAX_PROMPT = 16_000
MAX_REPLY = 32_000
MAX_CONCURRENT = 4
_guard = Lock()
_active: set[str] = set()


class PiUnavailable(RuntimeError):
    """Pi could not complete a model turn."""


def _gateway_url() -> str:
    raw = os.environ.get("SOCRATOPIA_PI_URL", "http://127.0.0.1:8787").strip()
    parsed = urlsplit(raw)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.fragment or parsed.query
            or parsed.path not in ("", "/") or not parsed.port):
        raise PiUnavailable("Pi gateway must use a loopback HTTP endpoint")
    return raw.rstrip("/")


def runtime_status() -> dict:
    # Configuration does NOT attest that a model/provider is available.
    return {
        "backend": "pi",
        "collaboration_backend": "agentscope",
        "configured": bool(os.environ.get("SOCRATOPIA_API_TOKEN")),
        "model": "Pi SDK selected model",
        "model_credentials_verified": False,
        "max_concurrent_turns": MAX_CONCURRENT,
        "verified_history": "course-scoped-sqlite",
    }


async def ask_pi(course: str, prompt: str) -> str:
    validate_course_name(course)
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT:
        raise PiUnavailable("Invalid or excessive Pi prompt")
    token = os.environ.get("SOCRATOPIA_API_TOKEN", "")
    if len(token) < 16:
        raise PiUnavailable("Pi gateway token is not configured")
    endpoint = _gateway_url()
    with _guard:
        if course in _active:
            raise PiUnavailable("A Pi turn is already running in this course")
        if len(_active) >= MAX_CONCURRENT:
            raise PiUnavailable("Pi gateway is at capacity")
        _active.add(course)
    try:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(95.0, connect=3.0)) as client:
                result = await client.post(
                    endpoint + "/internal/reply",
                    headers={"Authorization": "Bearer " + token},
                    json={"course": course, "prompt": prompt},
                )
        except (httpx.HTTPError, OSError) as exc:
            raise PiUnavailable("Pi gateway unavailable or timed out") from exc
        if result.status_code != 200:
            raise PiUnavailable("Pi request failed (HTTP " + str(result.status_code) + ")")
        try:
            answer = result.json()["text"]
        except (ValueError, KeyError, TypeError) as exc:
            raise PiUnavailable("Pi response is malformed") from exc
        if not isinstance(answer, str) or not answer.strip() or len(answer) > MAX_REPLY:
            raise PiUnavailable("Pi response is empty or excessive")
        return answer
    finally:
        with _guard:
            _active.discard(course)
