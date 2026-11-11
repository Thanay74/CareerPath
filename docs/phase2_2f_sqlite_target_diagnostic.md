# Phase 2.2F — Read-Only SQLite Target Resolution Diagnostic

## Source findings

`backend/database_config.py::resolve_database_target` selects a non-empty `DATABASE_URL` before considering `CAREERPATH_DB`. With an empty URL and the supplied absolute `CAREERPATH_DB`, it returns a local SQLite target. For the approved target, its credential-free identity should be:

```text
sqlite:///C:/Users/THANAY/AppData/Local/Temp/careerpath_phase22f_student_uvqnduq1/db/student_test.sqlite3
```

`backend/database_config.py::validate_setup_target` blocks a target only when its database name is exactly `careerpath`, or when a SQLite file's stem is exactly `careerpath`. The approved file stem is `student_test`, so it does not satisfy the production-name condition. A bad `--confirm-target` is checked separately and produces a different error.

`backend/app.py` calls `load_dotenv()` before reading `DATABASE_URL` and `CAREERPATH_DB` into module globals. `backend/setup.py` imports `backend.app` before its CLI function, then independently resolves the target using the app's captured `DATABASE_URL` and the current process's `CAREERPATH_DB`. It requires explicit `--confirm-target` before a mutating operation. The read-only diagnostics below intentionally avoid importing `backend.app` and do not call a connection, initializer, or seed.

## Minimal diagnostic — proposed, not executed

Run from the project root in the same PowerShell session intended for a later setup. This diagnostic sets its own process environment before importing only `backend.database_config.resolve_database_target`. It prints no inherited URL, username, password, or other secret.

```powershell
$targetDiagnostic = @'
import os
from pathlib import Path

approved = Path(r"C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1\db\student_test.sqlite3").resolve()
os.environ["DATABASE_URL"] = ""
os.environ["CAREERPATH_DB"] = str(approved)

from backend.database_config import resolve_database_target

target = resolve_database_target(
    os.environ["DATABASE_URL"],
    os.environ["CAREERPATH_DB"],
    allow_default=False,
)
resolved_path = target.sqlite_path.resolve() if target.sqlite_path else None
matches = resolved_path == approved
print(f"driver={target.driver}")
print(f"mysql_enabled={target.mysql}")
print(f"sqlite_path={resolved_path}")
print(f"target_identity={target.identity}")
print(f"matches_approved_path={matches}")
if target.driver != "SQLite" or target.mysql or not matches:
    raise SystemExit(2)
'@
$targetDiagnostic | python -
if ($LASTEXITCODE -ne 0) { throw 'Target diagnostic failed; do not initialize a database.' }
```

### Expected output

```text
driver=SQLite
mysql_enabled=False
sqlite_path=C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1\db\student_test.sqlite3
target_identity=sqlite:///C:/Users/THANAY/AppData/Local/Temp/careerpath_phase22f_student_uvqnduq1/db/student_test.sqlite3
matches_approved_path=True
```

The diagnostic has no database access: it resolves a path and constructs a `DatabaseTarget` object only. It does not import the Flask app or run the setup CLI. Its environment assignments exist only in that Python process; they do **not** persist to the PowerShell parent. If a later, separately approved setup is considered, set the same two values in the PowerShell session itself before launching Python, and keep them set for every setup subprocess. The setup process must then print its target as SQLite/local with the approved full path and receive the exact `--confirm-target` identity above. Do not proceed if its output differs.

## How a different setup target could arise

- If the setup process inherits a non-empty supported `DATABASE_URL`, `resolve_database_target` gives it precedence and ignores `CAREERPATH_DB`. A MySQL URL naming the `careerpath` schema reaches the explicit production-name guard. The diagnostic overwrites the URL within its own child process, so it confirms the expected resolution under the required explicit settings; it cannot report the prior process's inherited URL.
- If `CAREERPATH_DB` is missing while `DATABASE_URL` is empty, `backend.setup` calls the resolver with `allow_default=False`, which should refuse with “No explicit database target is configured” before setup. `backend.app` alone permits a project-root `careerpath.sqlite3` default, but the setup CLI does not use that default for its own guard resolution.
- If a setup process instead receives `CAREERPATH_DB` pointing to a file named `careerpath.sqlite3`, the SQLite stem check blocks it.
- A wrong confirmation string would cause the separate exact-confirmation refusal, not the observed production-name message.

Because setup's target is resolved from the environment of the actual Python process, a successful diagnostic establishes only that the resolver returns the approved target when its explicit assignments are applied. It does not prove which variables were present in the earlier failing setup process. The observed refusal means that process resolved a target matching the production-name condition; it does not, on its own, distinguish stale URL, missing/different path, a different shell, or source-checkout mismatch.

## PowerShell 5.1 finding and corrected configuration

The project owner reported that in Windows PowerShell 5.1, assigning `$env:DATABASE_URL = ''` or using `[Environment]::SetEnvironmentVariable('DATABASE_URL', '', 'Process')` removes the variable; `Test-Path Env:DATABASE_URL` returns false and child Python sees it as missing. This is consistent with PowerShell process-environment behavior as reported, but was not independently reproduced here.

