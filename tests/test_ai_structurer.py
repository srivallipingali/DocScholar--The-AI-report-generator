import json

import pytest

from report_generator.ai_structurer import (
    MAX_INPUT_CHARACTERS,
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
