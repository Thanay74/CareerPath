# CareerPath Phase 2.2F — Prerequisite Readiness Assessment

**Assessment date:** 2026-10-22  
**Mode:** Static inspection and planning only. Flask/Vite were not started; no browser was opened; no database was contacted; no tests, account provisioning, catalog edits, publish, restore, or configuration changes were performed.

## Summary

| Prerequisite | Status | Finding |
|---|---|---|
| Browser automation capability available | **PASS** (tool available); **NOT VERIFIED** (usable browser session) | The CUA browser-control tool is available to this task. The prior Phase 2.2D2 attempt could not establish the active browser URL, and no browser was opened in this assessment. |
| Database target can be selected for isolated runtime | **PASS, conditional** | `backend/app.py` resolves `DATABASE_URL` or `CAREERPATH_DB`; without either it defaults to project-root `careerpath.sqlite3`. A launcher can set an isolated target before importing the app, but the target must be asserted at runtime. |
| Catalog, release, pointer, and lock paths can be isolated without source edits | **PASS, via temporary launcher only** | These are module-level Python path constants, not environment overrides. The D2 report records that a temporary launcher redirected them and used copied catalogs. Repeat and assert every resolved path before future execution. |
| Admin draft directory and lock can be isolated without source edits | **PASS, via temporary launcher only** | `backend/app.py` defines mutable `CAREER_DRAFT_DIR`; its lock path derives from that directory. D2 records a previous temporary redirection. |
| Dedicated isolated Admin identity available | **BLOCKED** | No Admin account is established for a future runtime. `backend/setup.py` offers explicit `--bootstrap-admin`, but that is a database write and requires a separately approved isolated target and provisioning action. |
| Publish/restore isolation ready for execution | **BLOCKED pending run-specific proof and approval** | Code permits path redirection through module globals, but the current active catalog/release state must be copied and redirected in a fresh launcher; publish/restore also needs separate owner approval. |
| Runtime/browser behavior verified by this assessment | **NOT VERIFIED** | This was static inspection only. |

## Browser automation availability

The current tool inventory exposes `mcp__cua_repl` for computer/browser control. This satisfies availability of a browser-control capability, but it does not demonstrate that a specific browser is open, that a usable tab/session is available, or that the tool can inspect this application's live page. The Phase 2.2D2 report says its browser-control attempt stopped because it could not determine the current URL with sufficient confidence. Therefore a future run must first establish the browser/session and application URL through the approved control path; if that fails, browser cases remain **BLOCKED** and must not be represented as passed. No browser-control call was made for this static assessment.

The frontend package lists React/Vite and Node's built-in test runner (`frontend/package.json`); no Playwright, Puppeteer, or Cypress dependency is listed there. This does not rule out desktop/browser tooling outside the project dependency set.

## Static path and configuration trace

### Database selection

- `backend/app.py`: `DATABASE_URL` is read from the environment after dotenv loading. `resolve_database_target(...)` receives it with `CAREERPATH_DB` and `allow_default=True`; resolved values populate `DATABASE_TARGET`, `DB_PATH`, and `USE_MYSQL`.
- `backend/database_config.py::resolve_database_target`: an empty URL selects `CAREERPATH_DB`, otherwise the project-root `careerpath.sqlite3` default when allowed. A configured MySQL URL selects its parsed host, port, and schema. Unsupported or malformed schemes raise `DatabaseTargetError`.
- `backend/app.py::connect_db`: uses the resolved MySQL URL when `USE_MYSQL` is true, otherwise connects to `DB_PATH` using SQLite. This makes pre-import environment configuration plus an assertion of actual `DATABASE_TARGET`/`DB_PATH`/`USE_MYSQL` essential. Merely setting an environment variable in a shell is not sufficient evidence of the connection target.
- `tests/mysql_integration/harness.py` has its own fail-closed MySQL target resolution for the Phase 2.2E integration harness. It does not provide a browser runtime and should not be reused to initialize or write a database without the separate approvals and harness preflight defined for that task.

### Catalog, release, pointer, and lock selection

- `backend/services/recommendation_engine.py`: `KB` and `METADATA` are assigned to `data/career_knowledge_base.csv` and `data/career_metadata.json` relative to the project root.
- `backend/services/catalog_releases.py`: `RELEASES_DIR`, `ACTIVE_MANIFEST`, `MANAGED_MARKER`, and `ACTIVATION_LOCK` are assigned to `data/career_releases/`, `data/career_active.json`, `data/career_catalog_managed.json`, and `data/career_catalog_activation.lock`.
- `backend/services/recommendation_engine.py::careers` and its metadata reader call `load_active_catalog(KB, METADATA)`; the catalog release reader selects the active pair using the manifest/marker and release directory. Consequently redirecting only the CSV/JSON paths would be insufficient: both the recommendation module paths and all release module paths must point within the disposable runtime.
- These are mutable module globals, not environment-driven settings. They can be redirected by a dedicated temporary launcher after imports and before request handling, without editing tracked application source. The report `docs/phase2_2d2_browser_api_verification.md` records a prior isolated launcher that copied the career CSV/metadata and redirected the release pointer, managed marker, release directory, activation lock, and draft directory. This is historical report evidence, not a fresh verification of the current path state.
- `backend/app.py::CAREER_DRAFT_DIR` is `ROOT/instance/career_drafts`; `backend/app.py::_career_draft_lock_path` derives `catalog.lock` from it. A future launcher must redirect this global before serving requests and verify the resulting directory/lock are under the temporary root.

