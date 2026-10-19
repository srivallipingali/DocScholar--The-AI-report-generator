
import json
from pathlib import Path


def load_config(config_path):
    """
    Load report formatting settings from a JSON file.
    """

    config_path = Path(config_path)

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    try:
        with config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON configuration: {error}"
        ) from error

    required_keys = [
        "report_title",
        "font_name",
        "font_size",
        "margins",
    ]

    for key in required_keys:
        if key not in config:
            raise ValueError(
                f"Missing required configuration setting: {key}"
            )

    required_margins = ["top", "bottom", "left", "right"]

    for margin in required_margins:
        if margin not in config["margins"]:
            raise ValueError(
                f"Missing margin setting: {margin}"
            )

    return config
