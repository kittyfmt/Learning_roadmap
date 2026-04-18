import spacy
import re
import math
import os
import numpy as np
import joblib
from dataclasses import dataclass
from typing import List, Set, Dict, Any, Tuple

# --- Load Models & Config ---
nlp_base = spacy.load("en_core_web_sm")

# Path to the custom NER model
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'hard_skill_model.pkl')
try:
    nlp_custom_ner = spacy.load(MODEL_PATH)
except:
    nlp_custom_ner = nlp_base 

# Path to the new skill ranker model
RANKER_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'skill_ranker.joblib')

from backend.taxonomy_loader import TAXONOMY, ALIAS_LOOKUP 

# Mapping categories to difficulty scores (0.0 to 1.0)
CATEGORY_DIFFICULTY = {
    "ML/AI": 0.85, "Deep Learning": 0.9, "NLP": 0.85, "Computer Vision": 0.85,
    "Reinforcement Learning": 0.9, "Generative AI": 0.85, "ML Framework": 0.75,
    "Data Engineering": 0.75, "MLOps/DevOps": 0.7, "MLOps": 0.7, "DevOps": 0.65,
    "Cloud": 0.6, "Programming": 0.6, "Database": 0.55, "Statistics": 0.6,
    "Analytics": 0.45, "Visualization": 0.4, "Tools": 0.3, "Soft Skills": 0.2,
    "ML_Discovered": 0.5
}

@dataclass
class SkillResult:
    canonical_name: str
    category: str
    relevance_score: float
    difficulty_score: float
    priority_level: str
    is_matched: bool

