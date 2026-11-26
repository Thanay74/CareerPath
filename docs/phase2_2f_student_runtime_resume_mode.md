# Phase 2.2F — Guarded Resume Mode

**Status:** Implemented and covered by isolated temporary-database tests. The resume command has not been run against the current student-test runtime. No MySQL connection or write to the current runtime was made for this change.

## Why this mode exists

The original `serve` command intentionally accepts only a clean initialized database. It refuses to start after student records have been created, which prevents accidental reuse but also prevents safely continuing a test run after a server restart. The separate `resume` command is an explicit path for preserving and reopening an already-populated student-only test database.

The existing `serve` behavior remains unchanged: it rejects accounts, student data, assessment/recommendation/event/error/audit rows, and retained sequence history. `prepare` also remains preflight-only.

## Resume checks

`resume` still uses the same launcher validations as `serve`:

- Exact runtime ID, direct-child temporary-root check, and expected project root.
- Database target resolved in-process to the exact runtime SQLite file, with MySQL disabled and no configuration error.
- An explicit external SHA-256, regular-file and non-reparse checks, no WAL/SHM/journal sidecars, read-only SQLite URI, and hash checks before and after validation.
- Exact schema shape derived from `backend/app.py::init_db`: tables, columns/types, primary and foreign keys, unique and check constraints, no extra views/triggers/indexes, `user_version=0`, `quick_check`, and `foreign_key_check`.
- Catalog, release pointer, marker, release, lock, and draft path containment and catalog-reader validation.
- Existing data must include at least one student account and an equal number of student profiles; every profile must be linked to a user. Any administrator account or Admin audit record makes resume fail closed.

The resume validation is read-only. It does not initialize or repair schema, seed education or aptitude data, bootstrap an Admin, or remove records. Once the server starts, ordinary API requests can write to the exact isolated SQLite file as part of student testing.

## Start a resumed test runtime

Stop all processes that may write to the SQLite file first. Confirm that `.sqlite3-wal`, `.sqlite3-shm`, and `.sqlite3-journal` sidecars are absent. Compute the current database hash only after those checks; keep it outside the runtime and do not use a hash from before later student writes.

For the currently prepared runtime, the marker records:

```powershell
$runtimeRoot = 'C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_1tftni0k'
$runtimeId = 'c6d3131d073d45cabfdff2eb5aaad441'
$dbPath = Join-Path $runtimeRoot 'db\student_test.sqlite3'
$dbSha256 = (Get-FileHash -LiteralPath $dbPath -Algorithm SHA256).Hash.ToLowerInvariant()
```

After the backend is stopped and the database path/sidecars have been checked, run from the project root:

```powershell
python scripts/phase2_2f_student_runtime.py resume `
  --runtime-root $runtimeRoot `
  --runtime-id $runtimeId `
  --expected-database-sha256 $dbSha256 `
  --confirm-existing-student-data `
  --port 5000
```

The explicit confirmation flag is mandatory. Successful output binds only to `127.0.0.1:5000`; any failed preflight returns `ISOLATION SERVER REFUSED` before Flask is bound. Stop the foreground server with Ctrl+C. After any writes, stop it and establish a fresh external hash before a later resume.

The latest browser registration attempt displayed `Failed to fetch`; it had no successful API response, so whether the test account was created is unverified. Do not retry the same registration until the isolated API is available and the account outcome is checked. The hash observed before that attempt is not an attestation for subsequent use.

## Verification performed for this change

Command:

```text
python -B -m unittest discover -s tests -p test_phase2_2f_student_runtime_resume.py -v
```

Result: **9 tests passed.** The tests create the schema and sample student/Admin rows only in per-test temporary SQLite files under `tests/`, verify validation leaves the database hash unchanged, ensure default `serve` still rejects populated data, and cover resume confirmation and student-only restrictions. The test-created directories and databases were removed by the tests.

The first attempt used Python's sandbox temporary root and failed with access-denied errors before creating a database; cleanup of those sandbox temporary folders was also denied by the environment. The tests were then directed to temporary folders under the writable project `tests/` directory and passed. No broad cleanup was attempted. `git diff --check` passed, with only Git's line-ending normalization warning for the modified Python script.

The current runtime's database was not opened, hashed again, or modified by these tests. The new resume mode itself has not been run. No MySQL, browser workflow, or production verification is claimed.

## Limits

- Resume proves the configured file and schema match the supplied checks; the runtime marker and hash are accidental-substitution controls, not an adversarial trust anchor.
- This is for the explicitly approved local student-test runtime only. It does not authorize MySQL, another database, Admin workflows, catalog publishing/restoration, or production use.
- No browser journey, account switching, MySQL integration, or production readiness is established by this code change.
