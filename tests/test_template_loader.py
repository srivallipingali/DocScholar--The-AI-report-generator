
import json
import pytest

from report_generator.template_loader import load_templates


def test_load_valid_templates(tmp_path):
    template_path = tmp_path / "templates.json"

    templates = {
        "Academic Report": {
            "font_name": "Times New Roman",
            "font_size": 12,
            "title_font_size": 18,
            "heading_font_size": 14,
            "margins": {
                "top": 1,
                "bottom": 1,
                "left": 1,
                "right": 1,
            },
        }
    }

    template_path.write_text(
        json.dumps(templates),
        encoding="utf-8",
    )

    result = load_templates(template_path)

    assert "Academic Report" in result
    assert result["Academic Report"]["font_size"] == 12


def test_missing_template_file():
    with pytest.raises(FileNotFoundError):
        load_templates("missing_templates.json")


def test_invalid_template_json(tmp_path):
    template_path = tmp_path / "templates.json"
    template_path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid template configuration"):
        load_templates(template_path)


def test_missing_template_setting(tmp_path):
    template_path = tmp_path / "templates.json"
    template_path.write_text(
        json.dumps({"Academic Report": {"font_name": "Arial"}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing"):
        load_templates(template_path)