### Can all paths be redirected without source changes?

**Assessment: PASS, using a temporary launcher and run-time assertions; no built-in configuration switch exists for the catalog/draft paths.** The prior D2 report documents an actual temporary launcher that redirected these module globals and used copied catalog files. A future Phase 2.2F run can follow that pattern without changing application source, provided the launcher is recreated inside the disposable runtime and verifies before server startup that:

1. `DATABASE_URL` is empty for SQLite mode, `USE_MYSQL` is false, and `DB_PATH` resolves exactly to the approved temporary database; or, for a separately approved MySQL run, the exact schema/account/host are independently preflighted.
2. Recommendation `KB` and `METADATA`, release module active manifest, managed marker, releases directory, and activation lock, plus app `CAREER_DRAFT_DIR` and derived draft lock, all resolve beneath the approved temporary root.
3. Catalog source files are copied into that root and baseline hashes are recorded; no global/canonical path remains selected by the running process.
4. Assertions are checked at the actual imported module/runtime boundary before serving. Abort if any module path is missing, points outside the root, or is inconsistent with another catalog reader.

Because the necessary launcher from the D2 run was temporary and was removed with its runtime, its specific implementation is not presently available as a reusable checked-in harness according to the reviewed report. The isolation pattern is supported by the recorded prior execution and static mutable globals, but a fresh run's path containment remains **NOT VERIFIED until its launcher performs and records these assertions**.

## Dedicated isolated Admin identity

`API_DOCUMENTATION.md` states that Admin login uses the regular `/login` route and describes setting `ADMIN_EMAIL` and a 12-character-or-longer `ADMIN_PASSWORD`. `SETUP_GUIDE.md` says the first administrator is created only through the explicit, target-confirmed setup workflow and that normal startup does not bootstrap an Admin. In code:

- `backend/setup.py::main` exposes `--bootstrap-admin`, validates and prints a credential-free target identity for mutating setup actions, and dispatches to `application.bootstrap_admin()` only for that explicit flag.
- `backend/app.py::bootstrap_admin` reads `ADMIN_EMAIL` and `ADMIN_PASSWORD`, checks for an existing account with that email, and inserts an Admin account if absent. This writes to whichever database `application.connect_db()` resolves; it is not suitable for an unverified or shared target.
- `backend/app.py::admin_required`/`admin_authorized` enforce authenticated active Admin role on protected endpoints.

**Safe requirement for execution:** use a dedicated Admin account in the same disposable browser-test database. Prefer owner provisioning specifically for that isolated database. If explicit bootstrap is needed instead, obtain separate owner approval for the exact target and one-time bootstrap operation, configure credentials through an untracked secret source/environment, verify the resolved target at the connection boundary, and invoke only the target-confirmed setup action. Never use MySQL root, a production Admin, a student role-promotion path, or implicit startup bootstrap. No Admin identity was created or checked in this assessment.

## Readiness decisions

| Item | Status | Evidence / next gate |
|---|---|---|
| Browser-control tool exists | **PASS** | `mcp__cua_repl` is available. Successful control of the application browser is not verified. |
| Project includes a dedicated browser automation test dependency | **NOT VERIFIED** | `frontend/package.json` does not list Playwright/Puppeteer/Cypress; desktop control is available outside project dependencies. Choose and validate an approved browser path before execution. |
| Isolated SQLite can be selected without source edits | **PASS, conditional** | `CAREERPATH_DB` is supported; set before import, verify `DB_PATH`, `DATABASE_TARGET`, and `USE_MYSQL` in the actual launcher. |
| Canonical catalogs/release/pointer/lock can be redirected without source edits | **PASS, conditional** | Module globals permit temporary launcher redirection and D2 reports a prior successful setup. Repeat all containment assertions; no environment overrides exist. |
| Admin drafts/lock can be redirected without source edits | **PASS, conditional** | Redirect `backend.app.CAREER_DRAFT_DIR`; derived lock follows it. Verify at runtime. |
| Disposable Admin account ready | **BLOCKED** | Owner must provide one for the isolated DB or separately authorize explicit target-checked bootstrap. |
| Career publish/restore testing approved | **BLOCKED** | Requires separate approval plus copy-only release/pointer/draft/lock paths and proof of path containment. |
| Browser E2E or runtime isolation passed in this assessment | **NOT VERIFIED** | No application/browser/database commands were run. |

## Safety and limits

- This assessment did not start Flask or Vite, open/control a browser, connect to a database, create accounts, run tests, alter environment/configuration, or modify catalog/release files.
- It did not independently verify the Phase 2.2D2 or Phase 2.2E reported results; those remain attributed to their reports and owner-supplied terminal evidence as documented there.
- MySQL use for Phase 2.2F is not required for the first browser pass if an isolated SQLite runtime is approved. If MySQL is chosen, it requires a new explicit approval and exact target preflight; prior Phase 2.2E evidence does not authorize reuse for browser tests.
- No claim is made about actual browser behavior, application startup, database state, current account availability, catalog health, publish/restore behavior, or production readiness.
