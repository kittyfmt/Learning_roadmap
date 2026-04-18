# JDSkillExtractor Logic Documentation

The `JDSkillExtractor` is a hybrid machine-learning-driven module designed to identify, categorize, and prioritize technical skills within a Job Description (JD).

## 1. Core Architecture
The extractor operates as a multi-stage pipeline combining deterministic taxonomy lookup, Named Entity Recognition (NER), and a ranking model.

### Stage 1: Taxonomy Discovery
- **Method**: Exact and Alias-based Regex Matching.
- **Logic**: Iterates through the `TAXONOMY` (defined in `taxonomy_loader.py`). It searches for canonical names and their defined aliases (e.g., "SQL" matches "PostgreSQL", "T-SQL", etc.).
- **Precision**: High. This stage ensures that known industry-standard skills are captured with their correct metadata.

### Stage 2: ML-Based NER Discovery
- **Method**: Custom spaCy NER Model (`hard_skill_model.pkl`).
- **Logic**: Processes the JD text to find entities labeled as potential skills that were missed by the taxonomy.
- **Cleaning**:
    - Filters out "Banned Entities" (Organizations, Dates, Locations, People).
    - Filters by Token Length (rejects single-character or overly long spans).
    - **POS Filtering**: Rejects extractions consisting purely of stop words, verbs, or pronouns.

### Stage 3: Feature Engineering
For every identified skill, the system extracts a feature vector used for importance prediction:
1. **Frequency (`log_freq`)**: Number of times the skill appears, scaled logarithmically to prevent outliers from dominating.
2. **First Position (`first_pos`)**: The normalized index of the first occurrence. Skills mentioned earlier are typically more critical.
3. **Context Weight (`context_weight`)**: Scans the sentences containing the skill for "Priority Keywords" (e.g., *must*, *required*, *essential*) vs. "Secondary Keywords" (e.g., *plus*, *preferred*).
4. **NER Boost (`ner_boost`)**: A binary indicator of whether the custom ML model identified the span as a technical entity.

### Stage 4: Importance Ranking (ML Model)
- **Model**: `skill_ranker.joblib` (Linear Regression trained via Knowledge Distillation).
- **Prediction**:
    - Combines the 4 extracted features with a `cat_bias` (extra weight for core categories like ML/AI and Programming).
    - Outputs a `relevance_score` between 0.0 and 1.0.

### Stage 5: Difficulty & Priority Assignment
- **Difficulty Score**: Retreived from a pre-defined mapping of categories (e.g., Deep Learning = 0.9, Tools = 0.3).
- **Priority Level**:
    - Formula: `priority_score = (relevance * 0.7) + (difficulty * 0.3)`.
    - **High**: score > 0.72
    - **Medium**: score > 0.42
    - **Low**: otherwise.

## 2. Outputs
The extractor returns a list of `SkillResult` objects, containing:
- `canonical_name`: The standardized name of the skill.
- `category`: The logical grouping (e.g., "Cloud", "ML/AI").
- `relevance_score`: Predicted importance to the job.
- `difficulty_score`: Categorical complexity.
- `priority_level`: Final priority tag (High/Medium/Low).
- `is_matched`: Boolean indicating if the skill already exists on the user's resume.
