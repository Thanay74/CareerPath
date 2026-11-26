# CareerPath Phase 2.2H — Runtime Reconciliation and Final Verification

Date: 2026-11-15  
Checkout: `C:\Users\THANAY\Documents\Codex\2026-09-29\files-pasted-by-the-user-build\outputs\CareerPath`  
Runtime: `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_1tftni0k`  
Runtime ID: `c6d3131d073d45cabfdff2eb5aaad441`

## Overall result

**NOT READY for release sign-off.** The fresh isolated backend returned the corrected Class 10 roadmap data, and authenticated API workflows passed for all four education levels. The earlier browser-rendered course mismatch is not reproduced by the fresh backend. However, the browser session could not be reliably driven through authenticated workflows, so live API-to-DOM parity, browser console/network inspection, complete responsive/accessibility checks, and the entire browser journey remain incomplete. Eligibility evidence is limited to representative official admission routes, not every recommended course or institution.

No application source, test, canonical catalog, release pointer, model artifact, production configuration, or MySQL database was changed in this Phase 2.2H work. One synthetic student and its test activity were added to the approved isolated SQLite database as part of the authenticated API workflow; details are recorded below.

## Runtime/source reconciliation

| Check | Status | Evidence |
|---|---|---|
| Baseline working tree captured and preserved | **PASS** | Before work, `git status --short` showed existing changes in `backend/app.py`, `backend/services/school_roadmap.py`, `frontend/src/main.jsx`, `scripts/phase2_2f_student_runtime.py`, tests, and earlier reports/fixtures. These existing changes were preserved. This report is the only new repository file from this phase. |
| Approved runtime identity and database | **PASS** | Runtime marker identified the exact runtime ID, root, and current project root. The launcher accepted the externally supplied current database SHA-256 and its read-only checks before serving. The database was SQLite, not MySQL. |
| Runtime data integrity before this run | **PASS** | Read-only SQLite `quick_check` returned `ok`; 18 application tables existed. Before API writes, aggregate counts were 5 users, 5 students, 4 aptitude attempts, and 3 recommendation rows. No individual student records were printed. |
| Canonical catalog copies | **PASS** | The project and runtime copy hashes matched: `career_knowledge_base.csv` = `229d6b4ed077e81f2043515a5ca02ea2ffdea72e1d32467899f4e7c3aa021e78`; `career_metadata.json` = `238800fffa961eb70fd70e028552bd05cc639215a0ccfd2adda8dfc1cee36629`. These files were not written. |
| Fresh guarded Flask startup and SQLite identity | **PASS** | Started with `python scripts/phase2_2f_student_runtime.py resume` from the checkout root, supplying the exact runtime root, runtime ID, current database SHA-256, explicit existing-data confirmation, and port 5000. The launcher sets `PROJECT_ROOT` from its own file, inserts it at the front of `sys.path`, imports `backend.app`, asserts SQLite and the exact database path, validates existing schema/data, and installs its SQLite connection guard. PID 25412 served the fresh API response and was stopped after testing. Server bound to `127.0.0.1:5000`. |
| Project Python/Node process inventory | **PASS** | The read-only checkout-path process inventory found no remaining project Python process after shutdown. It found the Vite `node.exe` process PID 23236, serving `127.0.0.1:5173`; it was left running. |
| Direct capture of the running `school_roadmap.__file__` | **NOT TESTED** | The launcher’s import ordering and fresh response support current-checkout resolution, but the running process did not emit the imported module path as a separate observation. |
| Vite listener identity and loopback binding | **PASS** | The listener on 5173 was bound to `127.0.0.1`; its `node.exe` command line pointed to this checkout’s `frontend/node_modules/.../vite.js`. The process was not stopped. |
| Vite working directory and browser request through its proxy | **NOT TESTED** | `frontend/vite.config.js` proxies `/api` to `http://127.0.0.1:5000`, and `frontend/src/main.jsx` defaults to `/api`, but its process working directory and an actual browser request through that proxy were not independently verified. |
| Cause of the Phase 2.2G mismatch | **BLOCKED** | The earlier rendered page showed 13 broad course names, while the current source and fresh API response return an empty Stage 3 list. A stale/different backend or a previously retained result remains plausible, but the old response body and its Python process/module path were not captured. The precise historical cause cannot be proven. |

Current source references: `scripts/phase2_2f_student_runtime.py` (`PROJECT_ROOT`, `_configure_and_assert`, `_command_start`); `backend/services/school_roadmap.py::build_pathway_roadmap()`; `frontend/vite.config.js`; `frontend/src/main.jsx::PathwayRoadmap()`.

## Authenticated API workflow evidence

The API run used the guarded backend on localhost and only the approved SQLite runtime. A new synthetic test account (`STU000006`) was registered for this run because credentials for the existing synthetic account were not available in this execution context. Its generated password was held in memory only and was not displayed or retained. The account was logged out at the end. No existing account was overwritten or deleted.

The synthetic student completed one server-scored 25-question aptitude attempt. The attempt returned `completed`, seven domain scores, one history entry, and seven hydrated aptitude domains. The profile’s aptitude result survived profile save/reload while the education level changed.

