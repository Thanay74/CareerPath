# CareerPath Phase 2.1 — Independent Post-Implementation Safety Review

**Review date:** 2026-10-22  
**Review type:** Read-only code and test review. No source, catalog, schema, model, credential, or student-data files were changed. No live MySQL connection or write was made.

## Executive summary

The application import/start path is materially safer: importing `backend.app` and invoking its `__main__` server path do not call the schema/seed/admin setup functions. The explicit seed function uses insert-ignore semantics and does not update or delete existing question IDs.

This review found material gaps before treating Phase 2.1 as safe for production use. Explicit setup commands have no target-database guard and inherit `DATABASE_URL` from the shell or `.env`; `--schema` still runs the legacy assessment rename without preserving a usable normalized copy or a rollback plan. Career publication replaces two files sequentially, has no cross-process lock, and its fingerprint check is not atomic with reading/staging/publishing. The draft validator also skips several metadata fields when validating staged snapshots.

These are static findings. MySQL migration, permissions, DDL behavior, and live request behavior remain unverified.

## Findings

### High — Explicit setup commands can target the live database

**Status: Confirmed by code; actual target configuration unverified.**

- `backend/app.py:11-18` calls `load_dotenv()` and then resolves `DATABASE_URL`. `python-dotenv` does not override a shell-provided variable by default, but a `.env` value is used when the shell variable is absent. `USE_MYSQL` becomes true for MySQL URL prefixes; `connect_db()` then connects to the database named in the URL at `backend/app.py:35-40`.
- `backend/setup.py:17-34` exposes `--schema`, `--seed-education`, `--seed-aptitude-fixture`, and `--bootstrap-admin`. None requires an explicit target name, confirms the resolved server/schema, or blocks the known live database name. The schema, seed and bootstrap options call `init_db`, seed functions, or `bootstrap_admin` using the same global connection configuration.
- `CAREERPATH_DB` falls back to `<project-root>/careerpath.sqlite3` when MySQL is not selected (`backend/app.py:16,40`). A malformed or unsupported non-MySQL URL silently selects SQLite rather than failing closed.
- A project `.env` file is present, but its values were not printed or used to select a database during this review. Consequently, the actual configured setup-command target remains unverified.

**Impact:** An operator following the documented setup command can run DDL, insert lookup/question rows, or create the configured admin in the live database if the shell or `.env` points there. No setup command was run in this review.

**Recommended remediation:** Make setup fail closed unless an explicit target is supplied and verified. Print the resolved driver, host and schema (never password), require an explicit confirmation/allow flag for non-test targets, and reject the production schema name. Use a dedicated isolated schema and scoped account. Consider making unsupported `DATABASE_URL` schemes an error rather than falling back to SQLite.

### High — The explicit schema command still renames legacy assessments without a preservation migration

**Status: Confirmed by code; real legacy schema/data shape unverified.**

- MySQL `init_db()` conditionally renames `assessments` to `assessments_legacy_json` when the old table lacks `assessment_type`, then creates a new normalized `assessments` table (`backend/app.py:118-122`). The SQLite branch has analogous behavior at `backend/app.py:157-160`.
- No data conversion into the new `assessments` table, post-copy row-count check, migration version record, backup check, or reverse migration is present in the command path. The rename may retain the original bytes/table, but current application queries use the newly created normalized table, so legacy assessment values can become unavailable to the app.
- The same function executes multiple MySQL `CREATE`, `ALTER`, `MODIFY`, and `RENAME` statements before commit (`backend/app.py:103-140`). MySQL DDL can commit implicitly; a later failure cannot be assumed to roll back the earlier changes.

**Impact:** Running `python -m backend.setup --schema` against a legacy database can leave a mixed/partially migrated schema and can make old assessment data inaccessible to normal application flows. This remains unresolved and was not tested against MySQL.

**Recommended remediation:** Keep `--schema` blocked for databases with the legacy shape until a separately reviewed, versioned migration defines the source-to-target mapping, checks row counts and values, preserves the old table, and has a tested recovery procedure on a disposable MySQL clone. Do not run it against production before that review.

### High — Career CSV and metadata publication is not crash-atomic

**Status: Confirmed by code.**

- `save_career_catalog()` prepares temporary files, then replaces the active CSV and JSON separately (`backend/app.py:630-655`). If replacing the JSON raises synchronously it attempts to restore the CSV. A process termination, machine failure, or power loss after the CSV replace and before the JSON replace skips that rollback.
- The publish route has a second best-effort rollback if audit logging fails (`backend/app.py:717-731`), but its two restoration replaces are also sequential. An error during that rollback is not caught and can leave the files mismatched.
- The implementation report itself acknowledges this is not a true filesystem transaction.

