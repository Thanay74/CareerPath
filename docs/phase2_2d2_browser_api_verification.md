# CareerPath Phase 2.2D2 — Isolated Browser and API Verification

**Date:** 2026-10-22  
**Scope:** Temporary SQLite/API integration and React/Vite-to-Flask proxy verification. No production or MySQL verification.

## Summary

The isolated API workflow passed through the live Flask server and Vite proxy, and the selected backend and frontend automated tests passed after redirecting Python's temporary directory to a workspace-local test folder. The Vite entry document was served successfully. The Windows browser-control helper stopped before interacting with the page because it could not establish the browser's current URL with sufficient confidence; therefore JavaScript execution, rendered UI behavior, and browser console state are **not verified**.

MySQL, an active administrator's successful workflow, and production deployment were not tested. Readiness remains blocked on isolated integration and browser/deployment verification.

## Environment and isolation

Reviewed `docs/phase2_2d_report.md`, `docs/phase2_2d_isolated_integration_plan.md`, `README.md`, `SETUP_GUIDE.md`, `SRS_IMPLEMENTATION.md`, `ARCHITECTURE.md`, `API_DOCUMENTATION.md`, frontend routes/session code, Flask API routes, database target resolution, and `tests/test_api.py`.

The repository contains `SRS_IMPLEMENTATION.md` and `ARCHITECTURE.md`, but no standalone SRS or System Design PDF was found in the project. Compliance observations below are limited to those implementation/design documents and the API contract.

Isolation used a temporary runtime folder named `.phase2_2d2_runtime_78454dba409d464097410856ccbc9467` under the project root. The temporary Flask launcher asserted before initialization that `DATABASE_URL` was empty, `USE_MYSQL` was false, and `DB_PATH` resolved exactly to the runtime folder's `test.sqlite3`. It copied the canonical career CSV and metadata into that folder and redirected the release pointer, managed marker, release directory, activation lock, and draft directory there. It then initialized only that fresh SQLite file and explicitly seeded education and aptitude fixtures there. No admin bootstrap was performed. The runtime folder, including the test accounts and database, was removed after the servers stopped.

The frontend used the existing Vite proxy at `127.0.0.1:5000`, with `VITE_API_URL=/api`; both services were bound to loopback. A first unprivileged Vite launch failed with `EACCES` binding port 5173. The launch succeeded under reviewed local-run permission. The initial Flask process in the restricted sandbox could not be reached from the Vite process; it was stopped and relaunched under the same reviewed local-run context. A later direct GET and a Vite-proxied GET both returned 200.

No `.env` contents or credentials were read. The app used `DATABASE_URL=''`; no MySQL connection was attempted.

## Commands and results

### Runtime services

Backend launcher command (the temporary Python launcher performed the isolation assertions and path redirections described above):

```powershell
$env:PYTHONPATH = (Get-Location).Path
python .phase2_2d2_runtime_78454dba409d464097410856ccbc9467\isolated_server.py .phase2_2d2_runtime_78454dba409d464097410856ccbc9467
```

It reported `ISOLATED_RUNTIME_READY db=temporary-sqlite catalog=temporary-copies releases=temporary` and served `http://127.0.0.1:5000`.

Frontend command (the first invocation without reviewed local-run permission failed with `EACCES`; this invocation started successfully):

```powershell
$env:VITE_API_URL = '/api'
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Vite 5.4.21 served `http://127.0.0.1:5173/`. Read-only checks of `GET http://127.0.0.1:5000/api/education/catalog` and `GET http://127.0.0.1:5173/api/education/catalog` both returned HTTP 200.

### Live isolated API workflow through Vite

A PowerShell `System.Net.Http.HttpClient` script sent requests to `http://127.0.0.1:5173/api`. It used a unique `@example.test` student account and did not print bearer tokens. Results:

| Workflow | Result | Evidence |
|---|---|---|
| React entry document | PARTIALLY VERIFIED | `GET /` returned 200 and contained the CareerPath entry document. The page's JavaScript was not executed in a browser. |
| Vite-to-Flask API routing | VERIFIED | `GET /api/education/catalog` through Vite returned 200 from the local Flask server. |
| Four education catalogs | VERIFIED | Catalog response contained 10th, 12th, Bachelor's, and Master's, each with pathway/course choices and subjects. |
| Anonymous protected resources | VERIFIED | Anonymous `GET /api/student/profile?...` returned 401; anonymous `GET /api/admin/dashboard` returned 403. |
| Student registration, login, identity | VERIFIED | Registration returned 201/student; login returned 200; `/api/auth/me` returned the same test email and student role. |
| Profile persistence across education levels | VERIFIED (API) | Save and retrieve returned 200 for Class 10, Class 12, Bachelor's, and Master's profiles with matching education level. |
| Five assessment areas | VERIFIED (API) | Academic subjects were saved in profile; interest and technical/employability APIs returned 200; a seeded aptitude attempt started and its submitted answers produced a persisted score. |
| Recommendation and skill-gap APIs | VERIFIED (API) | `/api/recommend`, `/api/skill-gap`, and `/api/improvement-plan` returned 200 with results for the Class 10 test profile. |
| Class 10 roadmap | VERIFIED (API) | The leading result included roadmap data with multiple progression stages. Roadmap rendering and interactive expansion were not exercised. |
| Invalid inputs | VERIFIED | An invalid education/pathway combination and an interest score above 100 each returned 400. |
| Logout/session invalidation | VERIFIED (API) | Logout returned 200; subsequent `/api/auth/me` returned 401 and profile access returned 401 with the revoked token. |
| Cross-account isolation | VERIFIED (API) | One test student's request for another test student's profile returned 401. |
| Admin authorization | VERIFIED (API denial) | Twenty Admin route/method pairs—including dashboard, users, career CRUD, drafts, publish, release list/restore, skills, models, dataset/recommendation, audit/error, and aptitude-question operations—returned 403 for both anonymous and student requests. No active Admin token was created, so successful Admin operations were not tested. |
| Browser JavaScript errors and visual UI | NOT VERIFIED | Browser-control setup stopped with: “could not determine the current browser URL on Windows with enough confidence to enforce policy.” No page interaction, console capture, responsive viewport, or accessibility interaction check was performed. |

