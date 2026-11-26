# CareerPath Machine Learning Implementation Audit

**Audit date:** 2026-11-16
**Scope:** Read-only source, documentation, artifact-inventory, aggregate dataset inspection, and SRS PDF text extraction. No training, model loading, application startup, database access, tests, or build commands were run.

**SRS source reviewed:** `C:\Users\THANAY\Documents\CP SRS.pdf` (20 pages). Relevant requirements are pp. 3-8 (scope, ML/XAI architecture and pipeline), pp. 14-16 (UI, scikit-learn/RF/XGBoost/SHAP/Pandas/NumPy and API communication), and pp. 17-19 (safety, evaluation, explainability and environment). The SRS describes RF/XGBoost as candidate algorithms that can be evaluated; no numeric accuracy target was present in the inspected requirements. It expects understandable recommendation factors and says recommendations do not guarantee outcomes.

## Executive summary

CareerPath has a real, stage-specific machine-learning component in its live recommendation path: a saved Random Forest or XGBoost pipeline predicts one of five broad, generator-defined career families for each education level. That family probability contributes 10% of the hybrid ranking score. Most student-to-career fit calculation, the Class 10 stream comparison, the skills analysis, and the explanations for the compatibility score are deterministic catalog/rule calculations. Accordingly, the product is a **rule/profile recommender with a small experimental ML signal**, not a career-specific prediction system.

Random Forest and XGBoost are both implemented as candidates in `backend/ml/train_career_models.py`; only the CV-selected candidate is saved for each stage. The checked-in metrics identify Random Forest as selected at all four stages, and the model report says the existing artifacts and metrics predate the corrected CV-only selection protocol. Thus the source implements corrected selection, but the current artifacts do **not** have verified corrected-protocol provenance. SHAP is implemented as a best-effort tree-model explanation of family scores, not an explanation of career compatibility or pathway rules.

The career training data is explicitly synthetic. Its labels are selected first and its profile fields are generated from family-specific distributions, so the very high historical metrics measure agreement with the generator's assumptions. They do not establish real-student validity. The separate Kaggle university benchmark is also synthetic, is not wired into inference, and its documented holdout accuracy is about 40%. The UCI experiment predicts grade bands, not careers.

**Overall ML evidence status: NOT READY for real-world predictive-validity claims or production claims based on model performance.** Source architecture and the corrected selection code are present; corrected artifacts/metrics, external validation, and reliable empirical career outcomes are absent.

## Actual end-to-end implementation

1. **Training data:** `data/generate_career_training_data.py` creates `data/synthetic/career_training_profiles.csv`. It samples a latent `career_family` first, then draws scores from a family-specific profile distribution. `backend/ml/career_data_loader.py::load_career_data` reads this file and currently checks only required label columns and missing family labels.
2. **Feature construction:** `backend/ml/feature_engineering.py::STAGE_FEATURES` defines separate subject/skill feature sets for 10th, 12th, Bachelor's, and Master's. `feature_row` creates a row from the saved profile and leaves unprovided dimensions missing. `stream` is a categorical feature.
3. **Preprocessing and training:** `backend/ml/career_preprocessing.py::make_career_preprocessor` median-imputes numeric inputs (with missing indicators) and most-frequent-imputes/one-hot-encodes stream within a scikit-learn pipeline. `backend/ml/train_career_models.py::main` splits each stage 80/20 with stratification and fixed seed 20260929; candidate selection uses mean five-fold CV macro-F1 on the training partition, then evaluates the selected candidate once on holdout. It writes four stage pipelines and a metrics JSON when explicitly run; it was not run for this audit.
4. **Inference:** `backend/ml/predict.py::predict_career_families` loads the education-level `.joblib` artifact and returns probabilities for the five family classes. It does not directly predict a specific course, institution, degree, or job.
5. **Eligibility and ranking:** `backend/app.py::create_recommendations` authenticates/loads the saved student profile and calls `recommend_with_catalog_fingerprint`. In `backend/services/recommendation_engine.py::_recommend_with_catalog`, later-stage careers are screened by minimum stage and `assess_eligibility`; verified `not_currently_eligible` entries are removed. Remaining records receive a catalog/profile compatibility score and a family probability. The combined score is 90% compatibility and 10% family probability. Class 10 uses `backend/services/school_pathways.py::evaluate_pathway` and its four configured pathway rules; it aggregates broad family probabilities into pathway signals and labels them experimental.
6. **Explanation and API/UI:** Recommendation responses and saved snapshots are returned from the Flask API. The engine supplies score components, catalog-based reasons, skill gaps, eligibility status, and model-family probabilities. `backend/ml/explain.py::explain_career_model` optionally computes SHAP `TreeExplainer` values for a family class. `frontend/src/ModelExplanation.jsx` labels the output as a family signal only; `frontend/src/main.jsx::RecommendationCard` separately presents compatibility, eligibility, score reasons, and gaps.