Read-only inspection confirmed that the project `.env` exists and contains a non-empty `DATABASE_URL` assignment. Its value was not displayed or recorded. Because `backend.app` invokes `load_dotenv()` before it captures `os.environ['DATABASE_URL']`, a missing process variable may allow the `.env` assignment to populate the app's URL. A non-empty URL takes precedence over `CAREERPATH_DB`. **This is the leading explanation for the previous refusal, conditional on the undisplayed `.env` URL resolving to a database named `careerpath`; the URL target was not independently established.** Other environment or checkout mismatches remain possible.

The resolver does support an explicit SQLite URL. The safest supported workaround is therefore to set a non-empty SQLite URL for this exact file in the parent PowerShell session. This avoids depending on an empty environment variable and prevents `load_dotenv()` from replacing the explicit process value under its default non-overriding behavior. Keep `CAREERPATH_DB` set to the same path as an additional explicit target assertion.

Set the parent session values:

```powershell
$env:DATABASE_URL = 'sqlite:///C:/Users/THANAY/AppData/Local/Temp/careerpath_phase22f_student_uvqnduq1/db/student_test.sqlite3'
$env:CAREERPATH_DB = 'C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1\db\student_test.sqlite3'
$targetIdentity = 'sqlite:///C:/Users/THANAY/AppData/Local/Temp/careerpath_phase22f_student_uvqnduq1/db/student_test.sqlite3'
```

Then, in that same session and from the project root, this read-only check verifies the child inherited the exact non-secret SQLite URL and path. It mirrors the setup CLI's resolution behavior (`sqlite_path=None` when the URL is non-empty), calls the same pure resolver and target guard, and does not import Flask, invoke setup, or connect to any database:

```powershell
$setupTargetCheck = @'
import os
from pathlib import Path
from backend.database_config import resolve_database_target, validate_setup_target

approved = Path(r"C:\Users\THANAY\AppData\Local\Temp\careerpath_phase22f_student_uvqnduq1\db\student_test.sqlite3").resolve()
expected_url = "sqlite:///C:/Users/THANAY/AppData/Local/Temp/careerpath_phase22f_student_uvqnduq1/db/student_test.sqlite3"
expected_identity = "sqlite:///C:/Users/THANAY/AppData/Local/Temp/careerpath_phase22f_student_uvqnduq1/db/student_test.sqlite3"
if os.environ.get("DATABASE_URL") != expected_url:
    raise SystemExit("DATABASE_URL is not the exact approved SQLite URL")
if Path(os.environ.get("CAREERPATH_DB", "")).resolve() != approved:
    raise SystemExit("CAREERPATH_DB does not match the approved absolute path")

target = resolve_database_target(
    os.environ.get("DATABASE_URL", ""),
    None if os.environ.get("DATABASE_URL") else os.environ.get("CAREERPATH_DB"),
    allow_default=False,
)
validate_setup_target(target, expected_identity)
resolved = target.sqlite_path.resolve() if target.sqlite_path else None
matches = resolved == approved and target.identity == expected_identity
print(f"driver={target.driver}")
print(f"mysql_enabled={target.mysql}")
print(f"sqlite_path={resolved}")
print(f"target_identity={target.identity}")
print(f"setup_target_guard=PASS; matches_approved_path={matches}")
if target.driver != "SQLite" or target.mysql or not matches:
    raise SystemExit(2)
'@
$setupTargetCheck | python -
if ($LASTEXITCODE -ne 0) { throw 'Read-only setup-target check failed; do not initialize.' }
```

Expected output is the same driver, path, and identity shown above, ending with:

```text
setup_target_guard=PASS; matches_approved_path=True
```

This check proves the inherited values resolve through the same pure configuration functions and satisfy the production-name and exact-confirmation guards. It does not prove future setup will use the same environment if variables are changed, the command is launched from a different session, or a different checkout is used. The non-empty explicit SQLite URL is also what `backend.app` should capture before `load_dotenv()` can supply the project URL. `backend.setup.main` then resolves independently from that captured URL, using no `CAREERPATH_DB` fallback because the URL is non-empty, and `allow_default=False`. Both values point to the same approved file. The setup action remains unexecuted.

## Initialization gate

**Current recommendation: NO-GO until the corrected parent-session check above is run and passes in the intended checkout.** The previously reported child-process diagnostic set an empty URL itself and tested only the resolver; it did not import `backend.app` or account for the project's non-empty `.env` assignment. Even a passing parent-session check is not authorization to write: the runtime/path and database-absence checks must also pass, setup's own printed target must match exactly at a later approved execution, and schema/seed writes require separate approval. Keep `validate_setup_target` unchanged; never skip `--confirm-target`, add `--allow-non-test-target`, or weaken the production-name guard to work around the refusal.

## Safety and limitations

The owner-provided first diagnostic result and PowerShell behavior are recorded above; the corrected parent-session check has not been run here. The `.env` key's presence was checked without displaying its value. No database or application was opened, no setup command was executed, and no code/configuration/environment file was changed in this review. The `.env` explanation is a supported leading hypothesis, not a proven root cause, until the corrected target check passes and the prior effective target is established.
