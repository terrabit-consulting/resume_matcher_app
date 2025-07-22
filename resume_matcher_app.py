import streamlit as st
import fitz  # PyMuPDF
import docx
import pandas as pd
import re
import openai
import os

st.write("✅ App started")

# Set up OpenAI client
try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    st.write("✅ OpenAI client initialized")
except Exception as e:
    st.error(f"❌ Failed to init OpenAI: {e}")

# Load spaCy model
try:
    import spacy
    st.write("📦 Loading spaCy model...")
    @st.cache_resource
    def load_spacy_model():
        return spacy.load("en_core_web_sm")
    nlp = load_spacy_model()
    st.write("✅ spaCy model loaded")
except Exception as e:
    st.error(f"❌ spaCy load failed: {e}")

# File upload section
st.write("📂 Waiting for JD and resumes...")
jd_file = st.file_uploader("Upload Job Description", type=["pdf", "docx", "txt"])
resume_files = st.file_uploader("Upload Resumes", accept_multiple_files=True, type=["pdf", "docx", "txt"])

if jd_file:
    st.write(f"📄 JD uploaded: {jd_file.name}")

if resume_files:
    st.write(f"📄 {len(resume_files)} resume(s) uploaded")

st.write("🧪 App loaded basic UI successfully.")
