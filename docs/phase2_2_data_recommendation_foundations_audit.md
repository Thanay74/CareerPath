# CareerPath Phase 2.2 — Data and Recommendation Foundations Audit

**Audit type:** Read-only inspection  
**Project root:** `outputs/CareerPath`  
**Audit date:** 2026-10-22  
**Scope:** Dataset provenance and quality, model evaluation and use, recommendation scoring, missing-value semantics, catalog/qualification references, and evidence needed before future data or model changes.

## Executive summary

CareerPath has a documented separation between public academic-grade data, Kaggle-published synthetic career data, locally generated synthetic career-family profiles, project-authored catalogs, and student questionnaire data. The local file audit supports the documented row counts for the primary files and found no exact duplicate rows in the files checked. No supplied user-collected survey dataset was found in the project inventory. Neither absent datasets nor `CareerPath.ipynb` were recreated.

The strongest recommendation-model limitation is validity, not headline accuracy: the four stage-specific models learn locally generated synthetic family labels. The generator constructs family-conditioned profile distributions, so reported scores measure recovery of that simulation. They do not establish predictive accuracy for real student choices, educational outcomes, employability, or career success. The separate Kaggle dataset is itself synthetic and only supports a Bachelor's-level, placement-conditioned career-field benchmark.

A confirmed evaluation defect needs correction before future retraining: `backend/ml/train_career_models.py` chooses the winner by the held-out test macro-F1, although 5-fold CV is calculated. This makes the reported test result a model-selection signal rather than an untouched final estimate and contradicts the documented CV-only selection policy. The Kaggle trainer does select by mean CV macro-F1.

A second high-priority operational risk is that running `data/generate_synthetic_data.py` writes `data/career_knowledge_base.csv` from embedded generator records. It can overwrite the maintained catalog. This audit did not run that generator or any training/preprocessing/download/setup mutation.

## 1. Evidence and method

Inspected source and documentation, including `DATA_SOURCES.md`, `docs/phase2_data_foundation_audit.md`, `docs/phase2_1_catalog_architecture_plan.md`, `docs/phase2_1_final_acceptance_audit.md`, `backend/catalog_validation.py`, education/career catalog consumers, recommendation and school-pathway services, ML training/evaluation/inference/explainability modules, and generator scripts.

CSV/ZIP inspection used read-only standard-library parsing. The catalog structural validator was invoked with `PYTHONDONTWRITEBYTECODE=1` and an explicitly empty `DATABASE_URL`:

```text
python -m backend.setup --validate-catalogs
Education and career catalogs are structurally valid.
exit code 0
```

The `--validate-catalogs` branch in `backend/setup.py::main` imports and calls `validate_project_catalogs()` without resolving a database target or opening a connection. No model artifacts were deserialized, no training or inference was run, and no database connection was attempted. This is a source/data audit, not a runtime application or MySQL integration test.

Git inspection required a per-command safe-directory override. The checkout reports `## No commits yet on master`; project files appear untracked, so Git cannot distinguish prior user edits from the baseline. No global Git configuration was changed.

## 2. Data inventory and provenance

