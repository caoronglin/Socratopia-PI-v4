"""Focused structured PREP validation without invoking a model provider."""
import pytest
from platform_api import prep_sections, prep_editor


def test_sections_only_known_headings():
    body = "## 教学评一致性\n第一问\n\n## 资料来源\n不可改\n\n## 预期误概念\n证据\n"
    assert prep_sections.sections(body) == {"教学评一致性": "第一问", "预期误概念": "证据"}


def test_duplicate_section_rejected():
    with pytest.raises(prep_editor.DraftEditorError):
        prep_sections.sections("## 教学评一致性\na\n## 教学评一致性\nb\n")


@pytest.mark.parametrize("updates", [
    {"任意字段": "text"},
    {"教学评一致性": "## 非法标题"},
    {"教学评一致性": "---"},
    {"教学评一致性": "\x00"},
])
def test_invalid_updates_do_not_write(tmp_path, updates):
    with pytest.raises(prep_editor.DraftEditorError):
        prep_sections.save(tmp_path, "unused", "unused", updates, "0" * 64)
