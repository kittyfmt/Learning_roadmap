import spacy
import re
import math
import os
from dataclasses import dataclass
from typing import List, Set, Dict, Any

# --- Load Models & Config ---
nlp_base = spacy.load("en_core_web_sm")

# Path to the custom NER model
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'hard_skill_model.pkl')
try:
    import joblib
    # Loading custom model. Fallback to base if it fails.
    nlp_custom_ner = spacy.load(MODEL_PATH)
except:
    nlp_custom_ner = nlp_base 

from backend.taxonomy_loader import TAXONOMY, ALIAS_LOOKUP 

@dataclass
class SkillResult:
    canonical_name: str
    category: str
    relevance_score: float
    difficulty_score: float
    priority_level: str
    is_matched: bool

class JDSkillExtractor:
    def __init__(self):
        self.nlp_base = nlp_base
        self.nlp_ner = nlp_custom_ner

    def _get_scores(self, aliases, sentences, total_sent):
        rel_score = 0.0
        diff_score = 0.5
        count = 0
        for sent in sentences:
            sent_low = sent.lower()
            for a in aliases:
                if re.search(r'\b' + re.escape(a.lower()) + r'\b', sent_low):
                    count += 1
                    rel_score += 0.2
                    break
        rel_final = min(1.0, rel_score + (count / max(1, total_sent)))
        return round(rel_final, 2), diff_score

    def _get_priority(self, rel, diff):
        score = rel * 0.7 + diff * 0.3
        if score > 0.7: return "High"
        if score > 0.4: return "Medium"
        return "Low"

    def extract(self, jd_text: str, resume_text: str, resume_extracted_skills: List[str] = None) -> List[SkillResult]:
        sentences = [s.text for s in self.nlp_base(jd_text).sents]
        found = {}

        # 1. Taxonomy-based Discovery in JD
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
        base_doc = self.nlp_base(jd_text)
        banned_entities = {e.text.lower() for e in base_doc.ents if e.label_ in ['GPE', 'LOC', 'ORG', 'DATE', 'PERSON']}
        ner_doc = self.nlp_ner(jd_text)
        existing_keys_lower = {k.lower() for k in found.keys()}

        for ent in ner_doc.ents:
            # Rule: Split by comma to handle mixed strings
            raw_skills = [s.strip() for s in ent.text.split(',')]
            for raw_skill in raw_skills:
                clean_skill = raw_skill.strip('./;')
                name = clean_skill.title()
                name_lower = name.lower()

                # Filtering noisy extractions
                if len(name_lower) < 2 or len(name_lower.split()) > 3: continue
                if name_lower in banned_entities: continue
                
                # POS Filtering: Reject if it's purely verbs or stop words
                tokens = self.nlp_base(clean_skill)
                if all(t.pos_ in ['VERB', 'ADV', 'PRON'] or t.is_stop for t in tokens): continue

                if name_lower not in existing_keys_lower:
                    found[name] = {"aliases": [name_lower], "cat": "ML_Discovered"}
                    existing_keys_lower.add(name_lower)

        # 3. Resume Matching (Hybrid: Regex + SkillNER Results)
        res_low = resume_text.lower()
        matched_canonical_names = set()

        # Logic A: Global Regex check based on Taxonomy Aliases
        for alias, canonical in ALIAS_LOOKUP.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', res_low):
                matched_canonical_names.add(canonical)

        # Logic B: Integrate teammate's SkillNER extraction list
        if resume_extracted_skills:
            for r_skill in resume_extracted_skills:
                s_low = r_skill.lower().strip()
                if s_low in ALIAS_LOOKUP:
                    matched_canonical_names.add(ALIAS_LOOKUP[s_low])
                else:
                    # Keep skills found by SkillNER even if not in Taxonomy
                    matched_canonical_names.add(r_skill.title())

        # 4. Final Result Compilation
        results = []
        for name, data in found.items():
            rel, diff = self._get_scores(data["aliases"], sentences, len(sentences))
            
            # Match check: is the found JD skill present in our matched resume set?
            is_matched = (name in matched_canonical_names) or (name.lower() in [s.lower() for s in matched_canonical_names])
            
            results.append(SkillResult(
                canonical_name=name,
                category=data["cat"],
                relevance_score=rel,
                difficulty_score=diff,
                priority_level=self._get_priority(rel, diff),
                is_matched=is_matched
            ))
        
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)