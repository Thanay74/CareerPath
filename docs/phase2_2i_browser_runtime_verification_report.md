# Phase 2.2I — Browser Runtime Verification and UI/API Parity

**Date:** 2026-11-15  
**Overall release status: NOT READY.** Several browser checks passed, but recommendation snapshots are not restored into the UI after refresh, exact requested viewport testing was unavailable, and the browser did not expose a complete Network panel or all four Class 10 roadmap variants.

## Environment and isolation

- Checkout served: `C:\Users\THANAY\Documents\Codex\2026-09-29\files-pasted-by-the-user-build\outputs\CareerPath`.
- Frontend: Vite 5.4.21 at `http://127.0.0.1:5173/`. The inspected Vite config proxies `/api` to `http://127.0.0.1:5000`. A read-only `GET /api/education/catalog` through port 5173 returned HTTP 200.
- Backend: started using `scripts/phase2_2f_student_runtime.py resume` against the guarded isolated runtime below. It announced `http://127.0.0.1:5000`; no MySQL target was enabled.
- Isolated SQLite runtime: `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_1tftni0k`, runtime ID `c6d3131d073d45cabfdff2eb5aaad441`, database `db\student_test.sqlite3`.
- The browser initially showed port 5174, so I did not treat it as the target. I navigated to the verified Vite origin on port 5173 and confirmed the rendered application and authenticated synthetic account there.
- A new synthetic student, `STU000007` (`phase22i.student.1794740130@example.test`), was registered in the isolated SQLite runtime. It had no prior ratings. No Admin account was created.
- The approved runtime was the only database that received writes. At the end, read-only verification reported SQLite integrity `ok`; aggregate counts were 7 users, 7 students, 5 aptitude attempts, 16 recommendation events, and 5 saved recommendation rows. The count change from Phase 2.2H reflects the one synthetic student and four recommendation requests; no records were deleted.
- Canonical catalog SHA-256 hashes still match Phase 2.2H: `career_knowledge_base.csv` `229d6b4ed077e81f2043515a5ca02ea2ffdea72e1d32467899f4e7c3aa021e78`; `career_metadata.json` `238800fffa961eb70fd70e028552bd05cc639215a0ccfd2adda8dfc1cee36629`.

## Browser and recommendation results

The controlled in-app browser provided Playwright-style DOM/locator access. The repository itself has no Playwright package or E2E configuration. Browser actions were performed at the verified 5173 origin. Backend request logs are evidence of HTTP statuses, but they do not contain POST response bodies.