## Model implementation status

| Model/requirement | Status | Evidence and interpretation |
|---|---|---|
| Per-stage Random Forest | **IMPLEMENTED AND USED** (candidate is used in training; artifact metadata itself not opened) | `backend/ml/train_career_models.py::candidates` defines RF; four stage artifacts are present and `data/processed/career_model_metrics.json` records `random_forest` selected for every stage. Current artifact bytes were not deserialized during this read-only audit. |
| Per-stage XGBoost | **IMPLEMENTED BUT NOT SELECTED in recorded current metrics** | `candidates` defines XGBoost; the recorded metrics list RF for all four stages. The candidate is evaluated by the training source, but evidence does not show it is the currently served pipeline. |
| Live ML inference | **IMPLEMENTED AND USED** | `recommendation_engine.py::_recommend_with_catalog` calls `predict_career_families` and uses the resulting family probability in the combined score. The model is one of five broad family classes, not a specific-career classifier. |
| SHAP | **PARTIALLY IMPLEMENTED** | `backend/ml/explain.py::explain_career_model` calls `shap.TreeExplainer` if available and returns `unavailable` on error. It explains a target family score only; it does not explain the 90% rule/profile compatibility score. Runtime support/results were not tested. |
| Kaggle career-field RF/XGBoost | **IMPLEMENTED BUT NOT USED by live recommendations** | `backend/ml/train_kaggle_career_model.py` builds a separate university career-field benchmark. Its own module documentation says it does not replace the four-stage recommender; `predict.py` does not load its artifact. |
| UCI grade-band Random Forest | **IMPLEMENTED BUT NOT USED for career recommendations** | `backend/ml/train_model.py` predicts grade bands from UCI Student Performance data; the target is not career choice. |
| Scikit-learn | **IMPLEMENTED AND USED** | Pipelines, imputers, encoder, RF, splitting/CV and metrics use scikit-learn in `backend/ml/`; dependency is in `backend/requirements.txt`. |
| Pandas | **IMPLEMENTED AND USED** | Data loading, training frames and inference inputs use Pandas (`career_data_loader.py`, `train_career_models.py`, `predict.py`). |
| NumPy | **IMPLEMENTED AND USED** | CV aggregation and SHAP array handling use NumPy (`career_evaluation.py`, `explain.py`); dependency is in `backend/requirements.txt`. |

“Used” in the table refers to source-level inference/training wiring and recorded metrics, not an executed runtime verification in this audit.

## Dataset evidence and limitations

Read-only CSV aggregation was run using Python's standard `csv` module; it printed aggregate counts only and did not alter files.

| Dataset | Observed aggregate facts | Audit assessment |
|---|---|---|
| `data/synthetic/career_training_profiles.csv` | 1,600 rows, 59 columns; 400 rows per stage; five family labels; class counts per stage range from 64–101; 11,125 blank cells in 11 feature columns; zero duplicate IDs, zero duplicate full rows, zero nonnumeric observed feature values, and zero numeric feature values outside 0–100. | Clean basic structure for a synthetic experiment, but labels are deliberately generated before correlated profile features. The 400 rows/stage and label-generation process are not empirical observations or evidence of generalization. Missing subject values are intentional by stream/stage per generator comments. |
| `data/processed/kaggle_student_career_success/career_field_training.csv` | 39,040 rows, 16 columns, 16 labels, no blank cells or duplicate full rows. | Separate synthetic university-only conditional-on-placement benchmark. Do not treat as observed career outcomes or feed into stage models. |
| `data/raw/kaggle_student_career_success/student_career_success_dataset.csv` | 50,000 rows, 29 columns; includes 10,960 `Not Placed` labels; no blank cells or duplicate full rows observed in this inspection. | `DATA_SOURCES.md` documents synthetic provenance. The training benchmark excludes `Not Placed` and predicts field only among placed rows, limiting interpretation. |
| UCI Student Performance | `DATA_SOURCES.md` records 395 mathematics and 649 Portuguese records; `backend/ml/train_model.py` predicts grade bands and excludes G1/G2/G3 from features. | Academic benchmark only; not career training or evidence of career prediction. Dataset row counts were not independently recounted in this audit. |

