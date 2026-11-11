# CareerPath Phase 2.1 — Controlled Implementation Report

**Date:** 2026-10-22  
**Scope:** Startup-write isolation, catalog validation, aptitude seed behavior, and staged Admin career publishing. No live MySQL connection, migration, seed, reset, or record write was performed.

## 1. Read-only baseline

The project has no Git metadata in the inspected `CareerPath` directory, so a Git status/diff baseline was unavailable. Before source changes, SHA-256 hashes were captured for the files below:

| Baseline file | SHA-256 |
|---|---|
| `backend/app.py` | `8C42110D92232DBC37767ADA613D9FEAA95096BDB8C1C31959FA0F83C24BD220` |
| `backend/education_catalog.py` | `DBB564139BEB183F07CA345E85730ECD80421A9F964BB5C7A4E089F026A8C7EF` |
| `backend/aptitude_bank.py` | `70C714F83D14876CDD1F71323416DB27B1F089F5A7064D76FABD6DE6179E607B` |
| `backend/services/recommendation_engine.py` | `88252524CEB4702136CDA6169CD3DE42018A420440D2707DBB3DD44822FB21AC` |
| `backend/services/school_pathways.py` | `34DE01D67AF3446E2474EC4AA7553B314F959E762E1E9612DEF780A7B1519B8F` |
| `backend/services/school_roadmap.py` | `A417B010BDD0AA231C6B8A9D74E60607E12B279330A66C2CC7C524E460AB1773` |
| `data/career_knowledge_base.csv` | `229D6B4ED077E81F2043515A5CA02EA2FFDEA72E1D32467899F4E7C3AA021E78` |
| `data/career_metadata.json` | `238800FFFA961EB70FD70E028552BD05CC639215A0CCFD2ADDA8DFC1CEE36629` |
| `backend/schema.sql` | `925912D282D8AA77F7E9B7D36302C5578B89A28651EA421487449C3D122969BC` |
| `backend/migrations/001_education_and_aptitude.sql` | `5D3E9B54C3C7D0A5F6751924BD6881FE8F471B8E18B33BCFF84C7FEB65AFCD25` |
| `backend/migrations/002_admin_observability.sql` | `4B1670F92C134A83CB3C49E61949AA54840EE6C4890E598E0BEB20F672D08845` |
| `tests/test_api.py` | `DEC400AF521BC7A257CA640B339D4381144A4DEC84445B957CFF7ECB03E8158C` |
| `frontend/src/AdminPortal.jsx` | `0CF182ECEA33E182D5A1DA86419BFEB478D9CE9157BEFB46CCE14102711EE408` |

Baseline catalog inventory: four education levels; subject-option counts by level were 5 (10th), 22 (12th), 86 (Bachelor's), and 55 (Master's); CSV contains 25 career rows (`C01`–`C25`), with 25 metadata entries. The API had 41 route declarations before implementation; the implementation adds three Admin draft routes and does not change existing route paths. Catalog validation reported no structural errors against the unchanged baseline catalogs.

Baseline tests were run with `DATABASE_URL` explicitly empty and `CAREERPATH_DB` pointed at a disposable file under `.test-tmp/`:

- Backend: 32 tests passed (`python -m unittest discover -s tests -v`). This was SQLite-only, not MySQL integration.
- Frontend: 7 tests passed (`npm test`).

## 2. Confirmed startup behavior before changes

`backend/app.py` called `init_db()` at module import. That function created tables, conditionally altered existing tables and renamed legacy `assessments`, inserted missing education and aptitude rows, committed, then optionally created the configured first admin. Thus importing the WSGI application or starting Flask could require database write/DDL permissions. MySQL DDL can implicitly commit. The rename preserved the old table but did not map its legacy payload into normalized assessment rows.

The aptitude API reads and manages MySQL `aptitude_questions`, while startup reinserted missing question IDs from `backend/aptitude_bank.py`. Career Admin CRUD previously wrote directly into the active CSV/JSON on each create, edit, or deactivation. Career/skill relational tables were not used by the current recommendation catalog; the earlier read-only Phase 2 audit found them empty. This work left those tables untouched.

## 3. Changes made

