# CareerPath Phase 2.2D — Build Diagnosis, Deployment Documentation, and Isolated Integration Preparation

**Date:** 2026-10-22  
**Scope:** Safe baseline, Vite diagnosis, catalog-mode documentation, isolated SQLite/API test subset, and preparation for separately authorized MySQL verification.

## Executive summary

**Readiness: `BLOCKED — ISOLATION PREREQUISITES`.** Safe backend tests passed (32 total across focused tests and selected Flask API tests), and the frontend unit suite passed (7/7). The project owner has supplied evidence that the production build passed in the approved Windows environment outside the sandbox (Vite 5.4.21; 30 modules; 894 ms). MySQL integration, authenticated browser behavior, and production deployment remain unverified. The build does not by itself establish release readiness.

README and setup documentation now describe canonical-bootstrap behavior for local development, fail-closed managed mode, explicit Admin publishing, and production prerequisites. A stale statement that normal API startup bootstraps the first Admin was corrected to match the explicit setup workflow.

Selected API cases used only temporary SQLite databases and catalog copies, not MySQL or canonical catalog writes. No isolated MySQL schema was provided, so MySQL persistence/integration remains unverified. Catalog pointer, marker, and releases remained absent as they were at baseline; no activation or recovery was attempted.

## Baseline and integrity

Detailed baseline: [`phase2_2d_baseline.md`](phase2_2d_baseline.md).

- Branch `master`, no commits yet; project contents were untracked before the work. No reset, stash, checkout, commit, or Git configuration change occurred.
- `frontend/node_modules`, `frontend/dist`, and root `.test-tmp` pre-existed; they were left in place.
- Canonical data baseline and final hashes match:
  - `data/career_knowledge_base.csv`: `229D6B4ED077E81F2043515A5CA02EA2FFDEA72E1D32467899F4E7C3AA021E78`
  - `data/career_metadata.json`: `238800FFFA961EB70FD70E028552BD05CC639215A0CCFD2ADDA8DFC1CEE36629`
- `data/career_active.json`, `data/career_catalog_managed.json`, and `data/career_releases/` were absent both before and after this phase. No pointer/marker/release was created, removed, restored, or modified.
- Existing model metrics and all four career model artifact hashes match baseline. Recommendation API tests performed read-only inference; no training, serialization, or metrics regeneration occurred.
- Temporary API test root was absent after verification. The later Windows build output is in `C:\Users\THANAY\Documents\Codex\.phase2_2d_frontend_build`, outside the project and `frontend/dist`; the evidence does not indicate that `frontend/dist` was modified. Pre-existing `.test-tmp` remains present.

## Vite build diagnosis

Detailed diagnosis: [`phase2_2d_build_diagnosis.md`](phase2_2d_build_diagnosis.md).

The historical sandbox build error is Vite `EPERM` while resolving `frontend/src/main.jsx`. Current read-only checks found Node v24.19.0, npm 11.17.0, installed Vite 5.4.21, `pnpm-lock.yaml`, a matching exact-case entry path, a regular non-symlink file, and successful direct Node `realpathSync`/`statSync`/`lstatSync`. The Vite config only contains a dev-server API proxy. ACLs grant the current user FullControl; broad permission changes are not justified.

The prior Phase 2.1 build report recorded that the same build passed outside the sandbox, while multiple sandboxed attempts failed. The project owner has now supplied the following successful Windows build evidence for this checkout:

```powershell
npm.cmd run build -- --outDir "C:\Users\THANAY\Documents\Codex\.phase2_2d_frontend_build"
```

**PASS** — Vite 5.4.21, 30 modules transformed, 894 ms. `Test-Path` confirmed the generated `index.html`, and `Get-ChildItem` confirmed `index.html` and `assets/` in the output directory. This output is outside the project and `frontend/dist`; no claim is made that the existing `frontend/dist` was modified. The build was not rerun in this sandbox. The historical sandbox `EPERM` remains preserved; the evidence supports an environment restriction, but the precise enforcement mechanism remains unconfirmed.

## Documentation changes

- `README.md` — explains canonical bootstrap only when pointer and marker are absent, fail-closed behavior, staged/explicit publication, production catalog safeguards, and corrects the outdated Admin-bootstrap startup statement.
- `SETUP_GUIDE.md` — adds the same local/production catalog policy and controlled publication guidance; corrects the Admin-bootstrap statement.

No application source, Vite configuration, lockfile, dependency, or environment configuration was changed.

## Isolated integration preparation and results

Plan: [`phase2_2d_isolated_integration_plan.md`](phase2_2d_isolated_integration_plan.md).