### Data and leakage review

- Career labels are generator-defined latent scenarios; the generator samples the label first, then uses label-specific means for relevant skills/interests/subjects. This is intentional synthetic target construction, but it creates a task that rewards recovering the simulator's own rules.
- The career loader does not currently validate exact allowed stages, feature schema/types/ranges, duplicate IDs, duplicate records, per-stage class completeness, or empty stage partitions. The current checked-in CSV passed the aggregate checks above, but the reusable loader's validation is weaker than that evidence.
- Missing-value handling is fitted inside the training pipeline, which is a good separation practice. However, score fields and labels are synthetic; high model scores are not transportable to users without external validation.
- The Kaggle training feature contract in `backend/ml/kaggle_career_features.py` excludes direct identifiers, the target, and documented post-outcome fields. It excludes `Not Placed`, so it cannot answer placement probability or outcomes for all students. Its labels/data are also synthetic according to project provenance documentation.
- The UCI grade-band experiment excludes G1/G2/G3 from inputs as leakage controls. It is unrelated to the live career-family classifier.
- The SRS (PDF pp. 15-17) also expects timely processing and handling of model/database/communication failures. These latency, load, and failure-mode behaviors were not measured in this audit.

## Evaluation and artifact trust

`backend/ml/train_career_models.py::select_candidate_by_cv` chooses the candidate from CV macro-F1 only. `evaluate_and_select` runs holdout evaluation after that selection. `tests/test_phase2_2a_catalog_and_model_selection.py` contains a unit test with deliberately reversed holdout scores to assert that holdout cannot select the winner.

However, `MODEL_REPORT.md` explicitly states the stage artifacts and metrics currently present were created under the earlier test-macro-F1 selection protocol and are selection-biased. `career_model_metrics.json` confirms recorded selected models, but these are legacy metrics; they are not corrected-protocol results. No training or artifact regeneration is authorized in this audit, and the artifacts were not loaded to inspect embedded metadata. Therefore the current served models’ precise artifact provenance is **unverified**, and no corrected-protocol performance can be reported.

The Kaggle benchmark's code and docs describe CV macro-F1 selection; its metrics are around 0.4 accuracy, below the documented 90% target. Do not present that benchmark as a successful real-world model or as the live four-stage model.

## Recommendation and eligibility behavior

- Most personalized scoring comes from `recommendation_engine.py::_profile_score`, catalog requirements, observed ratings, education level, stream, degree/specialization, and preferences. Missing dimensions are excluded from profile-score normalization; observed scores are bounded by `_num`.
- For later education levels, a verified eligibility status can order/filter candidates before compatibility ranking. But `backend/services/eligibility.py::VERIFIED_PROGRAM_RULES` is empty. Thus no current record has institution-specific verified requirements, and the system appropriately presents eligibility as unverified rather than applying unsupported rules.
- For Class 10, rules in `school_pathways.py::PATHWAY_RULES` compare assessed subjects/aptitude/interests/preferences and use project-defined thresholds. These are guidance comparisons, not admissions requirements. Family model scores are grouped into pathway-level signals and combined only when sufficient rule/profile score exists.
- The 10% ML share does not make the overall score a calibrated probability. Neither the score nor the family probability is an estimate of admission, employment, success, or student preference.
- `backend/services/eligibility.py` checks for current dated rules when entries exist, but no source-backed program rules currently exist in the registry. No institution or jurisdiction eligibility coverage can be claimed.

## SRS alignment matrix

