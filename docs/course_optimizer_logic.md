# CourseOptimizer Logic Documentation

The `CourseOptimizer` is a strategic module responsible for gap analysis and the automated construction of an optimized learning roadmap using a multi-factor utility model and a multi-phase recommendation strategy.

## 1. Core Architecture
The optimizer uses an iterative, multi-phase algorithm driven by a comprehensive **Utility Function** to identify the best courses across different learning scenarios.

### Stage 1: Pre-processing & Normalization
To ensure high performance, the optimizer pre-calculates static components of the course score during initialization:
- **Language Priority**: Assigns a binary `lang_score` (1.0 for 'en', 0.0 otherwise).
- **Difficulty Mapping**: Maps "Beginner", "Intermediate", and "Advanced" to numeric levels (1, 2, 3).
- **Quality Normalization**: 
    - **Ratings**: Min-Max scaling of course ratings.
    - **Reviews**: Log-normalization of review counts to handle the skewed distribution of popularity.
- **Static Quality Score**: A combined metric: `0.7 * Rating_Norm + 0.3 * Review_Norm`.

### Stage 2: The Multi-Factor Utility Model
Each course is evaluated using a dynamic Utility Score ($U$) based on the following weights:
- **Skill Coverage (45%)**: Measures alignment with current missing skills, weighted by JD relevance.
- **Language Preference (25%)**: Strongly prioritizes English (`en`) courses. Non-English courses receive a significant utility penalty.
- **Difficulty Match (10%)**: Aligns course level with user proficiency.
- **Course Quality (10%)**: Combined rating and review credibility.
- **Time Penalty (10%)**: Optimizes for the user's available budget.

### Stage 3: Multi-Phase Recommendation Strategy

#### Phase 1: Core Recommended Path (Greedy Optimization)
- **Goal**: Cover as many gaps as possible within the user's time budget.
- **Efficiency**: Courses are ranked by `Utility / Hours`.
- **Logic**: Iteratively selects the most efficient course, then removes covered skills from the "Missing" list and recalculates utility for the remaining pool.

#### Phase 2: Guaranteed Extensions (Next Steps)
- **Goal**: Ensure the user always has "future state" options even if gaps were covered in Phase 1.
- **Logic**: Target the **Top 3 most relevant gaps** from the JD. Even if these were partially covered in Phase 1, the system identifies alternative or advanced courses in the remaining pool.
- **Recall**: Uses a relaxed similarity threshold (0.45) to maximize recommendation variety.

#### Phase 3: Strict English Refreshers
- **Goal**: Polish existing skills that the JD weights heavily.
- **Constraint**: **Strict English Only**. Non-English courses are entirely excluded from this phase to ensure high-quality review material.
- **Priority**: Prioritized by JD relevance and course quality.

## 2. Global Similarity Cache
To ensure speed (under 200ms), the optimizer builds a **Global Similarity Matrix** upon initialization of the `get_roadmap` call. This cache maps every potential gap skill to every skill in the course catalog, eliminating redundant string matching during the optimization loops.

## 3. Interaction with UI
- **Budget Slider**: Influences the **Time Penalty** in Phase 1.
- **Inclusive Extensions**: Ensuring the "Extension" section is never empty provides a more engaging user experience, showing that the tool has depth beyond the immediate budget.
- **Language**: Users will primarily see English results unless no English equivalent exists for a specific niche skill.
