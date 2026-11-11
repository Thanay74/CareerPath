# CareerPath Phase 2.1 — Final Read-Only Acceptance Audit

**Audit date:** 2026-10-22  
**Scope:** Acceptance review of the five Phase 2.1 reports and current implementation. No source fixes were made.

## Executive decision

**Recommendation: do not close Phase 2.1 yet.** The principal setup-target, legacy-schema, release-pair, and concurrency safeguards are present, and the isolated backend and frontend test suites pass. Two publication-state issues still need a small follow-up: an error after the active pointer replacement can be reported as if the previous release stayed active, and a restore can commit before its audit write fails. The sandboxed production build also remains unverified here because Vite again failed with the documented filesystem `EPERM`; the earlier build-recovery report records a successful build outside the sandbox.

No live MySQL connection, migration, seed, admin publication, canonical catalog write, or student-data write was performed during this audit.

## Findings ranked by severity

### Medium — Post-switch durability error can be reported as an unsuccessful activation

**Status: confirmed by code; filesystem-failure occurrence unverified.** In `backend/services/catalog_releases.py::_atomic_replace_manifest` (lines 231–245), `os.replace(staging, pointer)` changes the active manifest before `_fsync_directory(pointer.parent)` runs. If the directory flush raises, the helper raises even though the new pointer may already be active. `backend/app.py::admin_publish_career_draft` (lines 737–745) catches `OSError` and responds that “the prior pointer remains authoritative,” which is not guaranteed after replacement. The draft also remains, so the caller can see a failed request while the release is active.

**Smallest corrective task:** distinguish pre-replacement failure from post-replacement durability uncertainty by rereading and validating the selected pointer/release; return a response that reports committed versus uncertain state and make draft completion/retry behavior reconcilable. Add failure injection specifically at directory fsync after pointer replacement.

### Medium — Restore can activate a release and then return an unhandled audit failure

**Status: confirmed by code; database failure behavior untested.** `backend/app.py::admin_restore_career_release` (lines 755–770) atomically restores the selected release, then calls `record_admin_action` outside the `try` block. If the audit insert fails, the request can error although the active pointer has already changed. This has the same state-versus-response ambiguity that the publish endpoint explicitly handles with `audit_warning`.

**Smallest corrective task:** make restore report the committed release and an explicit audit warning (or add a durable reconciliation mechanism); add an isolated test that injects audit failure after activation.

### Low — Authorization is enforced in code, but the route-by-route denial matrix is not tested

**Status: code inspection confirms guards; comprehensive test coverage is absent.** Career list, stage/create/edit/deactivate, draft list/publish/discard, release list/restore handlers all invoke `admin_required()` (`backend/app.py`, functions `admin_careers`, `admin_update_career`, `admin_create_career`, `admin_delete_career`, `admin_career_drafts`, `admin_publish_career_draft`, `admin_career_releases`, `admin_restore_career_release`, and `admin_discard_career_draft`, lines 647–887). Draft IDs are restricted by `_career_draft_path` to 24 lowercase hexadecimal characters. Existing `tests/test_api.py::test_admin_endpoints_require_admin_role_and_return_model_stats` checks a student denial for the dashboard, not every career route, and does not individually exercise missing/invalid credentials against each privileged endpoint.

**Smallest corrective task:** add a parameterized route authorization test for each listed endpoint, with unauthenticated, student, inactive-admin, and valid-admin cases as applicable. No route path currently accepts a request-supplied filesystem path.

### Low — Structural catalog validator does not validate every semantic relationship

**Status: confirmed gap; impact on current catalog unverified.** `backend/catalog_validation.py::validate_career_records` validates required fields, career IDs/names, score-map syntax/ranges, stream references, metadata IDs, and selected metadata types. It does not validate every token in `required_subjects` or `recommended_degrees` against an education catalog, and score-map keys are not checked against an authoritative skill-ID registry. This is consistent with the broader Phase 2.1 plan to leave catalog ownership in files, but “complete semantic validation” would be a stronger claim than the implementation supports.

