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
    def __init__(self, model_size: str = "en_core_web_sm"): # Default to 'sm' for faster loading
  
        self.nlp, self.extractor = self._load_resources(model_size)

    @st.cache_resource
    def _load_resources(_self, model_size):
        disabled_pipes = ["ner", "parser", "lemmatizer", "textcat", "custom"]
        
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
        text = re.sub(r"<.*?>", " ", text)  
        text = re.sub(r"\s+", " ", text)    
        # Optional Speedup: Limit text length to avoid N-gram explosion
        # text = text[:5000] 
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
                    extracted.append(str(skill_name).lower())
        return extracted

    # CRITICAL SPEEDUP: Set include_ngram_scored to False by default
    def extract_skills(self, raw_text: str, include_ngram_scored: bool = True) -> List[str]:
 
        cleaned = self.clean_text(raw_text)
        if not cleaned:
            return []

        try:
            annotations = self.extractor.annotate(cleaned)
            results = annotations.get("results", {})
            full_matches = self._parse_matches(results.get("full_matches", []))
            
            ngram_matches = []
            # Only run this expensive operation if explicitly requested
            if include_ngram_scored:
                ngram_matches = self._parse_matches(results.get("ngram_scored", []))

            all_skills = list(dict.fromkeys(full_matches + ngram_matches))
            return all_skills
        except Exception as e:
            print(f"❌ SkillNER error: {e}")
            return []

    def get_payload(self, text: str) -> Dict[str, Any]:
        skills = self.extract_skills(text)
        return {
            "cleaned_text": self.clean_text(text),
            "skills": skills,
            "count": len(skills)
        }