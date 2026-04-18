"""Analysis workspace: extraction, JD scoring, gap summary, roadmap launch."""
import html
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.streamlit_helpers import get_pipeline_models

st.set_page_config(page_title="Skill analysis", page_icon="\U0001f50d", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
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
        background: #495a6b;
        color: #ffffff;
        transform: translateY(0px);
    }
    .step-strip {
        display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0 1.5rem 0;
    }
    .step-pill {
        background: linear-gradient(135deg, #e0e7ff, #fae8ff);
        color: #3730a3;
        padding: 0.35rem 0.85rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .skill-cloud span {
        display: inline-block;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        color: #334155;
        padding: 0.2rem 0.55rem;
        border-radius: 8px;
        margin: 0.2rem;
        font-size: 0.78rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "jd_text" not in st.session_state or "resume_text" not in st.session_state:
    st.warning("Start from the home page and upload your resume and job description.")
    st.stop()

st.title("Skill analysis workspace")
st.markdown(
    '<div class="step-strip">'
    '<span class="step-pill">1 &mdash; Source text</span>'
    '<span class="step-pill">2 &mdash; Resume skills</span>'
    '<span class="step-pill">3 &mdash; JD skills &amp; match</span>'
    '<span class="step-pill">4 &mdash; Gap</span>'
    '<span class="step-pill">5 &mdash; Roadmap</span>'
    "</div>",
    unsafe_allow_html=True,
)


@st.cache_data
def run_extraction(jd_text: str, resume_text: str):
    resume_ex, jd_ex, opt = get_pipeline_models()
    resume_skills = resume_ex.extract_skills(resume_text, include_ngram_scored=True)
    jd_results = jd_ex.extract(jd_text, resume_text, resume_extracted_skills=resume_skills)
    missing = opt.calculate_gap(jd_results, resume_skills)
    refresher = opt.build_refresher_specs(jd_results)
    ref_tuple = tuple((r["skill"], r["relevance"], r["priority"]) for r in refresher)
    jd_rows = tuple(
        (
            r.canonical_name,
            r.category,
            round(r.relevance_score, 3),
            round(r.difficulty_score, 3),
            r.priority_level,
            r.is_matched,
        )
        for r in jd_results
    )
    resume_t = tuple(resume_skills)
    return resume_t, jd_rows, missing, ref_tuple


with st.spinner("Running NLP extraction and hybrid JD matching..."):
    resume_t, jd_rows, missing_skills, refresher_tuple = run_extraction(
        st.session_state["jd_text"],
        st.session_state["resume_text"],
    )

resume_skills = list(resume_t)
st.session_state["missing_skills"] = missing_skills
st.session_state["refresher_skills"] = [
    {"skill": a, "relevance": b, "priority": c} for a, b, c in refresher_tuple
]
st.session_state["jd_skill_rows"] = [
    {
        "Skill": name,
        "Category": cat,
        "Relevance": rel,
        "Difficulty": diff,
        "Priority": pri,
        "Resume match": matched,
    }
    for name, cat, rel, diff, pri, matched in jd_rows
]
st.session_state["resume_skills_list"] = resume_skills

# --- Step 1 ---
st.header("Step 1: Source text")
with st.status("Parsed inputs (truncated previews)", expanded=False):
    r_preview = st.session_state["resume_text"][:2200]
    j_preview = st.session_state["jd_text"][:2200]
    c1, c2 = st.columns(2)
    with c1:
        st.text_area("Resume excerpt", r_preview + ("\n\n..." if len(st.session_state["resume_text"]) > 2200 else ""), height=220, disabled=True)
    with c2:
        st.text_area("JD excerpt", j_preview + ("\n\n..." if len(st.session_state["jd_text"]) > 2200 else ""), height=220, disabled=True)

# --- Step 2 ---
st.header("Step 2: Resume skills (SkillNER)")
st.success(f"Detected **{len(resume_skills)}** skill mentions on the resume.")
if resume_skills:
    top = resume_skills[:20]
    cloud = "".join(f"<span>{html.escape(str(s))}</span>" for s in top)
    st.markdown(f'<div class="skill-cloud">{cloud}</div>', unsafe_allow_html=True)
    if len(resume_skills) > 20:
        st.caption("Showing first 20 entries…")

# --- Step 3 ---
st.header("Step 3: JD skills, relevance, and resume overlap")
jd_df = pd.DataFrame(st.session_state["jd_skill_rows"])
if not jd_df.empty:
    jd_display = jd_df.copy()
    jd_display["Resume match"] = jd_display["Resume match"].map(lambda x: "✅" if x else "❌")
    st.dataframe(
        jd_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Relevance": st.column_config.NumberColumn(format="%.2f"),
            "Difficulty": st.column_config.NumberColumn(format="%.2f"),
        },
    )

# --- Step 4 ---
st.header("Step 4: Skill gap")
matched_count = sum(1 for row in st.session_state["jd_skill_rows"] if row["Resume match"])
gap_count = len(missing_skills)
m1, m2, m3 = st.columns(3)
m1.metric("JD skills matched to resume", matched_count)
m2.metric("Distinct gap skills (deduped)", gap_count)
m3.metric("Refresher candidates (strong JD, on resume)", len(st.session_state["refresher_skills"]))

if missing_skills:
    st.dataframe(pd.DataFrame(missing_skills), use_container_width=True, hide_index=True)
else:
    st.info("No deduped gap rows: your resume covers every JD skill in our taxonomy for this run.")

# --- Step 5 CTA ---
st.divider()
st.subheader("Step 5: Build the learning roadmap")
budget = st.slider("Time budget for recommended core path (hours)", 5.0, 200.0, 30.0, 5.0)

has_courses = gap_count > 0 or len(st.session_state["refresher_skills"]) > 0
if st.button("Generate roadmap", type="primary", disabled=not has_courses):
    st.session_state["budget"] = budget
    st.switch_page("pages/2_Learning_Roadmap.py")

if not has_courses:
    st.caption("No gap skills and no refresher candidates: there is nothing to schedule into courses.")

st.divider()
if st.button("Back to home"):
    st.switch_page("app.py")
