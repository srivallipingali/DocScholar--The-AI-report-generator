from io import BytesIO

from docx import Document
import pytest

from report_generator.document_builder import (
    build_report,
    build_structured_report,
)


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
    assert "1. Renewable Energy" in paragraphs
    assert (
        "Renewable energy comes from natural sources."
        in paragraphs
    )
    assert "1. Renewable Energy" in paragraphs
    assert "Table of Contents" in paragraphs

    document_xml = document._element.xml
    assert 'TOC \\o "1-2" \\h \\z \\u' in document_xml
    assert "Update this field to populate the table of contents." in document_xml
    assert " PAGE " in document.sections[0].footer._element.xml
    assert 'w:val="true"' in document.settings.element.xml


def test_empty_text_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="empty text"):
        build_report(
            "   ",
            sample_config(),
            tmp_path / "report.docx"
        )


def test_build_structured_report_adds_numbered_headings_and_word_fields():
    output = BytesIO()
    outline = {
        "title": "Renewable Energy",
        "sections": [
            {
                "heading": "Introduction",
                "content": "Overview.",
                "subsections": [
                    {"heading": "Background", "content": "Context."},
                ],
            },
            {
                "heading": "Conclusion",
                "content": "Summary.",
            },
        ],
        "references": ["Source one"],
    }

    result = build_structured_report(outline, sample_config(), output)

    assert result is output
    output.seek(0)
    document = Document(output)
    paragraphs = [paragraph.text for paragraph in document.paragraphs]

    assert "1. Introduction" in paragraphs
    assert "1.1 Background" in paragraphs
    assert "2. Conclusion" in paragraphs
    assert "3. References" in paragraphs
    assert "Table of Contents" in paragraphs
    assert 'TOC \\o "1-2" \\h \\z \\u' in document._element.xml
    assert " PAGE " in document.sections[0].footer._element.xml
    assert 'w:val="true"' in document.settings.element.xml
