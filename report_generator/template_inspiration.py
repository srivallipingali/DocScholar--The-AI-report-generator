"""Extract reusable visual and structural cues from DOCX or PDF templates."""

from collections import Counter
from pathlib import Path

import pymupdf
from docx import Document


def _color_hex(color):
    if color is None:
        return None
    try:
        if isinstance(color, int):
            return f"#{color:06X}"
        value = str(color).strip().lstrip("#").upper()
        if len(value) == 6 and all(character in "0123456789ABCDEF" for character in value):
            return f"#{value}"
    except (TypeError, ValueError):
        pass
    return None


def _docx_style(style):
    font = style.font
    return {
        "font_name": font.name,
        "font_size": font.size.pt if font.size else None,
        "color": _color_hex(font.color.rgb if font.color else None),
    }


def _docx_style_if_present(styles, style_name):
    try:
        return _docx_style(styles[style_name])
    except KeyError:
        return {"font_name": None, "font_size": None, "color": None}


def _formatting_from_docx(document):
    styles = document.styles
    normal = _docx_style(styles["Normal"])
    title = _docx_style_if_present(styles, "Title")
    heading = _docx_style_if_present(styles, "Heading 1")
    section = document.sections[0]

    formatting = {}
    if normal["font_name"]:
        formatting["font_name"] = normal["font_name"]
    if normal["font_size"]:
        formatting["font_size"] = normal["font_size"]
    if title["font_name"]:
        formatting["title_font_name"] = title["font_name"]
    if title["font_size"]:
        formatting["title_font_size"] = title["font_size"]
    if heading["font_name"]:
        formatting["heading_font_name"] = heading["font_name"]
    if heading["font_size"]:
        formatting["heading_font_size"] = heading["font_size"]
    if title["color"]:
        formatting["accent_color"] = title["color"]
    elif heading["color"]:
        formatting["accent_color"] = heading["color"]
    if normal["color"]:
        formatting["text_color"] = normal["color"]

    margins = {
        "top": section.top_margin,
        "bottom": section.bottom_margin,
        "left": section.left_margin,
        "right": section.right_margin,
    }
    if all(margins.values()):
        formatting["margins"] = {
            name: round(value.inches, 2) for name, value in margins.items()
        }

    heading_styles = sorted({
        paragraph.style.name
        for paragraph in document.paragraphs
        if paragraph.text.strip()
        and paragraph.style.name.lower().startswith("heading")
    })
    return formatting, heading_styles


def _pdf_spans(page):
    spans = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text:
                    spans.append({
                        "text": text,
                        "font": span.get("font", "").split("+")[-1],
                        "size": float(span.get("size", 0)),
                        "color": _color_hex(span.get("color")),
                        "bbox": span.get("bbox"),
                        "flags": span.get("flags", 0),
                    })
    return spans


def _formatting_from_pdf(document):
    pages = [document[index] for index in range(min(document.page_count, 3))]
    spans = [span for page in pages for span in _pdf_spans(page)]
    if not spans:
        raise ValueError("The PDF template contains no readable text to analyze.")

    size_counts = Counter(round(span["size"], 1) for span in spans)
    largest_size = max(size_counts)
    non_title_counts = {
        size: count for size, count in size_counts.items()
        if size < largest_size
    }
    if non_title_counts:
        most_common_count = max(non_title_counts.values())
        body_size = min(
            size for size, count in non_title_counts.items()
            if count == most_common_count
        )
    else:
        body_size = largest_size
    body_spans = [span for span in spans if round(span["size"], 1) == body_size]
    body_font = Counter(span["font"] for span in body_spans if span["font"]).most_common(1)
    title_size = max(span["size"] for span in spans)
    heading_sizes = [
        span["size"] for span in spans
        if span["size"] > body_size * 1.1 and span["size"] < title_size
    ]
    heading_size = max(heading_sizes) if heading_sizes else body_size
    title_colors = [
        span["color"] for span in spans
        if span["size"] == title_size and span["color"]
    ]
    body_colors = [span["color"] for span in body_spans if span["color"]]

    formatting = {
        "font_size": body_size,
        "title_font_size": title_size,
        "heading_font_size": heading_size,
    }
    if body_font:
        formatting["font_name"] = body_font[0][0]
        formatting["title_font_name"] = body_font[0][0]
        formatting["heading_font_name"] = body_font[0][0]
    if title_colors:
        formatting["accent_color"] = Counter(title_colors).most_common(1)[0][0]
    if body_colors:
        formatting["text_color"] = Counter(body_colors).most_common(1)[0][0]

    page = pages[0]
    first_page_spans = _pdf_spans(page)
    text_boxes = [span["bbox"] for span in first_page_spans if span["bbox"]]
    if text_boxes:
        left = min(box[0] for box in text_boxes)
        top = min(box[1] for box in text_boxes)
        right = page.rect.width - max(box[2] for box in text_boxes)
        bottom = page.rect.height - max(box[3] for box in text_boxes)
        formatting["margins"] = {
            "top": round(max(0.35, min(1.5, top / 72)), 2),
            "bottom": round(max(0.35, min(1.5, bottom / 72)), 2),
            "left": round(max(0.35, min(1.5, left / 72)), 2),
            "right": round(max(0.35, min(1.5, right / 72)), 2),
        }
    return formatting


def analyze_template(file_path):
    """Return approximate document formatting and a content-free style summary."""
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Template file not found: {file_path}")

    extension = file_path.suffix.lower()
    if extension == ".docx":
        try:
            document = Document(file_path)
        except Exception as error:
            raise ValueError(f"Could not read the DOCX template: {error}") from error
        formatting, heading_styles = _formatting_from_docx(document)
        structure = (
            "Heading hierarchy styles: " + ", ".join(heading_styles)
            if heading_styles else "No built-in section heading styles were detected."
        )
    elif extension == ".pdf":
        try:
            document = pymupdf.open(file_path)
            try:
                formatting = _formatting_from_pdf(document)
            finally:
                document.close()
        except ValueError:
            raise
        except Exception as error:
            raise ValueError(f"Could not analyze the PDF template: {error}") from error
        structure = "Use a clear title and a visually distinct section-heading hierarchy."
    else:
        raise ValueError("Unsupported template type. Please use a DOCX or PDF file.")

    details = []
    for label, key in (
        ("body font", "font_name"),
        ("body size", "font_size"),
        ("title font", "title_font_name"),
        ("title size", "title_font_size"),
        ("heading font", "heading_font_name"),
        ("heading size", "heading_font_size"),
        ("accent color", "accent_color"),
        ("text color", "text_color"),
    ):
        if key in formatting:
            value = formatting[key]
            details.append(f"{label}: {value} pt" if key.endswith("_size") else f"{label}: {value}")

    margins = formatting.get("margins")
    if margins:
        details.append(
            "page margins (inches): "
            + ", ".join(f"{side} {value}" for side, value in margins.items())
        )

    return {
        "formatting": formatting,
        "style_reference": "; ".join(details + [structure]),
    }
