"""Extract ordered text and embedded images from PowerPoint presentations.

The reader preserves slide boundaries and associates each image with the text
on its slide. This context can later be passed to the AI for report placement.
"""
from pathlib import Path

from pptx import Presentation


def read_pptx(file_path):
    """Return slide-aware text and images extracted from a .pptx file.

    Returns:
        {
            "text": str,
            "images": [
                {
                    "name": str,
                    "data": bytes,
                    "caption": str,
                    "slide_number": int,
                    "context": str,
                }
            ],
        }
    """
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"PowerPoint file not found: {file_path}")

    if file_path.suffix.lower() != ".pptx":
        raise ValueError("Unsupported presentation type. Please use a .pptx file.")

    try:
        presentation = Presentation(str(file_path))
    except Exception as error:
        raise ValueError(f"Could not read the PowerPoint file: {error}") from error

    slide_texts = []
    images = []

    for slide_number, slide in enumerate(presentation.slides, start=1):
        text_parts = []
        slide_images = []

        # Keep the slide's shape order so the text context remains meaningful.
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                shape_text = "\n".join(
                    paragraph.text.strip()
                    for paragraph in shape.text_frame.paragraphs
                    if paragraph.text.strip()
                ).strip()
                if shape_text:
                    text_parts.append(shape_text)

            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        text_parts.append(row_text)

            if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                try:
                    picture = shape.image
                    extension = picture.ext or "png"
                    image_name = f"slide_{slide_number}_image_{len(slide_images) + 1}.{extension}"
                    slide_images.append({
                        "name": image_name,
                        "data": picture.blob,
                        "slide_number": slide_number,
                    })
                except (AttributeError, ValueError):
                    # One unsupported/corrupt picture should not discard slide text.
                    continue

        slide_context = "\n".join(text_parts).strip()
        if slide_context or slide_images:
            slide_texts.append(f"[SLIDE {slide_number}]\n{slide_context}".strip())

        # Give each picture the text extracted from its own slide as placement context.
        for image in slide_images:
            image["context"] = slide_context
            image["caption"] = (
                f"PowerPoint slide {slide_number}"
                + (f": {slide_context[:300]}" if slide_context else "")
            )
            images.append(image)

    extracted_text = "\n\n".join(slide_texts).strip()
    if not extracted_text and not images:
        raise ValueError("The PowerPoint file contains no readable text or images.")

    return {"text": extracted_text, "images": images}