**Impact:** A failed or interrupted publish can expose a CSV/JSON pair from different catalog versions. The recommendation reader combines both files (`backend/services/recommendation_engine.py`), so a family/keyword/qualification metadata mismatch can affect recommendations and explanations.

**Recommended remediation:** Store each complete catalog release in an immutable versioned directory and atomically switch a single manifest/pointer, or consolidate the runtime catalog into one atomically replaced artifact. Validate the complete release before pointer change and retain the last known-good version for rollback. Add failure-injection tests around each commit point.

### High — Fingerprint checks do not prevent all lost updates

**Status: Confirmed race windows in code; concurrent production occurrence unverified.**

- Career edit/create/deactivate handlers read catalog rows before `_stage_career_catalog()` captures `base_fingerprint` (`backend/app.py:783-805`, `815-840`, `850-858`, `682-696`). A local/external catalog change between that read and fingerprint capture can produce a stale full-snapshot draft carrying the newer fingerprint; publication then accepts it and may overwrite the intervening change.
- Publication compares the fingerprint and then writes the files without a lock (`backend/app.py:716-720`). Another publisher or external editor can change the catalog after the comparison but before the replacements.
- The “one pending draft” test is also check-then-create (`backend/app.py:683-693`) with no lock or atomic reservation. Two concurrent staging calls can both observe no pending draft and create drafts.

**Impact:** The stale fingerprint catches ordinary sequential conflicts, but does not provide compare-and-swap semantics under concurrency. A full-snapshot publish can lose a concurrent catalog edit.

**Recommended remediation:** Capture the source fingerprint together with the rows at read time; require it to match at stage time and again under a cross-process lock at publish time. Use an atomic single-pending-draft reservation and an idempotency key for publish requests. Recheck the active hash while holding the lock.

### Medium — Staged validation does not validate all metadata fields

**Status: Confirmed by code; malformed draft exploitation via local file tampering unverified.**

- `_stage_career_catalog()`, `_read_career_drafts()`, `admin_publish_career_draft()`, and `save_career_catalog()` call `validate_career_records(rows)` without a metadata object (`backend/app.py:685-687,676-679,713-715,630-634`).
- `validate_career_records()` validates core CSV fields, score ranges, stream references, and IDs, but checks `family`, `active`, `keywords`, `qualification_notes`, and `sources` only in the optional `metadata` argument (`backend/catalog_validation.py:122-132`). When career rows contain those merged metadata fields, they are ignored by this validator.
- Normal Admin request handlers separately check changed metadata fields (`backend/app.py:791-803,821-838`), but publication does not independently enforce the full staged-record contract. A locally tampered or corrupted draft containing an unsupported family, non-boolean `active`, or malformed keyword/source values can pass this validator and be written to metadata JSON.

**Impact:** The publish boundary does not fully guarantee that every field in the staged snapshot is valid, despite the UI showing “Catalog validation passed.”

**Recommended remediation:** Validate the complete merged record shape at stage and publish, including metadata types, allowed family values, source/keyword constraints, action enum, career ID membership, and record-to-metadata consistency. Make the validator reject unknown fields or explicitly whitelist them.

### Medium — Drafts are shared across all administrators, not owned by the initiator

**Status: Confirmed by code; intended governance policy unverified.**

- Draft files contain no creator/admin user ID (`backend/app.py:689`). The list endpoint returns every draft to any authenticated admin, and any active admin may publish or discard it (`backend/app.py:698-742`).
- `admin_required()` does correctly require an active bearer token whose database role is `admin` (`backend/app.py:236-239`), and all career create/edit/deactivate and draft list/publish/discard endpoints call it (`backend/app.py:699-701,705-707,736-738,780-782,812-814,847-849`). Thus unauthenticated users and students are excluded by the route guards, but there is no per-draft ownership or separate approver boundary.

**Impact:** Any admin can publish or discard another admin’s pending work. This may be acceptable for a shared one-draft queue, but it is not isolated by creator and the behavior is not documented as a policy.

**Recommended remediation:** Decide and document whether drafts are intentionally shared. If not, persist creator ID and enforce owner or designated reviewer rules in list/publish/discard operations. Add negative authorization tests for each endpoint, not only the dashboard.

### Medium — Admin audit events do not reliably cover failed or completed state changes

**Status: Confirmed by code; behavior under MySQL failures unverified.**

- Validation failures, stale-fingerprint rejection, malformed draft rejection, and authorization failures return without an `admin_audit_logs` event (`backend/app.py:704-716,735-742,780-809`). The generic `after_request` handler may write an `application_errors` row (`backend/app.py:184-193`), but that record does not include the admin identity, draft ID, or attempted operation details.
- Discard removes the draft before attempting its audit insert (`backend/app.py:739-742`). If the audit insert fails, the draft is already gone and the API returns an error without the corresponding audit event.
- Publish writes the catalog, then writes its audit event, then removes the draft (`backend/app.py:719-733`). If draft removal fails, the publish has succeeded and is audited but the API reports an error and leaves the draft present; a retry will hit the stale-fingerprint branch. If the audit write fails, rollback is best effort, not crash-atomic.

