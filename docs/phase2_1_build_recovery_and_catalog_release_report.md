# Phase 2.1 Build Recovery and Versioned Catalog Report

## Stage A — Vite build diagnosis

The frontend uses Vite 5.4.21. `frontend/package.json` defines `npm test` and `npm run build`; `frontend/index.html` loads `/src/main.jsx`. Vite's resolved root was `C:\Users\THANAY\Documents\Codex\2026-09-29\files-pasted-by-the-user-build\outputs\CareerPath\frontend`, and its resolved entry was the exact-case path `frontend/src/main.jsx`.

`src/main.jsx` is a regular, non-symlink file. PowerShell resolved it, the directory contains exactly `main.jsx`, and direct Node `statSync`, `lstatSync`, and `realpathSync` succeeded. The Vite configuration has no custom root, alias, or entry resolver. In the sandboxed run Vite failed during `commonjs--resolver` with `EPERM` at `realpath(src/main.jsx)` after transforming one module.

The same production build was run outside the workspace sandbox, without source or Vite configuration changes. It passed and transformed 30 modules. This establishes the observed error as a sandboxed filesystem access restriction in this environment, rather than a symlink, casing, or Vite root configuration defect. No source workaround was added.

Commands/results:

- `npm test` — **7 passed, 0 failed**.
- Sandboxed `npm run build` — **failed** with the above `EPERM`.
- `npm run build` outside the workspace sandbox — **passed**, 30 modules transformed; Vite emitted `frontend/dist/index.html`, JS, and CSS bundles.

## Stage B — Versioned release implementation

The implementation and on-disk contract are documented in [phase2_1_versioned_catalog_design.md](phase2_1_versioned_catalog_design.md).

Career catalog readers now resolve one active release containing both the CSV and JSON metadata. Release contents are validated as a pair, identified by content hash, and never replaced in place. A single manifest is switched atomically after validation. The initial canonical pair is copied into a rollback release before the first activation; canonical files are never overwritten. A managed marker makes a missing pointer after release mode begins fail closed. Recommendation reads pin the selected pair for the duration of a recommendation computation.

Admin publication now validates the staged snapshot, checks its base fingerprint while holding an OS-backed cross-process activation lock, and activates by switching the manifest. Admins can list validated releases and restore a previous release with an expected-fingerprint check. Existing draft staging/discard operations continue to use their cross-process lock.

## Files changed

- `backend/services/catalog_releases.py` — release validation, content-addressed storage, manifest selection, atomic activation, stale compare-and-swap, release listing, rollback, and read-context pinning.
- `backend/services/recommendation_engine.py` — load active release pairs; pin a single pair for each recommendation and avoid re-reading metadata separately.
- `backend/services/school_roadmap.py` — use metadata merged from the selected career snapshot.
- `backend/app.py` — stage snapshots from the release reader; publish staged drafts through version activation; admin list and restore endpoints.
- `frontend/src/AdminPortal.jsx` — enable validated publication and expose rollback releases in the existing Admin careers panel.
- `frontend/dist/` — generated production build output from the successful unsandboxed Vite build.
- `tests/test_catalog_releases.py` — isolated release, failure, concurrency, reload, and rollback tests.
- `tests/test_api.py` — publish, restore, stale draft, concurrent stage, and duplicate publish regression coverage.
- `docs/phase2_1_versioned_catalog_design.md` — release architecture and operations note.
- `docs/phase2_1_build_recovery_and_catalog_release_report.md` — this report.

## Test results

- `python -m unittest discover -s tests` with `DATABASE_URL=''` and temporary test paths — **58 tests passed**.
- `python -m unittest tests.test_catalog_releases` — **11 tests passed**.
- `python -m unittest tests.test_catalog_releases tests.test_api tests.test_recommendation_engine` — **40 tests passed** before the final separate-process reload assertion; the final full suite above includes that assertion.
- `npm test` — **7 tests passed**.
- `npm run build` — **passed outside the workspace sandbox**; the sandboxed attempt still fails as described above.

The tests exercise temp copies of the catalog and isolated SQLite. They do not establish MySQL behavior.

## Limits and safety confirmation

- No MySQL connection, migration, schema command, or seed command was run during this work.
- The live `careerpath` database and student data were not accessed or modified.
- Canonical education and career catalog files, datasets, credentials, and model artifacts were not modified. Release tests use temporary copies and temporary release directories.
- Restart/reload was tested after simulated interruption before and immediately after the atomic pointer replacement. Power-loss or storage-controller crash durability, MySQL integration, and non-Windows filesystem semantics remain unverified. The code relies on same-filesystem atomic rename/replacement; do not claim those untested environments are verified.
