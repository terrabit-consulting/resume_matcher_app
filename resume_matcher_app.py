# ✅ Final cleaned and complete version of resume_matcher_app.py with robust spaCy handling
import openai
import streamlit as st
import time
import fitz  # PyMuPDF
import docx
import pandas as pd
import re

# ✅ Optional spaCy fallback with auto-download on Streamlit Cloud
ttry:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
    except:
        import subprocess
        subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
        nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None

# ✅ OpenAI API setup
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def call_gpt_with_fallback(prompt):
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        st.warning(f"GPT-4o failed: {e}. Falling back to GPT-3.5-turbo...")
        time.sleep(1)
        try:
            resp = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return resp.choices[0].message.content.strip()
        except Exception as e2:
            st.error(f"Both models failed: {e2}")
            return "⚠️ API Error - unable to generate response."

# ✅ Name extraction helpers
def clean_filename_name(name: str) -> str:
    name = re.sub(r"[_\-.]+", " ", name)
    return name.strip().title()

def extract_candidate_name(resume_text: str, filename: str) -> str:
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    for line in lines[:10]:
        if "name:" in line.lower():
            return line.split(":", 1)[1].strip()
    if lines and len(lines[0].split()) <= 5:
        return lines[0]
    if nlp:
        doc = nlp(resume_text[:500])
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text
    return clean_filename_name(filename.rsplit(".", 1)[0])

# ✅ GPT prompts
def compare_resume(jd_text, resume_text, candidate_name):
    prompt = f"""
You are a Recruiter Assistant bot.

Compare the following resume to the job description and return the result in the following format:

📛 **Name**: {candidate_name}
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

# ✅ File handling
def read_pdf(file):
    text = ""
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf:
        text += page.get_text()
    return text

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join(para.text for para in doc.paragraphs)

def read_file(file):
    if file.type == "application/pdf":
        return read_pdf(file)
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return read_docx(file)
    else:
        return file.read().decode("utf-8", errors="ignore")

# ✅ Streamlit UI
st.set_page_config(page_title="Resume Matcher GPT", layout="centered")
st.title("🤖 Resume Matcher Bot (GPT-4o → 3.5 fallback)")
st.write("Upload a JD and multiple resumes. This tool gives match scores, red flags, and optional messaging.")

if 'results' not in st.session_state:
    st.session_state['results'] = {}

if 'processed_resumes' not in st.session_state:
    st.session_state['processed_resumes'] = set()

if st.button("🔄 Start New Matching Session"):
    st.session_state['results'].clear()
    st.session_state['processed_resumes'].clear()
    st.session_state.pop('jd_text', None)
    st.experimental_rerun()

jd_file = st.file_uploader("📌 Upload Job Description", type=["txt", "pdf", "docx"])
resume_files = st.file_uploader("📥 Upload Candidate Resumes", type=["txt", "pdf", "docx"], accept_multiple_files=True)

if jd_file and 'jd_text' not in st.session_state:
    st.session_state['jd_text'] = read_file(jd_file)

jd_text = st.session_state.get('jd_text', '')

if st.button("Run Matching") and jd_text and resume_files:
    for resume_file in resume_files:
        if resume_file.name in st.session_state['processed_resumes']:
            continue
        resume_text = read_file(resume_file)
        candidate_name = extract_candidate_name(resume_text, resume_file.name)
        with st.spinner(f"🔍 Analyzing {candidate_name}..."):
            result = compare_resume(jd_text, resume_text, candidate_name)
        m = re.search(r"\*\*Name\*\*:\s*(.+)", result)
        if m:
            candidate_name = m.group(1).strip()
        st.session_state['results'][resume_file.name] = {
            'candidate': candidate_name,
            'result': result,
            'jd_text': jd_text,
            'resume_text': resume_text
        }
        st.session_state['processed_resumes'].add(resume_file.name)

summary = []
for fname, data in st.session_state['results'].items():
    st.markdown("---")
    st.subheader(f"📛 {data['candidate']}")
    st.markdown(data['result'])

    try:
        line = next(l for l in data['result'].splitlines() if "Score" in l)
        score = int(re.search(r"(\d+)%", line).group(1))
    except:
        score = 0

    if score < 50:
        st.error("❌ Not suitable – Major role mismatch")
    elif score < 70:
        st.warning("⚠️ Consider with caution – Some relevant experience but lacks core skills")
    else:
        st.success("✅ Strong match – Good alignment with JD")

    summary.append({"Candidate": data['candidate'], "Score": score})

    if st.button(f"📩 Generate Follow-up for {data['candidate']}", key=f"followup_{fname}"):
        with st.spinner("Generating messages..."):
            followup = generate_followup(data['jd_text'], data['resume_text'])
            st.markdown("---")
            st.markdown(followup)

if summary:
    st.markdown("### 📊 Summary of All Candidates")
    df = pd.DataFrame(summary).sort_values("Score", ascending=False).reset_index(drop=True)
    st.dataframe(df)
