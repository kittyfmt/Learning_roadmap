# Career Roadmap AI Explorer 🧭

**Using machine learning to identify professional skill gaps and automate personalized career learning roadmaps.**

---

## 🚀 Project Overview
The **Career Roadmap App** is an interactive, AI-powered platform designed to bridge the gap between a candidate's current profile and their target career goals. By leveraging a custom Machine Learning pipeline, the tool automatically extracts technical competencies from resumes and job descriptions to provide a high-precision skill gap analysis.

## ✨ Key Features
- **ML-Hybrid Skill Extraction**: Combines deterministic taxonomy matching with a custom-trained **NER (Named Entity Recognition)** model.
- **Predictive Importance Ranking**: Uses a Linear Regression model (`skill_ranker.joblib`) to predict skill relevance based on frequency, context (must-have vs. nice-to-have), and document position.
- **Utility-Based Course Optimization**: An intelligent recommendation engine that maximizes learning utility based on:
    - **Skill Coverage** (45%)
    - **English Language Priority** (25%)
    - **Course Quality & Difficulty Match** (20%)
    - **Time Efficiency** (10%)
- **Interactive Roadmap**: A visual timeline that adapts in real-time to user-defined time budgets.

## 🏗️ Architecture
- **Backend**: Python, SpaCy (NLP), Scikit-Learn (Ranking Model), SkillNER.
- **Frontend**: Streamlit (Interactive Dashboard).
- **Data**: Curated skill taxonomy and a specialized course catalog.

## 🛠️ Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-repo/career-roadmap-app.git
   cd career-roadmap-app
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

3. **Run the Application**:
   ```bash
   streamlit run app.py
   ```

## 🧠 Model Logic
Detailed technical documentation for our core models can be found in the `docs/` directory:
- [JD Extractor Logic](./docs/jd_extractor_logic.md)
- [Resume Extractor Logic](./docs/resume_extractor_logic.md)
- [Course Optimizer Logic](./docs/course_optimizer_logic.md)

## 👥 Team
**Team Pathfinder AI** - INDENG 243 Analytics Lab (Module 3)
