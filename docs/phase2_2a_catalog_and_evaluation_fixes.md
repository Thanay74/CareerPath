# CareerPath Phase 2.2A — Catalog and Model Evaluation Fixes

**Date:** 2026-10-22  
**Scope:** Only the two confirmed Phase 2.2 defects: synthetic generator catalog writes and holdout-test model selection. No model training or database operation was performed.

## Preflight and preserved state

- Read `docs/phase2_2_data_recommendation_foundations_audit.md`; its identified functions and paths matched the checkout.
- Branch/status: `master`, `No commits yet`; the repository files were already untracked. No reset, stash, checkout, or commit was used. The prior working-tree state is therefore preserved; modified-file attribution is based on the edits made in this task.
- The generator source path was `data/generate_synthetic_data.py`; stage trainer/evaluator were `backend/ml/train_career_models.py` and `backend/ml/career_evaluation.py`.
- Before training-related commands, inspected `backend/models/career/` and the metrics path. Four existing stage `.joblib` files and `data/processed/career_model_metrics.json` exist. Training was not run and those files were not opened or overwritten.
- Final report path was absent before creation.

## Defect roots and changes

### Fix A — Synthetic generator no longer writes the maintained catalog

**Root cause:** `data/generate_synthetic_data.py::main` wrote generator-embedded `CAREERS` records to `ROOT/'career_knowledge_base.csv'` before generating questionnaire fixtures. This could replace the maintained recommendation catalog when a developer ran a synthetic profile generator.

**Change:** Removed that catalog write. Generation still creates its five profile/assessment CSV outputs under `data/synthetic/` (`OUT`) and preserves the existing fixed seed and generation behavior. It does not write career metadata or catalog files.

### Fix B — Stage model winner uses CV, with holdout evaluated once afterward

**Root cause:** the prior loop used `metrics['f1_macro']` from held-out test predictions to choose the persisted model. Although CV was also computed, the test set influenced selection.

**Change:** `backend/ml/career_evaluation.py` now exposes separate `evaluate_cross_validation` and `evaluate_holdout` functions. The stage trainer cross-validates every candidate on the training partition, chooses by mean CV macro-F1 through `select_candidate_by_cv`, then fits and evaluates only that winner on the holdout through `evaluate_holdout`. The holdout metrics are stored separately at `stage.final_held_out_test`; each candidate entry stores its `cross_validation` summary and selection flag. CV metric names are explicit (`f1_macro`, `accuracy`, etc.); the Kaggle benchmark's existing combined result shape is preserved by the compatibility wrapper `evaluate_candidate`.

The Admin models API adds the `final_held_out_test` field, and the Admin model view shows candidate CV results separately from final holdout metrics, with the holdout displayed only for the CV-selected candidate. The view retains compatibility with the existing historical metrics format.

`MODEL_REPORT.md` now marks existing stage artifacts/metrics as legacy results selected by the held-out test set and not an unbiased final estimate. It documents the corrected selection protocol without claiming corrected results exist. `DATA_SOURCES.md` clarifies the CV-only selection and the legacy artifact caveat. No recommendation weight, feature contract, data, model, or catalog value was changed.

## Files changed

- `data/generate_synthetic_data.py` — remove canonical catalog write.
- `backend/ml/career_evaluation.py` — separate training-partition CV from final holdout evaluation; retain compatibility helper for Kaggle.
- `backend/ml/train_career_models.py` — CV-only model choice, one final holdout evaluation, clearly separated saved metrics.
- `backend/app.py` — add final selected-model holdout metrics to the existing Admin model response.
- `frontend/src/AdminPortal.jsx` — render CV comparison and selected-model holdout data accurately; retain historical-format rendering.
- `DATA_SOURCES.md`, `MODEL_REPORT.md` — align evaluation/provenance documentation and warn about legacy artifacts.
- `tests/test_phase2_2a_catalog_and_model_selection.py` — isolated regression coverage.
- `docs/phase2_2a_catalog_and_evaluation_fixes.md` — this report.

## Tests and exact results

### Passed

