
import json
from pathlib import Path


def load_templates(template_path):
    """
    Load available report templates from a JSON file.
    """

    template_path = Path(template_path)

    if not template_path.is_file():
        raise FileNotFoundError(
            f"Template file not found: {template_path}"
        )

    try:
        with template_path.open("r", encoding="utf-8") as file:
            templates = json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid template configuration: {error}"
        ) from error

    if not isinstance(templates, dict) or not templates:
        raise ValueError(
            "The template configuration must contain at least one template."
        )

    required_keys = [
        "font_name",
        "font_size",
        "title_font_size",
        "heading_font_size",
        "margins",
    ]

    required_margins = [
        "top",
        "bottom",
        "left",
        "right",
    ]

    for template_name, settings in templates.items():

        if not isinstance(settings, dict):
            raise ValueError(
                f"Invalid settings for template: {template_name}"
            )

        for key in required_keys:
            if key not in settings:
                raise ValueError(
                    f"Template '{template_name}' is missing '{key}'."
                )

        for margin in required_margins:
            if margin not in settings["margins"]:
                raise ValueError(
                    f"Template '{template_name}' is missing margin '{margin}'."
                )

    return templates
