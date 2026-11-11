# Data sources and provenance

## UCI Student Performance

- Provider: UCI Machine Learning Repository; creators Paulo Cortez and Alice Silva.
- Dataset: Student Performance (UCI ID 320), DOI [10.24432/C5TG7T](https://doi.org/10.24432/C5TG7T).
- Original URL: https://archive.ics.uci.edu/dataset/320/student%2Bperformance
- Kaggle URL: No mirror used for this UCI academic experiment.
- License: Creative Commons Attribution 4.0 International (CC BY 4.0).
- Records: 395 mathematics-course students (`student-mat.csv`) and 649 Portuguese-course records (`student-por.csv`); the two cohorts overlap and must not be summed as unique students.
- Original columns: `school, sex, age, address, famsize, Pstatus, Medu, Fedu, Mjob, Fjob, reason, guardian, traveltime, studytime, failures, schoolsup, famsup, paid, activities, nursery, higher, internet, romantic, famrel, freetime, goout, Dalc, Walc, health, absences, G1, G2, G3`.
- CareerPath use: supplementary academic grade-band experiment only. Target is derived from `G3`; `G1`/`G2` are excluded to prevent temporal grade leakage. No career labels or career recommendation features are inferred from this dataset.
- Preprocessing: original official archive and nested CSV files are preserved under `data/raw/student_performance/`; official semicolon-separated CSVs preserved under `extracted/`; categorical columns one-hot encoded, numeric columns median-imputed/scaled; stratified split. `G3` mapped into disclosed grade bands. Input pipeline avoids using target and future/adjacent period grades.
- Role: training/test evaluation for the academic grade-band experiment; supplementary analysis only for career recommendations.
- Download: `python data/download_public_data.py` saves official archive and extracted files. The original source files are included in this project.

### Other Kaggle sources screened and excluded (not imported)

- [300K Student Performance Prediction Dataset](https://www.kaggle.com/datasets/rhythmghai/300k-student-performance-prediction-dataset): the data card explicitly identifies the 300,000 rows as synthetically generated and targets grades/pass-fail. License listed as Apache 2.0. Excluded as a real-data source; CareerPath instead uses the fixed-seed generator whose synthetic provenance is explicit.
- [Engineer Grad Prof. Outcomes Analysis](https://www.kaggle.com/datasets/manishkumardubey/engineer-grad-prof-outcomes-analysis): advertised fields include academic percentages, quantitative aptitude, engineering-domain skills, industry domain and starting salary. The Kaggle data card listed its license as unknown and its target/provenance could not be independently verified. Excluded.
- [Engineering Student Journey](https://www.kaggle.com/datasets/rakeshkapilavai/engineering-student-journey): the page lists a CC0 license and describes academic/placement outcomes, but its detailed raw schema and provenance were not independently verified for this project. Excluded rather than mixing unverifiable placement labels into a guidance model.

These additional candidates were reviewed but are not part of the training or evaluation data.

## Kaggle-published synthetic university career dataset

- Provider: Kaggle contributor Mobeen Fatima; dataset title **Student Career Success Prediction Dataset**.
- Source URL: https://www.kaggle.com/datasets/mobeenfatimah/student-career-success-prediction-dataset
- Download file: `student-career-success-prediction-dataset.zip`; source CSV: `student_career_success_dataset.csv`.
- License: **CC BY-SA 4.0** as shown on the Kaggle dataset page. Reuse and redistribution must provide attribution and comply with the share-alike terms. Dataset author attribution: Mobeen Fatima, Kaggle dataset above.
- Source type: **synthetic**. The Kaggle data card says the records are generated and contain no real student information.
- Records: 50,000 source rows, 29 columns; source claims no missing values or duplicate student IDs. `Career_Field` includes 10,960 `Not Placed` rows and 39,040 placed rows.
- Local files: unmodified archive and extracted source CSV are preserved in `data/raw/kaggle_student_career_success/`. `data/processed/kaggle_student_career_success/career_field_training.csv` contains the 39,040 rows whose target is a placed career field and 15 pre-outcome features.
- Downloaded archive SHA-256: `60F7BBF8B0421452B411932DE2AFF1EC16D7B6F9EB0FF26B692BAF2A253F0B9E`.
- Purpose: a separate Bachelor's/university-level RF vs XGBoost benchmark predicting the source's career-field label conditional on placement. It does **not** train or replace the four-stage recommender because its synthetic population, target taxonomy, and feature set do not cover 10th, 12th, Master's or the CareerPath assessment contract. It is not treated as real student or placement evidence.
- Leakage controls: `Student_ID`, demographics, derived `Academic_Performance`, post-outcome interview/employability/placement/company/salary/mode fields are not features. The `Career_Field` target and `Not Placed` label are excluded from the feature table.
- Evaluation: stratified 80/20 holdout and 5-fold stratified CV on the training partition; seed `20261010`; both RF and XGBoost; selection uses mean CV macro-F1 only. The holdout partition is used only for final evaluation. Accuracy, macro precision/recall/F1, confusion matrix, class-wise report and CV means/SD are saved in `data/processed/kaggle_career_model_metrics.json`.
- Download: configure Kaggle CLI credentials outside the repository, then run `kaggle datasets download -d mobeenfatimah/student-career-success-prediction-dataset -p data/raw/kaggle_student_career_success`. The archive is not overwritten by the preprocessing/training scripts.

## Application and reference data

Assessment answers entered by users are application questionnaire data. `data/synthetic/` contains reproducible locally generated synthetic development profiles; the Kaggle dataset is also synthetic but kept in its own provenance folder. Neither source is a public real-student dataset. `data/career_knowledge_base.csv` is a curated, versioned reference table with education/skill requirements; its values are guidance criteria, not empirical student outcomes. Career qualification references are in [docs/career-references.md](docs/career-references.md).

### Synthetic career-family model profiles

- Dataset: `data/synthetic/career_training_profiles.csv`.
- Provider/source: generated locally by `data/generate_career_training_data.py`; no external student data.
- License: project-generated synthetic records.
- Records: 1,600 (400 per education stage); five broad family labels; reproducible seed `20260929`.
- Columns: `synthetic_id`, `education_level`, `stream`, stage-relevant subject, aptitude, interest, technical and employability dimensions, `career_family`.
- Purpose: train and evaluate stage-specific Random Forest/XGBoost career-family models, enabling actual model probabilities in hybrid recommendations.
- Preprocessing: empty subject/skill values are missing or non-applicable; imputation and categorical stream encoding are fitted only within each training fold/pipeline. Synthetic labels are latent generator scenarios related to the sampled profile distributions. They do not represent known student choices or real outcomes.
- Role: stratified train/test evaluation and 5-fold cross-validation, all explicitly synthetic. Candidate selection uses mean CV macro-F1 from the training partition; only the selected candidate is evaluated on the held-out test partition. The held-out test scores measure agreement with synthetic labels only. This protocol describes the current training code; already-saved artifacts and metrics may predate it and must be checked against `MODEL_REPORT.md` before being treated as corrected-protocol results.

### Application questionnaire data

No user-collected survey dataset was supplied or included at project build time. Data submitted by a student during runtime is application questionnaire data stored in the configured application database and is not aggregated into model training data.

### Project-level aptitude question bank

- Source: 25 project-authored multiple-choice questions in `backend/aptitude_bank.py`; this is assessment content, not a student dataset and not externally validated test material.
- Coverage: Logical, numerical, verbal, spatial, analytical, problem-solving, and attention-to-detail domains. Questions include four options, one backend-held answer key, explanation, difficulty, and education-level eligibility.
- Purpose: In-session student aptitude assessment. The API returns question text/options without the key, then scores submitted answers server-side and persists responses/results per student.
- Classification: Original project content; not public data, not user-collected survey data, and not synthetic student records. Results must be described as a project-level exercise, not a professionally validated psychometric test.

### Education catalog

- Source: Configurable project-maintained metadata in `backend/education_catalog.py`.
- Purpose: Drive education-level-dependent stream/degree/specialization selectors and relevant academic subject choices. The catalog is curricular guidance and not a claim that all institutions use the same curriculum. Custom course and subject entries are supported.
- Classification: Reference metadata only; not training data or student outcome data.
