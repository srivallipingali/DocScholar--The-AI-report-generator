
import streamlit as st

st.title("DocScholar Diagnostic Test")
st.write("If you can see this, Streamlit is rendering.")
name = st.text_input("Type something here")
st.write("You typed:", name)