| SRS Requirement | Current Implementation | Evidence/File | Status | Required Work |
|---|---|---|---|---|
| Random Forest | RF is a per-stage training candidate and inference loads each saved stage pipeline; metrics record RF selected for all stages. Artifact contents were not deserialized. | `backend/ml/train_career_models.py::candidates`, `backend/ml/predict.py::predict_career_families`, `career_model_metrics.json`; CP SRS PDF pp. 15, 19 | **IMPLEMENTED AND USED (source/recorded metrics)** | Verify artifact identity/provenance and rebuild under corrected selection only in a separately approved isolated destination. |
| XGBoost | XGB is implemented and evaluated as a training candidate, but metrics record RF selected for all four stages. No evidence it is in current served artifacts. | `backend/ml/train_career_models.py::candidates`, `career_model_metrics.json`; CP SRS PDF pp. 15, 19 | **IMPLEMENTED BUT NOT SHOWN AS CURRENTLY USED** | Retain as comparison candidate; do not claim live XGB inference without artifact evidence. |
| Scikit-learn | Used for preprocessing, training, prediction pipelines and evaluation. | `backend/ml/career_preprocessing.py`, `train_career_models.py`, `career_evaluation.py`; CP SRS PDF pp. 15, 19 | **IMPLEMENTED (source-level)** | Verify runtime dependency compatibility and record environment details. |
| Pandas | Used to load CSVs, build feature frames and supply model inputs. | `career_data_loader.py`, `train_career_models.py`, `predict.py`; CP SRS PDF pp. 15, 19 | **IMPLEMENTED (source-level)** | Strengthen data validation and provenance lineage. |
| NumPy | Used for metric aggregation and SHAP output handling. | `career_evaluation.py`, `explain.py`; CP SRS PDF pp. 15, 19 | **IMPLEMENTED (source-level)** | Verify actual runtime behavior only in an isolated environment. |
| Model training | Four stage pipelines train RF/XGBoost candidates; current source uses a stratified holdout and training-partition CV. | `backend/ml/train_career_models.py` | **IMPLEMENTED; current artifacts predate corrected selection** | Retrain only in an approved isolated output and preserve provenance. |
| Model evaluation | Accuracy, macro precision/recall/F1, confusion matrix, classification report and CV metrics are implemented; checked-in stage results are legacy/selection-biased. | `backend/ml/career_evaluation.py`, `MODEL_REPORT.md` | **IMPLEMENTED in source; corrected results NOT AVAILABLE** | Generate corrected reports only with approved isolated retraining. |
| Model inference | Saved stage pipeline returns five broad family probabilities and influences hybrid ranking. | `backend/ml/predict.py`, `backend/services/recommendation_engine.py` | **IMPLEMENTED AND USED (source-level)** | Verify artifact loading/inference in an approved isolated runtime. |
| Four education levels | Separate feature contracts and stage artifacts; live inference selects by profile education level. | `feature_engineering.py::STAGE_FEATURES`, `predict.py`, `recommendation_engine.py` | **IMPLEMENTED (source-level)** | Exercise all four stages against isolated runtime and confirm current artifact compatibility; not performed in this audit. |
| Data preparation and missing-value processing | Stage-specific feature mapping, pipeline imputation, categorical stream encoding. | `career_preprocessing.py`, `feature_engineering.py` | **PARTIAL** | Strengthen schema/label/duplicate/range validation at loader boundary; define drift and input-coverage monitoring. |
| Training/test split and cross-validation | Stratified 80/20 split and 5-fold CV; current source chooses on train-partition CV macro-F1 and evaluates holdout afterward. | `train_career_models.py::main`, `career_evaluation.py` | **IMPLEMENTED in source; saved metrics stale** | Retrain in a separately approved artifact target and publish corrected CV/holdout metrics with lineage. |
| Accurate prediction of student career choice/outcomes | Models recover synthetic generator family labels; there is no real student outcome cohort. | `generate_career_training_data.py`, `MODEL_REPORT.md`, `DATA_SOURCES.md` | **NOT ESTABLISHED** | Obtain representative, consented, quality-reviewed longitudinal data and conduct external validation before any accuracy/validity claim. |
| Hybrid model plus profile/catalog compatibility | 90/10 rule/profile and family-probability score for later-stage careers; Class 10 uses grouped pathway rules. | `recommendation_engine.py::_recommend_with_catalog`, `school_pathways.py::evaluate_pathway` | **IMPLEMENTED, EXPERIMENTAL** | Keep score semantics clearly labeled; test calibration and sensitivity only after suitable evidence exists. |
| Explainable ML recommendations / SHAP | Best-effort SHAP tree explanation of broad family score; deterministic score components/reasons are separate. | `backend/ml/explain.py::explain_career_model`, `frontend/src/ModelExplanation.jsx` | **PARTIAL** | Verify runtime compatibility and explanation correctness; avoid presenting family SHAP as pathway/career explanation. |
| Flask integration | Authenticated recommendation endpoint calls the engine and returns score components, family probabilities and explanation fields. | `backend/app.py::create_recommendations`; CP SRS PDF pp. 14-16 | **IMPLEMENTED (source-level)** | Verify live UI/API parity and failure behavior using isolated runtime; not done here. |
| Frontend integration | React renders model signal separately from compatibility reasons and labels SHAP scope as family-level. | `frontend/src/main.jsx::RecommendationCard`, `frontend/src/ModelExplanation.jsx`; CP SRS PDF pp. 14-16 | **IMPLEMENTED (source-level)** | Verify rendered parity/accessibility in browser; not done here. |
| Saved recommendation model lineage | Snapshots store input/catalog fingerprints and results, but not a model artifact hash/version. Admin metrics compute artifact digests separately. | `backend/recommendation_snapshots.py::new_snapshot`, `backend/app.py` | **PARTIAL** | Add model-version lineage if reproducibility across artifact changes is required, with a separately reviewed compatibility change. |
| Eligibility and course prerequisites | Evidence-gated assessor exists, but the verified-rule registry is empty; catalog labels remain unverified. | `backend/services/eligibility.py::VERIFIED_PROGRAM_RULES`, Phase 2.2K report | **NOT ESTABLISHED** | Define jurisdictions/institutions, source and date every applicable rule, collect required student facts, and review rule updates. |
| Kaggle and UCI datasets support career model | Kaggle is a separate synthetic university-only benchmark; UCI is a grade-band experiment. Neither is live career training. | `train_kaggle_career_model.py`, `train_model.py`, `DATA_SOURCES.md` | **NOT USED for live stage career inference** | Do not combine or mislabel; preserve source-specific use and limitations. |
| Admin model metrics and comparisons | Admin metrics endpoint reads saved JSON; baseline diagnostics are separately generated. | `backend/app.py` model endpoints, `diagnose_career_models.py` | **PARTIAL / stale metrics risk** | Clearly flag legacy protocol metrics in Admin UI/API and update only after corrected isolated training/review. |

