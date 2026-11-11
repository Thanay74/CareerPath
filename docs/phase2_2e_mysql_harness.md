# CareerPath Phase 2.2E — Isolated MySQL Harness Prepared

**Status:** Harness and test cases prepared. No database connection, schema initialization, seed, or MySQL API test has been run. The user-provided server/account evidence is recorded as supplied, not independently reverified.

## Approved target and credential handling

The harness is fixed to the approved identity `mysql+pymysql://localhost:3306/careerpath_test_phase22e`, MySQL `8.0.46`, server hostname `LAPTOP-LJE9JD9B`, and account `careerpath_test_phase22e@localhost`. It accepts the password only through `CAREERPATH_MYSQL_TEST_PASSWORD`. It does not print the URL, password, or grants. It does not use MySQL root.

Required process environment variables:

| Variable | Required value |
|---|---|
| `CAREERPATH_MYSQL_TEST_HOST` | `localhost` |
| `CAREERPATH_MYSQL_TEST_PORT` | `3306` |
| `CAREERPATH_MYSQL_TEST_SCHEMA` | `careerpath_test_phase22e` |
| `CAREERPATH_MYSQL_TEST_USER` | `careerpath_test_phase22e` |
| `CAREERPATH_MYSQL_TEST_PASSWORD` | Restricted account password supplied through the local secret/environment mechanism |

No credential file was created. The root `.gitignore` already ignores `.env` and `.env.*` except `.env.example`; a future local secret file should use that ignored pattern and must never be committed.

## Fail-closed behavior

`tests/mysql_integration/harness.py` does not import the Flask application until the initialization path, and it does not connect on module import. Before an initialization or test command it:

1. Requires every target field to match the constants above and a non-empty password.
2. Rejects an inherited non-empty `DATABASE_URL` unless its scheme, host, port, schema, and username exactly match the approved target. It never trusts `CAREERPATH_DB` as a substitute.
3. Opens a PyMySQL connection with the approved host, port, schema, and restricted username, then verifies server version, `DATABASE()`, `CURRENT_USER()`, `@@hostname` equals `LAPTOP-LJE9JD9B` (case-insensitive), and `@@port`.
4. Inspects grants without printing them. It rejects global non-USAGE privileges, privileges on `careerpath`, `careerpath_db`, or `student`, and any schema scope other than the approved test schema.
5. Does not issue `USE`, `SHOW`, or data queries against any protected schema. It relies on the owner-provided account restriction and inspects the current account's grants, refusing global non-USAGE privileges or any scope outside the approved test schema.
6. Before initialization requires the test schema to have zero tables. Before tests it requires the expected table set and zero rows in every expected table. Unexpected/missing tables or existing rows stop the command.
7. The integration test module is outside the default test discovery package and skips unless launched with the harness opt-in flag. It independently asserts `USE_MYSQL`, the resolved `DATABASE_TARGET`, and exact target identity before any test request or direct DB access. It wraps every test connection and verifies server-reported schema, account, hostname, port, and version before allowing request or cleanup SQL to continue.

The harness is invoked as a direct script, so a `tests` package marker is not required. The integration directory intentionally has no package marker and is not recursively discovered by the ordinary backend suite. Its tests also skip unless the harness sets `CAREERPATH_ENABLE_MYSQL_INTEGRATION=1`. The harness removes inherited `CAREERPATH_DB` and sets the verified test `DATABASE_URL` in the same process before importing `backend.setup` or launching unittest. For initialization, it verifies Flask's resolved `DATABASE_TARGET`, `USE_MYSQL`, URL fields, and credentials, then guards the actual `application.connect_db()` boundary. That guard rechecks configuration and validates a read-only server identity query before returning the connection to `init_db()` for DDL. Thus the test fixture override in `tests/test_api.py::ApiTests.setUp` is not involved. Do not run that class for MySQL integration.

The generic setup safety helper does not recognize `careerpath_test_phase22e` as a test-name pattern (it only recognizes names beginning `test_`/`test-`, exact `test`/`testing`, or ending `_test`/`-test`). Therefore the harness supplies `--allow-non-test-target` only after its stricter exact-target, account, grant, hostname, and empty-schema preflight. No direct setup command is proposed that bypasses these checks.

### Setup command trace

