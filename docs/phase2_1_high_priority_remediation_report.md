# Phase 2.1 High-Priority Safety Remediation

> **Status update:** This report records the earlier remediation checkpoint. Career publishing was disabled at that time. The release implementation and current build/test status are documented in [phase2_1_build_recovery_and_catalog_release_report.md](phase2_1_build_recovery_and_catalog_release_report.md) and [phase2_1_versioned_catalog_design.md](phase2_1_versioned_catalog_design.md).

## Scope and safety

This work addresses the four High findings in `phase2_1_safety_review.md`. It does not implement Phase 2.2, change recommendation scoring, alter canonical career or education catalog content, or change model artifacts, datasets, credentials, or student data.

No schema or seed command was run. The live `careerpath` database was not written to, migrated, seeded, or altered. No canonical career catalog file was changed. MySQL integration remains unverified.

One initial test invocation inherited the project's `.env` MySQL selection before the API tests could substitute their SQLite fixture. The sandbox denied the connection attempt before a connection was established. All subsequent backend tests were run with `DATABASE_URL` explicitly empty and used isolated SQLite fixtures. No write was made to MySQL.

## Findings and disposition

### 1. Mutating setup target — fixed

`backend/database_config.py` resolves only supported MySQL/PyMySQL and local SQLite targets, rejects malformed/unsupported/ambiguous targets, blocks the `careerpath` database name, creates a credential-free target identity, and validates the exact `--confirm-target` value. Non-test targets also require `--allow-non-test-target`.

`backend/setup.py` applies this check before any schema, seed, or admin command, then prints only the driver, host, and database/path identity. Read-only catalog validation remains available without selecting a mutation target. `backend/app.py` no longer silently falls back to SQLite when a configured URL is invalid: database access fails closed.

### 2. Legacy assessment rename — fixed by fail-closed guard; migration remains blocked

`backend/app.py:init_db()` now inspects the existing `assessments` table shape before any schema DDL in both SQLite and MySQL branches. If the legacy table lacks `assessment_type`, setup closes the connection and raises an actionable error before creating, altering, or renaming tables.

No replacement migration was designed or run. MySQL metadata behavior, DDL behavior, migration preservation, and rollback remain unverified. A separately reviewed data-preserving migration is still required before legacy schemas can be upgraded.

### 3. Catalog release consistency — safely blocked; publishing disabled

The current runtime reads CSV and JSON independently. Replacing that data flow with an immutable version directory and one active-version pointer requires coordinated reader, deployment, rollback, and recovery changes; it was not safe to claim that a partial conversion would provide atomic release semantics.

Accordingly, the unsafe sequential replacement code was removed. The authenticated publish endpoint now returns HTTP 503 with an actionable explanation and retains the staged draft. The Admin UI disables the publish action and explains that the draft remains staged. Existing canonical files remain the active catalog. Immutable versioned releases, manifest validation, crash recovery, and last-known-good rollback are not implemented.

### 4. Concurrent staging and publication — staging protected; publication intentionally unavailable

`backend/interprocess_lock.py` provides an OS file lock (`msvcrt.locking` on Windows, `flock` on POSIX). Draft listing, staging, discard, and cleanup after a failed audit write use the shared lock file, so the single-pending-draft check and write are serialized across application processes.

`backend/app.py:_career_catalog_snapshot()` reads the canonical CSV and metadata pair twice, rejects a pair that changes during the read, and captures a length-delimited fingerprint with the rows. `_stage_career_catalog()` rechecks that fingerprint while holding the cross-process draft lock and rejects stale snapshots. Concurrent publish requests cannot activate anything because publishing is disabled.

The lock only coordinates application draft operations. An external editor or process that directly changes canonical catalog files does not participate in the lock. No publication race-safety or crash-recovery guarantee is claimed until versioned publishing replaces the current file pair.

## Files changed

- `backend/database_config.py` — safe target parsing, target identity, production-target rejection, confirmation and allow-flag validation.
- `backend/setup.py` — validate and display selected mutation target before setup work.
- `backend/app.py` — fail-closed database configuration, pre-DDL legacy assessments guard, consistent catalog snapshot/fingerprint checks, cross-process draft locking, and disabled publication endpoint.
- `backend/interprocess_lock.py` — OS-backed cross-process lock helper.
- `frontend/src/AdminPortal.jsx` — disabled publication control and accurate staged-draft status.
- `tests/test_setup_safety.py` — unsafe, missing, malformed, unsupported, production, confirmation, and no-connection setup checks.
- `tests/test_legacy_schema_guard.py` — legacy SQLite fixture proves setup stops before DDL.
- `tests/test_interprocess_lock.py` — separate-process lock serialization check.
- `tests/test_api.py` — publication-disabled/active-catalog-preservation assertions, stale snapshot rejection, concurrent staging, and concurrent publish request checks.
- `docs/phase2_1_high_priority_remediation_report.md` — this report.

## Verification

Run with `DATABASE_URL` explicitly empty and temporary test files rooted under the project test temp directory:

- `python -m unittest discover -s tests` — **46 tests passed**.
- `npm test` — **7 tests passed**.
- `npm run build` — **blocked / failed**. Vite repeatedly raised `EPERM` while realpath-resolving the existing `frontend/src/main.jsx`. The file is a regular file; direct Node `realpathSync`, `statSync`, and `lstatSync` succeeded. No Vite configuration or source workaround was applied.

No MySQL tests were run. The MySQL migration guard is based on static inspection and a SQLite fixture; its MySQL branch and server behavior remain unverified.

## Remaining work and risks

1. Implement immutable, versioned catalog releases and a single atomic active-version pointer, including strict manifest and pair validation, crash/failure injection, restart/reload, rollback, and last-known-good tests. Keep the current publish API disabled until then.
2. Review and test a data-preserving legacy assessment migration on a disposable MySQL clone before enabling any upgrade of legacy schemas.
3. Run MySQL target parsing/guard integration checks only against an approved isolated schema. Never use the live `careerpath` database for this verification.
4. Resolve the Vite `EPERM` build environment issue and rerun the production build.
5. External direct edits to the file-based career catalogs are not serialized by the application lock. The snapshot double-read and fingerprint reject ordinary concurrent changes, but they are not a transaction against arbitrary external writers.

**Data integrity confirmation:** test writes used isolated SQLite fixtures or temporary copies. Canonical career catalog files and live MySQL data were not modified.
