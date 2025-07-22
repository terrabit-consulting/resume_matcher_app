import openai
import streamlit as st
import time
import fitz  # PyMuPDF
import docx
import pandas as pd
import re
import io
import spacy

@st.cache_resource
def load_spacy_model():
    return spacy.load("en_core_web_sm")

nlp = load_spacy_model()

# --- Secure OpenAI Client ---
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def call_gpt_with_fallback(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"\u274c GPT-4o failed. {str(e)}")
        return "\u26a0\ufe0f GPT processing failed."

# --- File Readers ---
def read_pdf(file):
    text = ""
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def read_file(file):
    if file.type == "application/pdf":
        return read_pdf(file)
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return read_docx(file)
    else:
        return file.read().decode("utf-8", errors="ignore")

# --- Name and Email Extractors ---
def extract_candidate_name(text, filename):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        if re.search(r"Candidate Name\\s*$", line, re.IGNORECASE) and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if 2 <= len(next_line.split()) <= 4:
                return next_line.title()

    for line in lines:
        if re.search(r"(Candidate Name|Name)\\s*[:\-]", line, re.IGNORECASE):
            name_part = re.split(r"[:\-]", line, 1)[-1].strip()
            if 2 <= len(name_part.split()) <= 4 and not re.search(r"(Tester|Engineer|Developer|Manager|Resume|CV)", name_part, re.IGNORECASE):
                return name_part.title()

    sample_text = "\n".join(lines[:15] + lines[-15:])
    doc = nlp(sample_text)
    for ent in doc.ents:
        if ent.label_ == "PERSON" and 2 <= len(ent.text.split()) <= 4:
            return ent.text.strip().title()

    name = filename.replace(".docx", "").replace(".pdf", "").replace(".txt", "")
    name = re.sub(r"[_\-.]", " ", name)
    name = re.sub(r"\b(Resume|CV|Terrabit Consulting|ID \d+|Developer|Engineer|V\d+)\b", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name)
    return name.strip().title()

def extract_email(text):
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}", text)
    return match.group() if match else "Not found"

# --- Resume Comparator ---
def compare_resume(jd_text, resume_text, candidate_name):
    prompt = f"""
You are a Recruiter Assistant bot.

Compare the following resume to the job description and return the result in the following format:

**Name**: {candidate_name}
**Score**: [Match Score]%

**Reason**:
- Role Match: (Brief explanation)
- Skill Match: (Matched or missing skills)
- Major Gaps: (What is completely missing or irrelevant)

Warning: Add only if score < 70%

Job Description:
{jd_text}

Resume:
{resume_text}
"""
    return call_gpt_with_fallback(prompt)

def generate_followup(jd_text, resume_text):
    prompt = f"""
Based on the resume and job description below, generate:
1. WhatsApp message (casual)
2. Email message (formal)
3. Screening questions (3-5)

Job Description:
{jd_text}

Resume:
{resume_text}
"""
    return call_gpt_with_fallback(prompt)

# --- Streamlit UI ---
st.set_page_config(page_title="Resume Matcher GPT", layout="centered")
st.title("Resume Matcher Bot")
st.write("Upload a JD and multiple resumes. Get match scores, red flags, and follow-up messaging.")

if "results" not in st.session_state:
    st.session_state["results"] = []
if "processed_resumes" not in st.session_state:
    st.session_state["processed_resumes"] = set()
if "jd_text" not in st.session_state:
    st.session_state["jd_text"] = ""
if "jd_file" not in st.session_state:
    st.session_state["jd_file"] = None

if st.button("Start New Matching Session"):
    st.session_state.clear()
    st.rerun()

jd_file = st.file_uploader("Upload Job Description", type=["txt", "pdf", "docx"], key="jd_uploader")
resume_files = st.file_uploader("Upload Candidate Resumes", type=["txt", "pdf", "docx"], accept_multiple_files=True, key="resume_uploader")

if jd_file and not st.session_state.get("jd_text"):
    st.session_state["jd_text"] = read_file(jd_file)
    st.session_state["jd_file"] = jd_file.name

jd_text = st.session_state.get("jd_text", "")

if st.button("Run Matching") and jd_text and resume_files:
    for resume_file in resume_files:
        if resume_file.name in st.session_state["processed_resumes"]:
            continue
        resume_text = read_file(resume_file)
        correct_name = extract_candidate_name(resume_text, resume_file.name)
        correct_email = extract_email(resume_text)

        with st.spinner(f"Analyzing {correct_name}..."):
            result = compare_resume(jd_text, resume_text, correct_name)

        score_match = re.search(r"Score\*\*: \**([0-9]+)%", result)
        score = int(score_match.group(1)) if score_match else 0

        st.session_state["results"].append({
            "name": correct_name,
            "email": correct_email,
            "score": score,
            "result": result,
            "resume_text": resume_text
        })
        st.session_state["processed_resumes"].add(resume_file.name)

summary = []
for entry in st.session_state["results"]:
    st.markdown("---")
    st.subheader(entry["name"])
    st.markdown(f"**Email**: {entry['email']}")
    st.markdown(entry["result"])

    score = entry["score"]
    if score < 50:
        st.error("Not suitable – Major role mismatch")
    elif score < 70:
        st.warning("Consider with caution – Lacks core skills")
    else:
        st.success("Strong match – Good alignment with JD")

    summary.append({"Candidate": entry["name"], "Email": entry["email"], "Score": score})

    if st.button(f"Generate Follow-up for {entry['name']}", key=f"followup_{entry['name']}"):
        with st.spinner("Generating messages..."):
            followup = generate_followup(jd_text, entry["resume_text"])
            st.markdown("---")
            st.markdown(followup)

if summary:
    st.markdown("### Summary of All Candidates")
    df_summary = pd.DataFrame(summary).sort_values(by="Score", ascending=False)
    st.dataframe(df_summary)

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df_summary.to_excel(writer, index=False)

    st.download_button(
        label="Download Summary as Excel",
        data=excel_buffer.getvalue(),
        file_name="resume_match_summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
