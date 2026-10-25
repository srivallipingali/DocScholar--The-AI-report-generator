# DocScholar: The AI Report Generator

DocScholar turns raw notes, pasted text, or an uploaded PDF/DOCX into a
formatted Word report. An AI model (Google Gemini) organises the content into
a titled report with sections, and a template controls the final formatting
(fonts, margins, heading sizes).

## How it works

```
 text / PDF / DOCX
        |
        v
  file_reader.py        extract plain text
        |
        v
  ai_structurer.py      Gemini -> JSON -> validated StructuredReport
                        (can visually match supplied images to sections)
        |               (report_schema.py defines the shape)
        v
  document_builder.py   apply template formatting, write the .docx
        |
        v
  frontend.py           Streamlit UI: input, settings, download
```

Design choices worth knowing:

- **The AI step is isolated.** Only `ai_structurer.py` talks to Gemini, so the
  rest of the app (and its tests) works without a network or an API key.
- **Model output is validated, not trusted.** Gemini is asked for JSON that
  matches a Pydantic schema, and the reply is re-checked before use.
- **Templates are data.** Formatting lives in `config/templates.json`, so a
  new report style needs no code change.
- **Images are matched to report sections.** In AI mode, Gemini can inspect up
  to 12 uploaded, selected Wikimedia, or PowerPoint images and place relevant
  images beside matching sections. Unplaced user-provided images remain in an
  images section; PowerPoint images are included only when selected by the AI.
- **Custom templates provide inspiration.** Upload a DOCX or PDF report as a
  style reference and optionally tell the AI how to use its tone or structure.
  The app extracts formatting cues for the new report without using the
  template's subject matter as source content.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then put your Gemini API key in .env
streamlit run app.py
```

Get a key from Google AI Studio. Never commit `.env` (it is in `.gitignore`).

## Tests

```bash
python -m pytest
```

The AI tests use a fake model, so no API key is needed to run them.

## Project layout

| Path | Purpose |
|------|---------|
| `app.py`, `frontend.py` | Streamlit entry point and UI |
| `report_generator/ai_structurer.py` | Gemini call, prompt, reply validation |
| `report_generator/report_schema.py` | `StructuredReport` / `Section` models |
| `report_generator/document_builder.py` | Builds the Word document |
| `report_generator/file_reader.py` | Reads TXT, PDF, DOCX |
| `report_generator/template_loader.py` | Loads formatting templates |
| `config/` | Template and default format settings |
| `tests/` | Unit tests |
