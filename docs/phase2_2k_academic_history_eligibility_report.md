# CareerPath Phase 2.2K — Academic History and Eligibility Report

**Date:** 2026-11-15  
**Overall readiness: NOT READY for evidence-based admissions eligibility.** This change adds student-reported academic history, profile persistence, versioned snapshot freshness, and a conservative evidence-rule interface. The current career catalog has no reviewed program-specific eligibility rules, so the application correctly continues to label career admission eligibility as unverified.

## 1. Fields added and reused

`students.academic_history` stores optional structured JSON. It is returned by the authenticated student profile API and is scoped to that student's row.

- **Class 10:** board, qualification, current/completed status, and whether actual subjects are unknown, selected, or not applicable. The existing `stream` remains the preferred next pathway.
- **Class 12:** board and qualification, student-reported subjects, and Mathematics as `yes`, `no`, `unknown`, or `not_applicable`. Science PCM, PCB, and PCMB are distinct options. Commerce does not assume Mathematics.
- **Bachelor's:** the existing profile `degree` and `specialization` fields are reused; academic history adds major, optional minor, subjects, institution, qualification label, and completion status.
- **Master's:** existing degree and specialization fields are reused; academic history adds major, subjects, institution, completion status, and previous Bachelor's qualification/status.

Unprovided history normalizes to unknown/empty values. No subjects, degree completion, or qualification are inferred from subject ratings. The UI labels this as student-reported information and keeps fields conditional by education level. Changing a program clears its dependent current-program subject facts; a Master's program change preserves the independently recorded prior Bachelor's qualification.

Validation rejects malformed types, duplicate subject names, cross-level fields, inconsistent Mathematics answers, and incomplete PCM/PCB/PCMB core-subject combinations when the user says the subject list is complete. Validation does not verify transcripts, board results, recognition, or identity.

## 2. Schema and migration

- Fresh SQLite schema: `academic_history TEXT NULL` in `backend/app.py::init_db`.
- Fresh MySQL schema: `academic_history JSON NULL`; older schemas receive an additive column check in the explicit schema setup path.
- Added idempotent MySQL migration: [003_student_academic_history.sql](../backend/migrations/003_student_academic_history.sql). It uses `DATABASE()` from the selected connection and contains no hard-coded `USE` database statement. It only adds the nullable column when absent.
- Existing profiles with a null column load with unknown academic history. An isolated SQLite test built an older `students` table with a pre-existing row, ran the additive schema upgrade, and confirmed the account/profile row remained intact.
- Recommendation snapshot input version is now 2 because academic history affects currentness. Older version-1 snapshots are retained but are not treated as current; students must generate new recommendations after updating history.

**Not executed:** No migration or schema setup command was run. The MySQL migration and JSON adapter behavior remain unverified. No live or isolated project runtime database was opened for this change; API tests created and used their own temporary SQLite databases.

## 3. Eligibility and recommendation behavior

`backend/services/eligibility.py::assess_eligibility` assesses only an explicitly registered rule with an HTTPS source URL and a current ISO verification date. It uses actual-subject history, never self-assessed subject ratings, and supports the statuses:

- eligible now;
- eligible after an additional qualification;
- potentially eligible through a documented alternative route;
- not currently eligible under a verified rule;
- eligibility not verified.

Verified `not_currently_eligible` candidates are removed before personalized profile/model scoring. Remaining candidates are ordered by eligibility status before compatibility score. Incomplete/unknown history stays unverified rather than being treated as failure. Model-family scores cannot change a rule result.

The verified rule registry is intentionally empty. No career is currently associated with a source-backed required-degree/subject, exam, bridge, alternative-route, or institution-restriction record. The engine therefore does not filter actual catalog careers using unverified admissions assumptions. Its existing minimum-education-stage behavior and exploratory ranking remain. Academic history is available to the rule mechanism, but comprehensive eligibility cannot be claimed until rules are approved and populated from official, applicable sources.

The current profile does not record entrance-exam completion/results, verified marksheets, recognition/equivalence, or institution-specific application choices. Where a verified rule requires entrance-exam status, the assessor returns eligibility-unverified because that student fact is not collected. Official-source validation and last-verified dates for the actual current recommendations were **NOT TESTED** in this phase; no new official rules were authored.

Saved recommendation UI/API freshness now changes when academic history changes. Previous snapshots remain stored and become stale rather than being deleted.

## 4. Tests and actual results

All backend commands used `DATABASE_URL` set to an explicitly named SQLite target that tests did not connect to, an empty `CAREERPATH_DB`, `USE_MYSQL=false`, and `CAREERPATH_ENABLE_MYSQL_INTEGRATION=0`. Python's temporary directory was redirected to a newly created unique directory inside the repository because the sandbox-provided Windows temp path denied fixture writes. API test fixtures created temporary SQLite databases and copied catalog files only under their test temporary directories; those per-test directories were cleaned by the test fixtures.

