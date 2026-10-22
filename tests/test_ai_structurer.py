import json

import pytest

from report_generator.ai_structurer import (
    LENGTH_OPTIONS,
    MAX_INPUT_CHARACTERS,
    TONE_OPTIONS,
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


# ---------- length and tone ----------

@pytest.mark.parametrize("length", list(LENGTH_OPTIONS))
def test_prompt_includes_each_length_instruction(length):
    prompt = build_prompt("text", length=length)

    assert LENGTH_OPTIONS[length] in prompt


@pytest.mark.parametrize("tone", list(TONE_OPTIONS))
def test_prompt_includes_each_tone_instruction(tone):
    prompt = build_prompt("text", tone=tone)

    assert TONE_OPTIONS[tone] in prompt


def test_unknown_length_is_rejected():
    with pytest.raises(ValueError, match="Unknown length"):
        build_prompt("text", length="Enormous")


def test_unknown_tone_is_rejected():
    with pytest.raises(ValueError, match="Unknown tone"):
        build_prompt("text", tone="Sarcastic")


def test_structure_report_passes_length_and_tone_to_prompt():
    seen = {}

    def spy(prompt):
        seen["prompt"] = prompt
        return VALID_REPLY

    structure_report("text", generate=spy, length="Short", tone="Simple")

    assert LENGTH_OPTIONS["Short"] in seen["prompt"]
    assert TONE_OPTIONS["Simple"] in seen["prompt"]
