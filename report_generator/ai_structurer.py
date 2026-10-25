"""Turn raw text into a StructuredReport using Gemini.

This is the ONLY file that talks to Gemini. Everything else in the app works
with plain Python objects, so if Google changes its SDK or you switch to
another model, only this file changes.

The file is split into small pieces on purpose:

    build_prompt()       builds the instruction text      (pure, easy to test)
    parse_report()       validates the model's JSON reply (pure, easy to test)
    _call_gemini()       the real network call            (needs a key)
    structure_report()   glues the three together

`structure_report` accepts an optional `generate` function. Tests pass in a
fake one, so the logic can be tested without an API key or internet.
"""

import json
import os

from pydantic import BaseModel, Field, ValidationError

from report_generator.report_schema import StructuredReport

# Override with the GEMINI_MODEL environment variable if this name is retired.
DEFAULT_MODEL = "gemini-3.5-flash"
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]

# Guard against huge uploads. Very long inputs cost more and can exceed limits.
MAX_INPUT_CHARACTERS = 60_000


class _GeminiImageCaption(BaseModel):
    image_id: str
    caption: str


class _GeminiStructuredReport(StructuredReport):
    image_captions: list[_GeminiImageCaption] = Field(default_factory=list)


def build_prompt(
    source_text,
    report_type=None,
    custom_instructions=None,
    image_context=None,
    style_reference=None,
    template_instructions=None,
):
    """Create the instruction that tells the model what to produce."""

    focus = f" The report should follow a {report_type} style." if report_type else ""

    custom_section = ""
    if custom_instructions and custom_instructions.strip():
        custom_section = (
            "USER'S SPECIAL INSTRUCTIONS / NOTES:\n"
            f"{custom_instructions.strip()}\n"
            "Please follow these specific instructions closely when writing, "
            "tailoring, and structuring the report.\n\n"
        )

    template_section = ""
    if style_reference or (template_instructions and template_instructions.strip()):
        template_section = (
            "UPLOADED TEMPLATE STYLE REFERENCE (inspiration only; not report source material):\n"
            f"{style_reference or 'No automatic style details were extracted.'}\n"
            "Use this reference only to guide the new report's visual style and organization. "
            "Do not copy its wording, facts, names, or subject matter into the report.\n"
        )
        if template_instructions and template_instructions.strip():
            template_section += (
                "USER'S INSTRUCTIONS FOR THE TEMPLATE:\n"
                f"{template_instructions.strip()}\n"
                "Apply these instructions to the new report's layout, tone, and section organization "
                "while preserving the source material's facts.\n"
            )
        template_section += "\n"

    image_section = ""
    if image_context:
        image_section = (
            "SOURCE IMAGES AND THEIR CONTEXT:\n"
            f"{image_context}\n"
            "You will also receive the actual image files labelled with these IDs. Inspect the pixels of each "
            "image; names and nearby source text are clues, not proof of what the image depicts. Select an image "
            "only when its visible content directly supports a specific report section, and omit decorative, "
            "irrelevant, redundant, or unclear images. Add each selected image's exact ID to the most relevant "
            "section image_ids list. Use only supplied IDs and never assign one image to multiple sections. "
            "Return image_captions as a list of objects with image_id and caption. For each selected image, "
            "provide one concise, factual caption (ideally 5–15 words) "
            "describing only clearly visible content. Do not repeat surrounding text, infer details from a filename, "
            "or guess at details that cannot be seen. Do not create captions for images you did not select. "
            "When no image clearly fits, leave image_ids empty.\n\n"
        )

    return (
        "You are an assistant that writes clear, well-organised reports."
        f"{focus}\n\n"
        "Read the SOURCE MATERIAL below and turn it into a structured report "
        "with a title, an optional subtitle/abstract for the cover page, and "
        "logical sections (for example Introduction, key body topics, Conclusion).\n"
        "Each section should cover a distinct topic so it can be presented as an "
        "individual topic page with its own heading in the table of contents.\n\n"
        f"{custom_section}"
        f"{template_section}"
        f"{image_section}"
        "Rules:\n"
        "- Use only information from the source material. Do not invent "
        "facts, figures or citations.\n"
        "- Provide a professional title and a concise subtitle for the cover page.\n"
        "- Write in complete, formal paragraphs. Separate paragraphs with a "
        "blank line.\n"
        "- Keep each heading short and descriptive.\n\n"
        "SOURCE MATERIAL:\n"
        f"{source_text}"
    )


