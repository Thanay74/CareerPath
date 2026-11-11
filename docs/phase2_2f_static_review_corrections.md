# Phase 2.2F — Static Review Corrections

**Date:** 2026-10-22  
**Scope:** Correct the isolated student runtime launcher based on `docs/phase2_2f_static_review.md`. No launcher mode was executed.

## Changes made

### `scripts/phase2_2f_student_runtime.py`

- Preparation failures after `mkdtemp` are wrapped with the exact invocation-created runtime root and reported without automatic deletion. The error path explicitly directs the operator to inspect only that exact directory before cleanup.
- `sys.dont_write_bytecode = True` is set before backend imports, preventing backend import bytecode writes outside the temp runtime.
- Reparse-point/symlink checks cover runtime roots, redirected path components, and the SQLite target. The database target remains selected by setting `DATABASE_URL` empty and `CAREERPATH_DB` to the exact temporary file before importing the app; actual resolved target assertions remain fail-closed.
- Serve requires an externally retained SHA-256 and the printed runtime ID. It reads the exact SQLite file with `mode=ro&immutable=1`, checks SQLite file header and hash before/after, rejects sidecars, runs `quick_check` and `foreign_key_check`, verifies the implementation-derived table/column/type/primary-key/foreign-key/unique/check-constraint structure, and rejects pre-existing account/student/application history rows and retained user/event auto-increment history. It does not initialize or repair the database.
- After the read-only validation, a SQLite-only wrapper checks target configuration and file identity for each application connection, opens using `mode=rw` to refuse accidental file creation, enables foreign keys, and verifies the actual connection's `PRAGMA database_list` path.
- Schema expectations derive from the SQLite branch of `backend/app.py::init_db`. That code does not assign `PRAGMA user_version`, so the launcher accepts only the current default value `0` and separately checks the structure; no schema version was invented.
- Catalog validation now distinguishes fresh preparation from serve mode. Fresh mode requires canonical-bootstrap fallback and exact copied bytes/hashes. Serve mode relies on `catalog_releases.load_active_catalog` to validate a selected manifest/release and its hashes, and does not require a managed release to equal the original canonical copies. Missing/malformed/ambiguous managed state fails closed.
- The runtime ID and same-directory hashes are documented as accidental-substitution checks, not an adversarial trust anchor. The expected DB digest must be recorded outside the runtime after separately approved setup/fixture loading and associated with the printed runtime identity.

Source references inspected: `backend/app.py::init_db`, `connect_db`, `bootstrap_admin`; `backend/database_config.py::resolve_database_target`; `backend/services/catalog_releases.py::load_active_catalog`, `_read_release`; and `backend/setup.py::main`.

### `docs/phase2_2f_isolated_student_runtime.md`

Updated instructions to describe the bytecode behavior, partial-preparation error handling, schema checks and their implementation-derived basis, external database digest/runtime ID limitations, and separate canonical-bootstrap versus managed-release validation. Clarified the later explicit setup/fixture, serve, and cleanup gates.

## Commands and verification

Executed only this non-importing syntax parse:

```text
python -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/phase2_2f_student_runtime.py').read_text(encoding='utf-8')); print('AST syntax: PASS')"
AST syntax: PASS
```

Read-only source inspection was performed on the files listed above. No tests, launcher commands, setup, migrations, seeds, application servers, browser, SQLite/MySQL connections, account operations, or catalog operations were run.

## Remaining limitations and decision

- The code has no explicit SQLite schema-version marker. Structural checks are tied to the current SQLite initializer and must be updated if that initializer changes.
- An externally retained file hash, runtime ID, and process-local file identity detect accidental substitution only. They do not eliminate every filesystem race or protect against a malicious local user able to change both the database and supplied values. Do not use this local workflow if that threat model applies or the owner cannot retain the association independently.
- No runtime result has been observed. `prepare` has not been executed; separate approval is still required before running it. `serve` additionally requires separately approved schema/fixture setup and an external hash record. No Admin account or publishing/restore workflow is included.

**Decision:** preparation-only `prepare` is ready for separate approval to run, but is not runtime-verified. Do not run `serve` until its isolated SQLite target has been separately initialized, required fixture rows have been reviewed, and the database hash/runtime ID have been independently retained.
