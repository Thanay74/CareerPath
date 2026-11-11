# Phase 2.2F — Isolated Student Runtime Launcher

## Purpose and status

`scripts/phase2_2f_student_runtime.py` prepares and verifies a disposable student-test runtime. Its default preparation mode is preflight-only: it creates a unique temporary directory, copies the two canonical career catalog inputs, redirects runtime module globals, checks the selected DB/catalog paths, and asks the existing read-only catalog loader to validate the copied pair.

**This launcher has not been executed.** Flask/Vite were not started, no SQLite database was initialized or connected, no student/Admin account was created, and no browser or MySQL operation occurred. The launcher does not initialize a schema, seed data, bootstrap Admin, publish, restore, or train a model.

## Static path design

The application reads the database target from `DATABASE_URL` and `CAREERPATH_DB` before it imports `backend.app`. The launcher sets `DATABASE_URL` to the empty string and `CAREERPATH_DB` to `<runtime>/db/student_test.sqlite3` before importing the Flask app. It then asserts that `DATABASE_TARGET` is SQLite, `USE_MYSQL` is false, `_DATABASE_CONFIG_ERROR` is empty, and both resolved SQLite paths equal the exact temporary database path.

Catalog paths are module-level constants rather than environment settings. In the launched process, the script redirects:

- `backend.services.recommendation_engine.KB` and `METADATA` to temporary copies of `data/career_knowledge_base.csv` and `data/career_metadata.json`.
- `backend.services.catalog_releases.ACTIVE_MANIFEST`, `MANAGED_MARKER`, `RELEASES_DIR`, and `ACTIVATION_LOCK` to paths inside the runtime's `data/` directory.
- `backend.app.CAREER_DRAFT_DIR` to the runtime's `instance/career_drafts`; `_career_draft_lock_path()` must then resolve to that directory's `catalog.lock`.

The source education catalog and saved model artifacts remain code/project inputs and are not copied or modified by this launcher. Recommendation model training is not performed.

Before importing backend modules, the launcher disables Python bytecode writing in its process so imports do not create `__pycache__` files in the project checkout.

## Preparation preflight

Run from the project root in a later, separately authorized preparation step:

```powershell
python scripts/phase2_2f_student_runtime.py prepare
```

This command creates a fresh directory directly under the operating system temporary directory with the prefix `careerpath_phase22f_student_`. It does not start a server or make a database connection. It prints the runtime path and each selected test path; it does not print secrets. Keep the printed runtime path for any later approved use.

The preparation assertions fail closed if the runtime is not a fresh direct child of the temp directory, the catalog source is missing or a symlink/reparse point, MySQL is selected, the resolved DB path differs, any redirected path escapes the temp root or crosses a link/reparse point, the copied catalog hashes change, the catalog reader selects different bytes, or managed release state unexpectedly exists in the fresh runtime. The SQLite database path is configured but must remain absent after preparation. If preparation fails after creating its runtime, the exact invocation-created path is reported and no automatic recursive cleanup is attempted.

## Database setup and server start are separate actions

The script does **not** create the SQLite schema or seed education/aptitude rows. Student API flows cannot be used until the owner separately approves schema initialization and any required education/aptitude fixture loading against the exact temporary SQLite target. Use the application's reviewed target-confirmed setup process only after verifying the runtime path and target identity; do not initialize MySQL or any shared database. The launcher prints the target as a path and its code does not call `init_db()` or a seed function.

The SQLite branch of `backend/app.py::init_db` does not set `PRAGMA user_version`, so the code has no declared schema-version value. Serve-mode validation expects the current SQLite default (`user_version=0`) and derives its structural expectations from that initializer: the exact 18 application tables; each table's column names and declared types; primary keys; foreign-key relationships and delete actions; unique constraints; the three declared `CHECK` constraints; no extra views, triggers, or explicit indexes; and the `sqlite_sequence` internal table. It runs `PRAGMA quick_check` and `foreign_key_check`. These are implementation-derived checks; the launcher does not invent a new schema version.