The admin denial requests used intentionally nonexistent identifiers for publish/restore/discard/update/delete cases. Because authorization rejected them first, no Admin draft, release pointer, or catalog operation was performed.

### Automated tests

The first focused backend test attempt used the sandbox's default Windows temp directory. `tests/test_api.py::ApiTests.setUp` failed while copying a catalog fixture into that directory (`PermissionError: [Errno 13]`); Python's automatic temp cleanup also reported `WinError 5`. The test bodies did not run in that attempt. The tests were rerun with `TEMP`, `TMP`, and `TMPDIR` set to a fresh workspace-local temporary folder and `DATABASE_URL=''`; the temporary folder was removed afterward.

| Command / test | Result |
|---|---|
| `python -B -m unittest discover -s tests -p test_api.py -k test_registration_login_and_invalid_input -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_api.py -k test_authenticated_identity_logout_and_relogin -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_api.py -k test_profile_assess_recommend_and_gap_flow -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_api.py -k test_dynamic_education_catalog_and_profile_details_persist -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_api.py -k test_profile_rejects_cross_level_and_cross_degree_catalog_values -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_api.py -k test_requested_education_scenarios_return_calculated_recommendations -v` | PASS — 1 |
| `npm.cmd test` from `frontend/` | PASS — 7 passed, 0 failed |

The production build was not rerun in this phase; Phase 2.2D's separately recorded Windows build result remains the prior evidence.

## Data integrity and safety evidence

- The temporary SQLite database contained three test users, three test students, one aptitude attempt, one recommendation, and no Admin user. It was removed with the temporary runtime directory after the servers stopped.
- Current SHA-256 hashes match the Phase 2.2D baseline:
  - `data/career_knowledge_base.csv`: `229D6B4ED077E81F2043515A5CA02EA2FFDEA72E1D32467899F4E7C3AA021E78`
  - `data/career_metadata.json`: `238800FFFA961EB70FD70E028552BD05CC639215A0CCFD2ADDA8DFC1CEE36629`
  - `data/processed/career_model_metrics.json`: `4EAE655E86BD4A14A60DC5DB4C8747C16B7F5C2C2B8915278336F3E3EA3E1D57`
  - `backend/models/career/10th_career_model.joblib`: `AFFCC62D850B4B9E8706AA02FF11076046F7A1CCB2DB9AB1D7D4D1266D074793`
  - `backend/models/career/12th_career_model.joblib`: `3B31D0D1472EC2112FC734F9A6F756367048AD6A0F4C6EBEB23E30AD6B75A50A`
  - `backend/models/career/bachelors_career_model.joblib`: `C0A7891C11AAEBC9EF9F8B0A32F210F96D3D2B227B40D49F01407AE729FC98B6`
  - `backend/models/career/masters_career_model.joblib`: `6400A9359FF75241A0882EA129A6C71EC597DD945D538BC9120B7D17FE62F1DF`
- The canonical catalog pointer and managed marker remain absent, and `data/career_releases/` remains absent. Recommendation reads used temporary copies.
- No MySQL connection, setup/migration command, production/student database access, model training, model artifact write, catalog publication/restoration, or build-output write occurred. The existing `frontend/dist/` and Phase 2.2D build output were not used as outputs.

## Remaining gaps and next step

Browser-level JavaScript/console checks, responsive and accessible interactions, saved-profile behavior through the React UI, and Admin UI behavior remain unverified. The active Admin success path was not tested. MySQL behavior and deployment readiness also remain unverified. The available SRS implementation map and architecture documentation describe the major requirements, but the original standalone SRS/System Design source documents were not present in the repository for a complete document-level cross-check.

**Isolated MySQL integration can be safely planned next: YES, conditionally.** The plan should require an owner-provisioned disposable MySQL schema, a dedicated test account, explicit approval for initialization, and pre-connection verification that the resolved driver/host/schema are not the production `careerpath` target. Execution remains blocked until those isolation prerequisites are available; do not fall back to SQLite and describe it as MySQL verification.

**Production readiness: NOT ESTABLISHED.** No production deployment, browser end-to-end test, or MySQL integration is claimed.
