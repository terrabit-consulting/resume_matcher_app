import openai
import streamlit as st
import time
import fitz  # PyMuPDF
import docx
import pandas as pd
import re

# ----------------------------
# ✅ Secure OpenAI API Client
# ----------------------------
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ----------------------------
# ✅ GPT with Fallback
# ----------------------------
def call_gpt_with_fallback(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.warning(f"⚠️ GPT-4o failed: {str(e)}. Falling back to GPT-3.5-turbo...")
        time.sleep(1)
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return response.choices[0].message.content.strip()
        except Exception as e2:
            st.error(f"❌ Both models failed. Error: {str(e2)}")
            return "⚠️ Failed to generate response due to API errors."

# ----------------------------
# ✅ Read file types
# ----------------------------
def read_pdf(file):
    text = ""
    pdf_doc = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf_doc:
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

# ----------------------------
# ✅ Extract Candidate Name
# ----------------------------
def extract_candidate_name(resume_text, filename):
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]

    for line in lines[:10]:
        if "name:" in line.lower():
            return line.split(":", 1)[1].strip()

    for line in lines[:15]:
        match = re.search(r"(resume|cv)\s+of[:\-]?\s*(.+)", line, re.IGNORECASE)
        if match:
            return match.group(2).strip()

    if len(lines) > 0 and 2 <= len(lines[0].split()) <= 5:
        return lines[0]

    name = re.sub(r"[_\-.]+", " ", filename.replace(".pdf", "").replace(".docx", "").replace(".txt", ""))
    return name.strip().title()

# ----------------------------
# ✅ GPT Resume Comparison
# ----------------------------
def compare_resume(jd_text, resume_text, candidate_name):
    prompt = f"""
You are a Recruiter Assistant bot.

Compare the following resume to the job description and return the result in the following format:

💼 **Name**: {candidate_name}
✅ **Score**: [Match Score]%

🔧 **Reason**:
- ⚠️ **Role Match**: (Brief explanation)
- ✅ **Skill Match**: (Matched or missing skills)
- ❌ **Major Gaps**: (What is completely missing or irrelevant)

⚠️ **Warning**: Add only if score < 70%

Job Description:
{jd_text}

Resume:
{resume_text}
"""
    return call_gpt_with_fallback(prompt)

# ----------------------------
# ✅ GPT Follow-Up Message
# ----------------------------
def generate_followup(jd_text, resume_text):
    prompt = f"""
Based on the resume and job description below, generate:
1. 📱 WhatsApp message (casual)
2. 📧 Email message (formal)
3. 🧠 Screening questions (3-5)

Job Description:
{jd_text}

Resume:
{resume_text}
"""
    return call_gpt_with_fallback(prompt)

# ----------------------------
# ✅ Streamlit App UI
# ----------------------------
st.set_page_config(page_title="Resume Matcher GPT", layout="centered")
st.title("🤖 Resume Matcher Bot (GPT-4o → 3.5 fallback)")
st.write("Upload a JD and multiple resumes. This tool gives match scores, red flags, and optional messaging.")

# ----------------------------
# ✅ Session State Init
# ----------------------------
if "results" not in st.session_state:
    st.session_state["results"] = []

if "processed_resumes" not in st.session_state:
    st.session_state["processed_resumes"] = set()

# ----------------------------
# 🔄 Reset Button
# ----------------------------
if st.button("🔄 Start New Matching Session"):
    st.session_state.clear()
    st.rerun()

# ----------------------------
# 📤 Upload JD + Resumes
# ----------------------------
jd_file = st.file_uploader("📌 Upload Job Description", type=["txt", "pdf", "docx"])
resume_files = st.file_uploader("📄 Upload Candidate Resumes", type=["txt", "pdf", "docx"], accept_multiple_files=True)

# ----------------------------
# 📝 Read JD text
# ----------------------------
if jd_file and "jd_text" not in st.session_state:
    st.session_state["jd_text"] = read_file(jd_file)

jd_text = st.session_state.get("jd_text", "")

# ----------------------------
# ▶️ Run Resume Matching
# ----------------------------
if st.button("Run Matching") and jd_text and resume_files:
    for resume_file in resume_files:
        if resume_file.name in st.session_state["processed_resumes"]:
            continue

        resume_text = read_file(resume_file)
        candidate_name = extract_candidate_name(resume_text, resume_file.name)

        with st.spinner(f"🔍 Analyzing {candidate_name}..."):
            result = compare_resume(jd_text, resume_text, candidate_name)

        # Extract better name if GPT returned one
        match = re.search(r"\*\*Name\*\*:\s*(.+)", result)
        if match:
            name_candidate = match.group(1).strip()
            if len(name_candidate.split()) <= 5 and not name_candidate.lower().startswith("bachelor"):
                candidate_name = name_candidate

        # Extract Score
        score_match = re.search(r"Score\*\*:\s*([0-9]+)%", result)
        score = int(score_match.group(1)) if score_match else 0

        # Store result
        st.session_state["results"].append({
            "name": candidate_name,
            "score": score,
            "result": result,
            "resume_text": resume_text
        })

        st.session_state["processed_resumes"].add(resume_file.name)

# ----------------------------
# 📊 Show Results
# ----------------------------
summary = []
for entry in st.session_state["results"]:
    st.markdown("---")
    st.subheader(f"💼 {entry['name']}")
    st.markdown(entry["result"])

    score = entry["score"]
    if score < 50:
        st.error("❌ Not suitable – Major role mismatch")
    elif score < 70:
        st.warning("⚠️ Consider with caution – Some relevant experience but lacks core skills")
    else:
        st.success("✅ Strong match – Good alignment with JD")

    summary.append({"Candidate": entry["name"], "Score": score})

    if st.button(f"📩 Generate Follow-up for {entry['name']}", key=f"followup_{entry['name']}"):
        with st.spinner("Generating messages..."):
            followup = generate_followup(jd_text, entry["resume_text"])
            st.markdown("---")
            st.markdown(followup)

if summary:
    st.markdown("### 📊 Summary of All Candidates")
    st.dataframe(pd.DataFrame(summary).sort_values(by="Score", ascending=False))
