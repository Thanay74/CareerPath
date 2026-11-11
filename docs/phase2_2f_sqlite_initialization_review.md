# Phase 2.2F — Isolated SQLite Initialization Review

## Scope and evidence

This is a static review and a proposed procedure only. No setup, initializer, seed, test, server, browser, SQLite, or MySQL command was run. The runtime path and ID below are owner-provided; their current filesystem state was not independently verified.

- Runtime root: `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1`
- Runtime ID: `ba4386e369c844c69db270dea07762be`
- Intended database: `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1\db\student_test.sqlite3`
- Inspected: `backend/setup.py`, `backend/database_config.py`, `backend/app.py` (`connect_db`, `seed_education_catalog`, `seed_aptitude_questions`, `init_db`, `bootstrap_admin`, `/api/education/catalog`, `/api/aptitude/questions`), `backend/education_catalog.py`, `backend/aptitude_bank.py`, `scripts/phase2_2f_student_runtime.py`, and `docs/phase2_2f_isolated_student_runtime.md`.

## Findings

### Setup command and target guard

`backend/setup.py::main` requires exactly one action. Mutating actions first resolve the target from `application.DATABASE_URL` and, only when that is empty, `CAREERPATH_DB`; they then call `validate_setup_target` before dispatching to schema creation, seeding, or Admin bootstrap. The target must match `--confirm-target` exactly. The known `careerpath` production name is rejected. A non-test target additionally requires `--allow-non-test-target`; the requested filename `student_test.sqlite3` is classified as a test target. The setup command prints driver, host, and database path/name, not credentials.

`backend/app.py` calls `load_dotenv()` during import. The launcher sets `DATABASE_URL` to an explicit empty string and `CAREERPATH_DB` to the runtime database path before importing the app; `load_dotenv()` uses the existing environment by default and therefore should not replace these values with `.env` contents. `DATABASE_URL` takes precedence over `CAREERPATH_DB` in the app's configuration. Setting the former explicitly empty is important: a non-empty MySQL URL would select MySQL and disregard the SQLite path. Invalid configured URLs are kept as configuration errors and `connect_db()` refuses to connect rather than falling back.

`DB_PATH` is an application module variable resolved at import time; the source does not read an environment variable named `DB_PATH`. It is set from `DATABASE_TARGET.sqlite_path`, or falls back to the project-local `careerpath.sqlite3` only when no valid target was resolved. The launcher asserts both the resolved target and `application.DB_PATH` equal the requested runtime path. In `init_db()`'s SQLite branch, the connection is opened directly with `sqlite3.connect(DB_PATH)`; seed actions use `application.connect_db()`. Thus environment selection must happen before importing `backend.app`, and the target confirmation must be kept identical for every setup invocation.

### Effects of proposed actions

| Proposed action | Implementation and effects | Expected data/files |
|---|---|---|
| `--schema` | Calls `backend.app::init_db`. On SQLite it opens the configured `DB_PATH`, checks for a legacy `assessments` table before DDL, creates the schema, performs compatibility `ALTER TABLE` operations if columns are absent, commits, and closes. It does not call either seed or `bootstrap_admin`. | Creates `db\student_test.sqlite3` and the 18 application tables listed below, plus SQLite's `sqlite_sequence` internal table because several tables use `AUTOINCREMENT`. No project database or catalog file is intentionally selected by this target. |
| `--seed-aptitude-fixture` | Calls `seed_aptitude_questions` through `_with_connection`. It imports `backend.aptitude_bank.QUESTIONS` and uses `INSERT OR IGNORE` for SQLite. Existing question IDs are not updated or deleted. | Adds fixture rows to `aptitude_questions` only. No account/Admin rows are created. |
| `--seed-education` (optional for this student flow) | Calls `seed_education_catalog` through `_with_connection`. It reads `backend.education_catalog.EDUCATION_CATALOG`, inserts missing programs, specializations, subjects, and join rows, and does not delete rows. | May add rows to `education_programs`, `education_specializations`, `education_subjects`, `education_program_subjects`, and `education_specialization_subjects`. No account/Admin rows are created. |
| `--bootstrap-admin` | Calls `bootstrap_admin`, which may insert a first Admin when configured credentials are present. | **Not proposed. Do not run.** |

SQLite `init_db()` has a legacy-assessment guard before its schema statements. If an existing `assessments` table lacks `assessment_type`, it stops before DDL. Still, this initialization is a mutating operation: only proceed if the exact target file is confirmed absent and its parent/path is confirmed to be the stated disposable runtime. Do not point it at an existing SQLite file.

### Which fixtures student workflows need

