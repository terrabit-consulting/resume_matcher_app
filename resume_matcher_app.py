import openai
import streamlit as st

# ✅ Use OpenAI SDK v1.x style
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 🔍 Compare JD and Resume
def compare_resume(jd_text, resume_text):
    prompt = f"""
You are a recruiter assistant.

Compare the following resume to the job description. Return:
1. 📛 Candidate Name
2. ✅ Match Score (%)
3. 🔍 Key reasons for the score
4. ⚠️ Warning if score < 70%

Do NOT generate any messages until asked.

Job Description:
{jd_text}

Resume:
{resume_text}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

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
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

# 🎯 Streamlit UI
st.set_page_config(page_title="Resume Matcher GPT", layout="centered")
st.title("📄 Resume Matcher Bot (GPT-4o)")
st.write("Upload a JD + one or more resumes. Get match scores, then generate messages.")

jd_file = st.file_uploader("📌 Upload JD", type=["txt", "pdf", "docx"])
resume_files = st.file_uploader("📥 Upload Resumes", type=["txt", "pdf", "docx"], accept_multiple_files=True)

if st.button("Run Matching") and jd_file and resume_files:
    jd_text = jd_file.read().decode("utf-8", errors="ignore")
    followup_states = {}

    for idx, resume_file in enumerate(resume_files):
        resume_text = resume_file.read().decode("utf-8", errors="ignore")
        with st.spinner(f"Analyzing {resume_file.name}..."):
            result = compare_resume(jd_text, resume_text)

        st.markdown("---")
        st.subheader(f"📛 {resume_file.name}")
        st.markdown(result)

        followup_key = f"followup_{idx}"
        if st.button(f"✅ Generate WhatsApp/Email/Screening for {resume_file.name}", key=followup_key):
            with st.spinner("Generating messages..."):
                followup = generate_followup(jd_text, resume_text)
                st.success("🎉 Messages generated!")
                st.markdown(followup)
