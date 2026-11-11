# CareerPath Phase 2.2F — Browser and Admin Verification Plan

**Status:** Planning only. No tests, application startup, database connection, or catalog operation was performed for this plan.

## 1. Purpose and evidence status

This plan defines a safe browser end-to-end and Admin workflow verification pass. It reuses existing isolated API evidence where possible, then identifies what still needs a real browser and an authorized Admin test identity. It does not establish production readiness.

Status terms used below:

- **PLANNED:** included in this future verification; not run in this phase.
- **EXECUTED / PASSED / FAILED:** only for a test actually executed with recorded evidence.
- **BLOCKED:** execution must not proceed until the named safety prerequisite is met.
- **NOT VERIFIED:** available evidence does not demonstrate the behavior.

### Existing evidence reviewed

| Area | Recorded evidence | Current status for Phase 2.2F |
|---|---|---|
| React/Vite to Flask API | Phase 2.2D2 reports the React entry document and proxied education catalog returned HTTP 200; API requests exercised through Vite. | API proxy **VERIFIED** in the prior isolated run; browser rendering is **NOT VERIFIED**. |
| Student authentication and persisted flows | Phase 2.2D2 reports isolated API coverage for registration, login, identity, profile save/retrieval at all four stages, assessment APIs, recommendation/skill-gap/improvement-plan APIs, logout, and cross-account denial. | API behavior **VERIFIED** in that run; browser interaction is **NOT VERIFIED**. |
| Class 10 roadmap | The prior API response included a multi-stage roadmap. | API payload **VERIFIED**; rendering, expansion, and responsive interaction **NOT VERIFIED**. |
| Browser console, layout, keyboard, and usability | Browser automation could not establish the current URL and did not interact with the page. | **NOT VERIFIED**. |
| Admin authorization | Anonymous and student requests to 20 privileged route/method pairs were denied with 403 in Phase 2.2D2. | API denial **VERIFIED** for those tested requests; Admin success flows and UI **NOT VERIFIED**. |
| MySQL | The Phase 2.2E report records four passing dedicated integration tests from owner-provided terminal output and a separate passing post-test initialized-schema preflight. Neither was independently rerun during report editing. | Recorded integration evidence only; no Phase 2.2F database action is authorized by this plan. |
| Admin catalog and release operations | API contract describes protected Admin management. The architecture uses staged/versioned catalog handling; earlier reports identify publishing safety gates and unresolved coverage. | Successful Admin workflow and rollback **NOT VERIFIED**. |
| Production readiness | Existing reports state browser behavior and deployment are unverified. | **NOT VERIFIED**. |

The prior browser/API report describes a temporary SQLite runtime, copied catalogs, loopback-only Flask/Vite services, and cleanup. This is evidence of the prior run only; it is not an instruction to reuse a runtime directory or test account without recreating and verifying isolation.

## 2. Scope and prerequisites

### In scope

- Browser-based student registration, login/session behavior, all four education levels, academic and aptitude assessments, recommendations and roadmaps.
- Browser validation and access-denial behavior, cross-account privacy, console/network errors, responsive presentation, keyboard access, and basic usability.
- Supported Admin endpoints and UI: authorization, career/skill draft editing, validation, explicit publication, active release inspection, and recovery/rollback only where the isolated catalog release mechanism supports it.
- Comparison of observed results with `API_DOCUMENTATION.md`, `SRS_IMPLEMENTATION.md`, and `ARCHITECTURE.md`.

### Required isolation gates before execution