- `/api/education/catalog` reads and returns `backend.education_catalog.EDUCATION_CATALOG` directly. The ordinary education-level, stream/degree, specialization, and subject choices served by this endpoint do **not** require `--seed-education` in the reviewed code. The database seed is available for database-backed catalog consumers, but adding it is optional for the currently inspected student flow.
- `/api/aptitude/questions` reads active questions from MySQL/SQLite table `aptitude_questions`, filters them by the requested education level, and removes answer keys using `backend.aptitude_bank.public_question`. An empty table produces no aptitude questions. For the aptitude assessment flow, the explicit `--seed-aptitude-fixture` step is required unless questions are provisioned through another separately reviewed mechanism. The fixture is project-level exercise content, not a professionally validated psychometric instrument.
- Schema initialization creates tables but does not seed either catalog. Normal app import/startup does not call `init_db`, either seed function, or `bootstrap_admin`.

## Expected application tables

The expected set is derived from the SQLite `CREATE TABLE` statements in `backend/app.py::init_db` and independently matches `scripts/phase2_2f_student_runtime.py::EXPECTED_TABLES`:

`users`, `students`, `academic_records`, `assessments`, `recommendations`, `aptitude_questions`, `aptitude_attempts`, `aptitude_attempt_questions`, `aptitude_responses`, `aptitude_domain_scores`, `education_programs`, `education_specializations`, `education_subjects`, `education_program_subjects`, `education_specialization_subjects`, `recommendation_events`, `application_errors`, `admin_audit_logs`.

`sqlite_sequence` is an SQLite internal table expected after creation of AUTOINCREMENT tables. The student-runtime validator additionally checks exact columns/types, primary keys, foreign keys and delete actions, unique constraints, declared CHECK constraints, absence of unexpected tables/views/triggers/explicit indexes, `PRAGMA user_version=0` (the current initializer does not assign a schema version), `quick_check`, `foreign_key_check`, absence of student/account/event/error/audit data and relevant sequence history, absence of journal/WAL sidecars, and an externally supplied SHA-256. Education lookup rows and aptitude fixture rows are permitted.

## Proposed PowerShell procedure — NOT EXECUTED

These commands are a proposal for a later explicitly approved initialization. Run them from the repository root in one PowerShell session. They do not include an Admin bootstrap, MySQL command, or project-local database fallback. Stop if any assertion fails. The initial absence checks are essential because `init_db()` can create a missing SQLite file and can alter an existing schema.

```powershell
$ErrorActionPreference = 'Stop'
$runtimeRoot = 'C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1'
$runtimeId = 'ba4386e369c844c69db270dea07762be'
$dbFile = Join-Path $runtimeRoot 'db\student_test.sqlite3'
$runtimeRoot = [System.IO.Path]::GetFullPath($runtimeRoot)
$dbFile = [System.IO.Path]::GetFullPath($dbFile)
$tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\')
$markerPath = Join-Path $runtimeRoot '.phase2_2f_student_runtime.json'

if (-not (Test-Path -LiteralPath $runtimeRoot -PathType Container)) { throw 'Specified runtime root is missing.' }
if ([System.IO.Path]::GetDirectoryName($runtimeRoot).TrimEnd('\') -ne $tempRoot) { throw 'Runtime root is not a direct child of the OS temp directory.' }
if ((Split-Path -Leaf $runtimeRoot) -ne 'careerpath_phase22f_student_uvqnduq1') { throw 'Runtime root name does not match the supplied runtime.' }
if (-not (Test-Path -LiteralPath $markerPath -PathType Leaf)) { throw 'Runtime marker is missing.' }
$marker = Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
if ($marker.runtime_id -ne $runtimeId -or $marker.runtime_root -ne $runtimeRoot) { throw 'Runtime marker identity does not match the supplied runtime.' }
if ($marker.project_root -ne [System.IO.Path]::GetFullPath((Get-Location).Path)) { throw 'Run from the project root recorded in the marker.' }
foreach ($path in @($runtimeRoot, (Join-Path $runtimeRoot 'db'), $markerPath)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required runtime path is missing: $path" }
    if ([System.IO.File]::GetAttributes($path) -band [System.IO.FileAttributes]::ReparsePoint) { throw "Reparse point is not permitted: $path" }
}
if (Test-Path -LiteralPath $dbFile) { throw 'Database already exists; do not run schema initialization on it.' }
foreach ($suffix in @('-wal', '-shm', '-journal')) {
    if (Test-Path -LiteralPath ($dbFile + $suffix)) { throw "Unexpected SQLite sidecar: $suffix" }
}

$env:DATABASE_URL = ''
$env:CAREERPATH_DB = $dbFile
$targetIdentity = 'sqlite:///' + ($dbFile -replace '\\', '/')
if ($targetIdentity -ne 'sqlite:///C:/Users/THANAY/AppData/Local/Temp/careerpath_phase22f_student_uvqnduq1/db/student_test.sqlite3') { throw 'Resolved confirmation identity differs from the approved path.' }

python -m backend.setup --schema --confirm-target $targetIdentity
if ($LASTEXITCODE -ne 0) { throw 'Schema initialization failed; stop and inspect the reported error. Do not retry blindly.' }

python -m backend.setup --seed-aptitude-fixture --confirm-target $targetIdentity
if ($LASTEXITCODE -ne 0) { throw 'Aptitude fixture seeding failed; stop and inspect the reported error.' }

# Optional only if a later workflow is confirmed to query the normalized SQL education tables:
# python -m backend.setup --seed-education --confirm-target $targetIdentity
# if ($LASTEXITCODE -ne 0) { throw 'Education lookup seeding failed; stop and inspect the reported error.' }
```

