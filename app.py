
import streamlit as st
from io import BytesIO
from pathlib import Path
import tempfile

from report_generator.file_reader import read_file
from report_generator.config_loader import load_config
from report_generator.template_loader import load_templates
from report_generator.document_builder import build_report


# Project paths
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "report_format.json"
TEMPLATES_PATH = BASE_DIR / "config" / "templates.json"
LOGO_PATH = BASE_DIR / "assets" / "logo.png"


# Page settings
st.set_page_config(
    page_title="DocScholar - AI Report Generator",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "📄",
    layout="centered",
)

st.title("DocScholar")
st.subheader("AI Report Generator")
st.write("Turn your content into a professionally formatted Word report.")

st.divider()


# Load templates and configuration
try:
    config = load_config(CONFIG_PATH)
    templates = load_templates(TEMPLATES_PATH)
except Exception as error:
    st.error(f"Could not load configuration: {error}")
    st.stop()


# Input section
st.header("1. Enter your content")

input_method = st.radio(
    "Choose an input method",
    ["Type or paste text", "Upload a PDF or DOCX"],
)

report_text = ""

if input_method == "Type or paste text":
    report_text = st.text_area(
        "Your report content",
        height=220,
        placeholder="Paste your content here...",
    )

else:
    uploaded_file = st.file_uploader(
        "Upload your document",
        type=["pdf", "docx", "txt"],
    )

    if uploaded_file is not None:
        try:
            suffix = Path(uploaded_file.name).suffix

            with tempfile.NamedTemporaryFile(
                suffix=suffix,
                delete=True,
            ) as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_file.flush()
                report_text = read_file(temp_file.name)

            st.success("File read successfully.")

        except Exception as error:
            st.error(f"Could not read the file: {error}")


# Report settings
st.header("2. Report settings")

report_title = st.text_input(
    "Report title",
    value="My Report",
)

selected_template = st.selectbox(
    "Choose a template",
    list(templates.keys()),
)


# Generate report
st.header("3. Generate your report")

if st.button("Generate Word Report", type="primary"):
    if not report_text.strip():
        st.warning("Please enter text or upload a document first.")

    elif not report_title.strip():
        st.warning("Please enter a report title.")

    else:
        try:
            report_config = config.copy()
            report_config.update(templates[selected_template])
            report_config["report_title"] = report_title.strip()

            output = BytesIO()
            build_report(report_text, report_config, output)

            st.session_state["report_bytes"] = output.getvalue()
            safe_title = (
                report_title.strip()
                .replace("/", "-")
                .replace("\\", "-")
            )
            st.session_state["report_name"] = f"{safe_title}.docx"

            st.success("Your report is ready!")

        except Exception as error:
            st.error(f"Report generation failed: {error}")


# Download report
if "report_bytes" in st.session_state:
    st.download_button(
        label="Download Word Report",
        data=st.session_state["report_bytes"],
        file_name=st.session_state["report_name"],
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )




