# Phase 2.2J — Saved Recommendation Restoration Report

**Date:** 2026-11-15  
**Release decision: BLOCKED.** Backend persistence and frontend restoration logic are covered by isolated tests, but live browser restoration, four-level response-to-card parity, required viewport checks, and full accessibility checks could not be completed because the available Brave session could not reach the local frontend.

## 1. Summary

Phase 2.2I established that the recommendation API could save and return results, but refresh did not restore them in the page. The UI startup/profile hydration path did not retrieve saved recommendations. In addition, the stored `recommendations.results_json` was a bare list and contained no verifiable association to the profile or catalog that produced it. Fetching that list blindly would have risked showing results for changed inputs as current.

Phase 2.2J adds a versioned snapshot envelope and a profile/catalog freshness check. On workspace hydration, the frontend loads the authenticated student's profile first, then requests that student's saved recommendation state. The API returns saved recommendations only when their profile-input and active-catalog fingerprints match. Profile edits, a different session, stale catalog state, malformed or legacy records, and retrieval errors do not expose an old result array as current.

No recommendation weights, ranking logic, model artifacts, catalogs, database schema, or migrations were changed. The project remains blocked from release pending browser and other release checks below.

## 2. Snapshot freshness contract

`backend/recommendation_snapshots.py::recommendation_input_fingerprint` hashes a deterministic JSON representation of recommendation inputs using SHA-256 and input format version 1. Included fields are:

- Education level, stream, degree, and specialization.
- Academic subjects and assessment state, aptitude, interests, technical skills, and employability skills.
- Career preferences, research interests, academic performance, and academic scale.

Dictionary keys are sorted; numeric values are normalized so equivalent integers and floats hash consistently. Missing fields use an explicit missing sentinel; explicit `null` and numeric `0` remain distinct. Unsupported and non-finite values are rejected. Only the hash/version is returned as snapshot metadata; raw profile input is not included in that metadata.

Each generated snapshot stores a random ID, timestamp, input version, profile-input fingerprint, catalog fingerprint, and recommendation array. Catalog fingerprinting is returned from `recommend_with_catalog_fingerprint`, which uses the same catalog read context as recommendation scoring. The existing JSON column stores a versioned envelope containing multiple snapshots.

The authenticated `GET /api/recommendations` route selects the newest matching profile-and-catalog snapshot. It returns one of `current`, `stale`, `unverified`, or `none`. Legacy and malformed records are hidden from the current-results field. Legacy bytes/records are retained in the envelope rather than silently discarded. The client-supplied student ID is checked against the bearer-token identity; it is not treated as authorization by itself.

## 3. Implementation changes

Phase 2.2J implementation files:

- `backend/recommendation_snapshots.py` — canonical fingerprinting, versioned history envelope, safe legacy preservation, and matching snapshot selection.
- `backend/services/recommendation_engine.py` — scoring wrapper returns the catalog fingerprint from the same loaded catalog snapshot.
- `backend/app.py` — authorized generation and retrieval, persistence of multiple snapshots, profile/catalog freshness checks, rollback on failed persistence, and current-only recommendation use by related recommendation endpoints.
- `frontend/src/studentWorkspace.js` — authenticated profile-first hydration followed by saved recommendation retrieval; accepts result arrays only for API freshness `current`.
- `frontend/src/main.jsx` — restoration/current/stale/error/empty messaging; profile/session context binding; reset and request-generation checks prevent previous-session or stale-profile results from rendering.
- `tests/test_api.py` — isolated API coverage for generation, retrieval, owner scoping, invalidation, no-aptitude recommendation generation, legacy preservation, and multi-snapshot persistence.
- `tests/test_recommendation_snapshots.py` — fingerprint normalization, missing/null/zero distinction, relevant-input invalidation, legacy handling, and deterministic current selection.
- `frontend/test/recommendationRestore.test.js` — profile-first retrieval and current/stale/unverified/none/error/auth-expiry handling.
- `frontend/test/studentProfile.test.js` — updated expected workspace hydration call sequence/state.

No database schema or migration change was made. The existing `recommendations.results_json` field is used. SQLite snapshot append is serialized with `BEGIN IMMEDIATE`; the MySQL code path uses a student-row `FOR UPDATE` lock, but this phase did not connect to MySQL and does not verify its transaction behavior.

The working tree already contained unrelated Phase 2.2F–I changes before this work. Those changes were preserved; no reset, checkout, stash, commit, or broad cleanup was performed.

## 4. API contract evidence

The relevant routes are `POST /api/recommend` (`backend/app.py::create_recommendations`) and `GET /api/recommendations` (`backend/app.py::get_recommendations`). Both use the existing bearer-token ownership check. Missing/invalid credentials return the existing JSON error style with HTTP 401; another student's identity returns HTTP 403. The GET route does not return another student's row.

The generation response shape is:

```json
{
  "student_id": "<authenticated-student>",
  "recommendations": [{"career_id": "<id>", "career_name": "<name>"}],
  "freshness": "current",
  "snapshot": {
    "snapshot_id": "<opaque-id>",
    "created_at": "<UTC timestamp>",
    "input_version": 1,
    "input_fingerprint": "<sha256>",
    "catalog_fingerprint": "<sha256>"
  }
}
```

The saved retrieval response uses the same `freshness` classification and includes `recommendations` only for a matching current snapshot. A stale/legacy/unverified response includes an empty array and a user-facing message; a missing record returns `freshness: "none"`. This is code/test evidence, not a captured live browser response body.

Backend tests exercise generation and retrieval equality, input invalidation (including education and null-versus-zero subject values), legacy handling, owner-only access, and preserving multiple snapshots. Fingerprint unit tests exercise additional recommendation dimensions such as course/degree, interests, and technical skills. Exact live response bodies for all four education levels remain unverified in this phase.

## 5. Browser evidence

| Education level / browser requirement | Status | Evidence |
|---|---|---|
| Class 10 generate, refresh, restore, compare pathways, Stage 3 | **BLOCKED** | No Phase 2.2J browser workflow completed. |
| Class 12 generate, refresh, restored count, stale-input test | **BLOCKED** | No Phase 2.2J browser workflow completed. |
| Bachelor's generate, refresh, restored count, degree-change test | **BLOCKED** | No Phase 2.2J browser workflow completed. |
| Master's generate, refresh, restored count, specialization-change test | **BLOCKED** | No Phase 2.2J browser workflow completed. |
| POST/GET response-body to rendered-card parity | **BLOCKED** | The current browser session did not load the app, and no response body was captured. No server log was substituted for response evidence. |
| Stale or unverified results hidden in a browser | **NOT TESTED** | Covered in frontend logic/tests, but not verified in a running browser. |

The controlled Brave session showed `http://127.0.0.1:5174` and `ERR_CONNECTION_TIMED_OUT` / `chrome-error://chromewebdata/`. Thus the live page, authentication state, and network responses could not be inspected. Backend and frontend tests are not represented as end-to-end browser evidence.

## 6. Responsive evidence

Each required viewport is **BLOCKED** because the browser could not reach the app and no reliable viewport run was available:

| Width | Status | Notes |
|---:|---|---|
| 1536px | **BLOCKED** | Not rendered. |
| 1024px | **BLOCKED** | Not rendered. |
| 769px | **BLOCKED** | Historically reported navigation issue remains unverified. |
| 390px | **BLOCKED** | Not rendered. |
| 360px | **BLOCKED** | Not rendered. |

No speculative CSS changes were made.

## 7. Accessibility evidence

| Check | Status | Evidence |
|---|---|---|
| Full keyboard tab order and focus visibility | **NOT TESTED** | No Phase 2.2J browser session. Phase 2.2I contains only partial prior keyboard evidence. |
| Enter/Space behavior and disclosure semantics | **NOT TESTED** | No Phase 2.2J browser session. |
| Forms, labels, dropdowns, heading hierarchy | **NOT TESTED** | No Phase 2.2J browser session. |
| Loading/error announcements | **NOT TESTED** | Status/alert roles are present in `frontend/src/main.jsx`; runtime announcement behavior was not observed. |
| Screen-reader behavior | **NOT TESTED** | A suitable screen-reader session was not available. |

## 8. Regression results

Commands and actual results:

- `python -m unittest discover -s tests -p test_recommendation_snapshots.py -v` — **PASS**, 5 tests.
- `python -m unittest discover -s tests -p test_api.py` — **PASS**, 25 tests, using an explicit temporary SQLite target. A preceding attempt without explicit SQLite configuration failed in test setup when the app tried the configured MySQL path; the sandbox refused that connection. No MySQL connection succeeded. The failure is not counted as a pass.
- `python -m unittest discover -s tests` — **PASS**, 99 tests, with explicit isolated SQLite test configuration. This is not MySQL integration verification.
- `npm.cmd test` — **PASS**, 38 tests, 0 failed (rerun during this continuation).
- `npm.cmd run build -- --outDir C:\Users\THANAY\Documents\Codex\.phase2_2j_frontend_build_c6e4b868c4da4c019103c6ade7e5ec85` — first sandbox attempt **FAILED** with Vite `EPERM` resolving `frontend/src/main.jsx`.
- The same separate-output build retried with the approved Windows filesystem permission — **PASS**, Vite 5.4.21, 36 modules transformed, 964 ms. `index.html` and `assets/` were present. The existing `frontend/dist` was not targeted or overwritten.
- `git diff --check` — **PASS**; Git emitted line-ending-normalization warnings for already modified files, not whitespace errors.

No repository Playwright dependency/configuration exists. No browser E2E test was run in this phase.

## 9. Database and safety audit

Read-only verification was performed against only the approved isolated SQLite runtime:

- Runtime root: `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_1tftni0k`.
- Runtime ID: `c6d3131d073d45cabfdff2eb5aaad441`; marker runtime root, project root, and runtime ID matched the requested runtime.
- Database: `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_1tftni0k\db\student_test.sqlite3`.
- Database SHA-256: `5c915516fc7786ead6a375cfdd6ff715dec251acc25df4f84ab1df95bacca9b3` (matches the owner-recorded resume hash used in the session).
- Opened read-only/immutable for inspection: `PRAGMA integrity_check` returned `ok`; 18 non-internal tables were present; `-wal`, `-shm`, and `-journal` sidecars were absent.
- Aggregate counts: users 7; students 7; aptitude attempts 5; aptitude questions 25; recommendation events 16; recommendation rows 5. No individual student values were read or reported.
- Canonical catalog SHA-256: `data/career_knowledge_base.csv` `229d6b4ed077e81f2043515a5ca02ea2ffdea72e1d32467899f4e7c3aa021e78`; `data/career_metadata.json` `238800fffa961eb70fd70e028552bd05cc639215a0ccfd2adda8dfc1cee36629`. Both match the runtime marker and Phase 2.2I report.
- No MySQL connection, schema initialization, migration, seed, Admin bootstrap, publish/restore action, model training, catalog write, or deployment occurred during this continuation. The browser attempt timed out before any application workflow.

## 10. Remaining gaps

- **BLOCKED:** Real browser lifecycle proof that current saved results restore after refresh, and that stale/other-session results never display.
- **BLOCKED:** Capture actual POST and saved GET response bodies for all four education levels and compare ID/order/score values with rendered cards.
- **BLOCKED:** Class 10 rendered comparison of all four pathways and their Stage 3 explanations.
- **BLOCKED:** Exact responsive viewport widths, especially 769px.
- **NOT TESTED:** Complete keyboard, screen-reader, and assistive-technology checks.
- **UNVERIFIED:** MySQL transaction/locking behavior; no approved isolated MySQL operation was part of this task.
- **UNVERIFIED:** Production deployment and power-loss durability. The SQLite and application tests do not establish those properties.

## 11. Final release decision

**BLOCKED.** The safe saved-recommendation contract and isolated automated tests are in place, but the primary acceptance criterion has not been demonstrated in a live browser in this phase. Release must remain not ready until browser restoration/parity and the remaining mandatory verification gates are completed with reachable isolated services and appropriate viewport/network inspection.
