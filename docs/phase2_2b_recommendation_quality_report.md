# CareerPath Phase 2.2B — Recommendation Quality Report

**Date:** 2026-10-22  
**Scope:** Skill identifier collision audit, missing/unassessed-value semantics, skill-gap/roadmap consistency, and Class 10 uncertainty language. No database, model, catalog, or release operation was performed.

## 1. Preflight and repository state

- Read `docs/phase2_2_data_recommendation_foundations_audit.md` and `docs/phase2_2a_catalog_and_evaluation_fixes.md`. The reported functions and paths match the current checkout.
- The Phase 2.2B report path did not exist before creation.
- Branch/status: `master`, no commits; repository files are untracked. No reset, stash, checkout, or commit was used. Existing changes were preserved.
- Current files inspected include `backend/services/recommendation_engine.py`, `backend/services/school_pathways.py`, `backend/services/school_roadmap.py`, `backend/app.py`, `backend/education_catalog.py`, `frontend/src/main.jsx`, `DATA_DICTIONARY.md`, and existing recommendation/catalog tests.
- Testing convention: Python `unittest`; `.gitignore` ignores `.test-tmp/`. Existing tests use temporary directories; the new tests are pure/in-memory except the roadmap builder, which reads maintained catalogs. They do not write those files. Tests were run with `PYTHONDONTWRITEBYTECODE=1` and an explicitly empty `DATABASE_URL`.

## 2. Skill identifiers and collision evidence

### Confirmed current state

- `skill_gap_analysis` in `backend/services/recommendation_engine.py` combines the `technical` and `employability` profile maps and the catalog's `technical_skills` and `employability_skills` maps using dictionary unpacking. If the same key exists in both maps, the employability value/requirement wins and the category source is lost.
- A read-only parse of the current canonical `data/career_knowledge_base.csv` found **no technical/employability key overlap**, either within any career row or across the union of those two fields. The four school-stage ML feature contracts also define technical and employability features as separate lists; the inspected lists have no overlap. The synthetic questionnaire generator likewise defines distinct `TECH` and `EMP` key lists. Existing API fixtures submit these categories separately.
- Common terms such as `communication`, `leadership`, and `problem_solving` occur in other profile domains (for example, interest, aptitude, or employability). They remain separate in the profile maps and in the corresponding dimension scoring; those are not current technical/employability collisions.

### Assessment and disposition

The overwrite behavior is a **confirmed latent risk**, but a real collision is **not present in the current active file-backed catalog or inspected category definitions**. The intended meaning of an identical future technical and employability identifier is not documented: it could be one shared construct recorded in two categories, or two category-specific constructs sharing a string. A category-specific implementation would impose a semantic choice without a data-owner decision. Therefore this phase makes **no skill scoring or gap algorithm change**, does not invent a registry, and does not merge concepts. If a future catalog introduces an overlap, require the catalog owner to decide whether IDs represent one construct or category-specific constructs before publication. Existing output shape remains unchanged.

## 3. Missing and unassessed-value behavior

### Confirmed code behavior

- `backend/app.py::valid_scores` accepts numeric scores from 0–100 or `null`; it rejects invalid score types. `student_profile` converts SQL `NULL` to Python `None` and numeric zero to `0.0` for subject and stored assessment values.
- In `recommendation_engine.py`, `_observed` omits `None` while retaining numeric zero. `_subject_score` averages only observed required subjects. `_requirements_score` considers only observed dimensions with a defined requirement. Irrelevant subjects do not enter the requirement-specific average.
- `skill_gap_analysis` reports a gap only when both a numeric assessment and catalog requirement exist. No requirements yields `insufficient_requirements`; no matching observed data yields `insufficient_data`; partial data yields gaps only for assessed required keys. An assessed zero is a valid score and can yield a gap; an unassessed `None` does not.
- Class 10 `school_pathways._numeric_map` accepts numeric zero, filters `None`, and `_subject_dimension` uses only pathway-relevant subject aliases. Class 10 practice markers are generated only from observed subject/aptitude values below the existing 60 project-guidance marker. No missing value is transformed into a zero gap.
- `school_roadmap.build_pathway_roadmap` carries an `unavailable_assessment` explanation for `insufficient_data` or `insufficient_requirements` and otherwise presents generic `skills_to_explore`, not a claim that the student has a deficit.
- Frontend consumers in `frontend/src/main.jsx` preserve zero using nullish checks (`??`) and show “Not assessed” for absent skill values. The skill-gap response/status/message fields are unchanged.

### New regression tests