1. **Dedicated test runtime:** use a disposable database and unique test accounts. The preferred browser runtime is a newly verified temporary SQLite database, consistent with the prior D2 setup. MySQL browser testing is a separate opt-in run and must use only a freshly verified, owner-approved disposable schema such as the Phase 2.2E test target. Do not infer that the old schema is still empty or available. No MySQL connection is part of this planning task.
2. **Fail-closed target assertions:** before launching Flask, assert the selected database driver and exact database path/schema. Abort on an unexpected `DATABASE_URL`, MySQL target, SQLite path, or environment fallback. Keep the runtime bound to loopback and use the existing Vite proxy (`VITE_API_URL=/api`) only after confirming the current configuration.
3. **Isolated catalog state:** use disposable copies of canonical catalog files and separate temporary draft, release, pointer/manifest, and lock paths. Confirm the running process resolves all catalog and draft paths inside the disposable runtime. Never publish or restore against canonical/shared catalog paths. If current code cannot be redirected safely without a source/config change, block publish/restore testing.
4. **Admin identity:** do not assume one exists and do not bootstrap one during normal startup. Use an owner-provisioned, dedicated Admin identity in the isolated test database, or obtain separate explicit authorization to create one using the documented explicit setup route after its target preflight. Do not promote an existing student or use an existing production Admin account.
5. **Approval:** before any execution that creates records, the owner must approve the exact disposable runtime, permitted setup actions, test-account creation, catalog draft/publish/restore operations, and cleanup scope. The current request authorizes planning only.
6. **Browser tooling:** select a real browser automation path available in the environment (for example, an already installed Playwright setup or approved desktop browser control). Do not treat static HTML, an API client, or a screenshot/export as browser execution. If no browser automation is available, report browser cases blocked and keep API evidence separate.
7. **Baseline and cleanup:** record test-only database/table counts, temporary catalog hashes, release pointer/manifest state, and runtime paths before execution. Use unique `@example.test` identities. After the run, remove only records and files created by that run, after confirming their IDs/paths. Preserve artifacts needed for review in a sanitized report; never include tokens or passwords.

### Known documentation alignment issue

`API_DOCUMENTATION.md` and `SRS_IMPLEMENTATION.md` describe education catalog structures as normalized database records, while the Phase 2.1/2.2 architecture and reports designate version-controlled project files as the near-term canonical source for education/career/skill/qualification catalogs. Verify the actual runtime behavior without mutating either source, and record this documentation mismatch as an unresolved SRS/design alignment item unless a current approved decision has superseded it.

## 3. Browser student test matrix

All rows below are **PLANNED**, not executed by this phase. Run each with a fresh or explicitly reset test identity only in the approved isolated runtime.

