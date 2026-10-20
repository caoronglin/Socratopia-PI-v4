"""AgentScope-only v5 runtime and distribution contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_second_model_gateway_or_runtime():
    assert not (ROOT / "runtimes/pi").exists()
    assert not (ROOT / "platform_api/pi_gateway.py").exists()
    app = (ROOT / "platform_api/app.py").read_text(encoding="utf-8")
    assert "from platform_api.agentscope_runtime import" in app
    assert "raw = await ask_agent(name, prompt)" in app
    desktop = (ROOT / "platform_api/desktop.py").read_text(encoding="utf-8")
    assert "_start_pi(" not in desktop
    assert "uvicorn.run(app" in desktop


def test_package_includes_only_server_and_frontend():
    package = (ROOT / "scripts/package_web_v5.py").read_text(encoding="utf-8")
    assert "runtimes/pi" not in package
    assert "node_modules" not in package
    assert "runtime/" not in package
    assert 'entries: dict[str, Path] = {executable.name: executable}' in package


def test_agent_scope_version_and_course_isolation():
    config = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    runtime = (ROOT / "platform_api/agentscope_runtime.py").read_text(encoding="utf-8")
    assert "agentscope==2.0.10" in config
    assert 'sdk_version": "2.0.10"' in runtime
    assert "if scope in _active:" in runtime
    assert "MAX_IN_FLIGHT = 4" in runtime
