
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


# ---------- build_structured_report (the AI path) ----------

from io import BytesIO

from report_generator.document_builder import build_structured_report
from report_generator.report_schema import Section, StructuredReport


def sample_report():
    return StructuredReport(
        title="AI Chosen Title",
        sections=[
            Section(
                heading="Introduction",
                content="First paragraph.\n\nSecond paragraph.",
            ),
            Section(heading="Conclusion", content="The end."),
        ],
    )


def test_structured_report_contains_headings_and_paragraphs(tmp_path):
    output_path = tmp_path / "structured.docx"
    config = sample_config()
    config["report_title"] = ""  # no user title -> AI title is used

    build_structured_report(sample_report(), config, output_path)

    document = Document(output_path)
    paragraphs = [p.text for p in document.paragraphs]

    assert paragraphs == [
        "AI Chosen Title",
        "Introduction",
        "First paragraph.",
        "Second paragraph.",
        "Conclusion",
        "The end.",
    ]


def test_structured_report_user_title_overrides_ai_title(tmp_path):
    output_path = tmp_path / "structured.docx"

    build_structured_report(sample_report(), sample_config(), output_path)

    paragraphs = [p.text for p in Document(output_path).paragraphs]

    assert paragraphs[0] == "Generated Report"
    assert "AI Chosen Title" not in paragraphs


def test_structured_report_can_write_to_memory():
    buffer = BytesIO()

    build_structured_report(sample_report(), sample_config(), buffer)

    buffer.seek(0)
    assert len(Document(buffer).paragraphs) > 0
