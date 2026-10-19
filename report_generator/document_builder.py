
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt


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

    # 8. Use the first line of the supplied text as a heading.
    lines = text.strip().splitlines()
    source_title = lines[0].strip()

    document.add_heading(
        source_title,
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

