"""The *shape* of a structured report.

These Pydantic models are the contract between the AI step and the Word
builder. The model is asked to return JSON matching this shape, and Pydantic
checks that what came back really does match before the rest of the app
trusts it.

    AI model  --JSON-->  StructuredReport  -->  build_report()  -->  .docx
"""

from pydantic import BaseModel, Field


class Section(BaseModel):
    """One heading plus the text that belongs under it."""

    heading: str = Field(
        min_length=1,
        description="Short section heading, e.g. 'Introduction'.",
    )
    content: str = Field(
        min_length=1,
        description=(
            "Body text of the section. Separate paragraphs with a blank line."
        ),
    )


class StructuredReport(BaseModel):
    """A whole report: title, optional subtitle/abstract, and an ordered list of sections."""

    title: str = Field(
        min_length=1,
        description="Concise title for the report.",
    )
    subtitle: str | None = Field(
        default=None,
        description="A concise subtitle or summary line for the cover page.",
    )
    abstract: str | None = Field(
        default=None,
        description="Optional brief abstract or executive summary for the cover page.",
    )
    sections: list[Section] = Field(
        min_length=1,
        description="Report sections in the order they should appear.",
    )
