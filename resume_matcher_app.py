import streamlit as st
import fitz  # PyMuPDF
import docx
import pandas as pd
import re
import openai
import os
import subprocess

st.set_page_config(page_title="🧪 Resume Matcher Debug", layout="centered")
st.title("🧪 Debug: Resume Matcher App")
st.write("✅ App started")

# ✅ OpenAI Client Setup
try:
    client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    st.success("✅ OpenAI client initialized")
except Exception as e:
    st.error(f"❌ OpenAI init failed: {e}")

# ✅ Load spaCy model with fallback
try:
    import spacy

    st.write("📦 Checking spaCy model...")

    @st.cache_resource
    def load_spacy_model():
        try:
            return spacy.load("en_core_web_sm")
        except OSError:
            st.warning("⚠️ spaCy model not found. Downloading...")
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            return spacy.load("en_core_web_sm")

    nlp = load_spacy_model()
    st.success("✅ spaCy model loaded")
except Exception as e:
    st.error(f"❌ spaCy load failed: {e}")

# ✅ File Upload Section
st.subheader("📂 Upload Section")
jd_file = st.file_uploader("📌 Upload Job Description", type=["pdf", "docx", "txt"])
resume_files = st.file_uploader("📄 Upload Candidate Resumes", accept_multiple_files=True, type=["pdf", "docx", "txt"])

if jd_file:
    st.success(f"✅ JD uploaded: `{jd_file.name}`")

if resume_files:
    st.success(f"✅ {len(resume_files)} resume(s) uploaded")

st.info("✅ Debug App loaded successfully. No GPT or scoring logic runs here.")