| Dataset/source | Local content and audit observations | Purpose and correct interpretation |
|---|---|---|
| UCI Student Performance, official archive and extracted `student-mat.csv` / `student-por.csv` | 395 × 33 and 649 × 33 respectively; no missing cells or exact duplicate rows detected. The cohorts overlap and are not 1,044 unique people. | Supplementary academic grade-band experiment only. Target is derived from G3; this is not career-choice or career-outcome data. Source/license are documented in `DATA_SOURCES.md` but were not independently checked online in this task. |
| Kaggle-published Student Career Success Prediction Dataset | Raw CSV 50,000 × 29; no missing fields or duplicate rows detected in local parse; `Student_ID` unique. Processed CSV 39,040 × 16 after filtering 10,960 `Not Placed` rows. | A source-described synthetic dataset, not real student records. The model predicts `Career_Field` among placed rows; not placement probability and not production model evidence. License/provenance statements are from project documentation, not independently verified in this audit. |
| Local career-family development data | `data/synthetic/career_training_profiles.csv`: 1,600 × 59, 400 per level according to generator/docs, five broad labels. Some blank features are structurally non-applicable; e.g. accountancy blank in 1,155 rows (72.2%), biology/chemistry/computer science/physics blank in 965 (60.3%), humanities subjects blank in 1,080 (67.5%), economics blank in 635 (39.7%). | Synthetic feature/label scenarios generated locally. Labels and features are jointly produced by family-conditioned rules; not observed outcomes. |
| Local synthetic questionnaire profiles | `data/synthetic/students.csv`: 240 × 18; subject blanks include physics in 94 rows (39.2%) and accountancy in 139 (57.9%). `technical_skills.csv`: 240 × 18, with programming blank in 140 (58.3%), Python in 144 (60.0%), and Java in 164 (68.3%). Aptitude, interests, and employability files were complete in the inspected parse. | Synthetic development/testing profiles only. Empty values represent unassessed or non-applicable data per the project dictionary/generator; they are not evidence of a score of zero. |
| Curated career knowledge base | `data/career_knowledge_base.csv`: 25 × 12; no blank values, exact duplicate rows, or duplicate `career_id` detected. IDs C01–C25. Metadata is paired in `data/career_metadata.json`. | Project-maintained compatibility and pathway guidance, not measured student outcome data or a universal eligibility authority. |
| Education catalog | `backend/education_catalog.py`; validator covers 10th, 12th, Bachelor's, Master's and internal references for streams, degrees, specializations, and subject groups. | Maintained reference metadata consumed by education options APIs and profile validation. |
| Aptitude bank | `backend/aptitude_bank.py`, 25 project-authored questions per `DATA_SOURCES.md`. | Assessment content, not a student dataset or validated psychometric instrument. |
| User-collected survey data | No user-collected survey dataset supplied or found in the project inventory, consistent with `DATA_SOURCES.md`. Database contents were not inspected. | Runtime assessment submissions are application data; there is no verified aggregate survey cohort available for model training in this audit. |
| Missing referenced files | `indian_education_full_dataset_with_interests_5000.csv`, `age_interest_career_dataset.csv`, and `CareerPath.ipynb` were absent from the inspected project inventory. | No replacement was invented. Recovery should use the user's original backup/source or a separately approved acquisition with provenance and license review. |

These observations are limited to local files inspected. They do not prove the authenticity of an upstream publisher, license, or source; those claims remain documentation-level until checked against provider pages and license text.

## 3. Data quality and missingness

1. **Synthetic class design is strongly encoded.** `data/generate_career_training_data.py` defines family-conditioned profiles and assigns `career_family` from a known generator scenario. Strong held-out classification on these records is expected to reflect the generator's separation. It is not evidence that the same features predict a real student's future.
2. **Missing values have more than one meaning.** Empty values in generated school/degree profiles can be structurally not applicable because a level or stream does not use that field. Live student profiles can also omit an answer because it was not assessed. Preserve this distinction where possible; neither state should be silently recoded as zero.
3. **Missingness can affect ML predictions.** Career preprocessing uses numeric imputation with missing indicators (and categorical handling) in the fitted pipeline. At inference, a missing value is imputed and its missingness may be represented to the model. Thus the compatibility scorer's omission of unassessed dimensions does not imply the ML component is neutral to missingness. On the synthetic models, such patterns can encode generator conventions.
4. **Recommendation compatibility is not eligibility.** Catalog requirements are curated score thresholds and broad pathway alignments. They should not be exposed as a pass/fail determination, admission guarantee, or proof of qualification.
5. **Feature-contract drift is a risk.** `backend/ml/feature_engineering.py::STAGE_FEATURES` defines different subject/technical feature sets by stage, which is appropriate in principle. The sets and aliases must remain aligned with the education catalog, form payload, synthetic generator, and saved artifacts. Model files were not loaded to inspect their embedded feature contract in this read-only audit.