class JDSkillExtractor:
    """
    Advanced ML-Hybrid Skill Extractor for Job Descriptions.
    Features:
    1. Feature Engineering (Frequency, Position, Context, NER Confidence)
    2. ML Model Inference (using skill_ranker.joblib)
    3. Hybrid Matching (Taxonomy + Contextual NER)
    """
    def __init__(self):
        self.nlp = nlp_base
        self.nlp_ner = nlp_custom_ner
        self.priority_keywords = ["must", "required", "requirements", "essential", "strong", "expert"]
        self.secondary_keywords = ["plus", "preferred", "nice to have", "familiarity", "experience with"]
        
        # Load the ranking model
        try:
            self.ranker_model = joblib.load(RANKER_MODEL_PATH)
            self.has_model = True
        except:
            self.has_model = False
            # print("Warning: skill_ranker.joblib not found. Using fallback.")

    def _extract_features(self, skill_name: str, aliases: List[str], doc: spacy.tokens.Doc) -> np.ndarray:
        """Extract ML features for a specific skill in the document context."""
        count = 0
        first_pos = 1.0
        context_score = 0.0
        ner_match = 0.0
        
        # Check NER detection
        ner_entities = {ent.text.lower() for ent in doc.ents}
        if any(a.lower() in ner_entities for a in aliases):
            ner_match = 1.0

        sentences = list(doc.sents)
        total_sents = len(sentences)
        
        for i, sent in enumerate(sentences):
            sent_text = sent.text.lower()
            found = False
            for alias in aliases:
                if re.search(r'\b' + re.escape(alias.lower()) + r'\b', sent_text):
                    count += 1
                    found = True
                    if first_pos == 1.0:
                        first_pos = i / max(1, total_sents)
                    break
            
            if found:
                # Context Analysis: boost if near priority/secondary keywords
                if any(kw in sent_text for kw in self.priority_keywords):
                    context_score += 0.3
                if any(kw in sent_text for kw in self.secondary_keywords):
                    context_score += 0.1

        log_freq = math.log2(1 + count)
        pos_feature = 1.0 - first_pos
        context_feature = min(1.0, context_score)
        
        # Feature Vector: [log_freq, first_pos, context_weight, ner_boost]
        # (cat_bias is added in _ml_ranker_predict)
        return np.array([log_freq, pos_feature, context_feature, ner_match])

    def _ml_ranker_predict(self, features: np.ndarray, category: str) -> float:
        """Predict relevance using the joblib model or fallback heuristics."""
        cat_bias = 1.0 if category in ["ML/AI", "Deep Learning", "Programming", "Data Engineering"] else 0.0
        full_features = np.append(features, cat_bias).reshape(1, -1)
        
        if self.has_model:
            score = self.ranker_model.predict(full_features)[0]
        else:
            # Heuristic fallback if model missing
            score = (features[0]*0.4 + features[1]*0.2 + features[2]*0.2 + features[3]*0.1 + cat_bias*0.1)
        
        return float(np.clip(score, 0.0, 1.0))

    def extract(self, jd_text: str, resume_text: str, resume_extracted_skills: List[str] = None) -> List[SkillResult]:
        doc = self.nlp(jd_text)
        found = {}

        # 1. Taxonomy-based Discovery
        jd_low = jd_text.lower()
        for canonical, info in TAXONOMY.items():
            combined_aliases = [canonical.lower()] + [a.lower() for a in info.get("aliases", [])]
            if any(re.search(r'\b' + re.escape(a) + r'\b', jd_low) for a in combined_aliases):
                if canonical not in found:
                    found[canonical] = {
                        "aliases": combined_aliases, 
                        "cat": info.get("category", "Other")
                    }

        # 2. ML NER Discovery & Cleaning
        base_doc = self.nlp(jd_text)
        banned_entities = {e.text.lower() for e in base_doc.ents if e.label_ in ['GPE', 'LOC', 'ORG', 'DATE', 'PERSON']}
        ner_doc = self.nlp_ner(jd_text)
        existing_keys_lower = {k.lower() for k in found.keys()}

        for ent in ner_doc.ents:
            raw_skills = [s.strip() for s in ent.text.split(',')]
            for raw_skill in raw_skills:
                clean_skill = raw_skill.strip('./;')
                name = clean_skill.title()
                name_lower = name.lower()

                if len(name_lower) < 2 or len(name_lower.split()) > 3: continue
                if name_lower in banned_entities: continue
                
                tokens = self.nlp(clean_skill)
                if all(t.pos_ in ['VERB', 'ADV', 'PRON'] or t.is_stop for t in tokens): continue

                if name_lower not in existing_keys_lower:
                    found[name] = {"aliases": [name_lower], "cat": "ML_Discovered"}
                    existing_keys_lower.add(name_lower)

        # 3. Resume Matching
        res_low = resume_text.lower()
        matched_canonical_names = set()
        for alias, canonical in ALIAS_LOOKUP.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', res_low):
                matched_canonical_names.add(canonical)

        if resume_extracted_skills:
            for r_skill in resume_extracted_skills:
                s_low = r_skill.lower().strip()
                if s_low in ALIAS_LOOKUP:
                    matched_canonical_names.add(ALIAS_LOOKUP[s_low])
                else:
                    matched_canonical_names.add(r_skill.title())

        # 4. Final Result Compilation with ML Prediction
        results = []
        for name, data in found.items():
            features = self._extract_features(name, data["aliases"], doc)
            rel = self._ml_ranker_predict(features, data["cat"])
            diff = CATEGORY_DIFFICULTY.get(data["cat"], 0.5)
            
            # Priority logic: weighted combination of relevance and difficulty
            pri_score = rel * 0.7 + diff * 0.3
            if pri_score > 0.72: pri = "High"
            elif pri_score > 0.42: pri = "Medium"
            else: pri = "Low"
            
            is_matched = (name in matched_canonical_names) or (name.lower() in [s.lower() for s in matched_canonical_names])
            
            results.append(SkillResult(
                canonical_name=name,
                category=data["cat"],
                relevance_score=round(rel, 3),
                difficulty_score=diff,
                priority_level=pri,
                is_matched=is_matched
            ))
        
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)
