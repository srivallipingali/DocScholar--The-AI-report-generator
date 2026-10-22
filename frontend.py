from io import BytesIO
from pathlib import Path
import tempfile
import base64
from html import escape

import streamlit as st

from report_generator.ai_structurer import structure_report
from report_generator.config_loader import load_config
from report_generator.document_builder import (
    build_report,
    build_structured_report,
)
from report_generator.file_reader import read_file
from report_generator.template_loader import load_templates

import os

# Load GEMINI_API_KEY from a local .env file if python-dotenv is installed.
# On a deployed app or Streamlit environment, fall back to st.secrets.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if "GEMINI_API_KEY" in st.secrets:
    current_key = os.environ.get("GEMINI_API_KEY")
    if not current_key or current_key == "your_key_here":
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]


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
            placeholder="Enter or paste the text for your report.",
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

    author_name = st.text_input(
        "Author / Prepared By (optional)",
        placeholder="e.g. Srivalli Pingali / Research Department",
        help="Appears on the cover page of your report.",
    )

    custom_notes = ""
    if use_ai:
        custom_notes = st.text_area(
            "Tailoring Notes / Instructions for AI (optional)",
            height=100,
            placeholder=(
                "Give specific instructions to tailor your report output, e.g.:\n"
                "• Focus heavily on business impact and key takeaways\n"
                "• Write in an executive, formal tone\n"
                "• Emphasize safety, privacy, and regulatory considerations\n"
                "• Target an undergraduate engineering audience"
            ),
            help="Gemini will read your instructions and tailor the structure, tone, and emphasis of the report accordingly.",
        )

    st.markdown("<p style='color: #4c227d; font-weight: 600; margin-top: 10px; margin-bottom: 4px;'>Document Layout & Structure</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        include_cover_page = st.checkbox(
            "Include Cover Page",
            value=True,
            help="Generate an elegant front cover page with title, subtitle, and metadata.",
        )
    with col2:
        include_index = st.checkbox(
            "Table of Contents (Index)",
            value=True,
            help="Generate an index page for AI-organised report sections.",
            disabled=not use_ai,
        )
    with col3:
        section_per_page = st.checkbox(
            "Each Topic on New Page",
            value=True,
            help="Insert a page break between each topic so each section starts fresh on a new page.",
        )

    template_descriptions = {
        "Modern Blue": "A polished blue-accented design for technical and engineering reports.",
        "Rose Editorial": "An editorial-inspired style for academic and research reports.",
        "Emerald Professional": "A clean green-accented layout for business and analytical reports.",
        "Warm Classic": "A warm, classic style for formal submissions and portfolios.",
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

    template_names = list(templates)
    if (
        st.session_state.get("selected_template") not in template_names
    ):
        st.session_state["selected_template"] = template_names[0]

    st.markdown("### Choose a report template")
    st.caption("Select a style or expand its preview to see a sample page.")

    template_columns = st.columns(2)
    for index, template_name in enumerate(template_names):
        settings = templates[template_name]
        selected = st.session_state["selected_template"] == template_name
        font_name = escape(str(settings["font_name"]), quote=True)
        accent = escape(str(settings.get("accent_color", "#480870")), quote=True)
        accent_light = escape(str(settings.get("accent_light", "#F3EDF7")), quote=True)
        text_color = escape(str(settings.get("text_color", "#29232A")), quote=True)
        title_size = settings["title_font_size"]
        heading_size = settings["heading_font_size"]
        body_size = settings["font_size"]
        page_margin = max(
            10,
            min(24, round(settings["margins"]["left"] * 12)),
        )
        escaped_name = escape(template_name)
        description = escape(
            template_descriptions.get(
                template_name,
                "A predefined formatting style for your report.",
            )
        )
        selection_label = "Selected" if selected else "Use this template"
        selection_type = "primary" if selected else "secondary"

        with template_columns[index % len(template_columns)]:
            st.markdown(
                f"""
                <div style="
                    background: white;
                    border: 2px solid {accent if selected else '#e2d5df'};
                    border-radius: 14px;
                    padding: 16px;
                    margin-bottom: 8px;
                ">
                    <div style="
                        background: {accent_light};
                        border: 1px solid {accent};
                        border-radius: 5px;
                        box-sizing: border-box;
                        height: 155px;
                        margin: 0 auto 14px;
                        overflow: hidden;
                        padding: {page_margin}px;
                        width: 78%;
                        color: {text_color};
                        font-family: '{font_name}', serif;
                    ">
                        <div style="
                            color: {accent};
                            border-bottom: 3px solid {accent};
                            padding-bottom: 5px;
                            font-size: {title_size}px;
                            font-weight: bold;
                            line-height: 1.15;
                            margin-bottom: 10px;
                        ">Your Report Title</div>
                        <div style="
                            color: {accent};
                            font-size: {heading_size}px;
                            font-weight: bold;
                            margin-bottom: 5px;
                        ">Section Heading</div>
                        <div style="
                            font-size: {body_size}px;
                            line-height: 1.35;
                        ">Report text will appear here, formatted in
                        {font_name}.</div>
                    </div>
                    <div style="
                        color: {accent};
                        font-size: 18px;
                        font-weight: 700;
                    ">{escaped_name}</div>
                    <div style="color: #604d5b; min-height: 44px;">
                        {description}
                    </div>
                    <div style="color: #604d5b; font-size: 13px;">
                        <span style="display:inline-block;background:{accent};width:11px;height:11px;border-radius:50%;margin-right:6px;"></span>
                        {font_name} · {body_size} pt body ·
                        {title_size} pt title
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                selection_label,
                key=f"select_template_{index}",
                type=selection_type,
                use_container_width=True,
                disabled=selected,
            ):
                st.session_state["selected_template"] = template_name
                st.rerun()

            with st.expander(f"Preview {template_name}"):
                preview_title = escape(
                    report_title.strip() or "Your Report Title"
                )
                preview_author = escape(
                    author_name.strip() or "Prepared by: Your Name"
                )
                st.markdown(
                    f"""
                    <div style="
                        background: white;
                        border: 1px solid #ded6e0;
                        box-shadow: 0 3px 12px #00000012;
                        color: {text_color};
                        font-family: '{font_name}', serif;
                        margin: 0 auto;
                        max-width: 620px;
                        min-height: 390px;
                        padding: {settings['margins']['top']}in
                            {settings['margins']['right']}in
                            {settings['margins']['bottom']}in
                            {settings['margins']['left']}in;
                    ">
                        <div style="
                            color: {accent};
                            border-bottom: 3px solid {accent};
                            padding-bottom: 10px;
                            font-size: {title_size}px;
                            font-weight: bold;
                            margin-bottom: 22px;
                        ">{preview_title}</div>
                        <div style="
                            color: {accent};
                            font-size: {heading_size}px;
                            font-weight: bold;
                            margin: 16px 0 8px;
                        ">Introduction</div>
                        <div style="
                            font-size: {body_size}px;
                            line-height: 1.6;
                        ">
                            This is a preview of how your report text will
                            appear using the {escaped_name} template. Your
                            selected content and headings will use this
                            typography and page layout.
                        </div>
                        <div style="
                            color: {accent};
                            font-size: {heading_size}px;
                            font-weight: bold;
                            margin: 18px 0 8px;
                        ">Key Findings</div>
                        <div style="
                            font-size: {body_size}px;
                            line-height: 1.6;
                        ">Section headings and body paragraphs follow the
                        same template formatting.</div>
                        <div style="
                            border-top: 1px solid #ded6e0;
                            color: #604d5b;
                            font-size: 10px;
                            margin-top: 30px;
                            padding-top: 8px;
                        ">{preview_author}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    selected_template = st.session_state["selected_template"]


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
            config["author"] = author_name.strip()
            config["template_name"] = selected_template
            config["include_cover_page"] = include_cover_page
            config["include_index"] = include_index
            config["section_per_page"] = section_per_page

            # Generate the document in memory.
            document_bytes = BytesIO()

            if use_ai:
                with st.spinner("Organising your content with AI..."):
                    structured_report = structure_report(
                        report_text,
                        report_type=selected_template,
                        custom_instructions=custom_notes.strip() if custom_notes else None,
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
        type="primary",
        use_container_width=True,
    )


# --------------------------------------------------
# 10. FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "© 2026 Srivalli Pingali. All rights reserved. | "
)
