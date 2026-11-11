# CareerPath Phase 2.2C — Integration Verification and Release Readiness

**Date:** 2026-10-22  
**Scope:** Read-only integration and regression verification. No source fixes were made.

## 1. Executive summary

**Readiness: NOT READY for release.** The safe backend regression subset passed (25 tests) and the frontend unit suite passed (7 tests). The production build remains blocked by Vite `EPERM` resolving `frontend/src/main.jsx`. Authenticated workflows, database persistence, and browser behavior were not executed. Static inspection supports the reported API/UI contracts, but cannot establish live API/database behavior.

A catalog-integrity discrepancy was observed: the initial baseline saw `data/career_active.json` and `data/career_catalog_managed.json` as one-byte files; the final check found both absent. The tests selected for this audit do not invoke catalog publish, restore, or discard. I cannot attribute the change, so pointer integrity is **unverified**, not passed.

## 2. Repository baseline

- Project root: `outputs/CareerPath`.
- Branch: `master`.
- Git state: `No commits yet`; all project directories and files were already untracked at baseline. Final `git status --short --branch` showed the same untracked top-level paths and no extra test/build artifacts. Git ownership prevented ordinary status; status was read using a per-command `safe.directory` option. No global Git config was changed.
- Existing test commands: Python `unittest` under `tests/`; frontend `npm test` (`node --test`) and `npm run build` (`vite build`).
- Phase 2.1 and Phase 2.2A/2.2B reports listed in the request were present. The Phase 2.2C report path was absent before this report was created.

### Protected artifact baseline and final read

CSV, metadata, metric, and four model-artifact hashes were identical at baseline and final check:

| Path | Bytes | SHA-256 |
|---|---:|---|
| `data/career_knowledge_base.csv` | 10,109 | `229D6B4ED077E81F2043515A5CA02EA2FFDEA72E1D32467899F4E7C3AA021E78` |
| `data/career_metadata.json` | 4,319 | `238800FFFA961EB70FD70E028552BD05CC639215A0CCFD2ADDA8DFC1CEE36629` |
| `data/processed/career_model_metrics.json` | 28,691 | `4EAE655E86BD4A14A60DC5DB4C8747C16B7F5C2C2B8915278336F3E3EA3E1D57` |
| `backend/models/career/10th_career_model.joblib` | 1,234,257 | `AFFCC62D850B4B9E8706AA02FF11076046F7A1CCB2DB9AB1D7D4D1266D074793` |
| `backend/models/career/12th_career_model.joblib` | 1,192,615 | `3B31D0D1472EC2112FC734F9A6F756367048AD6A0F4C6EBEB23E30AD6B75A50A` |
| `backend/models/career/bachelors_career_model.joblib` | 1,207,355 | `C0A7891C11AAEBC9EF9F8B0A32F210F96D3D2B227B40D49F01407AE729FC98B6` |
| `backend/models/career/masters_career_model.joblib` | 1,205,021 | `6400A9359FF75241A0882EA129A6C71EC597DD945D538BC9120B7D17FE62F1DF` |

Pointer discrepancy: initial baseline reported `data/career_active.json` and `data/career_catalog_managed.json` each present with length 1; final `Test-Path` found both absent. No pointer hash/content was retained in the baseline output. No attempted test or build command called catalog-release mutation code, but the filesystem discrepancy prevents asserting pointer integrity.

## 3. Backend test results

All successful commands used `PYTHONDONTWRITEBYTECODE=1` and `DATABASE_URL=''` (the setup safety rerun also pointed Windows temp variables at a newly created workspace-local temp directory).

| Command | Result |
|---|---|
| `python -B -m unittest discover -s tests -p test_phase2_2a_catalog_and_model_selection.py -v` | PASS — 3 tests |
| `python -B -m unittest discover -s tests -p test_phase2_2b_recommendation_quality.py -v` | PASS — 11 tests |
| `python -B -m unittest discover -s tests -p test_catalog_validation.py -v` | PASS — 3 tests |
| `python -B -m unittest discover -s tests -p test_startup_safety.py -v` | PASS — 1 test |
| `python -B -m unittest discover -s tests -p test_setup_safety.py -v` | PASS on rerun — 4 tests |
| `python -B -m unittest discover -s tests -p test_recommendation_engine.py -k school_gap -v` | PASS — 1 test |
| `python -B -m unittest discover -s tests -p test_recommendation_engine.py -k class10_roadmap -v` | PASS — 2 tests |

