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

from pydantic import ValidationError

from report_generator.report_schema import StructuredReport

# Override with the GEMINI_MODEL environment variable if this name is retired.
DEFAULT_MODEL = "gemini-3.5-flash"
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]

# Guard against huge uploads. Very long inputs cost more and can exceed limits.
MAX_INPUT_CHARACTERS = 60_000


def build_prompt(source_text, report_type=None, custom_instructions=None, image_context=None):
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

    image_section = ""
    if image_context:
        image_section = (
            "SOURCE IMAGES AND THEIR CONTEXT:\n"
            f"{image_context}\n"
            "For relevant images, add their exact IDs to the appropriate section image_ids list. Use only supplied IDs.\n\n"
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

    try:
        return StructuredReport.model_validate(data)
    except ValidationError as error:
        raise ValueError(
            f"The AI response did not match the report format: {error}"
        ) from error


def _call_gemini(prompt):
    """Send the prompt to Gemini and return the raw JSON text it replies with."""

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
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    # Ask for JSON that follows our schema.
                    response_mime_type="application/json",
                    response_schema=StructuredReport,
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

    if generate is None:
        generate = _call_gemini

    prompt = build_prompt(
        source_text.strip(),
        report_type=report_type,
        custom_instructions=custom_instructions,
        image_context=image_context,
    )
    reply = generate(prompt)

    return parse_report(reply)
