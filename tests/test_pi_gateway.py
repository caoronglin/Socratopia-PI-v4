"""Regression gates for the thin Pi bridge: no external agent loop or tool access."""
import asyncio
import json
from pathlib import Path

import httpx
import pytest

from platform_api import pi_gateway as pi


@pytest.mark.parametrize("address", [
    "http://example.com:8787", "https://127.0.0.1:8787",
    "http://user:secret@127.0.0.1:8787",
    "http://127.0.0.1:8787/elsewhere",
    "http://127.0.0.1:8787/?redirect=x",
])
def test_gateway_rejects_nonlocal_or_ambiguous_addresses(monkeypatch, address):
    monkeypatch.setenv("SOCRATOPIA_PI_URL", address)
    with pytest.raises(pi.PiUnavailable):
        pi._gateway_url()


def test_unconfigured_request_never_dials(monkeypatch):
    monkeypatch.delenv("SOCRATOPIA_API_TOKEN", raising=False)
    with pytest.raises(pi.PiUnavailable):
        asyncio.run(pi.ask_pi("遗传学", "请解释减数分裂"))


def test_native_pi_authenticated_turn_and_liveness(monkeypatch):
    monkeypatch.setenv("SOCRATOPIA_API_TOKEN", "test-only-token-with-length")
    monkeypatch.setenv("SOCRATOPIA_PI_URL", "http://127.0.0.1:8787")
    original = httpx.AsyncClient
    observed = []
    def handler(request):
        observed.append((request.method, request.url.path,
                         request.headers.get("Authorization", "")))
        if request.url.path == "/internal/health":
            return httpx.Response(200, json={"gateway": "pi", "ready": True})
        data = json.loads(request.content)
        assert data == {"course": "遗传学", "prompt": "教材的问题"}
        return httpx.Response(200, json={"text": "课程已核验结果"})
    def client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)
    monkeypatch.setattr(pi.httpx, "AsyncClient", client)

    async def exercise():
        assert await pi.ping_pi() is True
        assert await pi.ask_pi("遗传学", "教材的问题") == "课程已核验结果"
    asyncio.run(exercise())
    assert [path for _, path, _ in observed] == ["/internal/health", "/internal/reply"]
    assert all(value == "Bearer test-only-token-with-length" for _, _, value in observed)
    assert not pi._active


def test_sdk_loop_is_owned_by_pi():
    node_source = (Path(__file__).resolve().parents[1] / "runtimes/pi/server.mjs").read_text()
    assert "SessionManager.inMemory" in node_source
    assert "await session.prompt(prompt)" in node_source
    assert "noTools: 'all'" in node_source
    assert "runNativeTurn" in node_source
    assert "continueRecent" not in node_source
