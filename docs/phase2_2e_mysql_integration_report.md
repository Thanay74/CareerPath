# CareerPath Phase 2.2E — MySQL Integration Report

**Date:** 2026-10-22  
**Current outcome:** Earlier terminal output provided in the conversation showed the dedicated tests passing; a later supplied terminal transcript showed the post-test initialized-schema preflight passing. Neither was rerun while editing this report. This does not establish production readiness or comprehensive application coverage.

## Latest Phase 2.2E verification

### Results shown in the terminal transcript provided

The supplied PowerShell transcript shows the command:

```powershell
python tests/mysql_integration/harness.py preflight-initialized
```

with this result:

```text
Preflight PASS: MySQL 8.0.46; server=LAPTOP-LJE9JD9B; port=3306; schema=careerpath_test_phase22e; account=careerpath_test_phase22e@localhost; tables=18 (initialized). Secrets were not displayed.
```

According to the harness checks, this passed the server, port, schema, account, grant-scope, expected-table, unexpected-table, and empty-row checks. This is evidence from the terminal output supplied by the project owner; the command was not rerun while preparing this documentation update.

### Test results shown in earlier terminal output

The earlier terminal output provided in this conversation showed the dedicated MySQL integration suite completing with **4 tests passed and 0 failures**. These results were not independently rerun while editing this report.

The four reported tests were:

1. Duplicate registration does not create an extra student.
2. MySQL adapter converts placeholders and preserves named rows.
3. Profile, assessment, recommendation, and authentication persistence.
4. Invalid profile validation does not save invalid data.

The transcript is the post-test preflight according to the supplied sequence. Its passing result and the harness checks support that the initialized schema was clean at that point. No cleanup command was run as part of this documentation update.

These results cover only the listed integration workflows. They do not establish production readiness, full browser behavior, Admin workflows, all assessment types (including seeded aptitude questions), arbitrary transaction rollback behavior, deployment readiness, or complete SRS compliance.

## Historical Phase 1 preparation snapshot

The following sections preserve the initial read-only preparation findings and its then-blocked isolation status. The database owner later provided the test target and preflight/test results recorded above; the original snapshot is not the current status.

## Summary

Reviewed the Phase 2.2D and Phase 2.2D2 reports, DB configuration/adapter, Flask schema initialization, explicit setup and migration files, API tests, and available SRS/architecture/API documentation. The detailed plan is [phase2_2e_mysql_integration_plan.md](phase2_2e_mysql_integration_plan.md).

No dedicated disposable MySQL test schema, schema-scoped test account, exact driver/host/port/schema identity, proof that the target contains no production/student data, or explicit initialization approval was supplied. Each is a required gate. **No database connection, target probe, schema initialization, migration, seed, or MySQL test was run.** No SQLite substitution is reported as MySQL verification.

## Isolation evidence and approvals

**Historical snapshot from the initial Phase 1 preparation:** the target and approval were not yet supplied. The later approved test-schema setup, terminal preflight output, and test results are recorded in “Latest Phase 2.2E verification” above. The initial blockers are superseded for the approved `careerpath_test_phase22e` target based on the owner-provided setup information and recorded preflight; they are not claims about any other database.

| Gate item | Initial Phase 1 status | Later status for `careerpath_test_phase22e` |
|---|---|---|
| Owner-provisioned disposable schema | BLOCKED — not identified or evidenced. | Addressed for the approved test target; owner identified the disposable schema, and the supplied initialized preflight reports it. |
| Dedicated test account scoped only to schema | BLOCKED — not provided/evidenced. | Addressed according to owner-provided account/grant information; the supplied preflight passed the harness grant-scope checks for the named account. |
| Explicit approval for schema initialization | BLOCKED — no specific target/approval supplied. | Addressed for this target by the owner's explicit Phase 2.2E authorization and subsequent initialized-schema evidence. |
| Driver, host, port, schema confirmed before connect | BLOCKED — target identity not supplied. | Addressed by supplied preflight output: MySQL 8.0.46 at `LAPTOP-LJE9JD9B:3306`, schema `careerpath_test_phase22e`, account `careerpath_test_phase22e@localhost`. |
| Confirmation target excludes live `careerpath` and student data | BLOCKED — no owner attestation or permitted read-only target evidence. | Addressed for this test target according to the owner's isolation statement and preflight checks; no broader isolation claim is made. |

The later statuses above rely on owner-provided setup details and terminal evidence. They were not independently reverified while editing this report. The separately reported four passing tests remain attributed to earlier terminal output, as noted above.

No credentials were printed, inspected, or recorded. `.env` contents were not read. No Admin account was created or bootstrapped.

## Preparation findings

