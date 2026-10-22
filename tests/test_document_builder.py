
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

    assert paragraphs == [
        "Generated Report",
        "Renewable energy comes from natural sources.",
        "Solar panels convert sunlight into electricity.",
    ]
    assert document.paragraphs[1].style.name != "Heading 1"


def test_build_report_requires_a_separate_title(tmp_path):
    config = sample_config()
    config["report_title"] = ""

    with pytest.raises(ValueError, match="report title is required"):
        build_report(
            "First line is report content.",
            config,
            tmp_path / "report.docx",
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


def test_structured_report_with_cover_page_and_index(tmp_path):
    output_path = tmp_path / "full_featured.docx"
    config = sample_config()
    config["report_title"] = ""
    config["include_cover_page"] = True
    config["include_index"] = True
    config["section_per_page"] = True
    config["author"] = "Research Team"
    config["template_name"] = "Academic Report"

    report = StructuredReport(
        title="Solar Power Future",
        subtitle="A Technical Evaluation",
        abstract="Executive overview of solar photovoltaics.",
        sections=[
            Section(heading="Introduction", content="Solar energy is growing."),
            Section(heading="Efficiency", content="Modern panels reach 24%."),
            Section(heading="Conclusion", content="Solar adoption is essential."),
        ],
    )

    build_structured_report(report, config, output_path)

    doc = Document(output_path)
    all_text = " ".join(p.text for p in doc.paragraphs)

    # Verify Cover Page items
    assert "ACADEMIC REPORT" in all_text
    assert "Solar Power Future" in all_text
    assert "A Technical Evaluation" in all_text
    assert "Executive overview of solar photovoltaics." in all_text
    assert "Prepared by: Research Team" in all_text

    # Verify Table of Contents
    assert "Table of Contents" in all_text
    assert "Introduction" in all_text
    assert "Efficiency" in all_text
    assert "Conclusion" in all_text

    # Verify page breaks (each topic on a new page)
    # In docx, page breaks are rendered as w:br w:type="page" or in runs
    page_break_count = sum(
        1 for p in doc.paragraphs
        for run in p.runs
        if "w:br" in run._r.xml and 'w:type="page"' in run._r.xml
    )
    # At least 4 page breaks: after cover, after index, after section 1, after section 2
    assert page_break_count >= 4