**Impact:** Audit records do not provide a complete, unambiguous history of failed attempts and completed state transitions. Some error responses can follow a state change.

**Recommended remediation:** Define audit semantics for rejected attempts and state transitions. Record a stable operation ID and draft/catalog version. Use a durable publication state machine or versioned release record so audit, active-version switch, and draft completion can be reconciled after process failure. Ensure API responses reflect whether the state change committed.

### Medium — Catalog validation has structural gaps

**Status: Confirmed by code; current catalog passes current checks.**

- The optional metadata checks detect metadata keys that reference unknown career IDs, but do not require each career row to have metadata or validate row-embedded metadata as noted above (`backend/catalog_validation.py:122-132`).
- `json.loads()` is used directly (`backend/catalog_validation.py:145`); JSON objects with duplicate textual keys are silently collapsed by the standard decoder, so duplicate metadata IDs/fields in the source text are not reported.
- Career `recommended_degrees`, `required_subjects`, and qualification/certification text are only checked as strings. They are not checked against the education degree/subject catalogs. Some catalog entries may intentionally use broader qualification labels, so any stricter mapping should use an explicit reviewed alias/reference catalog rather than naive string matching.
- Education validation checks list types, duplicates and degree/specialization/subject-group references, but does not enforce the expected top-level entry keys, stable machine identifiers separate from display labels, or duplicate JSON/Python mapping keys that were already discarded during parsing (`backend/catalog_validation.py:26-78`).

**Impact:** `--validate-catalogs` can report success for some ambiguous or semantically malformed metadata and career references.

**Recommended remediation:** Reject duplicate JSON keys with `object_pairs_hook`; require exact allowed fields and required metadata per career; validate metadata on merged records; introduce explicit reviewed aliases for degree/subject references; and add fixtures for malformed types, duplicate JSON keys, missing metadata and invalid references.

### Low — Test coverage does not establish all safety properties

**Status: Confirmed by test inventory.**

- `tests/test_startup_safety.py` blocks SQLite connection on import and checks that the DB file and aptitude fixture are not created/loaded. This supports the import-path conclusion but does not directly test the `python -m backend.app` server lifecycle or patch MySQL connector calls.
- `tests/test_api.py` covers a successful staged edit/publish and invalid score content, but does not cover create/deactivate draft publication, student/unauthorized access for each draft route, stale fingerprint rejection, duplicate/concurrent stage/publish, file replacement failure/crash points, audit failure, draft envelope tampering, or metadata validation gaps.
- No test uses an isolated MySQL schema. Existing test outcomes are SQLite/mock evidence only.

**Recommended remediation:** Add isolated tests for each item above. After the legacy migration and file publication strategy are redesigned, test failure/restart recovery against disposable environments. Do not use the live database for these tests.

## Startup and aptitude trace

### Startup conclusion

`backend/app.py` imports Flask, dotenv, and the recommendation service; its module-level statements resolve paths/configuration, construct the Flask app, register teardown/after-request handlers, and define functions/routes. There is no module-level `init_db()`, connection call, DDL, seeding, admin creation, or catalog write. The `if __name__ == '__main__'` path only calls `app.run(...)` at the bottom of the module. Static tracing therefore finds no database/file write during import or server startup itself.

The `after_request` handler is request-time, not startup-time: for API responses with status >=400 it tries to insert an `application_errors` record. A normal request also opens a database connection through `db()` when route logic needs it. With SQLite selected, `sqlite3.connect(DB_PATH)` creates the configured database file on first connection. This is expected runtime behavior, not an import/server-start write. The startup-safety test provides supporting isolated evidence for import only.

`backend/services/recommendation_engine.py` is imported at module load but catalog/model work occurs through functions; model loading in `backend/ml/predict.py` happens inside prediction calls, not during app import. No recommendation-service import path found here invokes `connect_db()` or writes catalog files.

### Aptitude fixture conclusion

`seed_aptitude_questions()` imports `backend.aptitude_bank.QUESTIONS` only when that function is invoked (`backend/app.py:50-57`). The normal Flask startup path does not call it. `backend.setup --seed-aptitude-fixture` is the explicit caller. It uses MySQL `INSERT IGNORE` or SQLite `INSERT OR IGNORE`, so existing primary-key question IDs are not updated and no delete statement is issued by this seed function. It can still insert fixture rows into whichever database the setup environment resolves to; see the High setup-target finding.

## Admin authorization and staged publishing

