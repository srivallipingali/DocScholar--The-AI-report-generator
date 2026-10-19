
import json
import pytest

from report_generator.config_loader import load_config


def test_load_valid_config(tmp_path):
    config_path = tmp_path / "config.json"

    config = {
        "report_title": "Generated Report",
        "font_name": "Arial",
        "font_size": 12,
        "margins": {
            "top": 1,
            "bottom": 1,
            "left": 1,
            "right": 1
        }
    }

    config_path.write_text(
        json.dumps(config),
        encoding="utf-8"
    )

    result = load_config(config_path)

    assert result["report_title"] == "Generated Report"
    assert result["font_name"] == "Arial"


def test_missing_config_file():
    with pytest.raises(FileNotFoundError):
        load_config("missing_config.json")


def test_invalid_json(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_config(config_path)


def test_missing_required_setting(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"report_title": "Test"}),
        encoding="utf-8"
    )

    with pytest.raises(ValueError, match="Missing required"):
        load_config(config_path)
