# CareerPath Phase 2.2D — Isolated Integration Verification Plan

## Isolation strategy

### Verified safe local API fixture

`tests/test_api.py::ApiTests.setUp` creates a `TemporaryDirectory`, points `application.DB_PATH` to a temporary SQLite file, copies the canonical career CSV and metadata into that temporary directory, redirects release pointer/marker/release/lock paths there, then initializes/seeds only that temporary SQLite database. `tearDown` restores the module paths and removes the temporary directory. During Phase 2.2D, the selected tests used `DATABASE_URL=''`, `PYTHONDONTWRITEBYTECODE=1`, and a workspace-local temporary root for Python temp files.

Selected tests were limited to authentication, profile and recommendation workflows, catalog validation, and Admin model statistics. No career draft, publish, restore, release-list mutation, setup command, or MySQL access was performed. Recommendation API cases read the existing model artifacts for inference; no training or artifact write occurred.

### MySQL boundary

No isolated MySQL test schema or verified test-only `DATABASE_URL` was provided. The existing API test fixture explicitly substitutes temporary SQLite, so it cannot be described as MySQL integration. Before a separate MySQL run:

1. The database owner must provision and identify a dedicated disposable test schema and dedicated test account, separate from `careerpath` and all student data.
2. The owner must provide the test-only connection configuration and explicitly approve schema initialization in that isolated target.
3. Before any connection, inspect the resolved target (driver, host, schema only; no credentials), reject ambiguous URLs and the production schema, and obtain exact target confirmation. Do not run setup if this cannot be proven.
4. Keep test account scope limited to that test schema. Never fall back to SQLite or production when the MySQL target is absent/invalid.
5. Use unique test identities, assert cross-account isolation, and clean up only records created in the disposable schema after the run.

This phase did not create, connect to, or initialize any test schema.

## Test matrix

| Area | Test/check | Expected evidence | Phase 2.2D result |
|---|---|---|---|
| Anonymous access | Protected profile, recommendation history, and Admin read routes | 401/403; no protected user data returned | API tests cover unauthenticated access in selected cases; broader route matrix remains for a later isolated run. |
| Student auth/session | Register, login, `/api/auth/me`, logout, relogin | Identity reflects the token owner; revoked token rejected; relogin creates a valid session | PASS in temporary SQLite (`test_authenticated_identity_logout_and_relogin`). |
| Student profile | Save/retrieve profile, subjects and assessment dimensions; cross-owner request denied | Values persist in test DB and another student cannot read them | PASS in temporary SQLite (`test_profile_assess_recommend_and_gap_flow`, `test_dynamic_education_catalog_and_profile_details_persist`). MySQL not tested. |
| Education validation | Four-level catalog, degree/specialization restrictions, invalid level and score cases | Correct options and expected 400 errors | PASS in temporary SQLite (`test_dynamic_education_catalog_and_profile_details_persist`, `test_profile_rejects_cross_level_and_cross_degree_catalog_values`, `test_registration_login_and_invalid_input`). |
| Catalog bootstrap read | Canonical CSV/metadata copied into the test fixture; active pointer/marker/release directory redirected to temp | Recommendations read the copied validated pair without touching canonical data | Exercised by selected API recommendation cases; fixture isolation is established by code inspection. No runtime MySQL behavior inferred. |
| Recommendation / roadmap | API recommendation request and pure Class 10 pathway/roadmap functions | Ranking and roadmap use current profile/catalog; output includes pathway and consistent score/guidance fields | API recommendation request PASS on temp SQLite and copied catalogs; pure gap/roadmap tests PASS. Same-snapshot linkage is also supported by source inspection; no release switching was exercised. |
| Input validation | Invalid education, scores, and `top_n` | Correct 400 response, not an unhandled error | PASS in `test_registration_login_and_invalid_input` and `test_profile_rejects_cross_level_and_cross_degree_catalog_values`. |
| Active Admin access | Dashboard, users, model statistics, datasets, aptitude administration | Active administrator gets authorized response; model metrics remain experimental | PASS for isolated SQLite test `test_admin_endpoints_require_admin_role_and_return_model_stats`; no live admin account used. |
| Student/inactive Admin denial | Active student and inactive admin against read-only Admin routes | 403; no privileged data exposed | Student denial covered in selected auth/admin case; inactive-admin matrix not run in this phase. Static authorization check only for remaining routes. |
| Career catalog Admin editing | Draft and publish lifecycle | Validated staged change and release activation | Deliberately not run; publishing is prohibited in Phase 2.2D. |
| MySQL persistence | Same user flows against dedicated MySQL test schema | Data survives API requests/reconnect as expected; no cross-user access | NOT VERIFIED; isolated-schema prerequisites/approval absent. |
| Browser workflow | React to Flask API, identity, Admin UI, logout | Running browser behavior | NOT VERIFIED; no browser was started. |

## Safe commands used / repeatable local commands

The selected temporary-SQLite API cases can be run from the project root with `DATABASE_URL` empty and temporary directories redirected to a fresh isolated path. Examples used in this phase:

```powershell
$env:DATABASE_URL = ''
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B -m unittest discover -s tests -p test_api.py -k test_authenticated_identity_logout_and_relogin -v
python -B -m unittest discover -s tests -p test_api.py -k test_profile_assess_recommend_and_gap_flow -v
python -B -m unittest discover -s tests -p test_api.py -k test_dynamic_education_catalog_and_profile_details_persist -v
```

These commands exercise only the fixture’s temporary SQLite/copy paths; they are **not** MySQL integration commands. Do not run the whole `test_api.py` module under this phase plan because it includes career publishing/restoration tests. Do not run setup/migration/seed commands against any shared database.

## Remaining prerequisites

- An approved, verified isolated MySQL schema and test account are required before MySQL integration can be planned for execution.
- An approved build environment that can access the same checkout is required before production-build verification.
- A separate approval is required before running any career publish/restore lifecycle test; current Phase 2.2D explicitly excludes those operations.
