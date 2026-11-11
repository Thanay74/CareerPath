# Phase 2.2F — Isolated Student Runtime Startup Checklist

## Current review status

This checklist is based on static inspection of `scripts/phase2_2f_student_runtime.py` and `docs/phase2_2f_isolated_student_runtime.md`, plus read-only inspection of the supplied runtime files. The server was not started and no HTTP request was made.

Owner-reported schema setup results: exit code 0, SQLite integrity `ok`, 18 expected application tables, checked account/activity tables empty, MySQL disabled.

Read-only runtime observations in this review:

- Marker runtime ID matches the supplied ID: `ba4386e369c844c69db270dea07762be`.
- Marker root is `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1` and its recorded project root matches this checkout.
- Current SQLite file SHA-256: `54572b2247428c101768ca822aad645fa60835f9f31e5cbd9ac369da04db548f`.
- SQLite file exists; `-wal`, `-shm`, and `-journal` sidecars are absent.
- The active catalog pointer and managed marker are absent; the runtime release directory and draft directory exist and are empty. Activation and draft lock files are absent.
- Runtime catalog and database paths inspected are beneath the supplied runtime root; no reparse-point attributes were found on the inspected existing paths.

**Blocker:** `scripts/phase2_2f_student_runtime.py::_assert_root_is_safe` requires the runtime root to be a direct child of the *same Python process's* `tempfile.gettempdir()`. In this review environment, `GetTempPath()` resolved to a sandbox-specific temp directory, not `C:\Users\THANAY\AppData\Local\Temp`. Therefore this environment would reject the supplied root. Verify the value using the exact PowerShell/Python installation intended to run the server before attempting startup. The owner-reported earlier preparation pass is not independently enough to establish that the current launcher process will use the same temp root.

## Checklist before startup

1. **Use the intended project checkout and PowerShell session.** Confirm the current directory is this checkout's project root.
2. **Confirm the launcher's temp-root invariant with the same `python` executable:**

   ```powershell
   python -c "import tempfile; print(tempfile.gettempdir())"
   ```

   The resolved temp directory must be exactly the parent of `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1`. Also confirm the runtime root remains a direct child of that temp directory, has the `careerpath_phase22f_student_` prefix, is not a symlink/reparse point, and is not inside the project checkout. If not, stop: do not relocate or recreate the runtime as part of this checklist.

3. **Confirm marker identity:** the marker `.phase2_2f_student_runtime.json` must match the exact runtime path, current project root, and runtime ID shown above. The marker is mutable and is an accidental-substitution check, not a trust anchor.
4. **Confirm database file and digest:** the exact DB path is `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1\db\student_test.sqlite3`. If the file changes after this review, calculate and record its new SHA-256 only after setup/other writers have exited and no sidecars exist. Keep the independently recorded digest outside the runtime. The current recorded digest is shown above.
5. **Check that the DB has no `-wal`, `-shm`, or `-journal` sidecars.** The launcher refuses startup if a sidecar is present.
6. **Do not run schema or seed commands as part of startup.** Serve mode performs read-only SQLite validation (`mode=ro&immutable=1`) for the expected structure, constraints, integrity, foreign keys, allowed fixture tables, user-data emptiness, and supplied hash. If any check fails, it refuses to start; it does not repair or reseed.

## Database/environment protection

In `_configure_and_assert(..., mode="serve")`, the launcher sets `DATABASE_URL` to an explicit empty value and `CAREERPATH_DB` to the runtime DB path **inside the launcher process before importing `backend.app`**. It disables bytecode writes before backend imports. The app must resolve to SQLite, `USE_MYSQL=False`, no config error, and the exact runtime DB path. Before returning a connection to a request, the installed guard rechecks the SQLite target and opens the existing file with SQLite `mode=rw`, which refuses to create a replacement if the file disappears.

The setup operation previously used an explicit SQLite URL because PowerShell 5.1 removes an empty environment variable. Serve mode does not depend on the parent shell's `DATABASE_URL`: the launcher sets it in its Python process before app import. Its assertions fail closed if the app does not resolve to the expected SQLite file. The server command below does not invoke `backend.setup`, `init_db`, a migration, a seed function, or Admin bootstrap.

## Runtime path redirection

The launcher derives every runtime storage path from the supplied root and installs these module path overrides before startup:

| Purpose | Selected runtime path |
|---|---|
| SQLite database | `db\student_test.sqlite3` |
| Career CSV and metadata | `data\career_knowledge_base.csv`, `data\career_metadata.json` |
| Active manifest and managed marker | `data\career_active.json`, `data\career_catalog_managed.json` |
| Releases and activation lock | `data\career_releases\`, `data\career_catalog_activation.lock` |
| Admin drafts and draft lock | `instance\career_drafts\`, `instance\career_drafts\catalog.lock` |

The launcher checks these paths for containment and reparse components. It validates the copied canonical catalog bytes in canonical-bootstrap mode. In managed mode it validates the selected release through the existing catalog reader. The current observed state is canonical-bootstrap: no pointer/managed marker, empty release directory, and empty draft directory. The setup subprocess itself did not apply these path overrides; this checklist applies to the dedicated `serve` launcher. Schema-only setup used the explicitly confirmed SQLite DB target and did not use catalog or draft storage.

## Exact supported serve command

**Run only after resolving the temp-root blocker above and obtaining the separate approval to start the runtime.** From the project root, using the intended Python and the exact runtime ID/database digest:

```powershell
python scripts/phase2_2f_student_runtime.py serve --runtime-root "C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1" --runtime-id "ba4386e369c844c69db270dea07762be" --expected-database-sha256 "54572b2247428c101768ca822aad645fa60835f9f31e5cbd9ac369da04db548f" --port 5000
```

The command runs preflight before binding. Expected successful output is:

```text
Isolated student runtime serving on http://127.0.0.1:5000
```

An identity, path, database, catalog, or SHA mismatch should instead produce `ISOLATION SERVER REFUSED: ...` and a nonzero result. Do not retry by changing hashes, paths, or guards until the mismatch is investigated.

The server runs in the foreground. Stop it with **Ctrl+C** in that same terminal and wait for the process to exit. Do not delete or clean up the runtime as part of stopping it.

## Remaining workflow limitation

The reported operation was schema-only. It did not seed aptitude questions. The student education catalog endpoint is file-backed, but `/api/aptitude/questions` reads `aptitude_questions`; that table will be empty unless the fixture is seeded later through a separately approved action. Startup must not silently seed it. This checklist does not start the frontend or verify browser behavior.

## Decision

**NOT READY TO START from the current execution environment.** The exact direct-child temp-root check is not satisfied here because this process reports a sandbox temp directory. If the intended user's Python reports `C:\Users\THANAY\AppData\Local\Temp` and all marker/hash/path checks still match immediately before launch, the command above is the supported student-runtime command, subject to separate approval. No server, database connection, HTTP request, schema mutation, seed, account creation, or catalog operation was performed for this checklist.
