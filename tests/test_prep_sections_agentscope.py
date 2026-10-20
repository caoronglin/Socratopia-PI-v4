"""Focused structured PREP validation without invoking a model provider."""
import pytest
from platform_api import prep_sections, prep_editor


def test_sections_only_known_headings():
    body = "## 问题链\n第一问\n\n## 资料来源\n不可改\n\n## 预期证据\n证据\n"
    assert prep_sections.sections(body) == {"问题链": "第一问", "预期证据": "证据"}


def test_duplicate_section_rejected():
    with pytest.raises(prep_editor.DraftEditorError):
        prep_sections.sections("## 问题链\na\n## 问题链\nb\n")


@pytest.mark.parametrize("updates", [
    {"任意字段": "text"},
    {"问题链": "## 非法标题"},
    {"问题链": "---"},
    {"问题链": "\x00"},
])
def test_invalid_updates_do_not_write(tmp_path, updates):
    with pytest.raises(prep_editor.DraftEditorError):
        prep_sections.save(tmp_path, "unused", "unused", updates, "0" * 64)