| Requirement | Status | Evidence and limits |
|---|---|---|
| Frontend and backend identity | **PASS** | Vite/API proxy GET returned HTTP 200; the guarded backend served on loopback port 5000. The UI was visibly served from port 5173. |
| Class 10 recommendations | **PASS** | Authenticated `POST /api/recommend` returned HTTP 200. The UI showed an insufficient-evidence comparison rather than a decisive winner. “Compare all pathways” expanded to Arts/Humanities, Commerce, Diploma/Vocational, and Science cards, each with explanatory text and its experimental-family signal; profile compatibility and combined score were shown as unavailable (`—`) for this unassessed profile. |
| Class 10 disclosure behavior | **PASS** | The disclosure expanded, collapsed, and reopened. Reopening showed exactly four pathway cards. |
| Class 10 comparison content | **PASS** for pathway list; **BLOCKED** for course eligibility per each pathway | The expanded list had four distinct names in this order: Arts/Humanities, Commerce, Diploma/Vocational, Science. No duplicate, missing, or unrelated pathway name appeared, and the cards did not present an unverified degree as pathway-approved. With no ratings, each card displayed “More information needed,” an unavailable profile-compatibility/combined score, and a separately labeled experimental synthetic-family signal. |
| Class 10 Stage 3 explanation | **PASS** for the displayed roadmap; **BLOCKED** for all four variants | The displayed Arts/Humanities roadmap's Stage 3 said no course is shown as pathway-eligible because the maintained catalog does not map Class 12 subject requirements to individual degrees, and directed students to verify with institutions. The UI displays one selected roadmap, not four separate Stage 3 roadmaps; the remaining three were not individually rendered in this browser run. Phase 2.2H records backend/API coverage for empty Stage 3 mappings across all four pathways, but that is not live rendered-browser evidence. |
| Class 12 | **PASS** | With Science PCM selected, the UI displayed recommendations including Public Administration Officer (82%), Teacher (82%), and Biotechnologist (81%). Server log recorded one `POST /api/recommend` with HTTP 200. |
| Bachelor's | **PASS** | With B.Sc selected, the UI displayed Biotechnologist (93%), Business Analyst (92%), and Financial Analyst among the leading results. Server log recorded one recommendation POST with HTTP 200. |
| Master's | **PASS** | With M.Sc selected, the UI displayed Research Scientist (93%), AI Engineer (92%), and additional recommendations. Server log recorded one recommendation POST with HTTP 200. |
| POST body parity for every education level | **BLOCKED** | UI result cards and successful POST statuses were observed for all four levels. This browser tool did not provide a Network response-body capture, so exact POST JSON-to-card equality for each level was not independently established in this run. |
| Saved recommendation API retrieval | **PASS** | A read-only authenticated `GET /api/recommendations?student_id=STU000007` returned HTTP 200 with five saved results. Its Research Scientist 92.5 and AI Engineer 91.6 values round to the UI's displayed 93% and 92%. The token was read from the isolated SQLite file in memory and never printed. |
| Saved results restored in UI after refresh | **FAIL** | After refresh, authentication and the saved Master's profile remained present, but the recommendations area returned to the empty “request matches” state. Static inspection of `frontend/src/main.jsx` confirms session/profile hydration but no startup call to `GET /api/recommendations`. The endpoint has saved data, but the UI does not retrieve it on reload. Do not add automatic restoration without binding a saved snapshot to the profile that produced it; the current API record does not establish that freshness relationship. |
| Authentication and profile hydration | **PASS** for registration and refresh; **NOT TESTED** for a separate login/logout cycle | Registration returned HTTP 201; `/api/auth/me`, the authenticated profile request, and aptitude history requests appeared as HTTP 200. The synthetic identity and saved Master's profile remained after page refresh. A separate logout followed by login and unauthorized-route check was not performed in this phase. |
| Request duplication and API errors | **PASS** for observed recommendation actions; **BLOCKED** for complete browser-network audit | Backend logs showed one `POST /api/recommend` HTTP 200 per each of the four button actions. Each action was preceded by one profile save and one interests and one skills save, each HTTP 200. No failed API status appeared in those logs. A complete browser Network panel was not available, so failed assets, requests outside the backend log, and full duplicate-request analysis remain unverified. |

### Console, assets, and runtime errors

The browser's captured console entries during the interaction showed Vite connection messages and the React DevTools informational notice; no `error` or `warn` entry was captured. This is **PASS** for the captured console entries, not a claim that every request or browser error surface was exhaustively audited. Failed asset requests and uncaught errors outside the captured console are **NOT TESTED** because the browser tool did not expose a complete Network panel. No JavaScript exception was visible in the page during the verified flows.

The tool displayed a browser screenshot during review, but did not provide a supported path to retain it as a repository artifact. No screenshot file was added.

## Responsive layout

The browser tool did not expose a viewport override, and native Brave coordinate input was unavailable. Therefore the required 1536px, 1024px, 769px, 390px, and 360px viewports are each **BLOCKED**, including a current retest of the historically reported 769px navigation issue. No CSS change was made based on guessed dimensions.

The in-app browser happened to render at 304 CSS pixels wide (not one of the requested widths). At that width, `document.documentElement.scrollWidth` was 306 and `document.body.scrollWidth` was 307; the decorative hero art card extended beyond its clipped illustration container. This is a narrow-width observation, not evidence for the requested 360px or 390px breakpoints. It remains a **WARNING / NOT TESTED at target sizes**.