Each of the four profile requests was saved, reloaded through the authenticated profile endpoint, used for `POST /api/recommend`, and then compared to authenticated `GET /api/recommendations`. The saved response exactly equaled the corresponding POST response for each level.

| Education level/profile | POST recommendation response | Saved retrieval | Returned labels |
|---|---|---|---|
| Class 10, Science | **PASS**, HTTP 200; 4 pathways | **PASS**, HTTP 200 and equal | Science; Diploma/Vocational; Arts/Humanities; Commerce |
| Class 12, Commerce | **PASS**, HTTP 200; 5 results | **PASS**, HTTP 200 and equal | Lawyer; Graphic Designer; Teacher; Journalist; Financial Analyst |
| Bachelor's, BCA/Data Analytics | **PASS**, HTTP 200; 5 results | **PASS**, HTTP 200 and equal | Cybersecurity Analyst; Web Developer; Data Analyst; Software Developer; Business Analyst |
| Master's, MCA/Cybersecurity | **PASS**, HTTP 200; 5 results | **PASS**, HTTP 200 and equal | Cybersecurity Analyst; Civil Engineer; Data Analyst; Web Developer; Data Scientist |

For Class 10, the response contained all four pathways. `roadmap.stages[id=after_12].program_options` had length **0** for Science, Diploma/Vocational, Arts/Humanities, and Commerce. The response therefore does not present unrelated degrees as approved pathway courses. The API response body SHA-256 values captured during the run were:

- Class 10: `e721ef504aa68152385b550192d692b42ed821608359eab8644ed2d12adb08ed`
- Class 12: `a8e362c1ac5aa796f74e30f070431f1fd13d21edca956ac8cb7110cdfb654efc`
- Bachelor's: `bd2f0122536f1ce5833173fb06757447b51bfa5b2036c8ed41f8137e822c6c1f`
- Master's: `222ed541a3e622a20f3d2769eabf6935c646ee5b5cde07636f77867a9962ce66`

This was API-level evidence. The raw response bodies were parsed in memory and hashed; they were not saved as separate artifacts. Exact per-result scores are not included in this report. User-visible rendering parity is **NOT TESTED**.

Session/API checks: registration `201`; authenticated identity `200`; education catalog `200`; aptitude create `201`; aptitude submit/history/profile `200`; profile save/reload and all recommendations/retrievals `200`; re-login and identity `200`; logout `200`; profile request after logout `401`. No unexpected HTTP error occurred in the 27 API calls made by the workflow. The post-logout `401` was expected. This direct API run does not establish browser request deduplication or console cleanliness.

After the workflow, a read-only integrity check again returned `ok`; the 18 application tables remained present. Aggregate counts were 6 users, 6 students, 5 aptitude attempts, 12 recommendation events, and 4 recommendation snapshots. The deltas are the one test account, one completed test attempt, and four recommendation submissions created by this run. No cleanup or deletion was performed. The isolated database’s post-run SHA-256 was `abf71cc33beff44aa780df874e71b9552ff412a5984ad680a3f26b751861ed34`.

The exact verified backend process was stopped after testing by matching its PID to the `phase2_2f_student_runtime.py resume` command, runtime root, and runtime ID. Port 5000 was confirmed closed. The existing Vite process on port 5173 was left running.

## Browser, console, network, responsive, and accessibility checks

| Check | Status | Evidence |
|---|---|---|
| Live authenticated browser journey on the fresh backend | **BLOCKED** | Brave could display a CareerPath page, but the computer-use tool then reported user-input/coordinate-geometry errors. It was not possible to complete authenticated browser interactions or confirm that its frontend requests reached the verified backend. No authenticated browser result is claimed. |
| Compare All Pathways rendered parity | **NOT TESTED** | Phase 2.2G historically verified that the disclosure expands/collapses and showed four Class 10 cards. In this run, the API returned four pathways and empty Stage 3 course lists, but a current expanded browser view could not be captured and compared to the response. |
| Browser console/runtime errors | **NOT TESTED** | No DevTools console export or complete browser console observation was available. |
| Browser network errors, duplicate requests, assets, auth status | **NOT TESTED** | Direct API workflow statuses are listed above. Browser Network-panel data, failed asset list, duplicate-request analysis, and browser/frontend-to-backend response equality were not captured. |
| Desktop responsive layout | **NOT TESTED** | Phase 2.2G recorded a historical desktop spot check as readable with no observed horizontal clipping in the inspected results. No full current-run desktop audit was performed. |
| Tablet responsive layout | **FAIL (historical)** | Phase 2.2G recorded crowded navigation, wrapped “Build my path,” and clipped account identity at about 769 px. No fix or current retest is included here. |
| Mobile responsive layout | **NOT TESTED** | No mobile viewport audit was completed. |
| Keyboard navigation | **NOT TESTED** | Phase 2.2G historically verified native Compare All disclosure activation with Space and a visible focus outline. Full tab order and keyboard operation across the student journey were not completed. |
| Screen reader | **NOT TESTED** | No screen reader was run. |