**Smallest corrective task:** define an approved reference vocabulary and validation policy for these fields before adding checks; do not infer or rewrite existing catalog values during that change.

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| Mutating setup rejects missing, malformed, unsupported, ambiguous, and production targets before connection/DDL | **PASS (isolated tests)** | `backend/setup.py::main` resolves and validates before calling schema/seed/bootstrap operations; `tests/test_setup_safety.py` verifies unsafe target cases return before `init_db`. Current test run included these tests. No setup command was executed. |
| Legacy assessment schema is rejected before schema mutation | **PASS for SQLite fixture; MySQL unverified** | `backend/app.py::init_db` checks for `assessment_type` before DDL in both branches (lines 114–164); the SQLite fixture asserts the legacy table is unchanged (`tests/test_legacy_schema_guard.py`). MySQL metadata/DDL behavior was not exercised. The unreachable-after-guard legacy rename code remains in the function and should not be treated as a completed migration. |
| Recommendation reads use one validated CSV/JSON release | **PASS for file-backed isolated tests** | `recommendation_engine.recommend` wraps the full ranking flow in `catalog_read_context`; `load_active_catalog` selects the manifest release and validates exact release metadata, hashes, fingerprint, and catalog structure. Test `test_recommendation_read_context_pins_csv_and_metadata_to_one_release` verifies snapshot pinning across activation. Before first release activation, the validated legacy file pair remains the bootstrap source. |
| Malformed/incomplete manifests and corrupted releases fail closed | **PASS (isolated tests)** | `tests/test_catalog_releases.py`: malformed pointer/incomplete release, corrupted file, malformed release manifest, missing pointer after managed mode. Readers do not fall back to a mixed pair after managed activation. |
| Stale-draft checks, release activation lock, rollback, and restart/reload | **PASS within tested file-system/process scope** | `publish_catalog` and `restore_release` use the OS-backed lock and compare active fingerprint under lock. Tests cover stale writes, concurrent process activation, rollback, reload in a fresh process, and injected interruption around pointer switching. Power-loss/storage durability is not established. |
| Failed activation always leaves old release active and API accurately describes state | **FAIL** | Pre-activation and pointer-replace failures preserve old pointer in tests. However, a directory-fsync failure after successful `os.replace` can raise after the pointer changed; the API's error text says the old pointer remains authoritative. No test injects this post-replacement failure. |
| Admin career CRUD, draft, publish, release-list, restore, and discard are server-side protected | **PASS by code inspection; route matrix partially tested** | Each handler calls `admin_required()`; identity must match active DB user with role `admin`. The draft path derives only from validated hex ID. Positive/negative tests cover some admin operations, but not the full route matrix (Low finding above). |
| Admin edit is staged and invalid drafts are rejected before activation | **PASS (isolated SQLite/temp catalog tests)** | CRUD routes stage validated snapshots; publish revalidates; `test_invalid_staged_catalog_cannot_be_published`, `test_admin_can_edit_career_and_skill_criteria_in_knowledge_base`, and stale/duplicate tests. Tests patch catalogs and release paths into temporary directories. |
| Education, pathway, roadmap, and recommendation behavior remain covered | **PASS for automated isolated coverage; runtime/MySQL unverified** | Existing API/recommendation tests cover the education catalog, level-specific profile validation, all four level scenarios, Class 10 roadmap stages, missing routes, evidence classification, ranking, and skill-gap availability (`tests/test_api.py`, `tests/test_recommendation_engine.py`, `tests/test_career_ml.py`). No live browser or MySQL workflow was performed in this audit. |
| Isolated backend tests | **PASS** | `python -m unittest discover -s tests` with `DATABASE_URL=''`, `TEMP`/`TMP` directed under `.test-tmp\phase2_1_acceptance`: **58 tests passed, 0 failed** (39.428 seconds). |
| Frontend tests | **PASS** | `npm test` in `frontend`: **7 passed, 0 failed**. |
| Frontend production build in sandbox | **UNVERIFIED / blocked** | `npm run build -- --outDir ..\.test-tmp\phase2_1_acceptance\vite-dist --emptyOutDir` failed with Vite `EPERM` at `realpath(frontend/src/main.jsx)`. The prior build-recovery report records this same sandbox failure and a successful build outside the workspace sandbox (30 modules). That earlier result is not a build pass in this sandboxed audit run. |
| MySQL integration, schema migration, and startup against MySQL | **UNVERIFIED** | No MySQL connection, schema/seed command, migration, or live application verification was attempted, as required by scope. |

## Detailed implementation review

### Setup and schema guard

`backend/database_config.py::resolve_database_target` accepts only MySQL/PyMySQL and local SQLite forms, rejects malformed or unsupported schemes, and creates a credential-free identity. `validate_setup_target` blocks the exact `careerpath` database/file stem and requires exact confirmation; non-test targets require the explicit allow flag. `backend/setup.py::main` performs those checks before dispatching mutating setup functions and displays driver, host, and database only. No connection was opened by the audit tests for rejected setup targets.

Normal import does not initialize the database. `tests/test_startup_safety.py` launches an isolated subprocess with SQLite connection patched to fail and verifies importing `backend.app` neither creates its configured temporary DB nor imports the aptitude fixture. This test supports import isolation; it does not establish MySQL server startup behavior.

`init_db` first queries the existing assessment shape and raises before DDL for the legacy shape. The later `RENAME TABLE assessments TO assessments_legacy_json` statement remains in source but is guarded by that early check. No safe migration for that legacy schema has been demonstrated; keep it blocked pending a separately reviewed migration and rollback exercise on an isolated MySQL clone.