## 4. Training and evaluation review

### 4.1 Stage-specific career-family models

`backend/ml/train_career_models.py::main` uses a fixed seed, stratified 80/20 split, and 5-fold stratified CV for each education level. `backend/ml/career_evaluation.py::evaluate_candidate` computes both training-partition CV metrics and held-out test metrics (accuracy, macro precision/recall/F1, confusion matrix, and class report). It then fits a candidate on the full training partition.

**Confirmed defect — test-set selection leakage:** `train_career_models.py` compares `metrics['f1_macro']` at line 41 to select `best_pipe`. `career_evaluation.py` defines that `f1_macro` from predictions on `X_test`/`y_test`; CV macro-F1 lives under `metrics['cv']['test_f1_macro']['mean']`. Therefore the test partition influences model choice, and the saved metrics no longer represent an untouched final evaluation of the selected model. This conflicts with the CV-only model selection description in `DATA_SOURCES.md` and `MODEL_REPORT.md`. No training was run as part of this audit.

### 4.2 Kaggle benchmark

`backend/ml/train_kaggle_career_model.py::main` also uses a stratified 80/20 holdout and 5-fold stratified CV, and selects by mean training-partition CV macro-F1. Its documented scope is only Bachelor's/university records with a placed `Career_Field` label. The processed table excludes the `Not Placed` rows, so this is conditional field classification among source-labeled placed records, not a placement-success model. Metrics in project reports are source-label agreement for a synthetic dataset, not measured real-world predictive performance.

### 4.3 UCI academic experiment

`backend/ml/train_model.py` predicts grade bands from UCI academic performance data. It is not a career recommendation model. `G1` and `G2` are documented as excluded from features; this avoids using adjacent/future grades for the disclosed G3 target. Its score must not be reported as CareerPath career accuracy.

### 4.4 Accuracy claims and metrics

The project's report values may be reported only with all of these qualifiers: dataset identity/type, prediction target, education-stage scope, split/CV protocol, and that synthetic label agreement is not real-student validity. A request to achieve 90% accuracy cannot justify fabricating samples, tuning against the holdout set, or presenting synthetic-test scores as real career recommendation accuracy. The current production recommendation is hybrid; its compatibility score is not model accuracy.

## 5. Model use, recommendation logic, and explainability

### 5.1 Active model flow

`backend/services/recommendation_engine.py::_recommend_with_catalog` calls `predict_career_families(profile)` and uses a stage-specific saved career-family model. For later-stage career records, it combines profile compatibility and the family-level model value using a 90/10 weighting when the model signal exists. For Class 10, `backend/services/school_pathways.py` computes four configured pathway compatibility scores and combines a broad family signal at 90/10 when available. This is actual inference integration in source code; live operation was not invoked in this audit.

A family probability is shared across careers assigned to that family. It is not a career-specific probability. The result is driven primarily by compatibility rules (90% where both signals exist); the 10% model term is experimental and trained on synthetic labels. Use “model-family classifier score/probability” with its synthetic provenance. Avoid “likelihood of success,” admission probability, or career outcome prediction.

### 5.2 Compatibility score

For later-stage recommendations, `_profile_score` uses career-specific subjects/academic performance, aptitude, interests, technical and employability scores, education stage, stream, degree/specialization, stated career preferences, and research interests. Weights are renormalized over applicable observed components. For Class 10, the school pathway evaluator uses relevant subjects, aptitude, interests, and preferences with its own stage-specific weights. These are exploratory compatibility estimates, not calibrated probabilities.

Dynamic evidence should continue to be tied to submitted inputs. `_observed` drops `None` but retains numeric zero, and requirement scoring only averages assessed keys. The narrative should not turn a low rating into positive evidence. Score changes are intended to update from input; dynamic browser behavior was not part of this audit.

### 5.3 Skill gaps

