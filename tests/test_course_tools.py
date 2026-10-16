"""AgentScope 2.0 native toolkit registration must not leak tools by default."""
import sys
import asyncio
import pytest
if sys.version_info < (3, 15):
    pytest.skip("Requires AgentScope 2 and Python 3.15", allow_module_level=True)

from platform_api.course_tools import build_toolkit

def test_toolkit_opt_in_and_course_scope(tmp_path):
    for course in ("课程A", "课程B"):
        (tmp_path/"TEXTBOOK"/course).mkdir(parents=True)
        (tmp_path/"TEXTBOOK"/course/"book.md").write_text(
            "# "+course+"\\n## 基础概念\\n教材证据\\n", encoding="utf-8")
    empty = build_toolkit(tmp_path, "课程A", graph_enabled=False)
    assert not asyncio.run(empty.get_tool_schemas())
    registered = build_toolkit(tmp_path, "课程A", graph_enabled=True)
    schemas = asyncio.run(registered.get_tool_schemas())
    assert len(schemas) == 2
    assert "course_outline" in str(schemas)
    assert "course_learning_evidence" in str(schemas)
    assert "execute_shell_command" not in str(schemas)
    assert "课程B" not in str(schemas)
