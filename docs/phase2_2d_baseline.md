# CareerPath Phase 2.2D — Read-Only Baseline

**Captured:** 2026-10-22  
**Project root:** `C:\Users\THANAY\Documents\Codex\2026-09-29\files-pasted-by-the-user-build\outputs\CareerPath`

## Checkout and existing state

- Branch: `master`; Git reports **No commits yet**. All project files were already untracked. No checkout, reset, stash, commit, or Git configuration change was made.
- The Phase 2.2C, C1, and C2 reports existed before this task. The four Phase 2.2D report destinations did not exist before this task.
- `frontend/node_modules/` exists. `frontend/dist/` and root `.test-tmp/` also existed before this phase; neither was cleared or overwritten.
- Frontend lock/config files: `frontend/pnpm-lock.yaml`, `frontend/package.json`, `frontend/vite.config.js`, and `frontend/index.html`. No npm/yarn lockfile was listed. Package scripts are `npm test` (`node --test`) and `npm run build` (`vite build`).
- No `.env` contents or credentials were read or recorded.

## Catalog state and protected hashes

| Path | Baseline state | Size | SHA-256 |
|---|---|---:|---|
| `data/career_knowledge_base.csv` | Present | 10,109 bytes | `229D6B4ED077E81F2043515A5CA02EA2FFDEA72E1D32467899F4E7C3AA021E78` |
| `data/career_metadata.json` | Present | 4,319 bytes | `238800FFFA961EB70FD70E028552BD05CC639215A0CCFD2ADDA8DFC1CEE36629` |
| `data/career_active.json` | Absent | — | — |
| `data/career_catalog_managed.json` | Absent | — | — |
| `data/career_releases/` | Absent | — | — |

The C1 investigation and C2 decision report the same current pointer/release state and canonical hashes. The earlier C report records the unexplained one-byte-to-absent history; this baseline does not infer a cause.

## Model artifacts and metrics

| Path | Size | SHA-256 |
|---|---:|---|
| `data/processed/career_model_metrics.json` | 28,691 bytes | `4EAE655E86BD4A14A60DC5DB4C8747C16B7F5C2C2B8915278336F3E3EA3E1D57` |
| `backend/models/career/10th_career_model.joblib` | 1,234,257 bytes | `AFFCC62D850B4B9E8706AA02FF11076046F7A1CCB2DB9AB1D7D4D1266D074793` |
| `backend/models/career/12th_career_model.joblib` | 1,192,615 bytes | `3B31D0D1472EC2112FC734F9A6F756367048AD6A0F4C6EBEB23E30AD6B75A50A` |
| `backend/models/career/bachelors_career_model.joblib` | 1,207,355 bytes | `C0A7891C11AAEBC9EF9F8B0A32F210F96D3D2B227B40D49F01407AE729FC98B6` |
| `backend/models/career/masters_career_model.joblib` | 1,205,021 bytes | `6400A9359FF75241A0882EA129A6C71EC597DD945D538BC9120B7D17FE62F1DF` |

## Frontend runtime and path evidence

- `node --version`: `v24.19.0`; `npm --version`: `11.17.0`; installed Vite package: `5.4.21`.
- `frontend/package.json` allows Vite `^5.4.14`; `pnpm-lock.yaml` resolves `5.4.21`.
- `frontend/index.html` references `/src/main.jsx`. That path resolves with exact casing to a regular file, not a symlink.
- Direct Node `realpathSync`, `statSync`, and `lstatSync` for the entry succeeded. PowerShell `Resolve-Path` succeeded. The frontend and source directories are owned by `CodexSandboxOnline`; the entry file is owned by `CodexSandboxOffline`. The current user ACL shows `FullControl`, so no broad permission change is justified.
- `frontend/vite.config.js` only configures the development `/api` proxy. It does not override root, aliases, build entry, or filesystem access.

## Baseline safety

This baseline was gathered with filesystem metadata/hash reads, source/doc inspection, runtime version queries, and read-only Git status. It did not start Flask, connect to any database, invoke setup/migration/seeding, train models, or mutate catalog state.