`skill_gap_analysis` uses only skills with an observed numeric rating and a defined catalog requirement. Missing scores are not treated as zero. It returns distinct statuses for insufficient catalog requirements, insufficient assessment data, identified gaps, and no gaps among assessed dimensions. This is an appropriate distinction in the code path.

Potential schema/semantic concern: `actual` and `requirements` merge technical and employability dictionaries by key. If the same identifier appears in both categories, one value/requirement overwrites the other. Shared constructs such as communication or leadership can therefore lose their category-specific provenance. Current catalogs/tests should determine whether such overlaps are intended to represent one construct or are accidental; identifiers should be standardized only after that review.

### 5.4 Explanations and SHAP

`backend/ml/explain.py` runs SHAP for the selected tree pipeline when the optional library and compatible artifact are available; failures return an unavailable explanation. Its output labels scope as `model_family`. SHAP contributions explain a family classifier output, not the rule-based score for a specific career. No SHAP calculation or artifact loading was executed in this audit.

For school pathways, `summarize_pathways` marks a clear leading recommendation only when there are at least two evidence items and a margin of at least 12 points (`school_pathways.py:185`). The accompanying note says differences under 8 are close (`:204`). Margins from 8 through under 12 are not a clear leader but are not described by that “under 8” note. Clarify this threshold language in a separate change so uncertainty messaging matches the ranking rule.

## 6. Catalog and qualification source review

The canonical file-backed career/education catalog strategy is consistent with the Phase 2.1 plan. Runtime career reads go through `recommendation_engine.careers()`/`catalog_releases.load_active_catalog`; this lets the active release pair supply the CSV rows and metadata together. The structural validator passed in this audit.

`docs/career-references.md` lists trusted regulator/official portals (NCS, AICTE, NMC, PCI, ICAI, BCI, NCTE, UGC) and a supplementary BLS reference. It explicitly says catalog criteria are project assumptions and vary by jurisdiction/institution. The catalog records do not thereby have verified per-row current eligibility evidence. A later qualification verification should attach an authoritative URL, jurisdiction, effective/review date, and exact requirement scope to each regulated qualification claim. No official sources were browsed in this task.

### Catalog overwrite risk

`data/generate_synthetic_data.py::main` calls `write(ROOT/'career_knowledge_base.csv', ...)` (line 50) using generator-embedded `CAREERS`. Running this data generator can overwrite the maintained canonical career catalog. This is particularly risky because the generator otherwise appears to be for synthetic student generation and its filename does not signal catalog replacement. It was not run. Split the operations or make generator outputs non-overwriting and confined to the synthetic directory in a separately approved fix.

## 7. Findings ranked by priority

| Severity | Finding | Status / evidence |
|---|---|---|
| **High** | Stage career models are selected using holdout-test macro-F1. | **Confirmed.** `backend/ml/train_career_models.py::main` line 41 reads `metrics['f1_macro']`; `backend/ml/career_evaluation.py::evaluate_candidate` calculates that field from held-out `y_test`. CV metrics exist separately. Makes reported test score optimistic/selection-biased. |
| **High** | Synthetic data generator can overwrite canonical career knowledge base. | **Confirmed.** `data/generate_synthetic_data.py::main`, line 50 writes `data/career_knowledge_base.csv`. Generator not executed. |
| **High** | Model scores cannot support real-student predictive-validity or “90% career accuracy” claims. | **Confirmed limitation by data provenance/code.** Locally generated family labels encode family-conditioned profiles; Kaggle source is documented synthetic. No real career outcome cohort was found. |
| **Medium** | Missingness has different semantics and can influence model family output through imputation/missing indicators. | **Confirmed.** Synthetic files contain many blanks; pipeline preserves imputation indicators; compatibility scorer excludes unassessed values. Needs careful explanation and stage-specific missingness evaluation. |
| **Medium** | A shared skill identifier in technical/employability maps may be overwritten during gap calculation. | **Potential, code confirmed.** `recommendation_engine.py::skill_gap_analysis` merges both maps by key. Impact depends on catalog/profile overlap; audit did not find/run a dedicated overlap inventory for all active releases. |
| **Medium** | Class 10 uncertainty text and clear-leader threshold are not aligned. | **Confirmed.** Clear leader needs >=2 evidence items and >=12-point margin; note calls under 8 close, leaving 8–11 unexplained. |
| **Medium** | Qualification records are not independently verified row-by-row, and upstream license/provenance assertions were not checked against provider pages in this task. | **Confirmed audit boundary/documentation.** Reference portals are listed; `career-references.md` itself describes project assumptions. |
| **Low** | Dataset checks establish local structural properties only, not authenticity, licensing, independence, or lack of synthetic duplication patterns. | **Confirmed scope limitation.** No external verification or person-level identity analysis performed. |
| **Low** | Git working tree lacks a committed baseline, so change attribution is limited. | **Confirmed.** No commits on master; project files appear untracked. |

