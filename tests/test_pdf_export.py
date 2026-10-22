from io import BytesIO

import pytest

from report_generator import pdf_export
from report_generator.document_builder import build_structured_report
from report_generator.pdf_export import (
    docx_to_pdf_bytes,
    find_libreoffice,
    is_pdf_export_available,
)
from report_generator.report_schema import Section, StructuredReport

needs_libreoffice = pytest.mark.skipif(
    find_libreoffice() is None, reason="LibreOffice is not installed"
)


def make_docx_bytes():
    report = StructuredReport(
        title="Solar Power",
        sections=[Section(heading="Introduction", content="Sunlight is free.")],
    )
    config = {
        "report_title": "",
        "font_name": "Times New Roman",
        "font_size": 12,
        "margins": {"top": 1, "bottom": 1, "left": 1, "right": 1},
    }
    buffer = BytesIO()
    build_structured_report(report, config, buffer)

    return buffer.getvalue()


def test_missing_libreoffice_gives_clear_error(monkeypatch):
    monkeypatch.setattr(pdf_export, "find_libreoffice", lambda: None)

    assert pdf_export.is_pdf_export_available() is False

    with pytest.raises(RuntimeError, match="LibreOffice"):
        pdf_export.docx_to_pdf_bytes(b"PK-pretend-docx")


@needs_libreoffice
def test_real_conversion_produces_a_pdf():
    assert is_pdf_export_available()

    pdf = docx_to_pdf_bytes(make_docx_bytes())

    assert pdf.startswith(b"%PDF")


def test_non_docx_input_is_rejected():
    with pytest.raises(ValueError, match="not a valid Word"):
        docx_to_pdf_bytes(b"this is not a word document")