### Catalog release path and failure behavior

`backend/services/catalog_releases.py` reads the active pointer, rejects malformed/extra manifest keys, validates the release ID, reads both files from one immutable release directory, verifies release-manifest hashes and the content-derived release ID, and passes the pair through catalog validation. The recommendation engine pins one snapshot for a recommendation call. Releases are written to a staging directory, flushed, validated, renamed to a content-addressed destination, and activated through a temporary manifest plus `os.replace`.

The test suite exercises malformed and missing data, hash mismatch, stale fingerprints, concurrent activation across processes, rollback, and reload after an injected interruption. These tests establish application-level behavior on the test filesystem. They do not establish power-loss durability, storage-controller behavior, or cross-platform filesystem semantics. Also, the “last known-good” record is retained but no automatic recovery occurs if the active manifest itself is corrupted; readers fail closed and an administrator must explicitly restore a validated release.

Drafts are shared in the application draft directory rather than owned by a specific administrator. This was previously identified as a medium concern in `phase2_1_safety_review.md`; the present request's listed criteria do not require per-admin ownership, but it remains a governance limitation. Audit records are also not transactionally coupled to file activation. Publish surfaces an audit warning after activation; restore currently does not (Medium finding above).

### Recommendation and Admin UI compatibility

The Class 10 recommendation branch still evaluates configured school pathways, sorts using the pathway summary, returns all configured pathways for comparison, and builds a roadmap from the selected pathway and maintained education/career records. The roadmap distinguishes the immediate post-Class 10 route, Class 11–12/equivalent, post-Class 12 program options, and longer-term career directions. Other levels continue through the career catalog ranking branch. Admin career changes remain staged until publication; the Admin UI includes release listing and restore controls. Automated coverage exists for core scoring/roadmap and API staging behavior.

This audit did not launch the running React/Flask application in a browser. Thus UI-level admin authentication, clicking release controls, or live browser-to-API behavior is not claimed as runtime-verified here.

## Report claims stronger than evidence

1. The build-recovery report's statement that “a failed activation leaves the previous release active” is too broad. It is supported for failures before replacement and for a failed `os.replace`, but not for an error in the directory fsync after replacement. The API response currently overstates the old-pointer guarantee in that case.
2. “Crash-safe” in the module docstring and descriptions of crash recovery should be read as atomic pointer selection plus process-reload behavior, not power-loss durability. The reports acknowledge power-loss/storage durability as unverified; retain that qualification.
3. The setup guard is proven by isolated tests for the supported cases, but MySQL DDL/metadata behavior and MySQL integration are not established. Reports that label the legacy guard “fixed” are accurate only as a fail-closed code path, not as a completed legacy migration.
4. Route guards are present, but tests do not establish a complete unauthorized-user matrix for every Admin career endpoint.

## Tests run in this audit

- Backend: `python -m unittest discover -s tests` — **58 passed, 0 failed**. Environment explicitly set `DATABASE_URL=''`; `TEMP` and `TMP` pointed into `.test-tmp\phase2_1_acceptance`. API fixtures used temporary SQLite databases and copied catalog/release paths. This is not MySQL integration.
- Frontend: `npm test` — **7 passed, 0 failed**.
- Sandboxed production build: `npm run build -- --outDir ..\.test-tmp\phase2_1_acceptance\vite-dist --emptyOutDir` — **failed**, Vite `EPERM` resolving `frontend/src/main.jsx`, matching the previously documented sandbox issue. No source workaround was attempted.
- The previous `phase2_1_build_recovery_and_catalog_release_report.md` records a production build outside the sandbox as passed (30 modules transformed); that result is noted but not repeated here.

## Remaining risks and blocked checks

- MySQL startup, schema setup, the legacy guard against MySQL metadata, and MySQL migrations remain unverified. No live MySQL access was used.
- Power-loss and filesystem crash durability remain unverified. Only injected exceptions, atomic-pointer behavior, and a fresh spawned-process reload were tested.
- Build is blocked inside this sandbox by filesystem `EPERM`; a previously documented outside-sandbox build passed.
- Admin route-by-route authorization tests and post-activation audit-failure tests are missing.
- The current active release pointer is fail-closed when malformed/missing; recovery is an explicit Admin restore, not automatic.

## Recommended follow-up order

1. Correct publish response/state handling for errors after pointer replacement and add a post-switch fsync failure test.
2. Make restore audit failure explicit without obscuring that the release was already activated; add an injected audit-failure API test.
3. Add an authorization matrix for every Admin career/draft/release endpoint.
4. Before any MySQL migration verification, provision an approved isolated MySQL schema and run the reviewed migration-preservation procedure there. Do not use the live `careerpath` schema.
5. Repeat the frontend production build in a permitted environment, retaining the sandbox failure as environment evidence.