**Total: 25 backend tests passed** across the safe subset.

The first `test_setup_safety.py` attempt ran 4 tests but two errored during cleanup of the OS-managed temporary directory (`WinError 5`, `PermissionError`); the same tests passed when rerun with temporary files redirected to a new writable workspace-local directory. The temporary directory created for that rerun was empty afterward and removed.

### Skipped backend tests

- `tests/test_api.py`: initializes and seeds SQLite and includes profile/recommendation persistence plus catalog publish/restore and draft mutation tests. Skipped because this verification expressly excludes database initialization/persistence and release mutations.
- `tests/test_catalog_releases.py`: exercises catalog release mutation, including publish/restore, even where temporary fixtures are used. Skipped under the no-release-operation constraint.
- `tests/test_career_ml.py`, `tests/test_kaggle_benchmark.py`, `tests/test_ml_pipeline.py`: model or training/artifact-related execution; skipped to avoid model loading/training/serialization risk.
- `tests/test_legacy_schema_guard.py`: executes schema initialization against a SQLite fixture; skipped because database initialization is excluded.
- `tests/test_interprocess_lock.py`: not needed for this acceptance run; it creates multiprocessing lock artifacts in temporary storage. No release locking test was run.
- Remaining unfiltered recommendation tests: not run as a suite because they include runtime recommendation/model paths. Only pure selected gap and roadmap tests above were executed.

Consequently, these results are **not** a full backend suite result and do not verify MySQL.

## 4. Frontend tests and production build

- From `frontend/`: `npm test` — **PASS**, 7 passed, 0 failed, 0 skipped.
- Production build command: `npm run build -- --outDir C:/Users/THANAY/Documents/Codex/.phase2_2c_frontend_build` — **FAIL**, exit code 1. Vite 5.4.21 transformed one module then failed:

  `EPERM: operation not permitted, realpath '.../frontend/src/main.jsx'`

  The output directory did not exist before the command and was not created. No Vite config, permissions, or security controls were changed. The frontend production bundle is therefore **unverified**.

## 5. Student and Admin workflows

### Student recommendations — static inspection plus pure-function tests

- **Static inspection:** `backend/app.py::create_recommendations` validates the supplied profile with `valid_profile`, requires the authenticated student's token when a `student_id` is supplied, and returns the recommendation list. `backend/services/recommendation_engine.py::recommend` pins a catalog snapshot with `catalog_read_context`; the Class 10 branch generates pathway results and `summarize_pathways` output, while other levels read catalog careers and use the hybrid score.
- **Static inspection:** `_recommend_with_catalog` calls `predict_career_families`; the hybrid path labels the model-family signal experimental and gives it a 10% contribution. The Class 10 response uses the configured pathway evaluator and reports score semantics as an exploratory compatibility estimate, not an admission/success probability.
- **Executed tests:** 2.2B tests cover missing versus zero values, required-skill gap behavior, incomplete requirements/data statuses, Class 10 close/inconclusive leader rules, and roadmap status. Selected existing recommendation tests cover school gap status and Class 10 roadmap progression.
- **Not tested:** actual `/api/recommend` calls, trained model inference/SHAP, authenticated profile persistence, dynamic browser input-to-results updates, or saved-roadmap retrieval. These require model/runtime or database execution not authorized in this phase.

### Admin model metrics — static inspection only

- `backend/app.py::admin_models` checks `admin_required()` and returns model stage metric records plus the separate `final_held_out_test` field.
- `backend/app.py::admin_authorized` queries for a bearer token belonging to an active administrator; student/inactive accounts do not satisfy that predicate. This was code inspection only; no authenticated endpoint request was sent.
- `frontend/src/AdminPortal.jsx::CareerModelMetrics` renders candidate cross-validation summaries separately from `stage.final_held_out_test`; the final holdout panel is shown only for the selected candidate. Its legacy branch tolerates old metrics lacking `cross_validation` by rendering the legacy keys. The surrounding Admin view explicitly says the labels are generated/synthetic and not validated against real student outcomes.
- The existence of this compatibility branch does not establish the truth or validity of legacy metrics. No model artifact was loaded, and no Admin browser view was run.

