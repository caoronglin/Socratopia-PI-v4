"""Single-AgentScope runtime and pedagogical trust contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def test_no_host_specific_agent_installation():
    for path in (".pi", ".claude", "runtimes/pi", "integrations/cherry-studio"):
        assert not (ROOT / path).exists(), path

def test_single_agent_execution_and_no_authoritative_model_edits():
    rules = read("AGENTS.md")
    server = read("platform_api/app.py")
    runtime = read("platform_api/agentscope_runtime.py")
    for key in ("AgentScope 2.0.10", "2700", "PROGRESS.md", "SHA", "课程隔离"):
        assert key in rules
    assert "raw = await ask_agent(name, prompt)" in server
    assert "generate_tutor_turn(" in server
    assert "from agentscope.agent import Agent, ReActConfig" in runtime
    assert 'ReActConfig(max_iters=' in runtime

def test_source_checks_are_deterministic():
    grounding = read("platform_api/grounding.py")
    assert "fact_verified" in grounding
    assert "source_id" in grounding
    assert "quote.strip() not in by_id[sid]" in grounding
    assert "mastery_updated" in grounding

def test_pedagogy_resources_preserved_without_runtime_sdk():
    for module in ("socratopia-learning", "socratopia-tutor", "socratopia-engineering"):
        assert (ROOT / "education" / "skills" / module / "SKILL.md").is_file()
    assert len(list((ROOT / "education/prompts").glob("*.md"))) == 7