`tests/test_phase2_2b_recommendation_quality.py` verifies: `None` is omitted and zero retained; missing subjects are unknown while zero is observed; irrelevant subjects do not lower a requirement-specific score; skill gaps require both evidence and a requirement; partial assessment only yields gaps for scored skills; missing requirements yield no student-deficit claim; and Class 10 roadmaps retain an unavailable-assessment note without asserting a deficit.

These tests exercise pure functions and do not connect to the application database or load/fit/serialize a model.

## 4. Class 10 uncertainty and change

The confirmed decision rule in `school_pathways.summarize_pathways` remains unchanged: a provisional clear leader requires at least two evidence items and a score margin of at least 12 points. The prior note only called differences under 8 close, leaving margins 8–under-12 insufficiently described.

Updated only `recommendation_guidance.small_difference_note` to say that a leading option appears only with at least two evidence items and a 12-point-or-larger lead; otherwise, compare pathways, and scores do not decide the student's future. Ranking formula, margin threshold, evidence requirement, labels, alternatives, score fields, and response keys were not changed. The existing Class 10 frontend displays this same note field; no frontend source change was needed.

Regression cases cover a margin below 8, margins of 8 and 11.9, a 12-point margin, and a large margin with insufficient evidence. They assert the existing thresholds and provisional/non-deterministic wording.

## 5. Files changed

- `backend/services/school_pathways.py` — clarify the threshold/uncertainty note only.
- `tests/test_phase2_2b_recommendation_quality.py` — add 11 focused missing-data, roadmap, and ranking-boundary tests.
- `docs/phase2_2b_recommendation_quality_report.md` — this report.

No source change was made for skill collisions because current evidence has no actual technical/employability overlap and the meaning of a hypothetical shared ID is unresolved.

## 6. Tests and exact results

All commands were run from the project root with `PYTHONDONTWRITEBYTECODE=1` and `DATABASE_URL=''`.

1. `python -m unittest discover -s tests -p test_phase2_2b_recommendation_quality.py -v` — **PASS**, 11 tests.
2. `python -m unittest discover -s tests -p test_recommendation_engine.py -k school_gap -v` — **PASS**, 1 test (`test_school_gap_status_distinguishes_missing_inputs_and_low_scores`).
3. `python -m unittest discover -s tests -p test_recommendation_engine.py -k class10_roadmap -v` — **PASS**, 2 tests (catalog progression and unassessed-gap status).

No complete backend suite, frontend test suite, or production build was run. The change is backend copy plus pure Python regression tests; the documented Vite `EPERM` issue remains outside this phase. No runtime browser test was performed.

## 7. API compatibility

The implementation changes only the value of the existing `recommendation_guidance.small_difference_note` string. `is_leader_clear`, `score_margin`, `evidence_count`, summary, recommendation ordering, skill-gap fields, roadmap keys, and pathway alternatives retain their existing shapes. Existing frontend code already renders `small_difference_note`; no API or UI contract change is required. This was checked by source inspection and unit tests of the produced guidance object; no live API/database request was made.

## 8. Protected state

No database connection or mutation, setup, migration, seed, admin operation, model training, prediction, artifact serialization, catalog publish/restore, or dataset generation occurred. No model artifact, model metric file, student record, credential, canonical catalog, active-release pointer, notebook, or dataset was modified. Tests used in-memory fixtures and read-only maintained records for roadmap construction.

## 9. Remaining ambiguity and approvals

1. **Potential future category collision:** the catalog owner must define whether an identifier shared by technical and employability catalogs represents one cross-category construct or two category-scoped constructs. Until then, this phase preserves current behavior; no active collision is hidden in the current catalog.
2. **Synthetic model validity:** unchanged; synthetic labels do not demonstrate real-student outcome validity. Retraining was not requested or performed.
3. **Frontend production build:** still unverified due to the previously documented sandbox `EPERM` resolving `frontend/src/main.jsx`; no attempt was made to weaken path checks or change Vite configuration.
4. **MySQL/runtime behavior:** not verified; this audit used no database.

## 10. Recommended next steps

- Ask the career catalog/data owner to decide the semantics of a shared technical/employability key before any future overlapping record is staged.
- Keep `None` distinct from zero in future API/profile changes and retain the new tests as guards.
- Keep the Class 10 leader threshold and explanatory copy aligned if ranking policy changes later; any threshold change needs a separate review because it changes recommendation behavior.
- Resolve the existing Vite filesystem `EPERM` in an approved environment before claiming a production build or browser workflow is verified.
