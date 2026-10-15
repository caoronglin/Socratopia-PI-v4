"""Per-course per-task model routing and finite budgets."""
from pathlib import Path
import pytest
from platform_api.course_harness import routes, choose, assign

def test_models_are_isolated_and_bounded(tmp_path, monkeypatch):
    for name in ("甲课", "乙课"):
        (tmp_path / "DATA" / name / "runtime").mkdir(parents=True)
    monkeypatch.setenv("SOCRATOPIA_MODEL", "base-model")
    assign(tmp_path, "甲课", "teach", "model-A")
    assert choose(tmp_path, "甲课", "teach")["model"] == "model-A"
    assert choose(tmp_path, "乙课", "teach")["model"] == "base-model"
    assert choose(tmp_path, "甲课", "tutor")["max_iterations"] == 1
    assert all(not x["can_write_course"] for x in routes(tmp_path, "甲课")["roles"].values())
    with pytest.raises(ValueError):
        assign(tmp_path, "甲课", "teach", "bad model with spaces")
    with pytest.raises(ValueError):
        choose(tmp_path, "甲课", "unlimited")
