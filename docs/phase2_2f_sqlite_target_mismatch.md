# Phase 2.2F — SQLite Setup Target Mismatch Investigation

## Scope

Read-only source review of the reported refusal:

> `Setup refused: The production CareerPath database name is blocked for setup commands`

The reported intended target is `C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1\db\student_test.sqlite3`, with `DATABASE_URL=''` and `CAREERPATH_DB=$dbFile` in the invoking environment. No setup command, application import for runtime diagnosis, database connection, or database inspection was performed. No configuration or environment value was changed.

## Source findings

### Exact guard condition

`backend/database_config.py::validate_setup_target` raises the reported message only when this predicate is true:

```python
target.database.strip().casefold() == "careerpath" or (
    target.sqlite_path and target.sqlite_path.stem.strip().casefold() == "careerpath"
)
```

It runs before the confirmation-identity check. An incorrect `--confirm-target` would instead produce `--confirm-target must exactly match the resolved credential-free target identity`; it does not produce the observed production-name refusal.

### Resolved target behavior

`backend/database_config.py::resolve_database_target` gives a non-empty `DATABASE_URL` precedence over its `sqlite_path` argument. If the URL is empty and `CAREERPATH_DB` is provided, it resolves that path and creates a SQLite target whose `database` is the full path and whose `sqlite_path.stem` is the filename stem.

For the reported intended target, the stem is `student_test`, and `target.database` is the full temporary path. Neither equals `careerpath`; the production guard should therefore allow that target to proceed to the confirmation and test-target checks. The expected exact Windows SQLite confirmation identity is:

```text
sqlite:///C:/Users/THANAY/AppData/Local/Temp/careerpath_phase22f_student_uvqnduq1/db/student_test.sqlite3
```

The setup command derives and validates this identity itself. If it were wrong, the distinct confirmation error above would be expected.

### Configuration and CLI path

`backend/app.py` calls `load_dotenv()` and then captures `DATABASE_URL` from `os.environ`; it resolves the target using `DATABASE_URL` first and `CAREERPATH_DB` second. `DB_PATH` is derived from that resolved target (or falls back to project-root `careerpath.sqlite3` only if the target is not a valid SQLite target). The source does not read an environment variable named `DB_PATH`.

`python -m backend.setup` imports `backend.setup`, which imports `backend.app` as `application`. It does not use `scripts/phase2_2f_student_runtime.py` or share that launcher process's in-memory module overrides. It does inherit the child process environment. The launcher sets `DATABASE_URL` empty and `CAREERPATH_DB` to its runtime path before its own app import; that assignment is process-local and is not persisted into a later PowerShell session or a separate Python process.

In the setup CLI, `backend/setup.py::main` re-resolves its target from `application.DATABASE_URL` and the current process's `CAREERPATH_DB`. It calls `validate_setup_target` before dispatching any operation. For `--schema`, the application initializer uses the already-imported `application.DB_PATH`; it does not independently use the CLI's local `target` variable. For seed actions, `_with_connection` uses `application.connect_db()` and the same imported app configuration.

If PowerShell truly launched the failing `python -m backend.setup` process with the stated empty `DATABASE_URL` and exact `CAREERPATH_DB`, source logic predicts the temporary SQLite target and does not predict this production guard error. The observed message therefore indicates that the effective target at guard time differed from the stated path, but this task did not inspect process environment or runtime state to establish how.

## Likely cause and alternatives

**Most likely: effective-target/environment mismatch.** At the time setup resolved its target, it likely saw either:

1. A non-empty `DATABASE_URL` selecting a MySQL schema named `careerpath` (this takes precedence over `CAREERPATH_DB`); or
2. No usable `CAREERPATH_DB`, causing the app's allowed default target to be project-local `careerpath.sqlite3`; or
3. A `CAREERPATH_DB` pointing to a SQLite file whose stem is exactly `careerpath`.

The first two cases can occur if the setup command was launched from another PowerShell session/process than the one where the runtime environment was set, or if the actual inherited environment differed. The supplied intended filename itself cannot trigger the production-name condition.

**Not supported by the observed error:** a wrong `--confirm-target` by itself. That check runs after the production-name guard and has a different message.

**Not established:** whether environment propagation failed, a stale/non-empty `DATABASE_URL` was present, an old application process/configuration was involved, or the executed source differed from the inspected repository. No command output showed the setup target line because validation stopped before it is printed. No process environment or alternate checkout was examined. The evidence is insufficient to identify one root cause conclusively.

## Safest corrective approach

Do not alter or bypass `validate_setup_target`. Before any separately approved initialization, establish the resolved target without opening a database connection, then run setup only in the same PowerShell process/session where the values are set:

1. Set `DATABASE_URL` explicitly to the empty string and `CAREERPATH_DB` to the exact full runtime database path immediately before launching Python.
2. Confirm, without displaying any secret, that `DATABASE_URL` is empty and `CAREERPATH_DB` equals the expected path.
3. Derive the confirmation string from the resolved absolute path using forward slashes, yielding exactly the identity shown above.
4. Use a read-only target-resolution diagnostic based on `backend.database_config.resolve_database_target` (which only parses/resolves configuration) to confirm driver `SQLite`, `mysql=False`, full path and identity before invoking setup. Do not call `connect_db`, `init_db`, or a seed function in that diagnostic.
5. During any later authorized setup, require setup's printed target to say SQLite/local and name the exact `student_test.sqlite3` target. Stop on any discrepancy; do not add `--allow-non-test-target` or skip the confirmation guard.

The setup refusal is fail-closed: the source shows validation occurs before setup action dispatch. No evidence indicates that this specific refusal reached `init_db` or a seed function, but database state was not inspected and no claim about current files/tables is made.

## Recommendation

**NO-GO for database initialization at this time.** The reason for the discrepancy is not conclusively established from the reported error alone. First confirm the resolved target through a read-only configuration diagnostic in the exact PowerShell session that will later run setup. If it resolves to the approved temporary SQLite path and the existing runtime/file-safety checks pass, the exact-target guard can remain enabled and the separate initialization approval can be revisited. Do not initialize until then.

## Safety statement

Only source and documentation were inspected. This report did not run setup, import the Flask application for a runtime probe, connect to SQLite or MySQL, inspect database contents, or modify code, environment, databases, catalogs, or runtime directories.
