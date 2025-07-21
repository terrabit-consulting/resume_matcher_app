
import openai
import streamlit as st
import time
import fitz  # PyMuPDF
import docx
import pandas as pd

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
        st.warning(f"⚠️ GPT-4o failed. Reason: {str(e)}\nFalling back to GPT-3.5-turbo...")
        time.sleep(1)
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return response.choices[0].message.content.strip()
        except Exception as e2:
            st.error(f"❌ Both models failed.\nError: {str(e2)}")
            return "⚠️ Failed to generate response due to API errors."

def extract_candidate_name(resume_text, filename):
    lines = resume_text.splitlines()
    for line in lines[:10]:
        if "name:" in line.lower():
            return line.split(":")[1].strip()
    return filename.split("_")[1] if "_" in filename else filename.replace(".docx", "")

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

st.set_page_config(page_title="Resume Matcher GPT", layout="centered")
st.title("🤖 Resume Matcher Bot (GPT-4o → 3.5 fallback)")
st.write("Upload a JD and multiple resumes. This tool gives match scores, red flags, and optional messaging.")

if 'results' not in st.session_state:
    st.session_state['results'] = {}

jd_file = st.file_uploader("📌 Upload Job Description", type=["txt", "pdf", "docx"])
resume_files = st.file_uploader("📥 Upload Candidate Resumes", type=["txt", "pdf", "docx"], accept_multiple_files=True)

if st.button("Run Matching") and jd_file and resume_files:
    jd_text = read_file(jd_file)
    st.session_state['results'].clear()

    for resume_file in resume_files:
        resume_text = read_file(resume_file)
        candidate_name = extract_candidate_name(resume_text, resume_file.name)
        with st.spinner(f"🔍 Analyzing {candidate_name}..."):
            result = compare_resume(jd_text, resume_text, candidate_name)
        st.session_state['results'][resume_file.name] = {
            'candidate': candidate_name,
            'result': result,
            'jd_text': jd_text,
            'resume_text': resume_text
        }

summary = []
for resume_name, data in st.session_state['results'].items():
    st.markdown("---")
    st.subheader(f"📛 {resume_name}")

    st.markdown(data['result'])

    try:
        score_line = next((line for line in data['result'].splitlines() if "Score" in line), "")
        score = int(score_line.split(":")[1].strip().replace("%", "").replace("**", ""))
    except:
        score = 0

    if score < 50:
        st.error("❌ Not suitable – Major role mismatch")
    elif score < 70:
        st.warning("⚠️ Consider with caution – Some relevant experience but lacks core skills")
    else:
        st.success("✅ Strong match – Good alignment with JD")

    summary.append({"Candidate": data['candidate'], "Score": score})

    if st.button(f"📩 Generate Follow-up for {data['candidate']}", key=f"followup_{resume_name}"):
        with st.spinner("Generating messages..."):
            followup = generate_followup(data['jd_text'], data['resume_text'])
            st.markdown("---")
            st.markdown(followup)

if summary:
    st.markdown("### 📊 Summary of All Candidates")
    df = pd.DataFrame(summary).sort_values(by="Score", ascending=False)
    st.dataframe(df)
