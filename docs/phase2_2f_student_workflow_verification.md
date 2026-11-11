# Phase 2.2F — Student Workflow and Recommendation Verification

## Outcome

**NOT READY FOR STUDENT WORKFLOW VERIFICATION.** The approved runtime cannot safely be used in its current state. Its database no longer matches the supplied SHA-256, it contains existing student/account and assessment data, its runtime career catalog copies are absent, and this process resolves a different system temporary directory from the runtime's parent. No database writes, server startup, HTTP requests, account creation, catalog operations, or cleanup were performed.

This report records current observations only. The earlier owner-reported clean-database state is superseded as a description of the current file; the cause and timing of the change cannot be established from this inspection.

## Environment and isolation evidence

| Check | Result | Evidence |
|---|---|---|
| Runtime marker ID and root | **PASS (identity fields only)** | Marker at `.phase2_2f_student_runtime.json` records runtime ID `ba4386e369c844c69db270dea07762be` and root `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1`. The directory is present and its inspected attributes do not indicate a reparse point. |
| Project identity in marker | **PASS** | Marker records this checkout as the project root. |
| Database file location | **PASS (path only)** | File is at `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1\db\student_test.sqlite3`. |
| Database digest | **FAIL / BLOCKER** | Current SHA-256 is `F0F0B3B3496601BC9835276FC5F1CE9316E4AFD2A132ED99A874084EC8B27C2F`, which differs from the owner-supplied attestation `54572b2247428c101768ca822aad645fa60835f9f31e5cbd9ac369da04db548f`. The launcher requires the external attestation and would refuse `serve`. |
| Database integrity and schema | **PASS (read-only)** | Opened only with SQLite `mode=ro&immutable=1`; `PRAGMA quick_check` returned `ok`; 18 application tables were present. |
| Existing user data | **FAIL / BLOCKER** | Aggregate counts found 2 rows each in `users` and `students`, plus existing account activity, assessments, recommendations, and aptitude records (table counts below). These records were not read individually, altered, or deleted. They must be treated as existing test data and preserved. |
| Database sidecars | **PASS at inspection** | No `-wal`, `-shm`, or `-journal` file appeared in the DB directory listing. |
| Runtime catalog copies | **FAIL / BLOCKER** | `data/career_knowledge_base.csv` and `data/career_metadata.json` are absent, though their expected hashes remain in the marker. The `data` directory contains only an empty `career_releases` directory. |
| Managed catalog state | **PASS as absence only** | Active pointer and managed marker are absent; release and draft directories are empty. This does not compensate for missing canonical catalog copies. No release was restored or activated. |
| Current Python temp root | **FAIL / BLOCKER** | `python -c "import tempfile; print(tempfile.gettempdir())"` returned a sandbox package temp path, not `C:\Users\THANAY\AppData\Local\Temp`. The launcher's direct-child safety assertion therefore rejects the supplied runtime. No environment override was used. |
| MySQL | **NOT CONNECTED** | No MySQL configuration or server was accessed. |

Read-only nonzero table counts were: `users` 2, `students` 2, `academic_records` 5, `application_errors` 5, `aptitude_attempt_questions` 50, `aptitude_attempts` 2, `aptitude_domain_scores` 7, `aptitude_questions` 25, `aptitude_responses` 25, `assessments` 8, `recommendation_events` 4, and `recommendations` 2. `sqlite_sequence` contained 3 sequence entries. No row contents or personal information were displayed.

The runtime catalog marker contains SHA-256 values for the expected career CSV and metadata, but the corresponding runtime files do not exist, so those hashes could not be verified. No canonical source catalog was modified.

## Executed checks

| Check | Result |
|---|---|
| `npm.cmd test` from `frontend` | **PASS** — 27 tests passed, 0 failed, 0 skipped. This includes client-side session/profile isolation and score control state/rendering tests. It does not exercise the Flask API, browser rendering, or persistence in the isolated runtime. |
| Production build to a unique directory outside `frontend/dist` | **FAIL (environment)** — Vite 5.4.21 stopped while resolving `frontend/src/main.jsx` with `EPERM: operation not permitted, realpath`. No successful build was produced; `frontend/dist` was not targeted. The precise sandbox enforcement cause remains unconfirmed. |
| Read-only isolated SQLite inspection | **PASS for integrity/schema; FAIL for test-readiness** — `quick_check=ok`, 18 application tables, but existing student data was present and the digest did not match the supplied attestation. |
| Backend/API tests | **BLOCKED** — running the API against the current runtime could access or alter the pre-existing records; the server launcher's hash, catalog-file, and temp-root safeguards also fail. No substitute database was used because the task requires this existing runtime. |
| Live browser and responsive/accessibility checks | **NOT VERIFIED** — no usable browser automation tool or approved live browser session was available. No frontend/backend servers were started. |

