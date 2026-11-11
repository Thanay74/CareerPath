# Phase 2.2F — Runtime Recovery Investigation and Plan

## Decision

The existing runtime is **not safe to resume**: its SQLite database has a different digest from the externally supplied digest and contains student/account and assessment data; its copied career CSV and metadata files are missing. Preserve the runtime unchanged. The project’s canonical catalog pair is present and its current SHA-256 values exactly match the values recorded in the old runtime marker.

The launcher code can prepare a separate, uniquely named runtime without reusing or editing the old runtime. However, this Codex execution environment supplies changing sandbox `TEMP`/`TMP` paths between tool invocations. Therefore a runtime prepared here cannot be relied on to pass the launcher's direct-child temp-root check in a later invocation. Use a normal, stable PowerShell/Python environment for a future approved preparation and serve workflow, and verify the temp root in that same environment before proceeding.

This was a read-only investigation. No database, runtime, catalog, application source, or model artifact was modified. No MySQL connection, server, setup, migration, seed, or test command was run.

## Existing runtime identity and layout

The marker is:

`C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1\.phase2_2f_student_runtime.json`

It records:

- Runtime ID: `ba4386e369c844c69db270dea07762be`
- Runtime root: `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1`
- Project root: `C:\Users\THANAY\Documents\Codex\2026-09-29\files-pasted-by-the-user-build\outputs\CareerPath`
- Canonical CSV digest: `229d6b4ed077e81f2043515a5ca02ea2ffdea72e1d32467899f4e7c3aa021e78`
- Canonical metadata digest: `238800fffa961eb70fd70e028552bd05cc639215a0ccfd2adda8dfc1cee36629`

Observed runtime entries:

