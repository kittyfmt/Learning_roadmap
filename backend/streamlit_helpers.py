"""Shared Streamlit utilities: upload parsing and cached pipeline models."""
from __future__ import annotations

import streamlit as st

from backend.pdf_parser import extract_text_from_pdf
from backend.resume_extractor import ResumeSkillExtractor
from backend.jd_extractor import JDSkillExtractor
from backend.course_optimizer import CourseOptimizer


def extract_text_from_txt(uploaded_file) -> str:
    try:
        return uploaded_file.getvalue().decode("utf-8", errors="replace")
    except Exception:
        return ""


def text_from_upload(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    name = (uploaded_file.name or "").lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(uploaded_file)
    return extract_text_from_txt(uploaded_file)


@st.cache_resource
def get_pipeline_models():
    return ResumeSkillExtractor(), JDSkillExtractor(), CourseOptimizer()