The production build command was `npm.cmd run build -- --outDir <unique sandbox temp directory>`. The output directory was outside `frontend/dist`; Vite failed before completing the build. The exact generated temporary directory was `C:\Users\THANAY\AppData\Local\Packages\sandbox.{2c2619d2-3919-47b2-bcb1-02c620da6634}\AC\Temp\careerpath_phase22f_build_ddd0b698cbbb4d07bbb5d58fb1d8554f`.

## Workflow results

| Workflow | Status | Evidence / reason |
|---|---|---|
| Academic subjects use number inputs; custom subjects follow the same behavior | **PARTIALLY VERIFIED** | Frontend unit tests passed for unassessed, intentional rating, zero/nonzero save/hydration, missing/null, and custom subject state. No live browser interaction was tested. |
| Interests, technical skills, and employability use 0–100 sliders | **PARTIALLY VERIFIED** | Frontend unit tests passed for missing/null, zero, 50, and 100 state; unassessed activation and save/hydration states. CSS appearance, thumb visibility, and track color were not visually verified in a browser. |
| Assessment save/refresh/logout/login persistence | **BLOCKED** | Requires running API against runtime DB. Current DB has pre-existing records and its attested hash differs; no writes were attempted. |
| Two-student account isolation, logout, account switching, aptitude/history ownership | **BLOCKED** | Client unit coverage passed for state replacement and authenticated identity scoping, but backend ownership and live account switching were not exercised. Existing runtime contains two accounts, which must not be overwritten or repurposed. |
| Recommendations for Class 10, Class 12, Bachelor's, Master's | **BLOCKED** | No authenticated API requests were made. No recommendation rankings or evidence comparisons were generated for this run. |
| Recommendations without aptitude completion | **BLOCKED** | Requires authenticated backend workflow; not exercised. |
| Unauthorized requests, cross-account profile/recommendation denial | **BLOCKED** | No API requests were made. Frontend tests do not establish server-side authorization. |
| Recommendation sensitivity to technology, business, research, and mostly unassessed profiles | **BLOCKED** | No controlled profiles were submitted, so ranking changes and explanations cannot be assessed. |
| Aptitude question retrieval, attempts, scoring, history, ownership | **BLOCKED** | No API workflow was executed. Existing aptitude data was left untouched. |
| Browser errors, network behavior, responsive layout, keyboard access | **NOT VERIFIED** | No browser session was available; no servers were started. |

## Defects and severity

### Critical — Isolated runtime integrity/provenance is no longer established

The database's current digest does not match the externally supplied digest, and read-only aggregate inspection shows existing student and activity records despite the earlier clean-state report. The cause is unknown. The runtime career CSV and metadata copies are also missing despite their hashes being recorded by the marker. This runtime must not be used for new student tests until its owner determines the provenance/state and separately authorizes a safe replacement or recovery plan. Do not update the expected digest, restore catalogs, or delete records as a workaround.

### High — Current environment fails launcher's temp-root invariant

The Python process's `tempfile.gettempdir()` is not the parent directory of the prepared runtime. The launcher's explicit safety check would refuse startup. Do not bypass the assertion or move the runtime as part of this verification.

### Medium — Production build remains unverified

The Vite build is blocked by Windows sandbox `EPERM` resolving `main.jsx`. This reproduces the prior environment limitation; it does not establish a source-code build defect.

## Files changed and safety

Only this report was created: `docs/phase2_2f_student_workflow_verification.md`. No application source, tests, configuration, canonical catalogs, model artifacts, runtime files, SQLite rows, or MySQL data were changed. No Admin account, user, test record, publish, restore, migration, seed, or model training operation occurred.

## Recommended next actions

1. Keep the current runtime untouched. The owner should investigate why its DB hash and contents changed and why the runtime catalog copies disappeared, without deleting or overwriting the existing records.
2. After that review, obtain explicit approval for a clean, isolated runtime/database or for testing with this one. Establish an externally recorded DB hash only after the owner confirms its exact contents and provenance; do not simply replace the old expected digest.
3. Resolve the Python temp-root mismatch through an owner-approved execution environment that naturally satisfies the launcher's check. Do not weaken the launcher guard.
4. Rerun focused authenticated API checks only after the isolation gate passes. Then arrange a real browser session for visual, responsive, and keyboard verification.
5. Re-run the production build in a Windows environment that permits Vite to resolve the project entry path.

**Overall readiness: BLOCKED.** Frontend unit-state behavior has passing automated coverage, but the student/API/recommendation/aptitude workflows and live UI remain unverified. No claim of runtime or production readiness is made.