`tests/test_api.py::ApiTests.setUp` was inspected: it redirects Flask to a temporary SQLite file, copies the career CSV/metadata to a temporary directory, redirects release paths to temporary paths, and initializes/seeds only that temporary SQLite fixture. Selected cases below used `DATABASE_URL=''`. The fixture’s initialization and seed calls affected only its disposable SQLite file, which was cleaned after each test.

### Backend commands/results

Run from the project root with `PYTHONDONTWRITEBYTECODE=1` and `DATABASE_URL=''`:

| Command/test selection | Result |
|---|---|
| `python -B -m unittest discover -s tests -p test_phase2_2a_catalog_and_model_selection.py -v` | PASS — 3 |
| `python -B -m unittest discover -s tests -p test_phase2_2b_recommendation_quality.py -v` | PASS — 11 |
| `python -B -m unittest discover -s tests -p test_catalog_validation.py -v` | PASS — 3 |
| `python -B -m unittest discover -s tests -p test_startup_safety.py -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_setup_safety.py -v` | PASS — 4; temp variables pointed to a new workspace-local test directory |
| `python -B -m unittest discover -s tests -p test_recommendation_engine.py -k school_gap -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_recommendation_engine.py -k class10_roadmap -v` | PASS — 2 |
| `python -B -m unittest discover -s tests -p test_api.py -k test_registration_login_and_invalid_input -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_api.py -k test_authenticated_identity_logout_and_relogin -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_api.py -k test_profile_assess_recommend_and_gap_flow -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_api.py -k test_dynamic_education_catalog_and_profile_details_persist -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_api.py -k test_profile_rejects_cross_level_and_cross_degree_catalog_values -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_api.py -k test_admin_endpoints_require_admin_role_and_return_model_stats -v` | PASS — 1 |
| `python -B -m unittest discover -s tests -p test_api.py -k test_mysql_adapter_uses_named_rows_and_mysql_placeholders -v` | PASS — 1; adapter mock only, no MySQL connection |

**Total: 32 backend tests passed** in the safe subset. The selected API cases exercised login/session, student profile save/read and access denial, education validation, recommendation requests, and Admin metrics in isolated SQLite. Recommendation cases read existing model artifacts for inference only.

An initial backend test command was mistakenly launched with `frontend/` as its current directory; unittest reported `Start directory is not importable: 'tests'`, so zero backend tests ran in that attempt. The commands above were rerun from the project root and passed. The first setup-safety run from the earlier Phase 2.2C report had a Windows temp cleanup error; the Phase 2.2D rerun with a workspace-local temp root passed all four tests.

Frontend, from `frontend/`:

- `npm test` — **PASS**, 7 passed, 0 failed, 0 skipped.

Build:

- Production build in the approved Windows environment — **PASS, based on project-owner-provided verification**; command and output evidence are recorded above.
- The sandboxed build itself was not rerun and retains its historical `EPERM`; the production build pass does not verify browser behavior or deployment.

### Coverage limits

- The isolated SQLite API tests are not MySQL integration. No MySQL connection, schema, migration, or seed command was used.
- No full `test_api.py` run occurred; it contains publish/restore and catalog-mutation cases, which were excluded.
- The inactive-Admin route matrix was not executed in this phase. Admin authorization was covered by selected tests and static inspection; the integration plan lists remaining cases.
- The recommendation tests verify API response paths and separate pure roadmap/gap behavior. Same-snapshot reader behavior is supported by source inspection; no active release switch was exercised.
- No browser or end-to-end React session was run.

## Integration plan and isolation prerequisites

The test plan distinguishes temporary SQLite API evidence from MySQL evidence. For a future MySQL pass, the owner must provide a dedicated test schema and test credentials, explicitly approve its schema initialization, verify the resolved non-production target before connecting, and use no live `careerpath` target. This phase stopped before creating or connecting to any such schema. Test matrix and safe local commands are in the integration-plan document.

## Remaining blockers and readiness

1. **MySQL integration:** No isolated MySQL schema/account or approval was available. SQLite fixture tests do not prove MySQL behavior.
2. **Browser flow:** Authenticated frontend/header/logout behavior remains unverified in a running browser.
3. **Production catalog deployment:** Local canonical-bootstrap mode is documented, but production catalog mode, persistent shared storage, release activation, and recovery must be approved and tested before deployment.

**Readiness status: `BLOCKED — ISOLATION PREREQUISITES`.** The production build passed in the approved Windows environment based on the supplied evidence. Selected temporary-SQLite integration checks are passing, but this is not release readiness and does not establish MySQL, browser, or deployment behavior.

## Safety confirmation

No live database connection, migration, explicit setup command, catalog publish/restore, pointer/marker manipulation, canonical catalog write, model training, artifact regeneration, dependency reinstall, ACL change, or security workaround occurred. Temporary SQLite and fixture writes were confined to the existing tests’ disposable directories. Final catalog, metrics, and model hashes match the baseline.