## Accessibility

| Check | Status | Evidence and limits |
|---|---|---|
| Visible keyboard focus | **PASS** | Keyboard traversal produced `:focus-visible` on links, select controls, inputs, disclosure summaries, and rating controls; computed outline was present. |
| Disclosure keyboard activation | **PASS** | Space collapsed Academic subjects and Enter reopened it; the DOM showed the Master's subject controls after reopening. |
| Initial tab sequence | **PASS** for observed segment | The observed order traversed account menu, assessment link, education and degree controls, performance/research/preferences fields, then academic disclosure and rating controls. The entire page tab sequence was not exhaustively captured. |
| Form labels and heading structure | **PASS** for inspected controls | DOM exposed named education/course comboboxes and named subject rating spinbuttons; page had one H1 and section H2 headings, with result and roadmap H3/H4 content when displayed. Not every control in every expanded workflow was audited. |
| Screen-reader behavior | **NOT TESTED** | No suitable screen-reader session was available in the controlled browser. |

## Regression tests and build

- First backend attempt: `python -m unittest discover -s tests -p 'test_*.py'` **FAILED** because the sandbox-provided Windows temp root denied interprocess lock-file access (`PermissionError` under the sandbox Temp path). It did not reach MySQL; this attempt was not treated as a test pass.
- Successful backend rerun used a new, workspace-local temporary root for `TEMP`, `TMP`, and `TMPDIR`, an explicit isolated SQLite `DATABASE_URL`/`CAREERPATH_DB`, and `CAREERPATH_ENABLE_MYSQL_INTEGRATION=0`: `python -m unittest discover -s tests -p 'test_*.py'` — **PASS**, 92 tests in 39.660 seconds. The MySQL integration subdirectory was not run.
- Frontend: `npm.cmd test` — **PASS**, 30 tests, 0 failed.
- First separate-output production build — **FAIL (sandbox restriction)**: `npm.cmd run build -- --outDir C:\Users\THANAY\Documents\Codex\.phase22i_frontend_build_20261115`; Vite 5.4.21 hit `EPERM` resolving `frontend/src/main.jsx`.
- Separate-output production build with approved Windows filesystem access — **PASS**: `npm.cmd run build -- --outDir C:\Users\THANAY\Documents\Codex\.phase22i_frontend_build_20261115_windows`; Vite 5.4.21 transformed 36 modules in 930 ms. `index.html` and `assets/` were confirmed. Output is outside `frontend/dist`.
- No application, test, configuration, dependency, or catalog source was changed in this phase; the only project file added is this report. The pre-existing modified/untracked files listed in Phase 2.2H were preserved.

## Safety, remaining gaps, and disposition

- No MySQL connection, schema operation, migration, seed, Admin bootstrap, catalog publish/restore, model training, or deployment occurred.
- The approved isolated SQLite runtime received one synthetic account and four recommendation requests/profile-save cycles. The database integrity check passed; canonical career CSV/metadata hashes still match Phase 2.2H.
- No code fix was made. In particular, responsive CSS was not changed without target viewport evidence. Saved-recommendation UI restoration remains a confirmed parity failure; fixing it safely requires a profile-to-snapshot freshness contract or equivalent backend evidence.
- Remaining required work: add and test safe saved-result hydration; capture exact POST response bodies alongside rendered cards; individually verify Class 10 Stage 3 behavior for all four pathways in the rendered UI; acquire deterministic viewport control and retest all requested sizes, especially 769px; run the full browser Network and failed-asset audit; finish complete keyboard and assistive-technology checks.
- Phase 2.1/2.2 MySQL integration evidence does not prove production deployment safety or readiness. No production readiness claim is made.

**Recommendation: keep release status NOT READY.** The isolated backend and frontend regression suites and separate production build passed, but the saved-results reload mismatch and blocked browser release checks remain open.
