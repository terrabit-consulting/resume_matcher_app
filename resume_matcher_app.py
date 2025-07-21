import openai
import streamlit as st
import time
import fitz  # PyMuPDF
import docx

# ✅ Secure OpenAI API client
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ✅ Fallback logic: Try GPT-4o → fall back to GPT-3.5
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

# 🔍 Compare JD and Resume
def compare_resume(jd_text, resume_text):
    prompt = f"""
    You are a recruiter assistant.
    Compare the following resume to the job description. Return:
    1. 📛 Candidate Name
    2. ✅ Match Score (%)
    3. 🔍 Key reasons for the score
    4. ⚠️ Warning if score < 70%
    
    Job Description:
    {jd_text}
    
    Resume:
    {resume_text}
    """
    return call_gpt_with_fallback(prompt)

# 💬 Generate WhatsApp, Email, and Screening Questions
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

# 📚 PDF reader helper (PyMuPDF)
def read_pdf(file):
    text = ""
    pdf_doc = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf_doc:
        text += page.get_text()
    return text

# 📚 DOCX reader helper
def read_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

# 📚 Universal file reader
def read_file(file):
    if file.type == "application/pdf":
        return read_pdf(file)
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return read_docx(file)
    else:
        return file.read().decode("utf-8", errors="ignore")

# 🎯 Streamlit UI
st.set_page_config(page_title="Resume Matcher GPT", layout="centered")
st.title("📄 Resume Matcher Bot (GPT-4o → 3.5 fallback)")
st.write("Upload a JD + candidate resumes to get match scores, WhatsApp, email, and screening questions.")

# Session state initialization
if 'results' not in st.session_state:
    st.session_state['results'] = {}

# 📂 File uploads
jd_file = st.file_uploader("📌 Upload Job Description", type=["txt", "pdf", "docx"])
resume_files = st.file_uploader("📥 Upload Candidate Resumes", type=["txt", "pdf", "docx"], accept_multiple_files=True)

# 🚀 Run Matching Logic
if st.button("Run Matching") and jd_file and resume_files:
    jd_text = read_file(jd_file)
    st.session_state['results'].clear()

    for resume_file in resume_files:
        resume_text = read_file(resume_file)
        with st.spinner(f"🔍 Analyzing {resume_file.name}..."):
            result = compare_resume(jd_text, resume_text)
        st.session_state['results'][resume_file.name] = {
            'result': result,
            'jd_text': jd_text,
            'resume_text': resume_text
        }

# Display results
for resume_name, data in st.session_state['results'].items():
    st.markdown("---")
    st.subheader(f"📛 {resume_name}")
    st.markdown(data['result'])

    btn_key = f"followup_{resume_name}"
    if st.button(f"✅ Generate WhatsApp/Email/Screening for {resume_name}", key=btn_key):
        with st.spinner("Generating messages..."):
            followup = generate_followup(data['jd_text'], data['resume_text'])
            st.success("🎉 Messages generated!")
            st.markdown(followup)
