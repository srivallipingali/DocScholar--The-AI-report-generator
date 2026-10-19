
from pathlib import Path

from report_generator.file_reader import read_file
from report_generator.config_loader import load_config
from report_generator.document_builder import build_report


# Locate the project folders.
PROJECT_DIRECTORY = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_DIRECTORY / "config" / "report_format.json"
OUTPUT_DIRECTORY = PROJECT_DIRECTORY / "output"
SAMPLES_DIRECTORY = PROJECT_DIRECTORY / "samples"


def generate_report_from_text(text, output_name="generated_report"):
    """
    Generate a Word report from text supplied by a user.
    This function can be called by a frontend.
    """

    # Load the report formatting settings.
    config = load_config(CONFIG_PATH)

    # Create a safe output filename.
    safe_name = Path(output_name).stem

    if not safe_name or safe_name in {".", ".."}:
        safe_name = "generated_report"

    output_path = OUTPUT_DIRECTORY / f"{safe_name}_report.docx"

    # Build and save the Word report.
    saved_path = build_report(
        text,
        config,
        output_path
    )

    return saved_path


def generate_report_from_file(file_path):
    """
    Read a supported file and generate a Word report from its text.
    """

    file_path = Path(file_path)

    # Extract the text from the uploaded or selected file.
    text = read_file(file_path)

    # Use the source filename to name the generated report.
    return generate_report_from_text(
        text,
        output_name=file_path.stem
    )


def generate_report():
    """
    Run the application through the terminal.
    """

    # Ask the user for a filename inside the samples folder.
    file_name = input(
        "Enter a TXT, PDF, or DOCX filename: "
    ).strip()

    if not file_name:
        print("Error: Please enter a filename.")
        return

    source_path = SAMPLES_DIRECTORY / file_name

    # Prevent access to files outside the samples folder.
    if source_path.resolve().parent != SAMPLES_DIRECTORY.resolve():
        print("Error: Please enter a filename from the samples folder.")
        return

    try:
        # Generate the report using the reusable backend function.
        saved_path = generate_report_from_file(source_path)

        print("\nReport generated successfully!")
        print(f"Saved to: {saved_path}")

    except (FileNotFoundError, ValueError, OSError, RuntimeError) as error:
        print(f"\nError: {error}")


if __name__ == "__main__":
    generate_report()



