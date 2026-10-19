
from pathlib import Path
import pymupdf

# Find the project folder
project_directory = Path(__file__).resolve().parent

# Locate the sample PDF
pdf_path = project_directory / "samples" / "renewable_energy.pdf"

# Open the PDF
with pymupdf.open(pdf_path) as pdf:
    print("Number of pages:", len(pdf))

    # Extract and display text from each page
    for page_number, page in enumerate(pdf, start=1):
        print(f"\n--- Page {page_number} ---")
        print(page.get_text())