| Path | Current state |
|---|---|
| `data\` | Directory; copied career CSV and metadata are absent. |
| `data\career_releases\` | Present and empty. |
| `data\career_active.json` | Absent. |
| `data\career_catalog_managed.json` | Absent. |
| `db\student_test.sqlite3` | Present, 417,792 bytes. |
| `instance\career_drafts\` | Present and empty. |
| `data\career_catalog_activation.lock` | Absent. |
| `instance\career_drafts\catalog.lock` | Absent. |
| `-wal`, `-shm`, `-journal` database sidecars | Absent at inspection. |

The directory listing did not show symlink/reparse attributes on the inspected runtime root or entries. This is only a current filesystem observation, not proof of historical provenance.

## Canonical catalog availability and hashes

Both canonical files exist directly under the project `data` directory. Hashes were computed by reading file bytes with SHA-256; neither file was written.

| Canonical source | SHA-256 | Match with old runtime marker? |
|---|---|---|
| `data\career_knowledge_base.csv` | `229d6b4ed077e81f2043515a5ca02ea2ffdea72e1d32467899f4e7c3aa021e78` | Yes |
| `data\career_metadata.json` | `238800fffa961eb70fd70e028552bd05cc639215a0ccfd2adda8dfc1cee36629` | Yes |

The old marker's catalog hashes match today's canonical files exactly, but that does not explain why the runtime copies disappeared. No cause for their disappearance is established. Do not restore them into the old runtime as part of this plan.

## SQLite read-only findings

Target inspected only at:

`C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1\db\student_test.sqlite3`

The file was opened in SQLite immutable read-only mode for aggregate checks. `PRAGMA quick_check` returned `ok`; 18 application tables were present. Current SHA-256:

`f0f0b3b3496601bc9835276fc5f1ce9316e4afd2a132ed99a874084ec8b27c2f`

The owner-provided earlier attestation was:

`54572b2247428c101768ca822aad645fa60835f9f31e5cbd9ac369da04db548f`

These values differ. The timing and cause of the difference cannot be determined from the available file. Aggregate nonzero counts (no row values or personal data were queried or displayed):

| Table | Rows |
|---|---:|
| `users` | 2 |
| `students` | 2 |
| `academic_records` | 5 |
| `application_errors` | 5 |
| `aptitude_attempt_questions` | 50 |
| `aptitude_attempts` | 2 |
| `aptitude_domain_scores` | 7 |
| `aptitude_questions` | 25 |
| `aptitude_responses` | 25 |
| `assessments` | 8 |
| `recommendation_events` | 4 |
| `recommendations` | 2 |

`sqlite_sequence` contained 3 sequence entries. These records may be test records, but their ownership is not established here. Treat all of them as existing data: do not use these accounts, add records, clean up, or overwrite the file without a separately approved data-preservation plan.

## Python temporary-directory mismatch

The launcher’s `_assert_root_is_safe()` requires the runtime root to be a direct child of `tempfile.gettempdir()` in the Python process that runs the command. In this execution environment:

- Process `TEMP` and `TMP` point under `C:\Users\THANAY\AppData\Local\Packages\sandbox...\AC\Temp`.
- `TMPDIR` is unset.
- `tempfile.gettempdir()` resolves to that sandbox-specific temp path, not the old runtime's parent `C:\Users\THANAY\AppData\Local\Temp`.
- The sandbox-specific GUID path changed across separate tool invocations observed during this investigation.

This explains why the current process refuses the old runtime. It is an environment/root mismatch, not evidence that the launcher's check should be relaxed. A newly prepared runtime in this execution environment would be rooted under its current sandbox temp path and may fail the same-root check in a later process. Future preparation and serve should use the same stable Python installation and environment in a persistent PowerShell session, after verifying `tempfile.gettempdir()` is stable across invocations.

## Preparation-script review

`scripts/phase2_2f_student_runtime.py::_prepare_runtime()`:

1. Checks that the project's canonical CSV and metadata exist and are regular non-link files.
2. Uses `tempfile.mkdtemp(prefix="careerpath_phase22f_student_")` to choose a new unique root; it does not select the old runtime path.
3. Creates only directories under that newly allocated root and copies the two canonical catalog files there.
4. Writes a marker containing the new runtime ID, project/root paths, and copied catalog hashes.
5. On preparation failure, reports the exact partial root and does not automatically delete it.

The `prepare` command then calls `_configure_and_assert(..., mode="prepare")`, which sets `DATABASE_URL` empty and `CAREERPATH_DB` to the new runtime's planned DB path before importing `backend.app`; it verifies SQLite selection, MySQL disabled, exact in-root paths, copied catalog hashes, and that the database file was not created. It does not call `init_db()`, setup, seed functions, or Admin bootstrap. Static inspection of `backend/app.py` shows those mutations are in explicit functions; there is no module-level call to `init_db`, a seed function, or `bootstrap_admin`. The normal request error logger can write only after HTTP requests, and `prepare` starts no server or requests.

The preparation command is therefore **designed to leave the old runtime untouched** and to create only a new isolated runtime with catalog copies and marker. It is still a write operation to a new temporary directory and must not be run until explicitly approved. A failed command may leave a partial directory; inspect the exact path it reports and do not use broad cleanup.

## Proposed procedure and commands — not executed

### 1. Confirm a stable execution environment

From the project root in the normal, persistent PowerShell session intended for both preparation and later serving:

```powershell
python -c "import tempfile; print(tempfile.gettempdir())"
python -c "import tempfile; print(tempfile.gettempdir())"
```

The same stable path should be printed twice. Confirm it is the intended Windows temporary directory and that the session will remain consistent for later commands. Do not override the launcher's root assertion. If values differ, stop and use an approved stable environment.

### 2. Prepare a new runtime only after explicit approval

```powershell
Set-Location "C:\Users\THANAY\Documents\Codex\2026-09-29\files-pasted-by-the-user-build\outputs\CareerPath"
python scripts/phase2_2f_student_runtime.py prepare
```

Expected effects: allocate a new uniquely named `careerpath_phase22f_student_*` directory under the Python temp root; copy canonical CSV/metadata into its `data` directory; create empty DB-parent, release, and draft directories; write a marker; print runtime identity and isolated paths. It must not create a SQLite DB, connect to MySQL, seed, create users, start Flask, or change the old runtime. Record the exact root and runtime ID printed. If it fails, preserve and inspect only the exact reported partial root.

### 3. Review before any database write

Independently inspect the new marker, runtime paths, and copied-file hashes; confirm all paths are under the newly printed root and the existing old runtime remains untouched. Then stop for approval. Do not proceed directly to schema initialization.

### 4. Schema initialization is a separate approval gate

Only after explicit approval of the exact new runtime and database path should the owner review a schema-only `backend.setup` invocation with `DATABASE_URL` set to an explicit SQLite URL and `--confirm-target` equal to the resolver's credential-free identity. The operation creates/upgrades tables and writes the SQLite file; it is not part of `prepare`. It does not seed education rows, aptitude questions, or an Admin account. Resolve and verify the exact URL/identity against the current `backend/database_config.py` and `backend/setup.py` immediately before any approved invocation. Do not run against the old runtime or a project-local fallback.

After separate schema approval and successful initialization, record the new DB hash externally and run the launcher's read-only `serve` preflight using the new runtime ID and that independently recorded hash. Any mismatch must stop the process. Aptitude endpoints will lack questions unless a separate fixture-seeding operation is explicitly approved; do not seed implicitly.

## Approval points

1. **Preparation approval:** permission to run the `prepare` command, which writes a new temporary runtime and copies canonical catalog files into it. No approval to modify or clean the existing runtime is implied.
2. **Schema approval:** permission to initialize tables in the exact new runtime SQLite file. This is a distinct database write.
3. **Fixture approval:** separate permission if education catalog rows or aptitude fixture questions are needed; neither is included in schema-only setup.
4. **Runtime/test approval:** permission to start the isolated server and create identified test accounts/assessments, with cleanup limited to only records created during that run after ownership and isolation are established.

## Limitations

- The old DB hash mismatch and existing data's origin remain unknown.
- The missing copied catalog files' removal cause remains unknown.
- SQLite integrity/schema and aggregate counts were read-only checks; no API behavior was verified.
- This environment's changing sandbox temp root prevents safe reuse of a runtime across separate invocations.
- No MySQL, Flask, browser, migration, seed, test, or production workflow was run or verified.

**Recommendation: preserve the current runtime and do not resume testing against it. A new runtime is structurally supported by the preparation script, but prepare it only after approval and from a stable owner-controlled PowerShell/Python environment whose temp root remains fixed for preparation and subsequent serve.**