- Removed implicit `init_db()` invocation from Flask module import. App import now constructs routes without opening the configured database.
- Kept the existing schema initialization function, but made it an explicit operation. Education seeding, aptitude fixture insertion, and first-admin creation are separate setup actions exposed by `python -m backend.setup`.
- Added a read-only structural catalog validator. It checks the required education levels, identifiers and references, career CSV fields and IDs, duplicate identifiers/names, score-map values, and metadata references. It reports validation problems and never rewrites source catalogs.
- Changed Admin career create/edit/deactivate requests to stage one validated proposed catalog snapshot under `instance/career_drafts/`. The active catalog remains unchanged until an authenticated Admin explicitly publishes. Draft publication checks validation and the active catalog fingerprint to reject stale drafts. Drafts may be explicitly discarded.
- Added Admin UI controls to review validation status, publish a valid draft, or discard it. Career editing is disabled while a draft is pending to avoid conflicting edits.
- Added staged publication file handling that writes both prepared catalog files before replacement and restores the CSV if replacing the metadata file fails. This is guarded against validation errors but the two-file storage is not a true filesystem transaction.
- Added tests for startup import isolation, catalog validation/no mutation, staged changes, and rejection of invalid staged content.

## 4. Explicit setup commands

First point `DATABASE_URL` or `CAREERPATH_DB` to an approved isolated environment and review the target before any write. Do not use these commands against the existing live `careerpath` database as part of this report.

```powershell
# Read-only catalog validation
python -m backend.setup --validate-catalogs

# Explicit schema initialization/migration (review current migration behavior first)
python -m backend.setup --schema

# Separate explicit data setup actions, only when approved for the target database
python -m backend.setup --seed-education
python -m backend.setup --seed-aptitude-fixture
python -m backend.setup --bootstrap-admin
```

The aptitude fixture command inserts only missing IDs; it does not update or delete live questions. First-admin credentials continue to come from environment variables, not source code. Normal `python -m backend.app` startup no longer performs any of these operations. No setup command above was run in this task.

## 5. Verification results

Final verification:

- Backend: **37 passed, 0 failed** (`python -m unittest discover -s tests -v`) with `DATABASE_URL` empty and a disposable SQLite file under `.test-tmp/`.
- Frontend: **7 passed, 0 failed** (`npm test`).
- Production build: **passed** (`npm run build`; Vite transformed 30 modules). Initial sandbox build attempt was blocked by Windows `realpath` permission; rerun with the approved elevated filesystem access succeeded.
- Catalog validation: **passed** (`python -m backend.setup --validate-catalogs`).
- Python compile check: **passed** (`python -m compileall -q backend tests`).
- The startup-safety test confirmed importing `backend.app` did not connect to SQLite, create the configured database file, or load `backend.aptitude_bank`.
- Staged Admin API tests confirmed a change remains unapplied before publish, can be explicitly published, and invalid staged content is rejected without modifying the active test catalog.

These are isolated tests, not MySQL integration results. They do not establish MySQL migration compatibility or live database behavior.

## 6. Files changed

- `backend/app.py` — remove import-time initialization; staged career change/publish/discard APIs; guarded file publishing.
- `backend/setup.py` — explicit schema, education seed, aptitude fixture seed, first-admin, and validation commands.
- `backend/catalog_validation.py` — non-mutating catalog validation.
- `frontend/src/AdminPortal.jsx` — pending draft review and explicit publish/discard controls.
- `tests/test_api.py` — explicit isolated setup and stage/publish regressions.
- `tests/test_catalog_validation.py` — malformed and duplicate catalog tests, with source immutability assertion.
- `tests/test_startup_safety.py` — import test blocks DB connections and checks the fixture is not loaded.
- `.gitignore` — exclude generated Admin draft files.
- `docs/phase2_1_implementation_report.md` — implementation record.

## 7. Remaining risks and blocked checks

- No isolated MySQL schema/credentials were approved or available for this run; MySQL migration and authenticated integration remain unverified. The live DB was not contacted.
- Existing `--schema` behavior includes the legacy assessment rename and other conditional DDL. Those operations were not redesigned or run; they still need a separate reviewed migration plan before use on any database containing student records.
- Career records remain split across CSV and metadata JSON. Publication prepares both files first and attempts a rollback on replacement failure, but the pair cannot be atomically committed across a process crash. The fingerprint prevents publishing over concurrent catalog changes.
- The data directory is host-local. Multi-instance/ephemeral deployments need shared/versioned draft storage before relying on Admin publishing across instances.
- Dataset provenance, qualification sources, real-student model validity, and the missing datasets/notebook were outside this implementation scope and remain as described in the Phase 2 plan.

## 8. SRS and safety status

No student records, datasets, notebook, model artifacts, credentials, or existing database records were intentionally changed. The catalog source files remain canonical and unchanged. No accuracy claim or MySQL integration claim is made. Setup/migration commands are documented but were not executed.
