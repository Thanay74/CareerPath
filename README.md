# CareerPath

CareerPath is an explainable student career guidance project for 10th Standard, 12th Standard, Bachelor's and Master's students. It combines a stage-specific trained career-family model with education-aware compatibility scoring against a career knowledge base. The combined score drives ranking; skill gaps, explanations and improvement plans are derived from the same profile and career requirements. A separate UCI experiment predicts academic grade bands only; its labels are not treated as career outcomes.

## Quick start

1. Install Python 3.10+ and Node.js 18+.
2. In `backend/`, run `python -m venv .venv`, activate it, then `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env`; set a strong `ADMIN_PASSWORD` and a dedicated MySQL `DATABASE_URL` for persistent MySQL mode. Without `DATABASE_URL`, local SQLite is used for development.
4. Configure Kaggle CLI credentials outside the repository (never add `kaggle.json` to the project), then download the optional university benchmark: `kaggle datasets download -d mobeenfatimah/student-career-success-prediction-dataset -p data/raw/kaggle_student_career_success`. The Kaggle data card identifies all 50,000 records as synthetic.
5. Generate assessment fixtures and CareerPath model data: `python data/generate_synthetic_data.py` and `python data/generate_career_training_data.py` (the latter produces only explicitly synthetic model records).
6. Train and compare per-stage models: `python -m backend.ml.train_career_models`. The saved pipelines and metric report are used by live recommendations. Reproduce the separate majority-class baseline report with `python -m backend.ml.diagnose_career_models`.
7. Optional Kaggle benchmark: `python -m backend.ml.preprocess_kaggle_career`, then `python -m backend.ml.train_kaggle_career_model`. It predicts Kaggle's synthetic university `Career_Field` labels only and does not replace the four education-level recommender models.
8. Run `python -m backend.app` from the repository root (API on port 5000).
9. In another terminal run `cd frontend; npm install; npm run dev` (Vite on port 5173).

For a new MySQL database, run `backend/schema.sql` and create a scoped application user. For an existing CareerPath database, apply the additive migration `backend/migrations/001_education_and_aptitude.sql` once before deployment; it adds student education fields and assessment-history tables without dropping or rewriting records. Put the dedicated application account in `.env` as `DATABASE_URL=mysql+pymysql://careerpath_app:...@localhost:3306/careerpath`. Do not use root as the application account. Set `ADMIN_EMAIL` and a 12+ character `ADMIN_PASSWORD` in `.env`; create the first administrator only through the explicit, target-confirmed setup workflow. Normal API startup does not bootstrap an administrator. Register/log in, complete and save the profile, take the scored aptitude assessment, then request recommendations. The app uses only backend-scored attempt results as aptitude inputs.

## Career catalog modes

For local development, when both `data/career_active.json` and `data/career_catalog_managed.json` are absent, the backend reads and validates the canonical `data/career_knowledge_base.csv` and `data/career_metadata.json` pair. This is the pre-versioned bootstrap mode. A present active pointer must be valid and select a complete validated release; if the managed marker exists but its pointer is missing, or either present file is malformed, catalog reads fail closed. Do not create or delete pointer/marker files manually.

Admin career edits are staged. Publishing is an explicit, controlled transition to a versioned release; the initial canonical pair is retained as a rollback release. Do not publish merely to make the Admin screen appear initialized.

Local bootstrap behavior is not production approval. Production must use an explicitly approved catalog mode; the deployment must validate the exact catalog artifacts, preserve versioned release state on persistent/shared storage where multiple instances need it, and exercise controlled activation plus rollback/recovery before release. Do not claim production readiness until those checks pass.

## Assessment workflow

Education options come from `/api/education/catalog`: 10th and 12th stream-specific subjects, Bachelor's degree/specialization subjects, and Master's degree/specialization subjects. Custom degrees, specializations, and subjects can be entered. Interests and technical/employability ratings remain distinct self-reported measures.

The 25-question aptitude bank lives in `backend/aptitude_bank.py`. Question APIs omit answer keys. An authenticated student starts an attempt, responds to every randomized question, and submits once; the Flask API calculates domain and overall scores, stores responses and history in MySQL/SQLite, and makes the latest completed result available to recommendations. It is a project-level exercise, not a professionally validated psychometric assessment. See `API_DOCUMENTATION.md` for route details.

## Data integrity

The UCI and Kaggle sources are documented in [DATA_SOURCES.md](DATA_SOURCES.md). UCI's 395 Mathematics course records describe grades and school/life attributes, not career outcomes or skills. They train only a separate academic grade-band experiment. The Kaggle university benchmark is synthetic and targets a career field among placed records; it does not cover the four-stage CareerPath profile. Career-family recommendation models are trained only on separately labeled, locally generated profiles. Their test metrics describe agreement with generated labels, not accuracy on real students. Original archives are preserved in `data/raw/`; processed artifacts are separate. No user-collected survey cohort is currently available. `data/career_knowledge_base.csv` is a separate curated reference table, not outcome labels.

## Project map

See [SRS_IMPLEMENTATION.md](SRS_IMPLEMENTATION.md), [ARCHITECTURE.md](ARCHITECTURE.md), [API_DOCUMENTATION.md](API_DOCUMENTATION.md), [SETUP_GUIDE.md](SETUP_GUIDE.md), [DATA_DICTIONARY.md](DATA_DICTIONARY.md), and [MODEL_REPORT.md](MODEL_REPORT.md). Run `python -m unittest discover -s tests` for checks; run `python -m backend.ml.train_model` for the UCI grade-band experiment, `python -m backend.ml.train_career_models` for the synthetic four-stage model comparison, and the Kaggle preprocess/train commands above for the separate university benchmark. SHAP TreeExplainer contributions are available for tree-model career predictions.

```text
CareerPath/
├── backend/
│   ├── app.py, schema.sql, requirements.txt
│   ├── aptitude_bank.py, education_catalog.py
│   ├── migrations/001_education_and_aptitude.sql
│   ├── ml/  (career data loader, stage features, preprocessing,
│   │        training, evaluation, prediction, SHAP, Kaggle benchmark)
│   ├── models/
│   │   ├── career/  (four saved stage-specific pipelines)
│   │   └── grade_band_pipeline.joblib
│   └── services/  (hybrid recommendation and skill-gap logic)
├── data/
│   ├── raw/student_performance/  (preserved UCI source archive/CSVs)
│   ├── raw/kaggle_student_career_success/  (Kaggle ZIP + extracted synthetic source)
│   ├── synthetic/  (separate reproducible profile and career training CSVs)
│   ├── processed/career_model_metrics.json
│   ├── processed/kaggle_career_model_metrics.json
│   └── career_knowledge_base.csv
├── docs/career-references.md
├── frontend/  (React/Vite source and built dist/)
├── tests/  (API, auth, recommendation, ML and sample profiles)
├── API_DOCUMENTATION.md
├── DATA_DICTIONARY.md
├── DATA_SOURCES.md
├── MODEL_REPORT.md
├── SRS_IMPLEMENTATION.md
├── ARCHITECTURE.md, SETUP_GUIDE.md
├── .env.example, .gitignore
└── README.md
```

Educational guidance is advisory. Students should confirm admissions, licensing, and professional requirements with official institutions.