| ID | Test | Procedure | Expected result / evidence |
|---|---|---|---|
| B-01 | Entry page and API connectivity | Open the Vite app in a real browser; capture console and network; load the assessment/profile route and education catalog. | App renders; requests target the isolated Flask API through the configured proxy; no uncaught JavaScript errors or unexpected external requests. Record URLs/statuses, sanitized console output, and screenshot. |
| B-02 | Registration | Register a unique test student using valid input, then inspect authenticated state. | Account is created once, user is a student, identity shown by the app matches `/auth/me`; no secrets in logs. Duplicate registration displays a useful validation message and does not create a second account. |
| B-03 | Login, refresh, and session | Log out/in, reload the page, open a protected page, and inspect session behavior. | Correct identity appears after authentication and reload; session is accepted while valid and protected resources remain inaccessible when anonymous. Token/session material is not exposed in UI or captured artifacts. |
| B-04 | Logout and revocation | Use the account menu to log out, then navigate/reload and request a protected page in the browser. | Menu and logout work; session is cleared/revoked; protected view redirects or shows the established unauthorized state. Capture post-logout API status and UI. |
| B-05 | Class 10 profile and dependent options | Select Class 10; inspect subjects/pathway options; change selections repeatedly and save a valid profile. | Only valid Class 10 values are offered/accepted; dependent values refresh; stale selections clear; saved values survive reload. |
| B-06 | Class 12 profile and dependent options | Repeat profile/catalog selection and persistence checks for Class 12. | Class 12 subjects and pathways are appropriate; invalid prior-stage selections are cleared/rejected; profile persists. |
| B-07 | Bachelor's profile and dependent options | Repeat for Bachelor's with degree, specialization, subjects, year/semester and performance scale. | Options match the selected level and degree; changing level/course invalidates dependent choices; profile persists. |
| B-08 | Master's profile and dependent options | Repeat for Master's and its degree/specialization/subjects. | Master's options are appropriate; invalid previous selections are cleared/rejected; profile persists. |
| B-09 | Academic assessment | Enter valid subject ratings for each applicable stage; include custom subject only where supported. | Only relevant subjects are submitted; displayed values match server response; unavailable values remain distinguishable from assessed zero; invalid ranges produce field-level feedback and no false success. |
| B-10 | Aptitude assessment | Start an attempt, answer all questions, submit, inspect score and domain breakdown, then try incomplete/duplicate submissions as appropriate. | Questions do not reveal keys before submission; server-scored total/domain values match submitted answers; incomplete/duplicate behavior follows API contract; unanswered or unavailable domains are not presented as zero. |
| B-11 | Interests and skills | Enter interest, technical, and employability ratings separately, including an assessed zero and an unassessed skill. | Interest remains distinct from proficiency; zero is retained as an assessed value; unassessed remains unavailable; saved profile reflects exact inputs. |
| B-12 | Recommendation and explanation | Submit the assessment, open recommendations and detail/explanation panels. | Results are recalculated from the current authenticated profile; rank and displayed scores are consistent; positive evidence, considerations, and practice opportunities reflect actual inputs; model-family contribution is described as experimental and not an individual career probability. |
| B-13 | Gaps and improvement plan | Open skill gaps and improvement plan for profiles with assessed skills, zero scores, missing ratings, and no defined requirement. | Gaps use only valid assessed values and defined requirements; zero is not confused with missing; missing requirements/data are reported as unavailable rather than fabricated; actions correspond to identified gaps. |
| B-14 | Class 10 pathways and roadmap | Use a profile with clear evidence and another with close/insufficient evidence; inspect primary, alternatives, compare-all, and each roadmap stage. | The guidance presents a defensible leader only when supported; otherwise communicates uncertainty. Roadmap is pathway-specific, progression stages are distinct, and requirements needing local confirmation are flagged. No invented admission guarantee or qualification requirement appears. |
| B-15 | Invalid profile and assessment input | Submit invalid stage/course pair, malformed scores, missing required fields, and invalid aptitude answers. | UI identifies the error; API returns documented 4xx response; no unhandled 500, false success, or partial unintended persistence. |
| B-16 | Anonymous access | Clear session and navigate directly to student profile, assessment history, recommendations, and Admin views. | Protected student resources require authentication; Admin resources remain forbidden; no other account data is rendered. |
| B-17 | Cross-account isolation | Create two unique test students; while authenticated as A, attempt to view B's profile/history using supported UI navigation/query parameters. | Ownership checks deny access; UI does not disclose B's records; verify the denial via network response and visible message. |
| B-18 | Responsive layout | Inspect key flows at narrow mobile, tablet, and desktop viewport sizes. | Navigation, form controls, result cards, comparison sections, and roadmap remain usable without clipped/overlapping essential content; capture viewport screenshots. |
| B-19 | Keyboard and basic accessibility | Navigate using keyboard only; test focus order, visible focus, labels, slider/select operation, disclosure controls, error association, and logout menu. | All primary actions are reachable and operable; focus is visible and logical; controls have accessible names; expanded/collapsed state is conveyed; errors are perceivable without relying only on color. Record any screen-reader checks separately if available. |
| B-20 | Basic usability and browser errors | Complete one representative end-to-end journey without developer tools, then review console/network logs. | Student can identify next actions and understand guidance as non-deterministic; no uncaught errors, failed essential assets, repeated request loops, or unexpected network calls. Any non-blocking warnings are documented. |

## 4. Admin workflow matrix

The API documentation lists user/role/status management; career create/edit/deactivate; skill and recommendation/model/dataset views; aptitude question CRUD/soft deactivation; errors and audit. Phase 2.2D2 directly tested denial for 20 privileged route/method pairs, including dashboard, users, career CRUD, drafts, publish, release list/restore, skills, models, recommendation/dataset, audit/error, and aptitude-question operations. Successful Admin behavior was not tested. The plan below focuses on currently described Admin functionality; route availability and names must be confirmed against the running code/API documentation before execution.