## Tests and commands

**Executed:**

- Read-only PowerShell source/document inspection (`Get-Content`, `rg`).
- Read-only `python -c` JSON parsing of `data/processed/career_model_metrics.json` for the recorded selected model names.
- A Python standard-library CSV aggregation over the two career training CSVs and the raw Kaggle CSV, reporting only counts, label distributions, blank counts, duplicates, and numeric validity. It made no file writes.

**Reviewed but not executed:**

- `tests/test_career_ml.py`: checks stage prediction probability shape, hybrid recommendation fields, and SHAP result shape/fallback.
- `tests/test_phase2_2a_catalog_and_model_selection.py`: checks synthetic generator output isolation, CV-only selection, and holdout evaluation ordering.
- `tests/test_recommendation_engine.py` and `tests/test_api.py`: inspectable coverage exists for ranking and API persistence/authentication, but these were not run during this audit. Prior test counts in the Phase 2.2K report are historical, not rerun evidence here.
- The wider backend/frontend suites were not run because this audit was required to remain read-only; application tests can construct temporary databases/catalog copies and are unnecessary to establish the static findings. No live runtime inference was performed.

**Training, app startup, database access, build, and model artifact loading:** not run.

## Findings and prioritized next steps

1. **High — No real-world predictive validation.** Current four-stage labels and scores are synthetic, with labels generated before correlated features. Obtain a consented, representative outcome dataset; define outcome/label windows; use subject-level/group-aware splits where repeated students exist; pre-register metrics and independent external validation.
2. **High — Checked-in stage model metrics/artifacts use the old selection protocol.** Keep their legacy warning; do not cite the displayed historical holdout metrics as unbiased. Retrain only in an approved isolated artifact destination using the current CV-only source, inspect the resulting lineage, and require separate artifact promotion approval.
3. **High — Program eligibility evidence is absent.** The verified rules registry is empty. Maintain “eligibility not verified” and do not describe recommendations as admission-qualified until institution-specific rules and student evidence are reviewed.
4. **Medium — Loader validation is incomplete.** Add tests and validation for exact schema, stage values, numeric ranges/types, duplicate identifiers, missing classes and empty stage groups before training; preserve intended blanks for inapplicable features.
5. **Medium — SHAP explains only family-model output and is best effort.** Keep UI language explicit; test supported RF/XGB SHAP output shapes and stability in an isolated environment, and do not conflate it with profile/eligibility reasoning.
6. **Medium — Kaggle synthetic benchmark is low-performing and conditional.** Retain it as a separate experiment only; do not wire it into inference or imply its roughly 40% accuracy meets the requested threshold.
7. **Low — Audit did not execute runtime tests.** In a separately authorized isolated environment, run focused model/recommendation tests and verify current artifacts without training or overwriting them; any retraining requires a separate approved output location.

