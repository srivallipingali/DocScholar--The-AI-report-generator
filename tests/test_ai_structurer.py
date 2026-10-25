import json

import pytest

from report_generator.ai_structurer import (
    MAX_INPUT_CHARACTERS,
    _GeminiStructuredReport,
    build_prompt,
    parse_report,
    structure_report,
)
from report_generator.report_schema import StructuredReport

VALID_REPLY = json.dumps(
    {
        "title": "Renewable Energy",
        "sections": [
            {"heading": "Introduction", "content": "Clean energy matters."},
            {"heading": "Conclusion", "content": "The future is renewable."},
        ],
    }
)


def fake_generate(prompt):
    """Stands in for Gemini: always returns a valid reply."""
    return VALID_REPLY


# ---------- parse_report ----------

def test_parse_valid_reply():
    report = parse_report(VALID_REPLY)

    assert isinstance(report, StructuredReport)
    assert report.title == "Renewable Energy"
    assert [s.heading for s in report.sections] == [
        "Introduction",
        "Conclusion",
    ]


def test_parse_rejects_non_json():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_report("Sorry, I can't do that.")


def test_parse_rejects_missing_sections():
    with pytest.raises(ValueError, match="report format"):
        parse_report(json.dumps({"title": "Only a title"}))


def test_parse_rejects_empty_section_list():
    with pytest.raises(ValueError, match="report format"):
        parse_report(json.dumps({"title": "T", "sections": []}))


def test_parse_rejects_blank_heading():
    bad = {"title": "T", "sections": [{"heading": "", "content": "x"}]}

    with pytest.raises(ValueError, match="report format"):
        parse_report(json.dumps(bad))


# ---------- build_prompt ----------

def test_prompt_contains_source_text():
    prompt = build_prompt("Solar panels convert sunlight.")

    assert "Solar panels convert sunlight." in prompt


def test_prompt_mentions_report_type_when_given():
    assert "Business Report" in build_prompt("text", "Business Report")


def test_prompt_includes_custom_instructions():
    prompt = build_prompt(
        "source material",
        report_type="Academic Report",
        custom_instructions="Focus on environmental impact",
    )
    assert "Focus on environmental impact" in prompt
    assert "USER'S SPECIAL INSTRUCTIONS" in prompt


def test_prompt_uses_uploaded_template_only_as_style_reference():
    prompt = build_prompt(
        "Use only verified source facts.",
        style_reference="body font: Arial; heading hierarchy: Heading 1",
        template_instructions="Use numbered sections and a restrained tone.",
    )

    assert "body font: Arial" in prompt
    assert "Use numbered sections and a restrained tone." in prompt
    assert "inspiration only; not report source material" in prompt
    assert "Do not copy its wording, facts, names, or subject matter" in prompt


# ---------- structure_report (with a fake model) ----------

def test_structure_report_uses_generate_function():
    report = structure_report("Some source text.", generate=fake_generate)

    assert report.title == "Renewable Energy"


def test_structure_report_sends_source_text_to_model():
    seen = {}

    def spy(prompt):
        seen["prompt"] = prompt
        return VALID_REPLY

    structure_report("Unique marker text.", generate=spy)

    assert "Unique marker text." in seen["prompt"]


def test_structure_report_sends_custom_instructions_to_model():
    seen = {}

    def spy(prompt):
        seen["prompt"] = prompt
        return VALID_REPLY

    structure_report(
        "Source text.",
        custom_instructions="Include ethical analysis",
        generate=spy,
    )

    assert "Include ethical analysis" in seen["prompt"]


def test_structure_report_rejects_empty_input():
    with pytest.raises(ValueError, match="empty"):
        structure_report("   ", generate=fake_generate)


def test_structure_report_rejects_oversized_input():
    with pytest.raises(ValueError, match="too long"):
        structure_report(
            "a" * (MAX_INPUT_CHARACTERS + 1), generate=fake_generate
        )


def test_structure_report_surfaces_bad_model_output():
    with pytest.raises(ValueError):
        structure_report("text", generate=lambda prompt: "not json")


def test_missing_api_key_gives_clear_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        structure_report("some text")


def test_prompt_requests_visual_selection_and_concise_captions():
    prompt = build_prompt(
        "A report about DC generators.",
        image_context="ID: slide1:image_1 | Slide: 1 | Context: Generator diagram",
    )

    assert "actual image files" in prompt
    assert "decorative, irrelevant, redundant" in prompt
    assert "image_captions" in prompt
    assert "names and nearby source text are clues, not proof" in prompt
    assert "leave image_ids empty" in prompt


def test_parse_report_accepts_ai_image_captions():
    reply = json.dumps({
        "title": "DC Generator",
        "sections": [{
            "heading": "Construction",
            "content": "The armature rotates in the magnetic field.",
            "image_ids": ["slide1:image_1"],
        }],
        "image_captions": {
            "slide1:image_1": "Labeled diagram of the generator's main components"
        },
    })

    report = parse_report(reply)

    assert report.sections[0].image_ids == ["slide1:image_1"]
    assert report.image_captions["slide1:image_1"].startswith("Labeled diagram")


def test_parse_report_normalizes_gemini_caption_entries():
    reply = json.dumps({
        "title": "DC Generator",
        "sections": [{
            "heading": "Construction",
            "content": "The armature rotates in the magnetic field.",
            "image_ids": ["slide1:image_1"],
        }],
        "image_captions": [{
            "image_id": "slide1:image_1",
            "caption": "Labeled diagram of the generator",
        }],
    })

    report = parse_report(reply)

    assert report.image_captions == {
        "slide1:image_1": "Labeled diagram of the generator"
    }


def test_gemini_response_schema_avoids_unsupported_dynamic_properties():
    schema = _GeminiStructuredReport.model_json_schema()

    def contains_additional_properties(value):
        if isinstance(value, dict):
            return "additionalProperties" in value or any(
                contains_additional_properties(item)
                for item in value.values()
            )
        if isinstance(value, list):
            return any(contains_additional_properties(item) for item in value)
        return False

    assert not contains_additional_properties(schema)
    assert schema["properties"]["image_captions"]["type"] == "array"


def test_structure_report_only_assigns_supplied_images_once():
    reply = json.dumps({
        "title": "DC Generator",
        "sections": [
            {
                "heading": "Construction",
                "content": "The generator has an armature.",
                "image_ids": ["known-image", "unknown-image"],
            },
            {
                "heading": "Operation",
                "content": "The armature rotates.",
                "image_ids": ["known-image"],
            },
        ],
        "image_captions": {
            "known-image": "Visible generator components",
            "unknown-image": "An unrelated image",
        },
    })

    report = structure_report(
        "A DC generator report.",
        generate=lambda prompt: reply,
        image_inputs=[{"id": "known-image", "data": b"image"}],
    )

    assert report.sections[0].image_ids == ["known-image"]
    assert report.sections[1].image_ids == []
    assert report.image_captions == {"known-image": "Visible generator components"}
