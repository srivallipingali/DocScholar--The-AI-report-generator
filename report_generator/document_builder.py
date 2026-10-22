
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from report_generator.docx_fields import (
    add_page_number_footer,
    add_table_of_contents,
    enable_update_fields_on_open,
)


def _prepare_output(output_path):
    """Create the output folder if a file path was given.

    The app passes an in-memory BytesIO instead of a path, so only real
    paths need a folder.
    """

    if isinstance(output_path, (str, Path)):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    return output_path


def _set_font(style, font_name):
    """Set a style's font, overriding Word's built-in theme font.

    Styles like Title and Heading 1 point at the document's *theme* font
    (via asciiTheme etc.). Those theme attributes win over a plain font
    name, so just writing style.font.name leaves the heading in the theme
    font (Calibri-like). We set the name and then delete the theme
    attributes so the chosen font is actually used.
    """

    style.font.name = font_name

    fonts = style.element.rPr.rFonts
    fonts.set(qn("w:eastAsia"), font_name)

    for attribute in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if fonts.get(qn(attribute)) is not None:
            del fonts.attrib[qn(attribute)]


def _create_styled_document(config):
    """Create an empty Word document with the template's formatting applied.

    Both build_report (plain text) and build_structured_report (AI sections)
    start from this, so the look of a template is defined in exactly one
    place.
    """

    document = Document()

    # Page margins.
    margins = config["margins"]

    for section in document.sections:
        section.top_margin = Inches(margins["top"])
        section.bottom_margin = Inches(margins["bottom"])
        section.left_margin = Inches(margins["left"])
        section.right_margin = Inches(margins["right"])

    # Default font for normal paragraphs.
    font_name = config["font_name"]
    font_size = config["font_size"]

    normal_style = document.styles["Normal"]
    _set_font(normal_style, font_name)
    normal_style.font.size = Pt(font_size)

    # Main report title style.
    title_style = document.styles["Title"]
    _set_font(title_style, font_name)
    title_style.font.size = Pt(
        config.get("title_font_size", 18)
    )
    title_style.font.bold = True

    # Section heading style.
    heading_style = document.styles["Heading 1"]
    _set_font(heading_style, font_name)
    heading_style.font.size = Pt(
        config.get("heading_font_size", 14)
    )
    heading_style.font.bold = True

    return document


def _add_paragraphs(document, body):
    """Split body text on blank lines and add each block as a paragraph.

    Line breaks inside a block are joined with spaces so text copied from a
    PDF (which breaks lines mid-sentence) flows as normal paragraphs.
    """

    for paragraph in body.split("\n\n"):
        cleaned_paragraph = " ".join(
            line.strip()
            for line in paragraph.splitlines()
            if line.strip()
        )

        if cleaned_paragraph:
            document.add_paragraph(cleaned_paragraph)


def _save(document, output_path):
    """Save the document and return the same path (or BytesIO) it was given."""

    document.save(output_path)

    return output_path


def build_report(text, config, output_path):
    """
    Create a formatted Word report from plain text (no AI involved).

    The first line of the text becomes a heading and the rest becomes
    paragraphs.
    """

    if not text or not text.strip():
        raise ValueError("Cannot generate a report from empty text.")

    output_path = _prepare_output(output_path)
    document = _create_styled_document(config)

    document.add_paragraph(
        config["report_title"],
        style="Title"
    )

    lines = text.strip().splitlines()
    document.add_heading(lines[0].strip(), level=1)

    body = "\n".join(lines[1:]).strip()

    if body:
        _add_paragraphs(document, body)

    return _save(document, output_path)


def build_structured_report(
    report,
    config,
    output_path,
    include_toc=False,
    page_numbers=False,
):
    """
    Create a formatted Word report from a StructuredReport (the AI path).

    `report` is a report_schema.StructuredReport: a title plus a list of
    sections, each with a heading and content. Each section becomes a
    Heading 1 followed by its paragraphs.

    config["report_title"], if present and non-empty, overrides the title
    chosen by the AI, so a title typed by the user always wins.

    include_toc:  add a table of contents (and ask Word to fill in its page
                  numbers when the file is opened).
    page_numbers: add "Page N" to the footer of every page.
    """

    if not report.sections:
        raise ValueError("Cannot generate a report with no sections.")

    output_path = _prepare_output(output_path)
    document = _create_styled_document(config)

    title = (config.get("report_title") or "").strip() or report.title

    document.add_paragraph(title, style="Title")

    if include_toc:
        add_table_of_contents(
            document,
            [section.heading for section in report.sections],
            heading_size=config.get("heading_font_size", 14),
        )
        enable_update_fields_on_open(document)

    if page_numbers:
        add_page_number_footer(document)

    for section in report.sections:
        document.add_heading(section.heading, level=1)
        _add_paragraphs(document, section.content)

    return _save(document, output_path)
