import pandas as pd
import numpy as np
import os
from typing import List, Dict, Any, Optional, Set
from difflib import SequenceMatcher
from backend.taxonomy_loader import ALIAS_LOOKUP

# Thresholds
SIM_THRESHOLD = 0.55
OPTIONAL_GAP_SIM = 0.45 
DEDUPE_SKILL_SIM = 0.86

# Difficulty mapping
DIFF_MAP = {"Beginner": 1, "Intermediate": 2, "Advanced": 3, "Mixed": 2}

class CourseOptimizer:
    def __init__(self, course_db_path: str = None):
        if not course_db_path:
            course_db_path = os.path.join(os.path.dirname(__file__), "..", "data", "course_list.csv")
        
        self.df_raw = pd.read_csv(course_db_path)
        self.df_raw = self.df_raw.drop_duplicates(subset=['Course title'])
        
        # Pre-processing
        self.df_raw['skill_list'] = self.df_raw['Skills'].apply(
            lambda x: [s.strip().lower() for s in str(x).split(',')] if pd.notnull(x) else []
        )
        self.df_raw['estimated_time_hours'] = pd.to_numeric(self.df_raw['estimated_time_hours'], errors='coerce').fillna(10.0)
        self.df_raw['Ratings'] = pd.to_numeric(self.df_raw['Ratings'], errors='coerce').fillna(4.0)
        self.df_raw['Review count'] = pd.to_numeric(self.df_raw['Review count'], errors='coerce').fillna(0)
        
        # Difficulty & Quality
        self.df_raw['level_score'] = self.df_raw['Difficulty_level'].map(DIFF_MAP).fillna(1)
        r_min, r_max = self.df_raw['Ratings'].min(), self.df_raw['Ratings'].max()
        self.df_raw['rating_norm'] = (self.df_raw['Ratings'] - r_min) / max(1, r_max - r_min)
        rev_max = np.log1p(self.df_raw['Review count'].max())
        self.df_raw['review_norm'] = np.log1p(self.df_raw['Review count']) / max(1, rev_max)
        self.df_raw['static_quality_score'] = 0.7 * self.df_raw['rating_norm'] + 0.3 * self.df_raw['review_norm']
        
        # Language Scoring: Preference for 'en'
        self.df_raw['lang_score'] = self.df_raw['Language'].apply(lambda x: 1.0 if str(x).lower() == 'en' else 0.0)
        
        if 'Course_link' not in self.df_raw.columns:
            self.df_raw['Course_link'] = "#"

    def _get_similarity(self, s1: str, s2: str) -> float:
        s1, s2 = s1.lower().strip(), s2.lower().strip()
        if s1 == s2: return 1.0
        if ALIAS_LOOKUP.get(s1) == s2 or ALIAS_LOOKUP.get(s2) == s1: return 1.0
        return SequenceMatcher(None, s1, s2).ratio()

    def _dedupe_skill_dicts(self, items: List[Dict], skill_key: str = "skill") -> List[Dict]:
        if not items: return []
        sorted_items = sorted(items, key=lambda x: -x.get("relevance", 0))
        kept: List[Dict] = []
        for m in sorted_items:
            s = m[skill_key]
            if any(self._get_similarity(s, k[skill_key]) >= DEDUPE_SKILL_SIM for k in kept): continue
            kept.append(m)
        return kept

    def calculate_gap(self, jd_results: List[Any], resume_skills: List[str] = None) -> List[Dict]:
        raw = [
            {
                "skill": item.canonical_name,
                "relevance": getattr(item, 'relevance_score', 0),
                "priority": getattr(item, 'priority_level', "Medium")
            }
            for item in jd_results if not getattr(item, 'is_matched', False)
        ]
        return self._dedupe_skill_dicts(raw)

    def build_refresher_specs(self, jd_results: List[Any], min_relevance: float = 0.65) -> List[Dict]:
        specs = []
        for item in jd_results:
            if not getattr(item, 'is_matched', False): continue
            pri = getattr(item, 'priority_level', "Low")
            rel = getattr(item, 'relevance_score', 0)
            if pri == "High" or rel >= min_relevance:
                specs.append({"skill": item.canonical_name, "relevance": rel, "priority": pri})
        return self._dedupe_skill_dicts(specs)

    def get_roadmap(
        self,
        missing_skills: List[Dict],
        time_budget: float,
        user_level: int = 1,
        refresher_skills: Optional[List[Dict]] = None,
        refresher_time_budget: Optional[float] = None,
    ) -> Dict[str, pd.DataFrame]:
        if not missing_skills or self.df_raw.empty:
            return {"recommended": pd.DataFrame(), "optional": pd.DataFrame(), "refresher": pd.DataFrame()}

        unique_db_skills = {s for sublist in self.df_raw['skill_list'] for s in sublist}
        all_potential_gaps = {m['skill'] for m in missing_skills}
        if refresher_skills: all_potential_gaps.update({r['skill'] for r in refresher_skills})
        sim_cache = {(gap, db_s): self._get_similarity(gap, db_s)
                     for gap in all_potential_gaps for db_s in unique_db_skills}

        current_missing = self._dedupe_skill_dicts(missing_skills.copy())
        recommended: List[Any] = []
        remaining_budget = float(time_budget)
        selected_titles: Set[str] = set()

        # Revised Weights with Language Support
        W = {"coverage": 0.45, "language": 0.25, "difficulty": 0.10, "quality": 0.10, "time": 0.10}

        def calculate_utility(row, missing_list):
            if not missing_list: return -1.0
            coverage_sum = 0.0
            new_skills_covered = 0
            for m in missing_list:
                best_sim = max([sim_cache.get((m['skill'], cs), 0) for cs in row['skill_list']] + [0])
                if best_sim > SIM_THRESHOLD:
                    coverage_sum += best_sim * m['relevance']
                    new_skills_covered += 1
            if new_skills_covered == 0: return -1.0
            
            coverage_score = coverage_sum / sum(m['relevance'] for m in missing_list)
            diff_score = max(0, 1 - 0.4 * abs(row['level_score'] - user_level))
            time_penalty = row['estimated_time_hours'] / time_budget if row['estimated_time_hours'] <= time_budget else 1.5
            
            # Combine all factors
            return (W['coverage'] * coverage_score + 
                    W['language'] * row['lang_score'] + 
                    W['difficulty'] * diff_score + 
                    W['quality'] * row['static_quality_score'] - 
                    W['time'] * time_penalty)

        # --- PHASE 1: CORE RECOMMENDED ---
        while remaining_budget > 0 and current_missing:
            pool = self.df_raw[~self.df_raw['Course title'].isin(selected_titles)].copy()
            if pool.empty: break
            pool['utility'] = pool.apply(lambda r: calculate_utility(r, current_missing), axis=1)
            candidates = pool[(pool['utility'] > 0) & (pool['estimated_time_hours'] <= remaining_budget)]
            if candidates.empty: break
            
            best = candidates.sort_values(['utility', 'Ratings'], ascending=False).iloc[0]
            recommended.append(best)
            remaining_budget -= float(best['estimated_time_hours'])
            selected_titles.add(best['Course title'])
            covered = [m['skill'] for m in current_missing 
                       if max([sim_cache.get((m['skill'], cs), 0) for cs in best['skill_list']] + [0]) > SIM_THRESHOLD]
            current_missing = [m for m in current_missing if m['skill'] not in covered]

        # --- PHASE 2: EXTENSIONS (Still preferring English) ---
        optional = []
        extension_pool = self.df_raw[~self.df_raw['Course title'].isin(selected_titles)].copy()
        gaps_to_target = sorted(missing_skills, key=lambda x: -x['relevance'])[:3]
        for gap_item in gaps_to_target:
            if extension_pool.empty: break
            extension_pool['score'] = extension_pool['skill_list'].apply(
                lambda cs: max([sim_cache.get((gap_item['skill'], c), 0) for c in cs] + [0])
            )
            # Add language weight to extension search
            extension_pool['final_score'] = extension_pool['score'] * 0.8 + extension_pool['lang_score'] * 0.2
            cand = extension_pool[extension_pool['score'] > OPTIONAL_GAP_SIM]
            if not cand.empty:
                best_opt = cand.sort_values(['final_score', 'Ratings'], ascending=False).iloc[0]
                optional.append(best_opt)
                selected_titles.add(best_opt['Course title'])
                extension_pool = extension_pool[extension_pool['Course title'] != best_opt['Course title']]

        # --- PHASE 3: REFRESHERS (Strict English for refreshers) ---
        refresher_df = pd.DataFrame()
        if refresher_skills:
            pool = self.df_raw[(~self.df_raw['Course title'].isin(selected_titles)) & (self.df_raw['lang_score'] == 1.0)].copy()
            rows = []
            rb = refresher_time_budget or 20.0
            for m in sorted(refresher_skills, key=lambda x: -x['relevance']):
                if rb <= 0 or pool.empty: break
                pool['rscore'] = pool['skill_list'].apply(lambda cs: max([sim_cache.get((m['skill'], c), 0) for c in cs] + [0]))
                cand = pool[(pool['rscore'] > SIM_THRESHOLD) & (pool['estimated_time_hours'] <= rb)]
                if not cand.empty:
                    pick = cand.sort_values(['rscore', 'Ratings'], ascending=False).iloc[0]
                    rows.append(pick)
                    rb -= float(pick['estimated_time_hours'])
                    selected_titles.add(pick['Course title'])
                    pool = pool[pool['Course title'] != pick['Course title']]
            refresher_df = pd.DataFrame(rows)

        return {"recommended": pd.DataFrame(recommended), "optional": pd.DataFrame(optional), "refresher": refresher_df}