- MySQL is selected by `DATABASE_URL`; PyMySQL with `DictCursor` is used. When that URL is empty, the Flask adapter falls back to SQLite using `CAREERPATH_DB`, then the project-root `careerpath.sqlite3` default. The separately prepared Phase 2.2E harness requires and verifies its exact target before use.
- `backend/setup.py` requires a credential-free exact `--confirm-target`, rejects the exact production schema name `careerpath`, and requires `--allow-non-test-target` for non-test names. It reports driver/host/database, not credentials.
- `backend/app.py::init_db` executes MySQL DDL after an `information_schema` legacy-assessment check. DDL is not atomic on MySQL and may leave partial schema state if interrupted.
- `backend/schema.sql` and both migrations contain `USE careerpath`; they are not appropriate for a named disposable test schema and were not executed.
- Existing `tests/test_api.py` forcibly overrides `DB_PATH` with SQLite temp storage but leaves `USE_MYSQL` determined by configured `DATABASE_URL`. Running that test class with MySQL configured can therefore connect to MySQL during setup. It must not be used for Phase 3; the adapter test is a mock only.
- Current career catalog, metadata, qualification guidance, and recommendation models are file-backed. MySQL stores application records and live aptitude questions. This differs from portions of `SRS_IMPLEMENTATION.md`/`schema.sql` that describe normalized career/skill/gap persistence; the current recommender does not use those MySQL catalog tables.

Detailed table, constraint, transaction, environment, and workflow findings are in the plan.

## Commands and tests

The following commands and statuses document the initial read-only preparation only; later Phase 2.2E evidence is summarized above.

Read-only inspection commands executed from the project root included:

```powershell
Get-Content docs/phase2_2d_report.md
Get-Content docs/phase2_2d2_browser_api_verification.md
Get-Content backend/database_config.py
Get-Content backend/setup.py
Get-Content backend/schema.sql
Get-Content backend/migrations/001_education_and_aptitude.sql
Get-Content backend/migrations/002_admin_observability.sql
rg -n "^CREATE TABLE|CONSTRAINT|INDEX|UNIQUE KEY|FOREIGN KEY|^CREATE DATABASE|^USE " backend/schema.sql backend/migrations/001_education_and_aptitude.sql backend/migrations/002_admin_observability.sql
rg -n "CREATE TABLE IF NOT EXISTS|ON DUPLICATE|INSERT IGNORE|information_schema|ON CONFLICT|PRAGMA|commit\(" backend/app.py backend
```

Also inspected the specific adapter mock and fixture setup in `tests/test_api.py`, the requirements list, and the documentation/test-target presence. These commands did not contact a database.

| Check | Result |
|---|---|
| Source/configuration and docs inspection | PASS — read-only preparation only. |
| MySQL target resolution without connecting | NOT RUN — no exact target supplied; intentionally did not evaluate a live URL. |
| MySQL schema/init/migrations | BLOCKED — isolation gate missing; not run. |
| MySQL registration/profile/assessment/recommendation tests | BLOCKED — not run. |
| Mock MySQL adapter test | NOT RUN in this phase; prior Phase 2.2D test was a mock only and is not live integration evidence. |
| SQLite/API or frontend regression tests | NOT RUN — not required for this read-only preparation. Phase 2.2D2's selected SQLite/API and frontend results remain historical evidence only. |

The initial read-only preparation did not create test identities or database records. Later test activity and post-test cleanup are described in the latest verification section above.

## Differences and unresolved SRS/System Design requirements

MySQL uses `%s` placeholders, `ON DUPLICATE KEY UPDATE`, `INSERT IGNORE`, `information_schema`, MySQL JSON/ENUM/AUTO_INCREMENT and native FK/DDL semantics; SQLite uses `?`, `ON CONFLICT`, `INSERT OR IGNORE`, `PRAGMA`, and its own schema types. MySQL DDL may commit implicitly, unlike the test fixture's SQLite execution model. These differences require real integration evidence.

Unverified requirements remain MySQL persistence and transaction behavior, successful Admin functionality, browser rendering/console and accessibility, and production deployment/catalog recovery. Additionally, current runtime file-based career/skill ownership conflicts with SRS implementation-map language that describes those records as MySQL-backed. No unused MySQL career or skill tables were populated to conceal this discrepancy.

## Initial Phase 1 changes and next step (historical)

During the initial Phase 1 preparation, these two documents were created:

- `docs/phase2_2e_mysql_integration_plan.md`
- `docs/phase2_2e_mysql_integration_report.md`

During that initial preparation, no database or application files, credentials, student data, catalog contents, datasets, notebooks, or model artifacts were modified, and no database connection was attempted. This statement describes that preparation period only; the later connection evidence is recorded above.

**Next step at the time:** provision and approve an isolated test schema. The owner has since supplied the target and the latest preflight evidence above. Browser, active Admin, and deployment checks remain separate requirements; these MySQL checks alone do not establish production readiness.