Serve opens only the exact SQLite path through a read-only `mode=ro&immutable=1` URI. It rejects link/reparse components, a non-SQLite header, journal/WAL sidecars, an unexpected or malformed schema, foreign-key violations, rows in account/student/assessment/recommendation/event/error/audit tables, retained auto-increment sequence history for user/event/error/audit tables, and a file hash that differs before or after validation. Education lookup rows and aptitude question fixtures are allowed because student flows may depend on them. The check never initializes or repairs the database. After validation, the launcher installs a SQLite-only connection wrapper. Each application connection rechecks target configuration and captured file identity, opens the existing file with SQLite `mode=rw` (which refuses to create a missing replacement), enables foreign keys, and confirms `PRAGMA database_list` reports the exact approved file before returning the connection.

The runtime marker and printed runtime ID are accidental-substitution checks, not adversarial tamper protection. The marker and its catalog hashes are editable and are not a trust anchor. After separately approved setup/fixture loading and after all setup connections are closed, the owner must record the SQLite file SHA-256 outside the runtime directory and associate it with the exact printed runtime path and runtime ID. For example, in PowerShell:

```powershell
$dbFile = Join-Path $runtimeRoot 'db\student_test.sqlite3'
$dbSha256 = (Get-FileHash -LiteralPath $dbFile -Algorithm SHA256).Hash
```

Retain `$dbSha256` outside the runtime directory and pass it to `serve`. This detects accidental file substitution relative to the independently retained values; it does not protect against a malicious local user who can replace the database and alter the supplied values. If that threat model applies or external attestation cannot be retained, do not serve this runtime.

Once the disposable SQLite schema and required education/aptitude fixtures exist through separately approved actions, record the database hash outside the runtime directory and retain the `runtime_id` printed by `prepare`. Then start with:

```powershell
python scripts/phase2_2f_student_runtime.py serve --runtime-root "<exact runtime_root printed by prepare>" --runtime-id "<runtime_id printed by prepare>" --expected-database-sha256 "<externally recorded database SHA-256>" --port 5000
```

The `serve` mode checks the exact runtime ID, external database digest, schema/content, and all redirected paths before binding Flask to `127.0.0.1` with the reloader disabled. It performs no schema setup and creates no Admin account. In fresh canonical-bootstrap mode it verifies copied hashes and that the reader returns those copied bytes. If a managed pointer exists, the project reader validates its manifest, selected immutable release, release ID, content hashes, and catalog records; a valid release is not required to match the original canonical copies. A malformed pointer, missing release, marker without pointer, or orphan release state without a pointer fails closed. Start the frontend separately only after explicit runtime approval, using the existing Vite proxy and a loopback-only host (for example, `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort` from `frontend/`). Do not assume browser access has been verified by either command.

## Cleanup boundary

After any later approved run, stop the Flask and Vite processes first. Read the runtime marker and verify that its recorded root equals the exact `runtime_root` printed for that run, that the directory is a direct child of the OS temp directory, and that its basename has the expected prefix. Remove only that exact temporary directory after confirming it contains only test-created files and data. If identity, containment, or ownership is uncertain, leave it in place and request a separate cleanup decision. Never use a broad temp cleanup and never remove `data/`, `instance/`, `frontend/dist/`, model paths, or other project directories.

## Limitations and approval gates

- The launcher is syntax-checked only and has not been executed in this task; no runtime guarantee is claimed.
- No explicit SQLite schema version exists in the current backend. `user_version=0` is only the current SQLite default; structural validation against the current initializer is the meaningful compatibility check. Update the derived expectations if the initializer changes.
- The database digest/runtime ID and process-local file identity detect accidental substitution only. They do not eliminate every filesystem race and are not protection against an adversarial local user. Do not proceed if those values cannot be independently associated with the exact disposable runtime.
- SQLite schema creation and student account/profile test writes need separate approval and must target the printed temporary path only.
- An Admin account is neither needed nor created for student-only verification. Admin testing requires a separately provisioned isolated Admin identity or separate explicit authorization for target-confirmed bootstrap.
- Career draft publishing/restoration is outside student-browser preparation. Do not perform it unless separately approved and the isolated path assertions have passed.
- The browser-control tool's availability does not prove an active browser session or successful UI interaction.
- No MySQL integration, production deployment, or production readiness is established.
