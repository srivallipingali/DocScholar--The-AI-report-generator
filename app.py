"""Streamlit entry point for DocScholar.

Run frontend.py on every Streamlit rerun instead of importing it as a cached
module. This ensures the widgets and page are rendered again after interaction.
"""
import runpy
from pathlib import Path

FRONTEND_PATH = Path(__file__).resolve().with_name("frontend.py")
runpy.run_path(str(FRONTEND_PATH), run_name="__main__")