def parse_report(json_text):
    """Check the model's reply and convert it into a StructuredReport.

    Models sometimes return malformed or incomplete JSON. Validating here
    means the rest of the app only ever sees a well-formed report.
    """

    try:
        data = json.loads(json_text)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError(
            "The AI response was not valid JSON."
        ) from error

    if isinstance(data, dict) and isinstance(data.get("image_captions"), list):
        caption_entries = data["image_captions"]
        if all(
            isinstance(entry, dict)
            and isinstance(entry.get("image_id"), str)
            and isinstance(entry.get("caption"), str)
            for entry in caption_entries
        ):
            data["image_captions"] = {
                entry["image_id"]: entry["caption"]
                for entry in caption_entries
            }

    try:
        return StructuredReport.model_validate(data)
    except ValidationError as error:
        raise ValueError(
            f"The AI response did not match the report format: {error}"
        ) from error


def _keep_valid_image_assignments(report, image_inputs):
    """Keep only supplied image IDs and assign each at most once."""
    available_ids = {
        str(image["id"])
        for image in image_inputs
        if image.get("id") is not None
    }
    assigned_ids = set()

    for section in report.sections:
        valid_ids = []
        for image_id in section.image_ids:
            if image_id in available_ids and image_id not in assigned_ids:
                valid_ids.append(image_id)
                assigned_ids.add(image_id)
        section.image_ids = valid_ids

    report.image_captions = {
        image_id: caption
        for image_id, caption in report.image_captions.items()
        if image_id in assigned_ids
    }
    return report


def _call_gemini(prompt, image_inputs=None):
    """Send text and optional labelled image parts to Gemini."""

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )

    # Imported here (not at the top) so the rest of the app and the tests
    # still work on a machine where the Gemini SDK is not installed.
    try:
        from google import genai
        from google.genai import types
    except ImportError as error:
        raise RuntimeError(
            "The google-genai package is not installed. "
            "Run: pip install google-genai"
        ) from error

    model_name = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    models_to_try = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]

    client = genai.Client(api_key=api_key)
    last_error = None

    for model in models_to_try:
        try:
            contents = [prompt]
            for image in image_inputs or []:
                image_id = str(image.get("id", "source image"))
                contents.append(
                    types.Part.from_text(
                        text=f"Inspect the following source image. Its exact ID is {image_id}."
                    )
                )
                contents.append(
                    types.Part.from_bytes(
                        data=image["data"],
                        mime_type=image.get("mime_type", "image/png"),
                    )
                )

            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    # Ask for JSON that follows our schema.
                    response_mime_type="application/json",
                    response_schema=_GeminiStructuredReport,
                ),
            )
            return response.text
        except Exception as error:  # SDK raises several different error types
            last_error = error
            continue

    raise RuntimeError(f"The Gemini request failed: {last_error}") from last_error


def structure_report(
    source_text,
    report_type=None,
    custom_instructions=None,
    generate=None,
    image_context=None,
    image_inputs=None,
    style_reference=None,
    template_instructions=None,
):
    """Convert raw text into a validated StructuredReport.

    `custom_instructions` allows the user to pass custom notes, style preferences,
    or guidelines to tailor the AI output.

    `generate` is a function that takes a prompt string and returns the
    model's JSON reply as text. It defaults to the real Gemini call.
    """

    if not source_text or not source_text.strip():
        raise ValueError("Cannot structure an empty document.")

    if len(source_text) > MAX_INPUT_CHARACTERS:
        raise ValueError(
            f"The input is too long ({len(source_text):,} characters). "
            f"Please keep it under {MAX_INPUT_CHARACTERS:,}."
        )

    prompt = build_prompt(
        source_text.strip(),
        report_type=report_type,
        custom_instructions=custom_instructions,
        image_context=image_context,
        style_reference=style_reference,
        template_instructions=template_instructions,
    )
    if generate is None:
        reply = _call_gemini(prompt, image_inputs=image_inputs)
    else:
        # Keep the injectable one-argument generator used by unit tests.
        reply = generate(prompt)

    report = parse_report(reply)
    if image_inputs is not None:
        report = _keep_valid_image_assignments(report, image_inputs)
    return report
