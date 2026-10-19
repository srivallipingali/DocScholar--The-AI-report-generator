
from docx import Document
import pytest

from report_generator.document_builder import build_report


def sample_config():
    return {
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


def test_build_report(tmp_path):
    output_path = tmp_path / "report.docx"

    text = (
        "Renewable Energy\n\n"
        "Renewable energy comes from natural sources.\n\n"
        "Solar panels convert sunlight into electricity."
    )

    result = build_report(
        text,
        sample_config(),
        output_path
    )

    assert result == output_path
    assert output_path.is_file()

    document = Document(output_path)

    paragraphs = [
        paragraph.text for paragraph in document.paragraphs
    ]

    assert "Generated Report" in paragraphs
    assert "Renewable Energy" in paragraphs
    assert (
        "Renewable energy comes from natural sources."
        in paragraphs
    )


def test_empty_text_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="empty text"):
        build_report(
            "   ",
            sample_config(),
            tmp_path / "report.docx"
        )