The `--schema` and `--seed-aptitude-fixture` invocations are separate and each repeats exact target validation before its action. The optional education seed should not be included just to populate the current education dropdown: the inspected endpoint is file-backed. Do not add `--allow-non-test-target` or `--bootstrap-admin`.

### Read-only checks before recording a database hash — NOT EXECUTED

After approved initialization and seeding, close all setup processes. Before recording the hash for later serve verification, the following proposed read-only check uses SQLite URI `mode=ro&immutable=1`; it does not create a database or write records. It checks the application table set, SQLite integrity, foreign keys, expected emptiness of account/student/activity tables, and that aptitude questions were seeded. `serve` remains the more complete structural validator and must still pass before it binds Flask.

```powershell
$verifySqlite = @'
import sqlite3, sys
from pathlib import Path

expected = {
    "users", "students", "academic_records", "assessments", "recommendations",
    "aptitude_questions", "aptitude_attempts", "aptitude_attempt_questions",
    "aptitude_responses", "aptitude_domain_scores", "education_programs",
    "education_specializations", "education_subjects", "education_program_subjects",
    "education_specialization_subjects", "recommendation_events", "application_errors",
    "admin_audit_logs",
}
empty = {
    "users", "students", "academic_records", "assessments", "recommendations",
    "aptitude_attempts", "aptitude_attempt_questions", "aptitude_responses",
    "aptitude_domain_scores", "recommendation_events", "application_errors",
    "admin_audit_logs",
}
path = Path(sys.argv[1]).resolve(strict=True)
conn = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
try:
    objects = conn.execute("SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
    tables = {name for kind, name in objects if kind == "table"}
    if tables != expected:
        raise SystemExit(f"table mismatch; missing={sorted(expected-tables)} unexpected={sorted(tables-expected)}")
    if any(kind in {"view", "trigger"} for kind, _ in objects):
        raise SystemExit("unexpected view or trigger")
    if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise SystemExit("quick_check failed")
    if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise SystemExit("foreign_key_check failed")
    nonempty = {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in sorted(empty)}
    nonempty = {t: n for t, n in nonempty.items() if n}
    if nonempty:
        raise SystemExit(f"unexpected student/account/activity rows: {nonempty}")
    if conn.execute("SELECT COUNT(*) FROM aptitude_questions WHERE is_active=1").fetchone()[0] == 0:
        raise SystemExit("no active aptitude fixture questions")
finally:
    conn.close()
print("Read-only database checks passed; no student/account/activity rows found.")
'@
$verifySqlite | python - $dbFile
if ($LASTEXITCODE -ne 0) { throw 'Read-only SQLite checks failed; do not record a serve hash or start the app.' }

# Only after the checks pass and all connections are closed:
$dbSha256 = (Get-FileHash -LiteralPath $dbFile -Algorithm SHA256).Hash
"Database SHA-256: $dbSha256"
```

Retain the digest outside the mutable runtime and associate it with this exact runtime root and runtime ID. The currently documented `serve` command requires that externally retained digest and then performs its own read-only validation before starting Flask. This report does not execute `serve` or establish that the current runtime satisfies these checks.

## Isolation conclusion and recommendation

**Source-inspection conclusion:** The proposed setup flow can select the specified SQLite path without selecting MySQL or the project-local database, provided the environment is set before Python imports `backend.app`, the DB file and sidecars are absent, and each command's exact `--confirm-target` matches the resolved path. MySQL selection requires a non-empty supported MySQL `DATABASE_URL`; the explicit empty value prevents it, while `CAREERPATH_DB` supplies the SQLite target. `DB_PATH` is not independently read from an environment variable.

**GO / NO-GO: GO for a separately approved initialization, conditional on the PowerShell absence/containment checks and review of their output immediately before execution.** This is not approval to run the commands in this task. If the target file exists, a reparse point is encountered, the setup output names anything other than the exact SQLite target, or any guard fails, stop. No MySQL integration or runtime state has been verified here.

## Limitations

- Owner-provided preparation preflight result, runtime path, and runtime ID were not rerun or independently authenticated in this read-only task.
- No database connection or initialization was made, so no tables, fixture counts, schema validity, SHA-256, or current target-file absence is confirmed.
- `init_db()` is general-purpose setup code with compatibility DDL, not a purpose-built create-only command. Its legacy guard reduces a known migration hazard but does not substitute for confirming the exact fresh file target.
- The education catalog is file-backed for the inspected student endpoint. Whether another unreviewed client uses normalized education tables was not established; seed education only if that consumer is identified.
- The read-only inline check above is a proposed narrow pre-hash sanity check. The launcher’s `serve` validator remains the authoritative structural check before server startup; neither has been executed as part of this task.
- No accounts, students, Admin identity, test records, database objects, or catalog state were created or changed in this task.