Command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; $env:DATABASE_URL=''; python -m unittest discover -s tests -p test_phase2_2a_catalog_and_model_selection.py -v
```

Result: **3 tests passed**.

1. `test_synthetic_generator_only_writes_inside_synthetic_output` — uses a temporary directory under `tests/`, hashes temporary catalog and metadata fixtures before/after, invokes the generator only with its output redirected to that fixture, and checks that only the five synthetic CSVs are created under the synthetic directory.
2. `test_selection_uses_cv_metrics_only` — verifies winner selection from the CV macro-F1 mapping.
3. `test_holdout_evaluation_occurs_once_after_cv_selection` — substitutes candidate evaluation functions, gives the holdout an intentionally contradictory score, verifies both candidates receive CV first, then only the CV winner receives one holdout evaluation.

Frontend command: `npm test` from `frontend/`. Result: **7 passed, 0 failed**. These are the existing frontend tests; they do not directly test visual rendering of the Admin metrics panel.

### Blocked / not passed

- `python -m pytest -p no:cacheprovider tests/test_phase2_2a_catalog_and_model_selection.py -q` — **not run successfully** because `pytest` is not installed (`No module named pytest`). The equivalent focused tests were run successfully with `unittest`.
- `npm run build -- --outDir C:/Users/THANAY/Documents/Codex/.phase2_2a_frontend_build` — **failed** at Vite resolution with `EPERM` on `frontend/src/main.jsx`, before the Admin component could be compiled. This matches the previously documented sandbox filesystem limitation. No Vite configuration/security workaround was made; the temporary output directory was not created.
- A direct JSX parse check was unavailable because `esbuild` is not resolvable as a direct frontend dependency. Thus frontend production compilation of the changed component remains unverified.
- Full backend suite was not run. It includes broader API/model/database-oriented tests and was not needed for the focused corrections. MySQL was not accessed.

## Protected files and artifacts

The isolated generator test's before/after hashes match for the **temporary fixture** catalog and metadata; it did not point the generator at project data. Read-only verification after the focused tests found:

| Path | SHA-256 / state |
|---|---|
| `data/career_knowledge_base.csv` | `229D6B4ED077E81F2043515A5CA02EA2FFDEA72E1D32467899F4E7C3AA021E78` (matches the prior Phase 2 audit baseline) |
| `data/career_metadata.json` | `238800FFFA961EB70FD70E028552BD05CC639215A0CCFD2ADDA8DFC1CEE36629` |
| `data/career_active.json` | absent at verification |
| `data/career_catalog_managed.json` | absent at verification |
| `data/processed/career_model_metrics.json` | `4EAE655E86BD4A14A60DC5DB4C8747C16B7F5C2C2B8915278336F3E3EA3E1D57` |
| `backend/models/career/10th_career_model.joblib` | 1,234,257 bytes; `AFFCC62D850B4B9E8706AA02FF11076046F7A1CCB2DB9AB1D7D4D1266D074793` |
| `backend/models/career/12th_career_model.joblib` | 1,192,615 bytes; `3B31D0D1472EC2112FC734F9A6F756367048AD6A0F4C6EBEB23E30AD6B75A50A` |
| `backend/models/career/bachelors_career_model.joblib` | 1,207,355 bytes; `C0A7891C11AAEBC9EF9F8B0A32F210F96D3D2B227B40D49F01407AE729FC98B6` |
| `backend/models/career/masters_career_model.joblib` | 1,205,021 bytes; `6400A9359FF75241A0882EA129A6C71EC597DD945D538BC9120B7D17FE62F1DF` |

The focused tests contain no database calls, artifact writes, or canonical catalog paths. The synthetic generation test writes only into a temporary test directory that is cleaned up. The active release pointer and managed marker were absent at final inspection; no release command or catalog mutation was invoked.

## Limitations and safety confirmation

The old stage model artifacts and metrics remain unchanged and were trained with the flawed selection process. The corrected code has not been used to regenerate them because training would overwrite existing model artifacts/metrics and no isolated artifact destination was approved. Therefore this change fixes the training procedure, but does not retroactively correct or validate the currently saved models' metrics. Synthetic labels still do not demonstrate real-student predictive validity.

**No model training, database connection/mutation, setup, migration, seeding, catalog publish/restore, or data download occurred.** No canonical catalog, release pointer, student record, credential, or model artifact was modified.
