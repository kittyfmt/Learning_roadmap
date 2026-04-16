"""
Career Roadmap — home: upload documents, set budget, launch the analysis pipeline.
"""
import streamlit as st
import sys
from backend.streamlit_helpers import text_from_upload
import subprocess
try:
    import pkg_resources
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools"])
    import pkg_resources

st.set_page_config(
    page_title="Career Roadmap",
    page_icon="\U0001f9ed",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');
    html, body, [class*="css"]  { font-family: 'DM Sans', sans-serif; }
    .block-container { padding-top: 2rem; max-width: 1200px; }
    div.stButton > button[kind="primary"] {
        background: #5f738a;
        border: 1px solid #506174;
        color: #ffffff;
        font-weight: 800;
        font-size: 1.08rem;
        min-height: 3.1rem;
        box-shadow: 0 16px 30px -18px rgba(71, 85, 105, 0.55);
    }
    div.stButton > button[kind="primary"]:hover {
        background: #526577;
        color: #ffffff;
        transform: translateY(-1px);
    }
    div.stButton > button[kind="primary"]:active {
        transform: translateY(0px);
        background: #495a6b;
        color: #ffffff;
    }
    .hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 45%, #312e81 100%);
        color: #f8fafc;
        padding: 2.5rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.45);
    }
    .hero h1 { margin: 0 0 0.5rem 0; font-size: 2.1rem; font-weight: 700; letter-spacing: -0.02em; }
    .hero p { margin: 0; opacity: 0.9; font-size: 1.05rem; line-height: 1.55; }
    .upload-card {
        background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.5rem;
        min-height: 200px;
        box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.06);
    }
    .upload-card h3 { margin-top: 0; color: #0f172a; font-size: 1.1rem; }
    .info-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #dbe4ee;
        border-radius: 18px;
        padding: 1.35rem 1.45rem;
        min-height: 220px;
        box-shadow: 0 10px 24px -18px rgba(15, 23, 42, 0.28);
        margin-bottom: 1.25rem;
    }
    .info-card h3 {
        margin: 0 0 0.8rem 0;
        color: #0f172a;
        font-size: 1.18rem;
        font-weight: 700;
    }
    .info-card p {
        margin: 0 0 0.85rem 0;
        color: #475569;
        line-height: 1.6;
        font-size: 0.98rem;
    }
    .feature-list {
        margin: 0;
        padding-left: 1.1rem;
        color: #334155;
        line-height: 1.7;
        font-size: 0.95rem;
    }
    .pipeline-steps {
        display: flex;
        flex-direction: column;
        gap: 0.7rem;
    }
    .pipeline-step {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.8rem;
        padding: 0.85rem 1rem;
        border-radius: 14px;
        background: #eef2f7;
        border: 1px solid #d5deea;
        color: #0f172a;
        font-weight: 700;
    }
    .pipeline-step span {
        display: inline-block;
        color: #475569;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .pipeline-arrow {
        text-align: center;
        color: #64748b;
        font-size: 1.2rem;
        font-weight: 700;
        line-height: 1;
        margin: -0.2rem 0;
    }
    /* Unified long rectangle for overview + pipeline (no split outer cards) */
    .long-info-card {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #dbe4ee;
        border-radius: 18px;
        padding: 1.35rem 1.45rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 10px 24px -18px rgba(15, 23, 42, 0.28);
    }
    .long-info-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;
        align-items: start;
    }
    .long-info-section {
        min-height: 160px;
    }
    .long-info-section + .long-info-section {
        border-left: 1px solid #e5e7eb;
        padding-left: 1.5rem;
    }
    .long-info-section h3 {
        margin: 0 0 0.8rem 0;
        color: #0f172a;
        font-size: 1.18rem;
        font-weight: 700;
    }
    .long-info-section p {
        margin: 0 0 0.85rem 0;
        color: #475569;
        line-height: 1.6;
        font-size: 0.98rem;
    }
    div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdown"] .hero) {
        margin-bottom: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>Career learning roadmap</h1>
        <p>Map job-description skills to your resume, surface gaps, and build a sequenced course path with direct links.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Top-of-page unified visualization card (app overview + pipeline)
st.markdown(
    """
    <div class="long-info-card">
        <div class="long-info-grid">
            <div class="long-info-section">
                <h3>App overview</h3>
                <p>
                    Upload your resume and the target job description. The app compares them to surface missing skills,
                    then turns them into a sequenced learning roadmap.
                </p>
                <ul class="feature-list">
                    <li>Extract resume skills and JD requirements</li>
                    <li>Highlight the most relevant missing skills</li>
                    <li>Recommend a practical course path within your time budget</li>
                </ul>
            </div>
            <div class="long-info-section">
                <h3>Pipeline</h3>
                <div class="pipeline-steps">
                    <div class="pipeline-step">1. Upload inputs <span>(Resume + JD)</span></div>
                    <div class="pipeline-arrow">↓</div>
                    <div class="pipeline-step">2. Analyze skills <span>(Extract + match + gap detection)</span></div>
                    <div class="pipeline-arrow">↓</div>
                    <div class="pipeline-step">3. Build roadmap <span>(Prioritized courses and next steps)</span></div>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2 = st.columns(2, gap="large")

with c1:
    st.subheader("Resume")
    resume_file = st.file_uploader("PDF or TXT", type=["pdf", "txt"], key="resume_up", label_visibility="collapsed")
    resume_paste = st.text_area(
        "Or paste the resume as text",
        height=140,
        placeholder="Paste resume text here if you prefer...",
        key="resume_paste",
    )

with c2:
    st.subheader("Job description")
    jd_file = st.file_uploader("PDF or TXT", type=["pdf", "txt"], key="jd_up", label_visibility="collapsed")
    jd_paste = st.text_area("Or paste the JD as text", height=140, placeholder="Paste full job description here if you prefer...")

go = st.button("Run skill pipeline", type="primary", use_container_width=True)

if go:
    resume_text = text_from_upload(resume_file) if resume_file else (resume_paste or "").strip()
    if jd_file:
        jd_text = text_from_upload(jd_file)
    else:
        jd_text = (jd_paste or "").strip()

    if not resume_text:
        st.error("Please upload a resume (PDF or TXT).")
    elif not jd_text:
        st.error("Please upload a job description or paste its text.")
    else:
        st.session_state["jd_text"] = jd_text
        st.session_state["resume_text"] = resume_text
        st.session_state.pop("missing_skills", None)
        st.session_state.pop("refresher_skills", None)
        st.session_state.pop("jd_skill_rows", None)
        st.session_state.pop("resume_skills_list", None)
        st.session_state.pop("budget", None)
        st.switch_page("pages/1_Missing_Skills.py")
