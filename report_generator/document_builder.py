
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


def _add_word_field(paragraph, instruction, displayed_text=""):
    """Add a Word field that can be recalculated when the document is opened."""
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    paragraph._p.append(begin)

    field_instruction = OxmlElement("w:instrText")
    field_instruction.set(qn("xml:space"), "preserve")
    field_instruction.text = f" {instruction} "
    paragraph._p.append(field_instruction)

    separator = OxmlElement("w:fldChar")
    separator.set(qn("w:fldCharType"), "separate")
    paragraph._p.append(separator)

    if displayed_text:
        paragraph.add_run(displayed_text)

    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    paragraph._p.append(end)


def _add_table_of_contents(document):
    document.add_paragraph("Table of Contents", style="Title")
    document.add_paragraph(
        "Update this table in Word or LibreOffice if entries or page numbers "
        "are not populated."
    )
    toc_paragraph = document.add_paragraph()
    _add_word_field(
        toc_paragraph,
        r'TOC \o "1-2" \h \z \u',
        "Update this field to populate the table of contents.",
    )
    document.add_page_break()


def _add_page_numbers(document):
    for section in document.sections:
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.add_run("Page ")
        _add_word_field(footer, "PAGE", "1")

    update_fields = OxmlElement("w:updateFields")
    update_fields.set(qn("w:val"), "true")
    document.settings.element.append(update_fields)


def build_report(text, config, output_path):
    """
    Create a formatted Word report using the supplied configuration.
    """

    # 1. Validate the input text.
    if not text or not text.strip():
        raise ValueError("Cannot generate a report from empty text.")

    if isinstance(output_path, (str, Path)):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # 2. Create a new Word document.
    document = Document()

    # 3. Apply page margins.
    margins = config["margins"]

    for section in document.sections:
        section.top_margin = Inches(margins["top"])
        section.bottom_margin = Inches(margins["bottom"])
        section.left_margin = Inches(margins["left"])
        section.right_margin = Inches(margins["right"])

    # 4. Apply the default font to normal paragraphs.
    font_name = config["font_name"]
    font_size = config["font_size"]

    normal_style = document.styles["Normal"]
    normal_style.font.name = font_name
    normal_style.font.size = Pt(font_size)

    # 5. Configure the main report title style.
    title_style = document.styles["Title"]
    title_style.font.name = font_name
    title_style.font.size = Pt(
        config.get("title_font_size", 18)
    )
    title_style.font.bold = True

    # 6. Configure the section heading style.
    heading_style = document.styles["Heading 1"]
    heading_style.font.name = font_name
    heading_style.font.size = Pt(
        config.get("heading_font_size", 14)
    )
    heading_style.font.bold = True

    # 7. Add the main report title.
    document.add_paragraph(
        config["report_title"],
        style="Title"
    )

    _add_table_of_contents(document)
    _add_page_numbers(document)

    # Use the first line of the supplied text as the first numbered heading.
    lines = text.strip().splitlines()
    source_title = lines[0].strip()

    document.add_heading(
        f"1. {source_title}",
        level=1
    )

    # 9. Add the remaining content as paragraphs.
    body = "\n".join(lines[1:]).strip()

    if body:
        paragraphs = body.split("\n\n")

        for paragraph in paragraphs:
            cleaned_paragraph = " ".join(
                line.strip()
                for line in paragraph.splitlines()
                if line.strip()
            )

            if cleaned_paragraph:
                document.add_paragraph(cleaned_paragraph)

    # 10. Save the Word document.
    document.save(output_path)

    if isinstance(output_path, (str, Path)):
        return Path(output_path)

    return output_path


def build_structured_report(outline, config, output_path):
    """Build a formatted Word report from Gemini's structured outline."""
    if not isinstance(outline, dict) or not isinstance(outline.get("sections"), list):
        raise ValueError("The AI report outline has an invalid format.")

    if isinstance(output_path, (str, Path)):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    document = Document()
    margins = config["margins"]

    for section in document.sections:
        section.top_margin = Inches(margins["top"])
        section.bottom_margin = Inches(margins["bottom"])
        section.left_margin = Inches(margins["left"])
        section.right_margin = Inches(margins["right"])

    font_name = config["font_name"]
    normal_style = document.styles["Normal"]
    normal_style.font.name = font_name
    normal_style.font.size = Pt(config["font_size"])

    title_style = document.styles["Title"]
    title_style.font.name = font_name
    title_style.font.size = Pt(config.get("title_font_size", 18))
    title_style.font.bold = True

    heading_style = document.styles["Heading 1"]
    heading_style.font.name = font_name
    heading_style.font.size = Pt(config.get("heading_font_size", 14))
    heading_style.font.bold = True

    heading_two_style = document.styles["Heading 2"]
    heading_two_style.font.name = font_name
    heading_two_style.font.size = Pt(config.get("subheading_font_size", 12))
    heading_two_style.font.bold = True

    report_title = str(outline.get("title") or config["report_title"]).strip()
    document.add_paragraph(report_title, style="Title")
    _add_table_of_contents(document)
    _add_page_numbers(document)

    section_number = 0
    for section_data in outline["sections"]:
        if not isinstance(section_data, dict):
            continue

        heading = str(section_data.get("heading") or "").strip()
        content = str(section_data.get("content") or "").strip()

        if heading:
            section_number += 1
            document.add_heading(f"{section_number}. {heading}", level=1)

        if content:
            for paragraph in content.split("\n\n"):
                paragraph = paragraph.strip()
                if paragraph:
                    document.add_paragraph(paragraph)

        subsections = section_data.get("subsections", [])
        if isinstance(subsections, list):
            subsection_number = 0
            for subsection in subsections:
                if not isinstance(subsection, dict):
                    continue
                subheading = str(subsection.get("heading") or "").strip()
                subcontent = str(subsection.get("content") or "").strip()
                if subheading:
                    subsection_number += 1
                    document.add_heading(
                        f"{section_number or 1}.{subsection_number} {subheading}",
                        level=2,
                    )
                if subcontent:
                    for paragraph in subcontent.split("\n\n"):
                        paragraph = paragraph.strip()
                        if paragraph:
                            document.add_paragraph(paragraph)

    references = outline.get("references", [])
    if isinstance(references, list) and references:
        section_number += 1
        document.add_heading(f"{section_number}. References", level=1)
        for reference in references:
            if isinstance(reference, dict):
                reference_text = str(
                    reference.get("text")
                    or reference.get("title")
                    or reference.get("url")
                    or ""
                ).strip()
            else:
                reference_text = str(reference).strip()
            if reference_text:
                document.add_paragraph(reference_text, style="List Number")

    document.save(output_path)
    if isinstance(output_path, (str, Path)):
        return Path(output_path)
    return output_path