- `python -m unittest tests.test_academic_history tests.test_recommendation_snapshots tests.test_api.ApiTests.test_recommendation_snapshots_restore_only_for_matching_profile_and_catalog -v` — **PASS**, 16 tests.
- `python -m unittest discover -s tests -p 'test_*.py' -v` — **PASS**, 113 tests, 0 failures. Includes the isolated runtime schema/resume tests; no MySQL integration suite was run.
- `npm.cmd test` — **PASS**, 43 tests, 0 failures.
- `npm.cmd run build -- --outDir C:\Users\THANAY\Documents\Codex\.phase2_2k_frontend_build_0bd029f93dcd4fab90515bc852d35450` — **PASS**, Vite 5.4.21, 37 modules, 1.04 seconds; generated `index.html` and `assets/` outside `frontend/dist`.
- `python -m py_compile backend/academic_history.py backend/services/eligibility.py backend/app.py backend/services/recommendation_engine.py` — **PASS**.
- `git diff --check` — **PASS**; Git printed line-ending normalization warnings (LF to CRLF) for modified files only.

During iteration, an early full backend run had 6 failures because the Phase 2.2F runtime schema allowlist still expected the prior `students` columns. The allowlist was updated for the additive column; the tests use `init_db` to construct their isolated schema. The final full run above passed all 113 tests. An initial API-test attempt also hit sandbox-temp fixture write errors; rerunning with a unique repository-local temporary directory resolved that environment issue. The early attempts did not connect to MySQL or the approved student runtime.

Tested profile combinations include Commerce with and without Mathematics, PCM, PCB, Arts/Humanities, BCA, B.Com, B.Sc Computer Science, B.Sc Biology, MCA, M.Sc, M.Com, and MBA. API save/read tests cover persistence across separate requests, malformed update preservation, incomplete/unknown history, and the additive SQLite schema upgrade. A rule-injection test proves a known unmet verified subject requirement is filtered before personalized ranking. These tests do not establish institution eligibility or MySQL integration.

## 5. Browser and responsive verification

**NOT TESTED.** Flask/Vite were not started; no browser session, visual rendering, responsive viewport, screen-reader, or keyboard test was run. The frontend build validates JSX/bundling, not runtime behavior.

## 6. Files edited for this Phase 2.2K work

- `backend/academic_history.py` — new normalization and validation.
- `backend/app.py` — additive schema field, profile API persistence and hydration.
- `backend/education_catalog.py` — explicit Class 12 PCMB stream and subjects.
- `backend/migrations/003_student_academic_history.sql` — guarded additive MySQL migration file; not run.
- `backend/recommendation_snapshots.py` — include academic history and version the fingerprint contract.
- `backend/services/eligibility.py` — new evidence-gated assessor and status ordering; no production rule records.
- `backend/services/recommendation_engine.py` — eligibility assessment/filtering before score ranking and response explanation fields.
- `frontend/src/AcademicHistoryFields.jsx` — new conditional profile fields.
- `frontend/src/enhancements.css` — responsive academic-history field layout.
- `frontend/src/main.jsx` — profile save/display integration and eligibility explanation display.
- `frontend/src/studentProfile.js` — unknown defaults, hydration, and dependent field reset behavior.
- `frontend/test/recommendationView.test.js` — profile-history changes invalidate shown results.
- `frontend/test/studentProfile.test.js` — unknown/default, reload, and dependent-program behavior.
- `scripts/phase2_2f_student_runtime.py` — schema allowlist includes the additive SQLite column so isolated runtime validation matches `init_db`.
- `tests/test_academic_history.py` — new validation, eligibility and pre-ranking filter tests.
- `tests/test_api.py` — API persistence, invalid update and old-schema preservation tests.
- `tests/test_recommendation_snapshots.py` — history-sensitive fingerprint and old snapshot behavior tests.

The repository was already dirty before this work and contained unrelated Phase 2.2F–J changes. Those changes were preserved. No checkout, reset, stash, clean, or commit was performed.

## 7. Safety and remaining limitations

- Canonical catalog files were read-only and their SHA-256 hashes still match the prior audit: `career_knowledge_base.csv` `229d6b4ed077e81f2043515a5ca02ea2ffdea72e1d32467899f4e7c3aa021e78`; `career_metadata.json` `238800fffa961eb70fd70e028552bd05cc639215a0ccfd2adda8dfc1cee36629`.
- No live MySQL connection, database setup/migration, seed, or write occurred. MySQL integration is **NOT VERIFIED**.
- No career/education canonical file, release pointer, model artifact, credential, or student record was modified. No model training occurred.
- The current empty verified-rule registry means no institution-verified admission decision is available. Registry completeness, official-source coverage, and real-world eligibility are **NOT VERIFIED**.
- Browser profile persistence, validation presentation, responsive layout, accessibility, and visual eligibility explanations remain **NOT TESTED**.

## 8. Readiness decision

**NOT READY** for a claim of evidence-based career/course eligibility or production readiness. The profile can now capture useful student-reported academic history, and the engine has a safe rule/evidence interface that ranks verified eligibility ahead of compatibility. Before eligibility decisions can be enabled in practice, choose the jurisdiction and institution/program scope, obtain and review official rules with verification dates, populate the registry through a separately reviewed catalog/data change, add entrance-exam facts if required, and test UI/API behavior against those rules. MySQL migration/integration and browser/accessibility verification also remain open.
