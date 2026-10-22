
import streamlit as st
from google import genai

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=(
            "Reply with exactly: "
            "DocScholar Gemini connection successful."
        ),
    )

    print(response.text)

except Exception as error:
    print("Gemini test failed.")
    print("Error type:", type(error).__name__)
    print("Error details:", error)