## Eligibility evidence

**Comprehensive eligibility verification: BLOCKED.** The catalog and recommendation output do not identify every institution, program, current entry cycle, board, category, and examination route. The following are official examples only and must not be generalized to all institutions or degrees:

- The Consortium’s [CLAT 2027 UG eligibility page](https://clat2027.consortiumofnlus.ac.in/clat-2027/ug-eligibility.html) states the current participating-NLU entrance route uses CLAT and describes 10+2/equivalent minimum marks (45%, or 40% for SC/ST/PwD categories). Individual NLU intake, reservations, and admission administration still require checking its current notice.
- The University of Delhi’s [2026 UG FAQs](https://admission.uod.ac.in/userfiles/downloads/2026/17052026_Updated_FAQsUG%202026-final.pdf) specify CUET-UG and a program-specific subject combination for DU B.Com. (Hons.), including one language plus Mathematics and two List B subjects, or one language plus Accountancy and two List B subjects. This is a University of Delhi rule, not a universal B.Com. rule.
- NTA’s [Engineering Exam page](https://www.nta.ac.in/Engineeringexam) describes Physics and Mathematics plus one of Chemistry/Biotechnology/Biology/Technical Vocational for the B.E./B.Tech. qualifying subject combination in the NIT/IIIT/participating-CFTI context. It explicitly allows that states and other institutions may use separate criteria.
- [JEE Advanced 2027 eligibility](https://jeeadv.ac.in/eligibility.html) has separate IIT-route conditions, including the relevant Class XII subject combination and other eligibility criteria. These are not requirements for every engineering degree or institution.

Other Class 12, Bachelor's, Master's, diploma, recognition, licensing, and institution/program prerequisites remain **BLOCKED** pending current official program-level evidence. No canonical catalog content was changed.

## Tests and production build

- Frontend unit suite: `npm.cmd test` — **PASS**, 30 tests, 0 failures, 0 skipped.
- Backend suite: `python -m unittest discover -s tests -p 'test_*.py' -v` — **PASS**, 92 tests, 0 failures. The invocation explicitly set `DATABASE_URL` to a fresh SQLite path under `.test-tmp`, set `CAREERPATH_DB` to the same path, and set `TEMP`, `TMP`, and `TMPDIR` to a new workspace-local scratch directory. Tests used their isolated SQLite/temp fixtures. No MySQL integration test was run.
- First separate-output build attempt — **FAIL (sandbox restriction)**: `npm.cmd run build -- --outDir C:\Users\THANAY\Documents\Codex\.phase2_2h_build_cfa2c17dddf243fe96a5437760e28ef0` failed with Vite `EPERM` resolving `frontend/src/main.jsx`.
- Separate-output production build with approved filesystem access: `npm.cmd run build -- --outDir C:\Users\THANAY\Documents\Codex\.phase2_2h_build_818a805f456e4d2b9fe77260c43802b0` — **PASS**, Vite 5.4.21, 36 modules transformed, 977 ms; `index.html` and `assets/` confirmed. The output is outside `frontend/dist`.

These tests and the build do not verify MySQL integration, full browser behavior, deployment, or real-student predictive validity.

## Safety and file accounting

- No MySQL connection, schema operation, migration, or seed command was run.
- Only the approved isolated SQLite runtime received writes: one new synthetic student, one aptitude attempt, profile snapshots, four recommendation events, and an updated recommendation snapshot. Existing student accounts and test data were preserved; no deletion occurred.
- Canonical catalog files and runtime copies retained the matching hashes listed above. No active pointer, managed marker, release, or model artifact was changed.
- The failed sandbox build output directory was not cleaned up. Successful build output was written outside `frontend/dist`.
- **File changed in this phase:** `docs/phase2_2h_runtime_reconciliation_report.md` only. No source code or test files were changed.

## Acceptance summary

| Priority | Status |
|---|---|
| 1. Identify current guarded backend, isolated SQLite identity, and project module path | **BLOCKED**: guarded backend and SQLite target verified; direct imported `__file__`, Vite working directory, and historical process cause were not captured |
| 2. Capture Class 10 API results and verify all four pathways and empty Stage 3 lists | **PASS** at API level |
| 2a. Verify frontend-rendered response parity | **NOT TESTED** |
| 3. Authenticated recommendation and saved retrieval across all four education levels | **PASS** at API level for one new synthetic profile; historical existing student’s credentials were unavailable |
| 4. Full browser console/network/responsive/keyboard/screen-reader audit | **BLOCKED** as detailed above |
| 5. Current institution-specific eligibility for every course | **BLOCKED**; official examples reviewed, comprehensive mapping absent |
| 6. Backend/frontend tests and separate-output production build | **PASS** |

**Final readiness: NOT READY.** The source/runtime discrepancy is reconciled for the fresh isolated backend at the API boundary, but historical cause, full browser parity/audits, the tablet issue, mobile/accessibility coverage, comprehensive eligibility sources, MySQL integration, Admin publishing, and production deployment remain open.
