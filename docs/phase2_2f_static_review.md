# Phase 2.2F — Static Review of the Isolated Student Runtime Launcher

**Review date:** 2026-10-22  
**Scope:** Static review only. This report does not establish runtime, database, or browser behavior.

## Scope and commands

Reviewed:

- `scripts/phase2_2f_student_runtime.py`
- `docs/phase2_2f_isolated_student_runtime.md`
- `backend/app.py`, `backend/database_config.py`, `backend/setup.py`
- `backend/services/recommendation_engine.py`, `backend/services/catalog_releases.py`
- `docs/phase2_2f_browser_admin_verification_plan.md` and `docs/phase2_2f_readiness_assessment.md`

Commands actually executed:

- `python -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/phase2_2f_student_runtime.py').read_text(encoding='utf-8')); print('AST syntax: PASS')"` — **PASS**. This parsed the script without importing or executing it.
- Read-only `Get-Content` and `rg` source/document inspection; scoped Git status for the review target. No application test, setup, migration, seed, server, browser, or database command was run.

## Findings

### BLOCKER — `serve` does not verify the database schema or student-only contents

**References:** `scripts/phase2_2f_student_runtime.py::_command_serve`, `_configure_and_assert`; `backend/app.py::connect_db`, `bootstrap_admin`; `backend/setup.py::main`.

In `serve` mode, `_configure_and_assert(..., require_database=True)` checks that `student_test.sqlite3` is a regular file. It does not open that file read-only to confirm that it is SQLite, that the expected CareerPath tables/schema exist, or that `users`/`students` contain no pre-existing records or Admin account. A file can exist but be empty, malformed, copied from another runtime, or contain an account. The launcher therefore cannot establish that the server will use a database initialized for this exact runtime or that the runtime is student-only. The marker does not record a schema identity or a post-initialization attestation.

**Required change, not implemented:** add a fail-closed, read-only SQLite preflight before server start. It should open only the exact resolved file in read-only mode, validate the required schema/version, verify there are no pre-existing users/student records or Admins (or require a separately documented reviewed fixture baseline), and reject symlinked DB targets. Never create the DB as a side effect of this check. Record the verified database fingerprint/schema marker only after the separately approved isolated initialization step.

### BLOCKER — stale or tampered runtime marker is not a proof of fresh provenance

**References:** `scripts/phase2_2f_student_runtime.py::_load_runtime_marker`, `_assert_root_is_safe`, `_configure_and_assert`, `_command_serve`.

The marker validates a version, project-root string, and runtime-root string. It has no creation nonce, timestamp, database identity, or authenticity check. `serve` accepts any existing direct child of the temp directory with the expected prefix and a matching editable marker; it does not prove that the directory was produced by the current `prepare` invocation or remains otherwise untouched. Catalog checksums are stored in that same editable marker, so they detect accidental copy drift but are not tamper evidence. A database symlink to another file within the runtime also resolves inside the root and can pass the current containment and equality checks.

**Required change, not implemented:** ensure the exact runtime selected by `serve` is freshly provisioned and explicitly attested for that run. Reject symlink/reparse-point database files and unexpected pre-existing files/directories. Protect the marker against accidental replacement using an external run token or a separate owner-held attestation; do not describe a self-written hash as adversarial tamper protection. Require database identity/schema verification at the actual SQLite connection boundary before the server is started.

### WARNING — preparation may leave an unreported partial temporary directory

**References:** `scripts/phase2_2f_student_runtime.py::_prepare_runtime`, `_command_prepare`.

`_prepare_runtime()` creates the temporary directory and writes directories/copies/marker before returning. The `try` in `_command_prepare()` starts only after that function returns. If copying or marker creation fails, the exception is uncaught and the created path is not printed; the partial directory remains. The documented cleanup process depends on the reported exact path, so it cannot safely identify this failure's directory.

**Recommended change, not implemented:** wrap creation and all writes in failure reporting that always emits the exact created root, and either safely remove only a root created by this invocation after validating its identity or preserve it with a clear exact-path cleanup instruction. Do not use broad temp cleanup.

### WARNING — import preflight can write Python bytecode caches in the checkout

**References:** `scripts/phase2_2f_student_runtime.py::_configure_and_assert`; top-level imports in `backend/app.py` and its imported modules.

The script imports `backend.app` and other project modules. Static inspection found no top-level call to `connect_db()`, `init_db()`, a seed function, `bootstrap_admin()`, or a catalog writer, so the import path does not appear to connect to the database or initialize state. Python may nevertheless write `__pycache__` bytecode files beside imported source modules unless bytecode writing is disabled. That does not alter application logic, but it is a filesystem side effect outside the temporary runtime and is not mentioned in the preflight's no-side-effect description.

**Recommended change, not implemented:** set `sys.dont_write_bytecode = True` before importing application modules, or explicitly document this cache behavior. The former better matches the isolated-preflight description.

### WARNING — restart after catalog publication is rejected when active bytes differ from baseline copies

**References:** `scripts/phase2_2f_student_runtime.py::_configure_and_assert`; `backend/services/catalog_releases.py::load_active_catalog`, `_read_release`.

Every configuration pass compares the returned active snapshot bytes with the copied canonical CSV/metadata. That is appropriate for the initial fresh preflight, but a valid later versioned release can intentionally contain different bytes. On a subsequent `serve` restart, the catalog reader returns release bytes and this assertion rejects the runtime, even if the manifest and immutable release are valid. This does fail closed, but it prevents restart/recovery after a separately approved publication and conflicts with the launcher document's general restart implication.

