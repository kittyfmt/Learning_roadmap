# ResumeSkillExtractor Logic Documentation

The `ResumeSkillExtractor` is a specialized module for high-recall skill extraction from diverse resume formats, utilizing the `SkillNER` framework.

## 1. Core Architecture
The extractor is designed for maximum robustness, using a multi-layered fallback strategy to handle noisy or complex resume text.

### Stage 1: Text Preprocessing
- **Method**: Regex-based normalization.
- **Cleaning**:
    - **HTML Tag Removal**: Strips any residual markup.
    - **Whitespace Normalization**: Collapses multiple newlines/spaces.
    - **ASCII Filtering**: Removes non-ASCII characters to prevent internal model crashes.
    - **Abbreviation Expansion**: Replaces common shorthand like "e.g." and "i.e." with expanded phrases to ensure the NER model interprets them correctly as context.

### Stage 2: SkillNER Pipeline
- **Engine**: `SkillExtractor` (leveraging spaCy and `SKILL_DB`).
- **Logic**: It uses a phrase-matching algorithm to identify both "Full Matches" (exact matches in the skill database) and "N-gram Scored" matches (partial or fuzzy matches based on token overlaps).
- **Matching Mechanism**:
    1. **Full Matches**: High-precision matches from the skill database.
    2. **N-gram Scored**: Higher-recall matches that identify candidate skills by their token similarity.

### Stage 3: Robust Fallback Strategy
If the `SkillNER` model fails on a large block of text (due to complexity or length), the system implements a recursive decomposition approach:
1. **Sentence Segmentation**: Uses spaCy's sentence boundary detection to break the resume into smaller, manageable chunks.
2. **Safe Annotation**: Attempts to extract skills sentence by sentence.
3. **Punctuation Splitting**: If a sentence is still too complex, it splits the text by commas and semicolons.
4. **Token-Level Recovery**: As a final resort, it attempts to extract skills token by token to ensure no mention is lost.

### Stage 4: Result Sanitization
- **Logic**: Filters out single-character extractions and standardizes all results to lowercase.
- **Deduplication**: Returns a unique list of canonical skill names identified across the entire document.

## 2. Outputs
The extractor provides:
- A list of **unique skills** extracted from the resume.
- A "Payload" containing the cleaned text, the list of skills, and the total count.

## 3. Interaction with JD Extractor
The skills extracted here are passed to the `JDSkillExtractor`'s matching logic. This ensures that the system can determine which of the JD's requirements the candidate already satisfies, regardless of whether the terminology used in the resume exactly matches the JD's phrasing.
