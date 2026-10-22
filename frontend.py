from io import BytesIO
from pathlib import Path
import tempfile
import base64

import streamlit as st

from report_generator.ai_structurer import structure_report
from report_generator.config_loader import load_config
from report_generator.document_builder import (
    build_report,
    build_structured_report,
)
from report_generator.file_reader import read_file
from report_generator.template_loader import load_templates

# Load GEMINI_API_KEY from a local .env file if python-dotenv is installed.
# On a deployed app the key comes from the host's secrets instead.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# --------------------------------------------------
# 1. PROJECT PATHS
# --------------------------------------------------

PROJECT_DIRECTORY = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_DIRECTORY / "config" / "report_format.json"
TEMPLATES_PATH = PROJECT_DIRECTORY / "config" / "templates.json"
LOGO_PATH = PROJECT_DIRECTORY / "assets" / "logo.png"

# --------------------------------------------------
# 2. PAGE SETTINGS
# --------------------------------------------------

st.set_page_config(
    page_title="DocScholar",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------
# 3. CUSTOM DESIGN
# --------------------------------------------------

st.markdown(
    """
    <style>
        .stApp {
    background-color: #e084a6;
    color: #360314;
    }

    /* Dark text boxes with readable white text */
    .stApp input,
    .stApp textarea {
        color: #ffffff !important;
        background-color: #24121d !important;
        border: 1px solid #b85c7d !important;
        caret-color: #ffffff;
    }

    .stApp input::placeholder,
    .stApp textarea::placeholder {
        color: #d7c3cd !important;
        opacity: 1;
    }

    /* Keep selected values and dropdown menus dark with white text */
    .stApp [data-baseweb="select"] > div {
        color: #ffffff !important;
        background-color: #24121d !important;
        border-color: #b85c7d !important;
    }

    .stApp [role="listbox"],
    .stApp [role="option"] {
        color: #ffffff !important;
        background-color: #24121d !important;
    }

    /* Uploaded filename and file-uploader text */
    .stApp [data-testid="stFileUploader"],
    .stApp [data-testid="stFileUploader"] label,
    .stApp [data-testid="stFileUploader"] small,
    .stApp [data-testid="stFileUploader"] span,
    .stApp [data-testid="stFileUploader"] p {
        color: #ffffff !important;
    }

    .stApp [data-testid="stFileUploader"] section,
    .stApp [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
        background-color: #24121d !important;
        border-color: #b85c7d !important;
    }

    /* File uploader buttons should remain readable */
    .stApp [data-testid="stFileUploader"] button {
        color: #ffffff !important;
        background-color: #480870 !important;
        border-color: #b85c7d !important;
    }

        .block-container {
            max-width: 1100px;
            padding-top: 2.5rem;
            padding-bottom: 3rem;
        }

        .hero {
            background: linear-gradient(120deg, #a8234b, #a8234b);
            padding: 2.2rem;
            border-radius: 18px;
            color: purple;
            margin-bottom: 1.8rem;
        }

        .hero h1 {
            font-family: "Caveat", cursive;
            color: #dec3ab;
            font-size: 4.5rem;
            margin-bottom: 0.5rem;
        }

        .hero p {
            color: #dec3ab;
            font-size: 2.5rem;
            margin-bottom: 0;
        }

        .section-heading {
            color: #4c227d;
            font-size: 2rem;
            font-weight: 700;
            margin-top: 0.8rem;
            margin-bottom: 0.3rem;
        }

        .section-description {
            color: #b52134;
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: white;
            border-radius: 14px;
            border-color: #360314;
        }

        div.stButton > button[kind="primary"] {
            background-color: #480870;
            color: white;
            border-radius: 9px;
            border: none;
            min-height: 3rem;
            font-weight: 600;
        }

        div.stButton > button[kind="primary"]:hover {
            background-color: #690442;
            color: #2e7d8c;
        }

        div[data-testid="stDownloadButton"] button {
            border-radius: 9px;
            min-height: 2.8rem;
            font-weight: 600;
        }

        footer {
            visibility: hidden;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# 4. LOAD TEMPLATES
# --------------------------------------------------

try:
    templates = load_templates(TEMPLATES_PATH)
except (FileNotFoundError, ValueError, OSError) as error:
    st.error(f"Could not load report templates: {error}")
    st.stop()


# --------------------------------------------------
# 5. HEADER
# --------------------------------------------------


# Convert the logo image into a format that HTML can display
with open(LOGO_PATH, "rb") as logo_file:
    logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")

# Display the header with our custom logo
st.markdown(
    f"""
    <div class="hero">
        <h1 style="
            display: flex;
            align-items: center;
            gap: 16px;
        ">
            <img
                src="data:image/png;base64,{logo_base64}"
                alt="AI Report Generator Logo"
                style="
                    width: 64px;
                    height: 64px;
                    object-fit: contain;
                "
            >
            <span>DocScholar</span>
        </h1>

    The AI report generator

      
    </div>
    """,
    unsafe_allow_html=True,
)




# --------------------------------------------------
# 6. INPUT SECTION
# --------------------------------------------------

st.markdown(
    '<div class="section-heading">01  |  Your content</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">'
    'Give us your input'
    '</div>',
    unsafe_allow_html=True,
)

report_text = ""

with st.container(border=True):

    input_method = st.selectbox(
        "Enter your choice of input method",
        ["Type or paste text", "Upload a PDF or DOCX"],
        index=0,
    )

    if input_method == "Type or paste text":

        report_text = st.text_area(
            "Report content",
            height=260,
            placeholder=(
                "Enter Title\n\n"
                "Press Enter for body text."
            ),
        )

        st.caption(
            "The first line becomes a heading inside your Word document."
        )

    else:

        uploaded_file = st.file_uploader(
            "Choose your source document",
            type=["pdf", "docx"],
            help="Upload a readable PDF or Word document.",
        )

        if uploaded_file is not None:

            suffix = Path(uploaded_file.name).suffix

            try:
                with tempfile.NamedTemporaryFile(
                    suffix=suffix,
                    delete=True,
                ) as temporary_file:

                    temporary_file.write(uploaded_file.getvalue())
                    temporary_file.flush()

                    report_text = read_file(temporary_file.name)

                st.success(
                    f"Successfully read: {uploaded_file.name}"
                )

            except (ValueError, OSError, RuntimeError) as error:
                st.error(f"Could not read the document: {error}")


# --------------------------------------------------
# 7. REPORT SETTINGS
# --------------------------------------------------

st.markdown(
    '<div class="section-heading">02  |  Report settings</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">'
    'Give your report a title and choose its formatting style.'
    '</div>',
    unsafe_allow_html=True,
)

with st.container(border=True):

    use_ai = st.checkbox(
        "Use AI to organise my content into sections",
        value=True,
        help=(
            "Gemini reads your content and arranges it into a titled report "
            "with headings. Turn this off to format your text exactly as "
            "written."
        ),
    )

    report_title = st.text_input(
        "Report title" + (" (optional with AI)" if use_ai else ""),
        placeholder="e.g. Renewable Energy: A Technical Overview",
    )

    selected_template = st.selectbox(
        "Choose a report template",
        options=list(templates.keys()),
    )

    template_descriptions = {
        "Academic Report": (
            "Suitable for academic assignments, research summaries, "
            "and college reports."
        ),
        "Engineering Project Report": (
            "Suitable for technical projects, engineering documentation, "
            "and project submissions."
        ),
        "Business Report": (
            "Suitable for business analysis, proposals, and formal "
            "professional reports."
        ),
        "Simple Structured Report": (
            "A clean, minimal layout for general-purpose reports."
        ),
    }

    st.markdown(
    f"""
    <p style="
        color: #360314;
        font-size: 15px;
        margin-top: 8px;
    ">
        {template_descriptions.get(
            selected_template,
            "A predefined formatting style for your report."
        )}
    </p>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# 8. GENERATE THE REPORT
# --------------------------------------------------

st.markdown(
    '<div class="section-heading">03  |  Generate your report</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">'
    'Generate your formatted Word document and download it below.'
    '</div>',
    unsafe_allow_html=True,
)

if st.button(
    "Generate Word Report  →",
    type="primary",
    use_container_width=True,
):

    if not report_text.strip():
        st.error("Please enter some text or upload a readable document.")

    elif not use_ai and not report_title.strip():
        st.error("Please enter a title for your report.")

    else:

        try:
            config = load_config(CONFIG_PATH)

            # Apply the selected template's formatting.
            config.update(templates[selected_template])

            # Use the title entered by the user (may be empty when using AI,
            # in which case the AI's suggested title is used instead).
            config["report_title"] = report_title.strip()

            # Generate the document in memory.
            document_bytes = BytesIO()

            if use_ai:
                with st.spinner("Organising your content with AI..."):
                    structured_report = structure_report(
                        report_text,
                        report_type=selected_template,
                    )

                build_structured_report(
                    structured_report,
                    config,
                    document_bytes,
                )

                final_title = (
                    report_title.strip() or structured_report.title
                )

            else:
                build_report(
                    report_text,
                    config,
                    document_bytes,
                )

                final_title = report_title.strip()

            st.session_state["generated_report_bytes"] = (
                document_bytes.getvalue()
            )

            st.session_state["generated_report_name"] = (
                final_title
                .replace("/", "-")
                .replace("\\", "-")
                + ".docx"
            )

            st.session_state["generated_template"] = selected_template

            st.success("Your report has been generated successfully!")

        except (FileNotFoundError, ValueError, OSError, RuntimeError) as error:
            st.error(f"Report generation failed: {error}")


# --------------------------------------------------
# 9. DOWNLOAD SECTION
# --------------------------------------------------

if "generated_report_bytes" in st.session_state:

    st.divider()

    st.markdown(
        '<div class="section-heading">Your report is ready</div>',
        unsafe_allow_html=True,
    )

    st.write(
        f"Formatting used: **{st.session_state['generated_template']}**"
    )

    st.download_button(
        label="⬇️ Download Word Report",
        data=st.session_state["generated_report_bytes"],
        file_name=st.session_state["generated_report_name"],
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        use_container_width=True,
    )


# --------------------------------------------------
# 10. FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "© 2026 Srivalli Pingali. All rights reserved. | "
)
