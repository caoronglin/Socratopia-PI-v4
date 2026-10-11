"""Typed, authenticated bridge to the local embedded Pi Node.js SDK service."""
from __future__ import annotations

import os
from urllib.parse import urlsplit
from typing import Any

import httpx


class PiUnavailable(RuntimeError):
    """Pi failed or is not configured; do not invent a lesson response."""


async def ask_pi(course: str, prompt: str) -> str:
    token = os.getenv("SOCRATOPIA_API_TOKEN", "")
    if not token:
        raise PiUnavailable("SOCRATOPIA_API_TOKEN is not configured")
    # Fixed loopback target; neither the URL nor cwd is controlled by the learner.
    url = os.getenv("SOCRATOPIA_PI_URL", "http://127.0.0.1:8787")
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise PiUnavailable("Invalid Pi gateway port") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.username is not None
        or parsed.password is not None
        or port is None
        or parsed.path not in {"", "/"}
        or parsed.query or parsed.fragment
    ):
        raise PiUnavailable("Pi gateway URL must be an exact loopback HTTP origin")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=5)) as client:
            response = await client.post(
                url.rstrip("/") + "/internal/reply",
                json={"course": course, "prompt": prompt},
                headers={"Authorization": "Bearer " + token},
            )
            if response.status_code == 409:
                raise PiUnavailable("The course already has an active Pi turn")
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            text = payload.get("text")
            if not isinstance(text, str) or not text.strip():
                raise PiUnavailable("Pi returned no assistant text")
            return text
    except (httpx.HTTPError, ValueError) as exc:
        raise PiUnavailable("Pi gateway failed or model credentials are missing") from exc
