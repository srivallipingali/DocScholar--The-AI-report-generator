"""Convert a finished Word report into a PDF.

Why convert instead of drawing the PDF separately? A second PDF renderer
would have to re-implement every template setting (fonts, margins, headings,
table of contents) and could drift out of sync with the Word file.
Converting the .docx guarantees the PDF looks exactly like the Word report,
and it keeps working with templates the user uploads.

The conversion is done by LibreOffice running in "headless" mode (no window).
If LibreOffice is not installed, the app simply hides the PDF button.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

# Names to look for on the PATH, then common install locations (macOS and
# Windows installs usually are NOT on the PATH).
EXECUTABLE_NAMES = ("soffice", "libreoffice")
EXTRA_LOCATIONS = (
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "C:/Program Files/LibreOffice/program/soffice.exe",
    "C:/Program Files (x86)/LibreOffice/program/soffice.exe",
)

CONVERSION_TIMEOUT_SECONDS = 120


def find_libreoffice():
    """Return the path to LibreOffice's command-line program, or None."""

    for name in EXECUTABLE_NAMES:
        found = shutil.which(name)

        if found:
            return found

    for location in EXTRA_LOCATIONS:
        if Path(location).is_file():
            return location

    return None


def is_pdf_export_available():
    """True when a PDF can be produced on this machine."""

    return find_libreoffice() is not None


def docx_to_pdf_bytes(docx_bytes):
    """Convert the bytes of a .docx file into the bytes of a PDF."""

    # A .docx file is a zip archive, and every zip starts with the letters PK.
    # LibreOffice would happily turn ANY bytes into a PDF (treating them as
    # plain text), so we check up front that this really is a Word file.
    if not docx_bytes.startswith(b"PK"):
        raise ValueError("The data is not a valid Word (.docx) document.")

    executable = find_libreoffice()

    if executable is None:
        raise RuntimeError(
            "PDF export needs LibreOffice, which was not found on this "
            "computer. Install it from libreoffice.org and try again."
        )

    # Everything happens inside a throw-away folder that is deleted after.
    with tempfile.TemporaryDirectory() as work_directory:
        work = Path(work_directory)
        source = work / "report.docx"
        source.write_bytes(docx_bytes)

        # A private profile folder stops LibreOffice from clashing with
        # another copy that may already be open on the same machine.
        profile = work / "profile"

        command = [
            executable,
            f"-env:UserInstallation={profile.as_uri()}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(work),
            str(source),
        ]

        try:
            subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=CONVERSION_TIMEOUT_SECONDS,
                check=True,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("The PDF conversion took too long.") from error
        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                f"The PDF conversion failed: {error.stderr.strip()}"
            ) from error

        result = work / "report.pdf"

        if not result.is_file():
            raise RuntimeError("The PDF conversion produced no file.")

        return result.read_bytes()