**Recommended change, not implemented:** distinguish initial `prepare` assertions from later `serve` assertions. On serve, verify the loaded snapshot against the selected release manifest/content hashes when a pointer exists; compare with the canonical-copy fingerprint only in canonical-bootstrap mode.

### PASS — database environment precedence is fail-closed for the selected SQLite path

**References:** `scripts/phase2_2f_student_runtime.py::_configure_and_assert`; `backend/app.py` environment loading and `connect_db`; `backend/database_config.py::resolve_database_target`.

The launcher overwrites `DATABASE_URL` with an empty value and sets `CAREERPATH_DB` before importing `backend.app`. The app calls `load_dotenv()` without requesting override; an already-present process environment value therefore takes precedence over a project `.env` value. The launcher then checks `DATABASE_URL == ""`, `_DATABASE_CONFIG_ERROR is None`, `DATABASE_TARGET.driver == "SQLite"`, `DATABASE_TARGET.mysql is False`, `USE_MYSQL is False`, and both configured SQLite paths resolve to the expected runtime database path. The checked `connect_db()` uses these resolved globals. No MySQL fallback is apparent if these checks pass.

This is a static finding; the actual import/configuration path was not executed.

### PASS — requested catalog and draft module globals are redirected and checked

**References:** `scripts/phase2_2f_student_runtime.py::_expected_paths`, `_configure_and_assert`; `backend/services/recommendation_engine.py::KB`, `METADATA`, `careers`; `backend/services/catalog_releases.py::load_active_catalog`; `backend/app.py::CAREER_DRAFT_DIR`, `_career_draft_lock_path`.

The listed runtime assignments match current module names and the catalog loader's keyword parameters (`active_manifest`, `releases_dir`, `managed_marker`). Recommendation paths, active pointer, managed marker, releases directory, activation lock, draft directory, and derived draft lock are checked beneath the temporary root. The DB path is included in the same containment loop. A service child path that resolves outside the root is rejected by `Path.resolve()` containment. The known pointer/marker/release paths are passed explicitly to the read-only load for the preflight.

The project education catalog is Python data (`backend/education_catalog.py`), not one of these external file paths. It is not modified by this launcher. This PASS concerns the paths requested for the file-backed career catalog and draft/release flow; it is not a full inventory of every project file read at runtime.

### PASS — catalog fallback and checksum assertions match the current reader for a fresh runtime

**References:** `scripts/phase2_2f_student_runtime.py::_prepare_runtime`, `_configure_and_assert`; `backend/services/catalog_releases.py::load_active_catalog`, `_validated_snapshot`.

The fresh directory receives copied CSV and metadata plus an empty releases directory; it does not create a pointer or managed marker. The current reader falls back to the supplied canonical pair only when both pointer and marker are absent, validates the pair, and returns its bytes in `CatalogSnapshot`. The launcher compares those bytes with the copied files and checks copied-file SHA-256 values against the marker. This is suitable for its intended initial preflight, subject to the marker-provenance and serve/restart findings above. No catalog read was actually performed during this review.

### PASS — application import has no identified database/startup mutation call

**References:** `backend/app.py` module top level, `connect_db`, `init_db`, `bootstrap_admin`; `backend/services/recommendation_engine.py` module top level.

Static inspection shows the app defines the Flask object, configuration globals, functions, and routes. `init_db`, seed functions, and `bootstrap_admin` are definitions or explicit setup dispatches, not normal import-time calls. Recommendation-engine module initialization sets catalog paths and constants; file reads are performed when its functions are called. No import-time database connection or schema/catalog mutation was identified. Import may load dotenv and may generate Python bytecode as noted in the warning.

## Go/no-go recommendation

**Preparation-only `prepare` command: NO-GO as written.** The command is designed to make a fresh temp directory, copy catalogs, import the app under forced SQLite environment, and run path/catalog assertions without connecting to a database or starting a server. Before running it, fix the unreported partial-directory failure path and prevent or explicitly accept the possible `__pycache__` writes outside the temporary runtime. After those changes receive static review, a separately authorized preparation run can be considered. This review did not execute it and therefore does not claim those properties at runtime.

**`serve` command: NO-GO.** It does not establish the database schema, contents, student-only state, or exact initialized-runtime provenance and must be corrected before any browser workflow. Also address valid managed-release restart behavior before using it for release/recovery workflows.

No Admin account should be created for student-only checks. Admin testing remains separately gated by an owner-provisioned isolated identity or separately approved, target-confirmed bootstrap. No publish/restore operation is authorized by this review.

## Required changes for a later corrective task

1. Add read-only SQLite schema and contents checks at serving startup; reject Admins/pre-existing user data and all SQLite symlink/reparse targets.
2. Strengthen runtime provenance and freshness checks; distinguish initial preflight from an already-approved initialized runtime without trusting a mutable self-marker alone.
3. Ensure partial preparation failures report their exact temporary root and document safe cleanup; prevent or document `__pycache__` writes.
4. Make serve-mode release validation verify the selected immutable release rather than requiring it to equal the original canonical copy.
5. After those fixes, separately authorize and execute only the preparation command first. Review its actual printed paths before any database initialization or server run.

## Safety confirmation

No launcher command was executed. No Flask/Vite/browser was started, no MySQL or SQLite database was opened, no tests/setup/migrations/seeds ran, no accounts were created, no catalog/release files were modified, and no temporary directories were deleted.