## 8. Recommended follow-up sequence

1. Correct stage-model selection to use mean training-partition CV macro-F1, then evaluate the selected candidate once on the held-out test set; update metrics/report provenance. Do this only with an approved generated-artifact destination because training overwrites model/metric artifacts.
2. Remove the canonical catalog write from the synthetic profile generator; add a test proving generators do not touch canonical catalogs and compare hashes before/after in a temporary copy.
3. Establish a real, consented, privacy-governed student/outcome dataset only if available; specify target, time horizon, inclusion criteria, and label provenance. Until then, label all family models experimental synthetic classifiers and treat compatibility rules as advisory.
4. Audit stage-specific missingness and feature importance using synthetic and, if later available, external validation; do not treat imputation indicators as student evidence.
5. Decide whether overlapping technical/employability skill IDs represent one shared construct or separate constructs; then normalize identifiers and add collision validation without merging distinct skills.
6. Align Class 10 uncertainty copy with the actual >=12 margin and evidence-count conditions.
7. Verify each career/qualification claim against current authoritative sources for the applicable jurisdiction; record source URL, requirement text, jurisdiction, and review date per catalog claim.
8. Recover missing files only from the user's original source/backup or a verified licensed provider. Recheck SHA-256, license, provenance, schema, and intended role before using them.

## 9. Tests and verification status

| Check | Result | Evidence / scope |
|---|---|---|
| Education and career structural catalog validation | **PASS** | `PYTHONDONTWRITEBYTECODE=1`, `DATABASE_URL=''`, `python -m backend.setup --validate-catalogs`; exit 0, printed “Education and career catalogs are structurally valid.” Read-only source path; no database connection. |
| Local CSV structural inventory | **PASS, limited** | Parsed selected raw/processed/synthetic/catalog CSVs and ZIP metadata read-only; row/column, blank, duplicate-row, and ID observations are reported above. Does not verify upstream data claims. |
| Backend test suite | **NOT RUN** | Audit-only scope and suite may create temporary/generated state; no test mutation was needed to establish the findings. Prior Phase 2.1 report results are not claimed as current Phase 2.2 tests. |
| Frontend tests/build | **NOT RUN** | No frontend changes or UI runtime verification were in scope. |
| Model training, CV, or prediction | **NOT RUN** | Training overwrites generated model/metric files; artifacts were not loaded or changed. Evaluation defect was confirmed by static source trace. |
| SHAP explainability | **NOT RUN** | No model deserialization or prediction invoked. |
| MySQL/data persistence | **NOT VERIFIED** | No database connection was attempted; no database contents were inspected. |
| Browser workflow | **NOT VERIFIED** | No live Flask/React session was exercised. |

## 10. Safety and changes

No source code, dataset, notebook, model artifact, configuration, credential, catalog, release manifest, or database record was modified. No database connection, migration, seed, catalog publish/restore, model training, data generation, or preprocessing command was run. The only project write from this task is this new audit report. Canonical catalogs and student data remain untouched by this audit.