| ID | Test | Procedure | Expected result / safety condition |
|---|---|---|---|
| A-01 | Anonymous/student denial | Attempt Admin dashboard, user, career/skill, draft, publish, release, restore/discard, aptitude, metrics, and audit operations as anonymous and as student. | Server denies each privileged operation before mutation; no draft, catalog, release pointer, account, or audit state changes. Repeat only with disposable runtime. |
| A-02 | Active Admin authentication | Sign in as dedicated isolated active Admin; inspect identity, navigation, dashboard, and logout. | Admin role is verified server-side; Admin UI appears only for Admin; dashboard data comes from isolated runtime; logout revokes access. |
| A-03 | Admin dashboard/read-only views | Review counts, users, skills, recommendation/system statistics, model metrics, datasets, errors, and audit history where exposed. | Views load with documented data and do not mutate catalogs or student records. Synthetic model metrics remain clearly labeled experimental. |
| A-04 | Career draft create/edit | Create a disposable draft, edit fields/requirements, then reload/reopen it. | Draft is isolated to the test runtime; stable IDs and expected fields are preserved; edits persist as drafts and do not affect active recommendations. |
| A-05 | Skill draft/edit | Edit skill requirements through the supported Admin workflow. | Required skill references validate; null/unassessed student values are not converted to zero; no active catalog changes before publication. |
| A-06 | Invalid draft validation | Attempt missing fields, duplicate IDs, invalid scores/references, malformed catalog data, and stale fingerprint. | Validation rejects each invalid/stale draft with actionable errors; active release remains unchanged; failed actions are accurately audited where applicable. |
| A-07 | Explicit publish in isolated catalog | After valid draft validation and separate execution approval, publish only into the disposable copied catalog/release paths. | A single validated release becomes active; readers load CSV/JSON from the same release; active pointer, release hash, and recommendation read are consistent. No canonical/shared file is touched. |
| A-08 | Publish failure and retry | In isolated tests, inject failures before/after pointer activation and inspect response, active state, draft state, and audit warning. | Response distinguishes not committed, committed with uncertain durability, and indeterminate state; retry does not duplicate or misrepresent an already-active release. |
| A-09 | Release list and active verification | List releases and inspect the active release using Admin UI/API. | Only releases from the isolated runtime are listed; active identity/hash matches the manifest and both catalog files. |
| A-10 | Restore/rollback | Restore a prior known-good test release only in the disposable catalog, then restart/reload the process and re-read recommendations. | Previous validated release becomes active consistently; failed audit insertion is reported without falsely claiming restore failed; restart retains the selected release. |
| A-11 | Discard draft | Discard a disposable draft and verify it is no longer actionable while active release is unchanged. | Only the test draft is discarded; active pointer/files remain unchanged; audit outcome matches the actual operation. |
| A-12 | Admin ownership/concurrency | Use two Admin sessions/processes if the implementation supports them to create stale drafts and race publish/update requests. | Stale snapshots are rejected; cross-process coordination prevents lost updates; concurrent outcomes and audit entries correspond to actual committed state. If multi-process safety is not demonstrated, mark **BLOCKED/NOT VERIFIED**, not passed. |

### Admin execution gate

No Admin account is presumed to exist. Preferred method is an owner-provisioned, dedicated Admin in the disposable test database. If explicit bootstrap is needed, require separate approval for the exact isolated target and command, then run only after its fail-closed preflight. Never create an Admin implicitly, use production credentials, change a student's role, or bootstrap against the existing `careerpath` database. Admin publish/restore tests require separate explicit approval even after an isolated Admin account exists, because they modify release state.

## 5. Isolation and cleanup plan

1. Create a fresh runtime folder with a unique run identifier. Use a disposable database path/schema, copied canonical catalogs, and separate draft/release/pointer/lock paths. Capture baseline hashes and counts.
2. Before backend startup, validate the resolved database target and all catalog/draft/release paths at the actual runtime boundary. Abort on any path outside the approved temporary root or any DB target mismatch. Do not weaken checks to make startup succeed.
3. Start Flask and Vite bound to loopback only. Preserve normal authentication and role checks. Configure the existing API proxy only after confirming current Vite config and runtime ports.
4. Use unique test-only student identities and a dedicated test Admin. Do not import real student data. Never print passwords, tokens, session values, or `.env` contents.
5. Avoid any catalog publish/restore until a valid disposable release setup is proven and separately approved. Never edit canonical catalog contents or the active release used by ordinary development.
6. At completion, stop services, verify target identities again, enumerate only test IDs created in this run, and remove only those test records and the unique temporary runtime. If target identity is uncertain or cleanup could touch non-test data, stop and report; do not run broad cleanup.
7. Keep sanitized logs, screenshots, response status summaries, hashes, and cleanup evidence. Redact personal data and all credentials/tokens.

## 6. Evidence to collect

- Run identifier, timestamp, OS/browser/version, viewport sizes, application commit/worktree state, and exact start/test commands.
- Backend DB driver and resolved disposable target (schema/path only); path containment assertions; catalog copy hashes and active pointer/release identity before and after.
- Browser console errors/warnings, network request method/path/status, screenshots for each viewport and critical interaction, and accessibility/keyboard observations.
- Test account roles/opaque test IDs (not passwords/tokens), UI outcome, corresponding API status, persistence checks, and cleanup results.
- For recommendations: submitted input fixture, returned ranking/score components, explainability/gap/roadmap payloads, and whether experimental ML labeling is visible. Use synthetic test profiles, never represent them as real students.
- For Admin: authorization response, draft ID, validation result, release/manifest hashes, audit outcome, active release before/after, and failure-injection results where supported.
- Explicitly separate API tests, browser tests, MySQL integration tests, and static/document review. Do not count a previous report's evidence as a new execution.

