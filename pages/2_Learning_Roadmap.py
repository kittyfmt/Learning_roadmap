"""Sequenced learning roadmap with rich context from the extraction pipeline."""
from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.course_optimizer import CourseOptimizer

st.set_page_config(page_title="Learning roadmap", page_icon="\U0001f5fa\ufe0f", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .rm-hero {
        background: linear-gradient(120deg, #042f2e 0%, #115e59 40%, #4338ca 100%);
        color: #ecfeff;
        padding: 2rem 2rem 1.75rem;
        border-radius: 20px;
        margin-bottom: 1.5rem;
        box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.35);
    }
    .rm-hero h1 { margin: 0; font-size: 1.85rem; font-weight: 700; letter-spacing: -0.02em; }
    .rm-hero p { margin: 0.6rem 0 0 0; opacity: 0.92; max-width: 52rem; line-height: 1.55; }
    .timeline {
        position: relative;
        margin: 1rem 0 2rem 0;
        padding-left: 0;
    }
    .timeline::before {
        content: "";
        position: absolute;
        left: 18px;
        top: 8px;
        bottom: 8px;
        width: 4px;
        border-radius: 4px;
        background: linear-gradient(180deg, #14b8a6, #6366f1, #a855f7);
        opacity: 0.85;
    }
    .tl-item {
        position: relative;
        padding-left: 56px;
        margin-bottom: 1.35rem;
    }
    .tl-dot {
        position: absolute;
        left: 6px;
        top: 12px;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: #0f172a;
        color: #f8fafc;
        font-weight: 700;
        font-size: 0.8rem;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 0 4px rgba(255,255,255,0.95);
        z-index: 1;
    }
    .course-card {
        background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.25rem 1.35rem;
        box-shadow: 0 10px 25px -15px rgba(15, 23, 42, 0.25);
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }
    .course-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 18px 35px -18px rgba(15, 23, 42, 0.35);
    }
    .phase-chip {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 0.2rem 0.55rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
    }
    .chip-core { background: #d1fae5; color: #065f46; }
    .chip-opt { background: #fef3c7; color: #92400e; }
    .chip-refresh { background: #ede9fe; color: #5b21b6; }
    .course-title-link {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0f172a;
        text-decoration: none;
        border-bottom: 2px solid transparent;
    }
    .course-title-link:hover { color: #2563eb; border-bottom-color: #93c5fd; }
    .meta-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 0.45rem 1rem;
        margin-top: 0.75rem;
        font-size: 0.82rem;
        color: #475569;
    }
    .meta-grid b { color: #0f172a; font-weight: 600; }
    .skill-pill {
        display: inline-block;
        background: #e0f2fe;
        color: #075985;
        padding: 0.15rem 0.45rem;
        border-radius: 6px;
        font-size: 0.72rem;
        margin: 0.15rem 0.2rem 0 0;
        border: 1px solid #bae6fd;
    }
    .context-box {
        background: #f1f5f9;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _safe(s) -> str:
    return html.escape("" if s is None or (isinstance(s, float) and pd.isna(s)) else str(s))


def _attr_href(url: str) -> str:
    u = (url or "").strip()
    if u.startswith("http://") or u.startswith("https://"):
        return html.escape(u, quote=True)
    return "#"


if "missing_skills" not in st.session_state or "budget" not in st.session_state:
    st.warning("Open this page after you run the analysis and click generate roadmap.")
    st.stop()

st.title("Your personalized learning roadmap")
budget = st.session_state["budget"]
refresher_list = st.session_state.get("refresher_skills") or []
jd_rows = st.session_state.get("jd_skill_rows") or []
resume_skills = st.session_state.get("resume_skills_list") or []


def get_courses(missing_tuple, time_budget, refresher_tuple):
    missing = [{"skill": a, "relevance": b, "priority": c} for a, b, c in missing_tuple]
    refresher = [{"skill": s, "relevance": r, "priority": p} for s, r, p in refresher_tuple]
    opt = CourseOptimizer()
    return opt.get_roadmap(missing, time_budget, refresher_skills=refresher or None)


missing_tuple = tuple(
    (m["skill"], m["relevance"], m["priority"]) for m in st.session_state["missing_skills"]
)
ref_tuple = tuple(
    (m["skill"], m["relevance"], m["priority"]) for m in refresher_list
)

with st.spinner("Optimizing course sequence..."):
    roadmap = get_courses(missing_tuple, budget, ref_tuple)

rec_df = roadmap["recommended"]
opt_df = roadmap["optional"]
ref_df = roadmap["refresher"]

gap_n = len(st.session_state["missing_skills"])
match_n = sum(1 for r in jd_rows if r.get("Resume match"))
jd_n = len(jd_rows)

st.markdown(
    f"""
    <div class="rm-hero">
        <h1>Your learning roadmap</h1>
        <p>
            Ordered steps link directly to each course. Context below summarizes JD scoring, resume overlap,
            and how each block fits your time budget ({_safe(budget)} h core allocation).
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("JD skills tracked", jd_n)
k2.metric("Matched to resume", match_n)
k3.metric("Gap skills (deduped)", gap_n)
k4.metric("Resume skill mentions", len(resume_skills))

with st.expander("JD skill scoring table (full extraction)", expanded=False):
    if jd_rows:
        st.dataframe(pd.DataFrame(jd_rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No rows in session.")

with st.expander("Resume skill mentions (SkillNER)", expanded=False):
    if resume_skills:
        st.write(", ".join(_safe(s) for s in resume_skills))
    else:
        st.caption("None stored.")

with st.expander("Deduped gap skills driving course search", expanded=False):
    if st.session_state["missing_skills"]:
        st.dataframe(pd.DataFrame(st.session_state["missing_skills"]), use_container_width=True, hide_index=True)
    else:
        st.caption("No gap rows for this run.")

with st.expander("Refresher targets (strong in JD, already on resume)", expanded=False):
    if refresher_list:
        st.dataframe(pd.DataFrame(refresher_list), use_container_width=True, hide_index=True)
    else:
        st.caption("None.")


def render_timeline_section(df: pd.DataFrame, heading: str, blurb: str, chip_class: str, chip_label: str, start_idx: int) -> tuple[float, int]:
    if df is None or df.empty:
        return 0.0, start_idx
    st.subheader(heading)
    st.caption(blurb)
    hours = 0.0
    idx = start_idx
    st.markdown('<div class="timeline">', unsafe_allow_html=True)
    for _, row in df.iterrows():
        idx += 1
        hours += float(row.get("estimated_time_hours") or 0)
        title = _safe(row.get("Course title", "Course"))
        href = _attr_href(row.get("Course_link"))
        org = _safe(row.get("Organization", ""))
        ctype = _safe(row.get("Course_Type", ""))
        diff = _safe(row.get("Difficulty_level", ""))
        lang = _safe(row.get("Language", ""))
        workload = _safe(row.get("Workload", ""))
        pay = _safe(row.get("Payment_Model", ""))
        reviews = row.get("Review count", "")
        if reviews is None or (isinstance(reviews, float) and pd.isna(reviews)):
            reviews_s = ""
        else:
            try:
                reviews_s = str(int(float(reviews)))
            except (TypeError, ValueError):
                reviews_s = str(reviews)
        rating = row.get("Ratings", "")
        try:
            rating_s = f"{float(rating):.1f}" if rating is not None and not (isinstance(rating, float) and pd.isna(rating)) else ""
        except (TypeError, ValueError):
            rating_s = _safe(rating)
        est = row.get("estimated_time_hours", "")
        try:
            est_s = f"{float(est):.1f}" if est is not None and not (isinstance(est, float) and pd.isna(est)) else ""
        except (TypeError, ValueError):
            est_s = _safe(est)

        raw_skills = row.get("Skills", "")
        if isinstance(raw_skills, str) and raw_skills.strip():
            parts = [p.strip() for p in raw_skills.split(",") if p.strip()]
        else:
            parts = []
        pills = "".join(f'<span class="skill-pill">{_safe(p)}</span>' for p in parts[:40])
        if len(parts) > 40:
            pills += f'<span class="skill-pill">+{len(parts) - 40} more</span>'

        st.markdown(
            f"""
            <div class="tl-item">
                <div class="tl-dot">{idx}</div>
                <div class="course-card">
                    <div class="phase-chip {chip_class}">{_safe(chip_label)}</div>
                    <div>
                        <a class="course-title-link" href="{href}" target="_blank" rel="noopener noreferrer">{title}</a>
                    </div>
                    <div class="meta-grid">
                        <div><b>Provider</b><br>{org or "—"}</div>
                        <div><b>Format</b><br>{ctype or "—"}</div>
                        <div><b>Est. hours</b><br>{est_s or "—"}</div>
                        <div><b>Difficulty</b><br>{diff or "—"}</div>
                        <div><b>Rating</b><br>{rating_s or "—"}</div>
                        <div><b>Reviews</b><br>{_safe(reviews_s) if reviews_s else "—"}</div>
                        <div><b>Language</b><br>{lang or "—"}</div>
                        <div><b>Workload text</b><br>{workload or "—"}</div>
                        <div><b>Payment</b><br>{pay or "—"}</div>
                    </div>
                    <div style="margin-top:0.75rem;font-size:0.78rem;color:#64748b;">Skill tags from catalog</div>
                    <div style="margin-top:0.25rem;">{pills or '<span class="skill-pill">—</span>'}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
    return hours, idx


if rec_df.empty and opt_df.empty and ref_df.empty:
    st.info("No catalog courses matched these gaps under your budget. Try raising the budget on the analysis page.")
else:
    step = 0
    h1, step = render_timeline_section(
        rec_df,
        "Core path",
        "Greedy sequence that covers deduped gap skills within your hour budget. Step numbers run in recommended order.",
        "chip-core",
        "Core",
        step,
    )
    h2, step = render_timeline_section(
        opt_df,
        "Extension: high-priority gaps",
        "Extra courses for gap skills that did not fit the core budget but are marked high priority in the JD view.",
        "chip-opt",
        "Gap add-on",
        step,
    )
    h3, step = render_timeline_section(
        ref_df,
        "Extension: deepen matched strengths",
        "Optional polish for skills already on your resume that the JD still weights heavily.",
        "chip-refresh",
        "Refresher",
        step,
    )
    total_h = h1 + h2 + h3
    st.markdown(
        f"""
        <div class="context-box">
            <b>Hours in view:</b> {_safe(round(total_h, 1))} h listed across all blocks &nbsp;|&nbsp;
            <b>Core block only:</b> {_safe(round(h1, 1))} h &nbsp;|&nbsp;
            <b>Budget you set:</b> {_safe(budget)} h
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()
b1, b2 = st.columns(2)
with b1:
    if st.button("Adjust budget / re-run", use_container_width=True):
        st.switch_page("pages/1_Missing_Skills.py")
with b2:
    if st.button("Start over (home)", use_container_width=True):
        st.switch_page("app.py")