The proposed initialization calls `backend.setup.main()` with exactly `--schema`, `--confirm-target <approved credential-free identity>`, and `--allow-non-test-target`. The mutually exclusive argparse group means no seed or bootstrap action is selected. `setup.main()` resolves `application.DATABASE_URL`, validates the setup target, prints only the resolved driver/host/database, then calls `application.init_db()`. This branch does not call `seed_education_catalog()`, `seed_aptitude_questions()`, or `bootstrap_admin()`.

`init_db()` calls `application.connect_db()`. The connection guard rechecks that the parsed host, port, schema, username, password, resolved `DATABASE_TARGET.identity`, and MySQL selection all match the approved values. Once connected, it queries `VERSION()`, `DATABASE()`, `CURRENT_USER()`, `@@hostname`, and `@@port` before giving that connection to `init_db()`. A mismatch closes the connection and aborts before DDL. `init_db()` uses unqualified table DDL against that connection's selected schema; it first performs the legacy assessment inspection, then the table DDL. No other setup action is selected.

## Prepared test coverage

`tests/mysql_integration/test_mysql_workflow.py` is separate from the SQLite fixture suite. It does not call `init_db()` or seed catalogs. The proposed suite covers:

- MySQL adapter placeholder conversion and named/positional row access (mocked adapter behavior).
- Registration, authenticated identity, profile and subject persistence across requests, interest/technical/employability assessment persistence, recommendations, recommendation retrieval, logout, relogin, and saved-profile retrieval.
- Invalid profile response and error-event persistence without changing the saved profile.
- Duplicate registration returns conflict and does not create a second user/student pair.
- Per-test cleanup of only the unique account and its child rows. It captures the initial application-error ID and deletes only later error rows; the harness requires the disposable schema to be empty before starting so these are attributable to this serial run.

The live aptitude workflow is intentionally not included yet: schema initialization creates an empty question table, and running the fixture seed is explicitly excluded. It needs separate approval if aptitude question seeding is to be tested. The current API suite also does not provide a fault-injection test proving MySQL rollback behavior for arbitrary mid-transaction server failures; the API assertions cover committed persistence and validation/error handling only.

## Proposed commands — not executed

Run from the project root in PowerShell. Set the password through an approved secret injector or the current shell's secure environment setup; do not place it in command history, source, or this document. These commands are proposals and **require explicit approval before initialization**.

```powershell
$env:CAREERPATH_MYSQL_TEST_HOST = 'localhost'
$env:CAREERPATH_MYSQL_TEST_PORT = '3306'
$env:CAREERPATH_MYSQL_TEST_SCHEMA = 'careerpath_test_phase22e'
$env:CAREERPATH_MYSQL_TEST_USER = 'careerpath_test_phase22e'
# CAREERPATH_MYSQL_TEST_PASSWORD must be populated securely before proceeding.

python tests/mysql_integration/harness.py preflight-empty
python tests/mysql_integration/harness.py initialize --approve-schema-init careerpath_test_phase22e --confirm-target mysql+pymysql://localhost:3306/careerpath_test_phase22e
python tests/mysql_integration/harness.py preflight-initialized
python tests/mysql_integration/harness.py test
```

`preflight-empty` is read-only but connects to MySQL. `initialize` invokes only `backend.setup --schema` after repeating the preflight; it can create/alter tables and MySQL DDL can implicitly commit. `preflight-initialized` is read-only. `test` writes uniquely identified disposable student rows and then cleans them. Do not run any of these until the user explicitly approves the connection and schema initialization. Do not run migrations, `backend/schema.sql`, any seed, Admin bootstrap, publishing, model training, or the general SQLite-backed API test class.

## Files prepared and current verification

- `tests/mysql_integration/harness.py` — target validation, server check, preflight, connection-boundary guard, gated initialization, and opt-in test runner.
- `tests/mysql_integration/test_mysql_workflow.py` — dedicated API persistence/error/cleanup tests with per-connection identity guard; skipped outside the explicit harness runner.
- `docs/phase2_2e_mysql_harness.md` — this design and command note.

Static source review and Python AST syntax checks were performed only. No database command or test was executed. The earlier `phase2_2e_mysql_integration_plan.md` and report remain historical Phase 1 findings; this note records the newly user-supplied target details and harness design without claiming independent connectivity verification.