## 7. Risks and blockers

- Current Phase 2.2D2 browser automation did not reach page interaction, so frontend rendering, browser console, responsive behavior, keyboard accessibility, and complete saved-profile UI flow remain unverified.
- Active Admin credentials/account are not established. Admin success paths remain blocked until an isolated Admin identity is safely available.
- Publishing/restore mutates catalog release state. It is blocked unless every pointer, release, draft, and lock path can be isolated and the owner separately approves these operations.
- Cross-process race behavior and crash/durability guarantees should not be inferred from single-process/API tests. Verify only what the implementation and failure-injection tests demonstrate.
- The previous MySQL run evidence is owner-provided and scope-limited; it does not prove browser behavior, all SRS requirements, MySQL parity for untested flows, or deployment readiness.
- The API/SRS documentation's normalized-catalog wording conflicts with the documented file-backed canonical catalog decision. Resolve documentation/source-of-truth alignment in a separate approved task; do not migrate catalogs during verification.
- Original standalone SRS/System Design source files were not present in the Phase 2.2D2 inspection; compliance comparison is limited to repository documents unless those source documents are provided.

## 8. Acceptance criteria and go/no-go

### Student browser acceptance

- Registration/login/identity/logout works in the browser and API; session invalidation is demonstrated after logout.
- All four education levels load appropriate options, persist profiles, and refresh dependent fields without stale values.
- Academic, interest, technical, employability, and aptitude inputs retain the distinction between zero and unavailable data.
- Recommendation rankings, explanations, skill gaps, improvement plans, and Class 10 roadmap are consistent with submitted inputs and server responses.
- Invalid inputs, anonymous access, and cross-account requests are denied safely without leaking another student's data or returning an unhandled error.
- No blocking console/network errors; responsive and keyboard checks meet the stated basic criteria or have documented defects.

### Admin acceptance

- Anonymous/student denial is demonstrated for every privileged route in scope, with no state changes.
- Dedicated active Admin can use supported read/edit flows in the isolated environment.
- Invalid/stale drafts cannot be published; valid publishing uses a consistent validated release; release verification and rollback work only in isolated release storage.
- Audit outcomes and publish/restore responses match committed state. Concurrency is accepted only if cross-process coordination is evidenced; otherwise the criterion remains open.

### Go/no-go

Execution is **NO-GO** until the owner approves the disposable runtime and data creation/cleanup scope, target and path checks are proven at runtime, and a dedicated Admin identity is available if Admin success testing is expected. Admin publication/restore remains individually gated by separate approval. A future pass may be marked complete only for test cases actually executed with evidence. It must not declare production readiness from local browser/API/MySQL checks alone.

## 9. Planned versus executed status

| Category | Status at time this plan was created |
|---|---|
| Review of prior browser/API and MySQL reports and repository API/SRS/architecture docs | **EXECUTED** — read-only document review for this plan. |
| Phase 2.2D2 isolated API workflows and selected tests | **PASSED AS RECORDED IN PRIOR REPORT** — not rerun for Phase 2.2F. |
| Phase 2.2E four MySQL integration tests | **REPORTED PASSED BY OWNER-PROVIDED TERMINAL OUTPUT** — not independently rerun for Phase 2.2F. |
| Phase 2.2E post-test MySQL preflight | **REPORTED PASSED BY OWNER-PROVIDED TERMINAL OUTPUT** — distinct from the four-test output and not independently rerun for Phase 2.2F. |
| Real browser student journeys | **PLANNED / NOT EXECUTED**. |
| Browser console, responsive, keyboard, accessibility, and usability checks | **PLANNED / NOT EXECUTED**. |
| Successful active-Admin UI/API workflows | **PLANNED / BLOCKED** pending isolated Admin identity and approval. |
| Publish/restore/rollback in an isolated catalog release | **PLANNED / BLOCKED** pending path-isolation proof and separate approval. |
| MySQL checks within this Phase 2.2F planning task | **NOT EXECUTED**; no connection or database command is part of this plan. |
| Production deployment/readiness | **NOT VERIFIED**. |