- **Route-level role check:** Confirmed for career CRUD and all draft endpoints. Each invokes `admin_required()`, which checks an active user with `role='admin'`. Route guards are not bypassed through request-supplied file paths.
- **Draft path input:** The requested draft ID must match 24 lowercase hex characters and the storage directory is a server constant (`backend/app.py:665-667`). No request field is joined to a filesystem path. Path traversal through the HTTP draft ID is therefore rejected by the current regex.
- **Draft isolation:** Shared for all active admins; no creator ID/ownership exists.
- **Invalid drafts:** Core CSV fields, IDs, duplicate IDs/names, stream names and numeric score ranges are validated. Staged metadata validation is incomplete (Medium finding). Invalid core scores are rejected by the existing tamper test.
- **Stale drafts:** Sequential changes to either active file alter the fingerprint and are rejected (`backend/app.py:659-663,716`). Concurrent check/write windows remain (High finding).
- **Duplicate/concurrent operations:** No lock, idempotency key, publication journal or atomic reservation is present. The single-pending check and publish flow are raceable. Duplicate publish requests can race around file replacement, audit insert and `path.unlink()`.
- **CSV/JSON consistency:** Best-effort rollback handles selected synchronous failures, but interruption/crash between file replacements can expose mixed versions. This is a confirmed High finding.
- **Audit:** Successful stage/publish actions are logged in ordinary cases. Failed validation/stale requests are not logged as admin audit events; discard/audit ordering and publish/audit/file ordering can report errors after state changes. Medium finding.

## Isolated MySQL verification procedure (recommendation only; not executed)

1. Have a DBA provision a disposable schema with a clearly non-production name (for example `careerpath_phase21_test`) and a dedicated user limited to that schema. Do not copy student rows; use only synthetic/test fixtures.
2. In a fresh shell, explicitly set `DATABASE_URL` to that isolated schema using a secret manager or protected environment variable. Confirm the resolved host and schema with a read-only connection (`SELECT DATABASE(), CURRENT_USER()` and `SHOW TABLES`) before any setup command. Do not print credentials.
3. Review the current legacy assessment shape first. If the schema contains an old `assessments` table without `assessment_type`, **do not run `--schema`** until the migration has a reviewed preservation/rollback plan. For a truly empty disposable schema only, run the reviewed setup command there.
4. Seed education rows or aptitude fixture questions only if the isolated schema needs them. Capture table counts before and after. Run the backend suite against only the disposable schema, review results, and discard/recreate that disposable environment through the DBA’s approved process after testing.
5. Do not infer MySQL safety from SQLite tests. Require explicit pre/post schema and row-count evidence, migration repeatability, and failure/recovery testing before production approval.

This procedure is not a claim that MySQL integration was verified.

## Tests reviewed or run

Tests reviewed: `tests/test_startup_safety.py`, `tests/test_catalog_validation.py`, and staged-career cases in `tests/test_api.py`.

Safe tests run in this review:

```text
$env:DATABASE_URL=''
$env:CAREERPATH_DB='.test-tmp\safety-review.sqlite3'
python -m unittest tests.test_startup_safety tests.test_catalog_validation tests.test_api.ApiTests.test_admin_can_edit_career_and_skill_criteria_in_knowledge_base tests.test_api.ApiTests.test_invalid_staged_catalog_cannot_be_published -v

Ran 6 tests — OK
```

The API tests use per-test temporary SQLite databases and copied catalog files; the startup test blocks SQLite connections during import. No MySQL tests, schema commands, seed commands, or server runtime tests were run. SQLite results do not verify MySQL DDL or locking behavior.

## Remediation priority

1. Add fail-closed target validation to every mutating setup command; document exact isolated schema selection.
2. Keep legacy assessment migration disabled until a versioned, data-preserving migration and rollback plan are reviewed and proven on a disposable MySQL clone.
3. Replace the two-file live publish with immutable catalog releases and one atomic active-version switch; add restart/failure injection coverage.
4. Add locking/compare-and-swap around read, stage, and publish; enforce an atomic single-pending reservation and request idempotency.
5. Validate the entire merged career record and draft envelope, including metadata, references, family/action/ID fields, and duplicate JSON keys.
6. Decide whether drafts are owner-scoped or intentionally shared; encode the policy and test every role/endpoint.
7. Make audit and catalog publication recoverable as one operation; include operation IDs and represent rejected attempts/state transitions clearly.
8. Expand regression tests for stale drafts, race conditions, authorization matrix, failed file operations, audit failures and migration preservation.

## Safety confirmation and limitations

No live database was connected to, and no database writes, migrations, seeds, schema changes, or student-record operations were performed. No catalog file was written. The only persistent project file created by this review is this report; isolated test artifacts were confined to the ignored `.test-tmp/` area or cleaned per-test temporary directories. No Git metadata is available in the inspected project copy, so this review could not compare Git status.
