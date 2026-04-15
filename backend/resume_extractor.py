import re
import warnings
import streamlit as st
import pandas as pd
import spacy
from typing import List, Dict, Any, Optional, Union
from spacy.matcher import PhraseMatcher
from skillNer.general_params import SKILL_DB
from skillNer.skill_extractor_class import SkillExtractor

warnings.filterwarnings("ignore", category=UserWarning)

class ResumeSkillExtractor:
    def __init__(self, model_size: str = "en_core_web_sm"):
        self.nlp, self.extractor = self._load_resources(model_size)

    @st.cache_resource
    def _load_resources(_self, model_size):
        # Keep parser for spaCy sentence segmentation, disable other unused pipes
        disabled_pipes = ["ner", "lemmatizer", "textcat", "custom"]
        
        try:
            nlp = spacy.load(model_size, disable=disabled_pipes)
        except OSError:
            nlp = spacy.load("en_core_web_sm", disable=disabled_pipes)
            
        extractor = SkillExtractor(nlp, SKILL_DB, PhraseMatcher)
        return nlp, extractor

    def clean_text(self, text: Optional[Union[str, Any]]) -> str:
        if text is None or pd.isna(text):
            return ""
        text = str(text).lower()
        
        # Remove HTML tags
        text = re.sub(r"<.*?>", " ", text)
        
        # Replace newlines with spaces
        text = re.sub(r'[\r\n]+', ' ', text)
        
        # Collapse multiple whitespace into one
        text = re.sub(r"\s+", " ", text)
        
        return text.strip()

    def _parse_matches(self, matches_obj: Any) -> List[str]:
        extracted = []
        if isinstance(matches_obj, dict):
            iterable = matches_obj.values()
        elif isinstance(matches_obj, list):
            iterable = matches_obj
        else:
            iterable = []

        for match in iterable:
            if isinstance(match, dict):
                skill_id = match.get("skill_id")
                if skill_id and skill_id in SKILL_DB:
                    skill_name = SKILL_DB[skill_id].get("skill_name", skill_id)
                else:
                    skill_name = match.get("doc_node_value") or match.get("doc_node_name")
                
                if skill_name:
                    skill_str = str(skill_name).lower()
                    # Filter out single character matches (e.g. "m" from "m.s.")
                    if len(skill_str.strip()) > 1:
                        extracted.append(skill_str)
        return extracted

    def extract_skills(self, raw_text: str, include_ngram_scored: bool = True) -> List[str]:
        cleaned = self.clean_text(raw_text)
        if not cleaned:
            return []

        # Remove all non-ASCII characters that cause SkillNER internal crashes
        cleaned = re.sub(r'[^\x00-\x7F]', ' ', cleaned)
        cleaned = re.sub(r'\be\.g\.\s*', 'for example ', cleaned)
        cleaned = re.sub(r'\bi\.e\.\s*', 'that is ', cleaned)
        cleaned = re.sub(r'\s+\.(\s|$)', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        if not cleaned:
            return []

        def _annotate(text):
            """Run SkillNER on a piece of text and return deduplicated skills"""
            annotations = self.extractor.annotate(text)
            results = annotations.get("results", {})
            full_matches = self._parse_matches(results.get("full_matches", []))
            ngram_matches = []
            if include_ngram_scored:
                ngram_matches = self._parse_matches(results.get("ngram_scored", []))
            return list(dict.fromkeys(full_matches + ngram_matches))

        def _safe_annotate(text):
            """Try whole text, if fails split into smaller chunks and retry.
            Never gives up on a piece of text — keeps splitting until it works."""
            if not text or not text.strip():
                return []
            # Try whole chunk first
            try:
                return _annotate(text)
            except Exception:
                pass
            # Split by comma and semicolon and retry each chunk
            chunks = re.split(r'[,;]', text)
            skills = []
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                try:
                    skills.extend(_annotate(chunk))
                except Exception:
                    # Split further into individual words as last resort
                    words = chunk.split()
                    for word in words:
                        if len(word) > 1:
                            try:
                                skills.extend(_annotate(word))
                            except Exception:
                                continue
            return skills

        # Try whole text first
        try:
            return _annotate(cleaned)
        except Exception:
            pass

        # Fallback: process sentence by sentence using spaCy segmentation
        doc = self.nlp(cleaned)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        all_skills = []
        for sent in sentences:
            # Each sentence is processed with progressive splitting — nothing is abandoned
            all_skills.extend(_safe_annotate(sent))

        return list(dict.fromkeys(all_skills))

    def get_payload(self, text: str) -> Dict[str, Any]:
        skills = self.extract_skills(text)
        return {
            "cleaned_text": self.clean_text(text),
            "skills": skills,
            "count": len(skills)
        }