## Recommended implementation order

1. Preserve the current separation: evidence-based eligibility first; profile/catalog compatibility ranking second; model-family probability only as a clearly labeled experimental signal.
2. Strengthen dataset loader checks and document a versioned schema/provenance contract before any future training. Keep synthetic examples separate from empirical outcome datasets.
3. Obtain representative, consented outcome data with a defensible outcome definition, time horizon, education-stage coverage, and documented label quality, missingness, sampling and permitted use. Use group/time-aware splits where warranted and retain an untouched external test set.
4. Compare RF and XGBoost only in an explicitly isolated artifact destination using macro-F1, per-class precision/recall, confusion matrix, calibration and uncertainty checks, plus simple baselines. Report variance and class behavior; do not optimize for a single accuracy figure without regard to provenance or imbalance.
5. Validate SHAP output against the selected artifact and actual family prediction. Keep explanations of model-family signal, compatibility evidence and admission-rule evidence distinct in the UI.
6. Add model artifact identity to recommendation snapshot lineage if repeatability across model changes is required; preserve compatibility and test changes in isolated storage.
7. Promote an artifact only after independent review. Monitor drift and fairness, preserve counselor review, and never present model scores as admission or career-success probabilities.

### Likely future change locations (no changes made)

- Dataset schema and provenance checks: `backend/ml/career_data_loader.py`, `backend/ml/kaggle_career_features.py`, focused loader tests, and `DATA_SOURCES.md`.
- Isolated training outputs and lineage: `backend/ml/train_career_models.py`, `backend/ml/career_evaluation.py`, and `MODEL_REPORT.md`; generated metrics/artifacts should only be changed under separate approval.
- Snapshot model version: `backend/recommendation_snapshots.py`, `backend/app.py`, `tests/test_recommendation_snapshots.py`, and `tests/test_api.py`.
- SHAP validation/scope: `backend/ml/explain.py`, `frontend/src/ModelExplanation.jsx`, and `tests/test_career_ml.py`.
- Runtime API/UI behavior: `backend/services/recommendation_engine.py`, `backend/app.py`, `frontend/src/main.jsx`, and focused isolated tests.

## Safety and conclusion

No source code, tests, configuration, catalogs, model artifacts, database files, or credentials were changed. No database was connected, no model was loaded or trained, and no test/build/application command was executed. This task updated only this existing audit report; all unrelated working-tree changes were preserved.

**Conclusion: the system has a functioning rule/profile recommendation engine with an experimental synthetic family classifier contributing 10% of its score. RF and XGBoost are both implemented as training candidates; RF is the model recorded as selected in all four current metrics, while the exact binaries were not deserialized for this review. SHAP is present for broad family-score attribution only. Real-world prediction validity, corrected-protocol artifact performance, institution-specific eligibility, and production readiness remain unverified.**