### Catalog routes and release safety — static inspection only

- `backend/services/catalog_releases.py::load_active_catalog` reads and validates one release selected by its manifest, verifies the CSV/metadata hashes, rejects malformed manifests, and refuses canonical fallback if a managed marker exists without a valid pointer. When neither marker nor pointer exists, the maintained canonical pair is used.
- `catalog_read_context` pins the loaded snapshot for a recommendation run; `recommendation_engine.recommend` uses that context. This was source inspection; no live release API was invoked.
- Admin career CRUD, draft, publish, release-list, restore, and discard handlers in `backend/app.py` call `admin_required()` before their privileged logic. The mutating endpoints were not exercised.
- Pointer files were unexpectedly absent at final check as described above. Therefore the current active-catalog state and runtime reader behavior are **not verified**.

## 6. Findings by severity

### High — Production build fails in this sandbox (confirmed)

Vite cannot resolve the real path of `frontend/src/main.jsx` due to `EPERM`, despite the source being present. Frontend unit tests pass, but production compilation and any bundled-UI contract remain unverified. Resolve by running the unchanged build in an approved environment where the project path is accessible; do not weaken Vite/Node security based on this evidence.

### High — Active catalog pointer integrity is indeterminate (confirmed discrepancy; cause unverified)

The initial check saw both pointer/marker files as one byte, while the final check found them absent. The test list used here does not call release mutation functions. No content hash was recorded for those initial one-byte files, and no live catalog state was modified intentionally. Investigate the environment/history that changed the file listing before relying on versioned active-release state.

### Medium — Integration and authentication workflows were not executed (not tested)

API compatibility is supported by code review and unit tests but not by runtime API requests. MySQL was never connected. Student persistence, authentication and admin authorization responses, isolation between accounts, and failed-save behavior remain unverified.

### Medium — Legacy model metrics have limited evidentiary value (static inspection)

The UI labels legacy format fields as test metrics and also displays legacy CV fields when present; current top-level copy warns that labels are generated and not real-world validated. The referenced Phase 2.2A report says existing model artifacts/metrics predate CV-only selection and are biased legacy results. Do not describe those metrics as real-student career accuracy or success probability. Retraining/re-evaluation was not performed.

### Low — Browser-level responsive/accessibility behavior not verified (not tested)

No browser session or live backend was used. Responsive layout, interactive accordions, header identity, and logout behavior have no runtime evidence from this run.

## 7. Integrity and prohibited-operation confirmation

- No MySQL or other database connection, setup, migration, seed, bootstrap, or persistence workflow was invoked.
- No model training, model inference, artifact serialization, or metrics regeneration was invoked.
- No synthetic-data generation against project data, catalog validation write, draft operation, catalog publish/restore/discard, or release API was invoked. The 2.2A regression test ran its generator only with a temporary root under a temporary tests directory; those files were cleaned up.
- Canonical CSV, metadata, metrics, and all four model-artifact hashes match between the initial and final observations.
- Active pointer/marker state did **not** match (one-byte present at baseline versus absent at final); this uncertainty is reported rather than represented as an integrity pass.
- No source, dependency, credential, configuration, student-record, dataset, notebook, or model-artifact changes were made by this task. The only intended new project file is this report.

## 8. Recommended next actions

1. Investigate why the active pointer and managed marker changed from one-byte files to absent; record their intended state and restore only through a separately authorized, reviewed action if required.
2. Run the unchanged frontend production build in an approved environment where the project filesystem permits Vite realpath resolution.
3. In a separately approved isolated integration environment, run API authorization and workflow tests against an approved test database; do not substitute or claim MySQL results from this report.
4. Add isolated API contract tests for the Admin metrics response and student recommendation payload if not already covered, without loading or retraining production artifacts.
5. Keep legacy synthetic-model metrics clearly marked and avoid claims of real-world career prediction validity.

**Phase 2.2C disposition:** Verification is complete for the safe, non-mutating subset. Phase 2.2C should remain open because the production build, live workflows, MySQL integration, and catalog pointer integrity are unresolved.
