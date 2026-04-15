import pandas as pd
import os
from typing import List, Dict, Any, Optional, Set
from difflib import SequenceMatcher
from backend.taxonomy_loader import ALIAS_LOOKUP

# Scoring and "covered / removable gap" logic share this threshold so a course cannot be picked
# while gaps stay open (which stacked redundant courses for the same topic).
SIM_THRESHOLD = 0.55
# Stricter similarity for leftover high-priority gaps after the main budget is exhausted.
OPTIONAL_GAP_SIM = 0.72
# Merge near-duplicate gap skills from the JD (e.g. excel / spreadsheets).
DEDUPE_SKILL_SIM = 0.86


class CourseOptimizer:
    def __init__(self, course_db_path: str = None):
        if not course_db_path:
            course_db_path = os.path.join(os.path.dirname(__file__), "..", "data", "course_list.csv")
        
        self.df_raw = pd.read_csv(course_db_path)
        self.df_raw['skill_list'] = self.df_raw['Skills'].apply(
            lambda x: [s.strip().lower() for s in str(x).split(',')] if pd.notnull(x) else []
        )
        self.df_raw['estimated_time_hours'] = pd.to_numeric(self.df_raw['estimated_time_hours'], errors='coerce').fillna(10.0)
        self.df_raw['Ratings'] = pd.to_numeric(self.df_raw['Ratings'], errors='coerce').fillna(4.0)
        
        # Ensure link column exists for downstream UI.
        if 'Course_link' not in self.df_raw.columns:
            self.df_raw['Course_link'] = "#"

    def _get_similarity(self, s1: str, s2: str) -> float:
        s1, s2 = s1.lower().strip(), s2.lower().strip()
        if s1 == s2:
            return 1.0
        if ALIAS_LOOKUP.get(s1) == s2 or ALIAS_LOOKUP.get(s2) == s1:
            return 1.0
        return SequenceMatcher(None, s1, s2).ratio()

    def _dedupe_skill_dicts(self, items: List[Dict], skill_key: str = "skill") -> List[Dict]:
        """Keep one row per topic; retain the representative with the highest relevance."""
        if not items:
            return []
        sorted_items = sorted(items, key=lambda x: -x.get("relevance", 0))
        kept: List[Dict] = []
        for m in sorted_items:
            s = m[skill_key]
            if any(self._get_similarity(s, k[skill_key]) >= DEDUPE_SKILL_SIM for k in kept):
                continue
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
        """Skills already on the resume but still important in the JD (high priority or high relevance); used for optional refresher paths."""
        specs = []
        for item in jd_results:
            if not getattr(item, 'is_matched', False):
                continue
            pri = getattr(item, 'priority_level', "Low")
            rel = getattr(item, 'relevance_score', 0)
            if pri == "High" or rel >= min_relevance:
                specs.append({
                    "skill": item.canonical_name,
                    "relevance": rel,
                    "priority": pri,
                })
        specs = self._dedupe_skill_dicts(specs)
        return sorted(specs, key=lambda x: -x['relevance'])

    def get_roadmap(
        self,
        missing_skills: List[Dict],
        time_budget: float,
        refresher_skills: Optional[List[Dict]] = None,
        refresher_time_budget: Optional[float] = None,
    ) -> Dict[str, pd.DataFrame]:
        if not missing_skills or self.df_raw.empty:
            base = {"recommended": pd.DataFrame(), "optional": pd.DataFrame(), "refresher": pd.DataFrame()}
            if refresher_skills and not self.df_raw.empty:
                base.update(self._refresher_only_roadmap(refresher_skills, refresher_time_budget, time_budget, set()))
            return base

        working_df = self.df_raw.copy()
        current_missing = self._dedupe_skill_dicts(missing_skills.copy())
        recommended: List[Any] = []
        remaining_budget = float(time_budget)
        selected_titles: Set[str] = set()

        unique_course_skills = {s for sublist in working_df['skill_list'] for s in sublist}
        sim_cache = {(m['skill'], cs): self._get_similarity(m['skill'], cs)
                     for m in current_missing for cs in unique_course_skills}

        def calc_weighted_coverage(course_skills, missing_list: List[Dict]) -> float:
            if not course_skills:
                return 0.0
            score = 0.0
            for m in missing_list:
                best_sim = max([sim_cache.get((m['skill'], cs), 0) for cs in course_skills] + [0])
                if best_sim > SIM_THRESHOLD:
                    score += best_sim * m['relevance']
            return score

        # --- PHASE 1: RECOMMENDED (prefer weighted coverage per unit time / efficiency) ---
        while remaining_budget > 0 and current_missing:
            working_df['match_val'] = working_df['skill_list'].apply(
                lambda cs: calc_weighted_coverage(cs, current_missing)
            )
            working_df['efficiency'] = working_df['match_val'] / working_df['estimated_time_hours'].clip(lower=0.5)

            candidates = working_df[
                (working_df['match_val'] > 0) & (working_df['estimated_time_hours'] <= remaining_budget)
            ]
            if candidates.empty:
                break

            best_course = candidates.sort_values(['efficiency', 'match_val', 'Ratings'], ascending=False).iloc[0]
            recommended.append(best_course)
            remaining_budget -= float(best_course['estimated_time_hours'])
            selected_titles.add(best_course['Course title'])

            covered_names = []
            for m in current_missing:
                if any(sim_cache.get((m['skill'], cs), 0) > SIM_THRESHOLD for cs in best_course['skill_list']):
                    covered_names.append(m['skill'])

            current_missing = [m for m in current_missing if m['skill'] not in covered_names]
            working_df = working_df.drop(best_course.name)

        # --- PHASE 2: OPTIONAL (high-priority gaps not fully covered within budget) ---
        optional: List[Any] = []
        high_pri_left = [
            m for m in current_missing
            if "High" in str(m['priority']) or "Critical" in str(m['priority'])
        ]
        for m in high_pri_left:
            working_df['opt_match'] = working_df['skill_list'].apply(
                lambda cs: max([sim_cache.get((m['skill'], c), 0) for c in cs] + [0])
            )
            opt_candidates = working_df[
                (working_df['opt_match'] > OPTIONAL_GAP_SIM)
                & (~working_df['Course title'].isin(selected_titles))
            ]
            if not opt_candidates.empty:
                best_opt = opt_candidates.sort_values(['opt_match', 'Ratings'], ascending=False).iloc[0]
                optional.append(best_opt)
                selected_titles.add(best_opt['Course title'])
                working_df = working_df.drop(best_opt.name)

        refresher_df = pd.DataFrame()
        if refresher_skills:
            for m in refresher_skills:
                for cs in unique_course_skills:
                    sim_cache[(m['skill'], cs)] = self._get_similarity(m['skill'], cs)
            refresher_df = self._build_refresher_courses(
                refresher_skills,
                sim_cache,
                selected_titles,
                time_budget,
                refresher_time_budget,
            )

        return {
            "recommended": pd.DataFrame(recommended),
            "optional": pd.DataFrame(optional),
            "refresher": refresher_df,
        }

    def _build_refresher_courses(
        self,
        refresher_skills: List[Dict],
        sim_cache: Dict,
        selected_titles: Set[str],
        main_budget: float,
        refresher_time_budget: Optional[float],
    ) -> pd.DataFrame:
        specs = self._dedupe_skill_dicts(refresher_skills)
        rb = refresher_time_budget
        if rb is None:
            rb = max(8.0, min(35.0, float(main_budget) * 0.35))
        pool = self.df_raw[~self.df_raw['Course title'].isin(selected_titles)].copy()
        rows: List[Any] = []

        for m in sorted(specs, key=lambda x: -x['relevance']):
            if rb <= 0 or pool.empty:
                break

            def row_score(cs):
                best = max([sim_cache.get((m['skill'], c), 0) for c in cs] + [0])
                return best * m['relevance'] if best > SIM_THRESHOLD else 0.0

            pool['rscore'] = pool['skill_list'].apply(row_score)
            cand = pool[(pool['rscore'] > 0) & (pool['estimated_time_hours'] <= rb)]
            if cand.empty:
                continue
            pick = cand.sort_values(['rscore', 'Ratings'], ascending=False).iloc[0]
            rows.append(pick)
            rb -= float(pick['estimated_time_hours'])
            selected_titles.add(pick['Course title'])
            pool = pool.drop(pick.name)

        return pd.DataFrame(rows)

    def _refresher_only_roadmap(
        self,
        refresher_skills: List[Dict],
        refresher_time_budget: Optional[float],
        main_budget: float,
        already: Set[str],
    ) -> Dict[str, pd.DataFrame]:
        unique_course_skills = {s for sublist in self.df_raw['skill_list'] for s in sublist}
        sim_cache = {}
        for m in refresher_skills:
            for cs in unique_course_skills:
                sim_cache[(m['skill'], cs)] = self._get_similarity(m['skill'], cs)
        df = self._build_refresher_courses(
            refresher_skills, sim_cache, already, main_budget, refresher_time_budget
        )
        return {"refresher": df}