## Safety confirmation

This was a read-only acceptance audit except for creating this report and running isolated tests. No live MySQL connection or write, migration, seed, administrative publish, canonical catalog write, model-artifact write, credential change, or student-data write occurred. Backend test database and catalog/release/draft files were confined to temporary test locations and removed by test cleanup; the temporary build output target was separate from `frontend/dist`.

---

## Dated follow-up — Final Corrective Pass (2026-10-22)

The following results supersede the two Medium publication-state findings and the incomplete authorization-test coverage above for the corrective changes. The earlier findings remain in place as the historical audit record.

### Corrective tasks and results

1. **Publish activation state — PASS in isolated failure-injection tests.** `backend/services/catalog_releases.py::_atomic_replace_manifest` now records whether `os.replace` completed and raises a typed failure without claiming the prior pointer is still active. Publish and restore flows reread and validate the selected release after activation errors. They classify the outcome as `committed`, `not_committed`, or `indeterminate`. The publish API returns a committed result with a durability warning if the new release is active but post-replacement directory fsync failed. It removes the draft on a verified commit; it retains the draft for not-committed/indeterminate outcomes. A retry after a committed switch is prevented from activating stale content because the draft base fingerprint no longer matches.

   Tests cover directory-fsync failure after pointer replacement (verified committed), pointer replacement failure (verified not committed), and inability to verify final state (indeterminate). Existing interruption/reload coverage was updated to assert a verified committed state.

2. **Restore audit failure — PASS in an isolated API test.** `admin_restore_career_release` now returns `restored: true` and `activation_status: committed` with an `audit_warning` if activation succeeds but audit recording fails. The test confirms the manifest points at the restored release and the recommendation catalog reads the restored content after the injected audit exception.

3. **Admin authorization matrix — PASS in isolated API tests.** Added a route matrix for career list, edit, create, deactivate, draft list, publish, release list, restore, and discard. Anonymous, student, and inactive-admin requests return 403. The matrix snapshots canonical copied catalog files, the active pointer, release files, drafts, and `admin_audit_logs`; denied requests leave those unchanged. A separate valid-active-admin test exercises all nine endpoints with success responses against temporary SQLite/catalog/release data.

   The Flask `after_request` handler continues to record denied 4xx requests in the general `application_errors` observability table. The matrix verifies that denied requests do not create Admin audit events or alter catalog, release, or draft state.

### Files changed

- `backend/services/catalog_releases.py` — typed activation failures and post-error active-release verification for publish and restore, including post-switch reread errors.
- `backend/app.py` — truthful publish/restore outcomes, durability warnings, safe draft cleanup on verified commit, and explicit restore audit warnings.
- `tests/test_catalog_releases.py` — fsync-after-switch, pointer-replacement failure, and indeterminate-state tests; updated interruption and pre-activation assertions.
- `tests/test_api.py` — Admin authorization matrix, valid-admin route coverage, committed publish after fsync warning, and restore audit failure coverage.
- `docs/phase2_1_final_acceptance_audit.md` — this dated follow-up.

### Verification in the corrective pass

- Focused backend run: `python -m unittest tests.test_catalog_releases tests.test_api` with `DATABASE_URL=''` and `TEMP`, `TMP`, and `TMPDIR` set to `.test-tmp\phase2_1_corrective` — **32 tests passed, 0 failed**. An initial run used the sandbox's host temp path and failed during fixture copy with `PermissionError`; it did not reach the changed tests. The rerun used the project-local temporary directory.
- Full backend run: `python -m unittest discover -s tests` with `DATABASE_URL=''` and isolated temporary paths — **64 tests passed, 0 failed** (45.524 seconds).
- Frontend run: `npm test` — **7 passed, 0 failed**.
- Production build: **not run in this corrective pass**. The current sandbox is the previously documented environment in which Vite fails with `EPERM` resolving `frontend/src/main.jsx`, so it does not meet the instruction to attempt the build only where filesystem access permits. The earlier build-recovery report records an outside-sandbox production build passing with 30 modules; no frontend files changed in this corrective pass.
- MySQL integration and power-loss/storage durability remain **unverified**. No MySQL setup, migration, seed, connection, or power-loss simulation was performed.

### Updated disposition

The two publication-state findings and the Admin route-matrix coverage gap are addressed by the corrective pass and its passing isolated tests. The earlier Low catalog semantic-validation gap remains. The Phase 2.1 application behavior tested in isolated environments can proceed to closure **for this corrective scope**, with MySQL integration, MySQL migration compatibility, a permitted-environment production build, and actual power-loss durability kept explicitly outside the verified claims. Do not describe those environments as tested.

The corrective pass used temporary SQLite fixtures and temporary catalog/release/draft directories only. No live database or canonical catalog writes occurred.
