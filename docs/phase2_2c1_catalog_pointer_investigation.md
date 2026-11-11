# CareerPath Phase 2.2C1 — Catalog Pointer Integrity Investigation

**Date:** 2026-10-22  
**Mode:** Read-only filesystem and source inspection. No repair attempted.

## Summary

The current checkout contains neither `data/career_active.json` nor `data/career_catalog_managed.json`; `data/career_releases/` is also absent. The canonical career CSV and metadata files remain present and match the SHA-256 values recorded in the Phase 2.2C report.

The earlier Phase 2.2C report states that its initial read saw both pointer/marker paths as one-byte files and its final read found them absent. It did not retain their contents, hashes, timestamps, or a file-system event log. This investigation cannot establish the cause of that state change.

Per the current reader code, when both pointer and marker are absent, the application treats the validated canonical CSV/metadata pair as the pre-versioned bootstrap catalog. If versioned mode had previously been established and the marker is present while the pointer is missing, it fails closed instead of falling back. Since both are absent now, source inspection predicts the canonical fallback branch; this is not a runtime test and does not prove that the intended operational catalog is healthy.

## 1. Current filesystem facts

Read-only inspection was performed in:

`C:\Users\THANAY\Documents\Codex\2026-09-29\files-pasted-by-the-user-build\outputs\CareerPath`

| Path | Current state | Metadata / SHA-256 |
|---|---|---|
| `data/career_active.json` | Absent | No current size, timestamp, or hash exists for an absent path. |
| `data/career_catalog_managed.json` | Absent | No current size, timestamp, or hash exists for an absent path. |
| `data/career_releases/` | Absent | No release files were available to inventory. |
| `data/career_knowledge_base.csv` | Regular file, 10,109 bytes; modified `2026-10-10T23:34:09.0425569+05:30`; created `2026-09-29T21:10:04.0237848+05:30` | `229D6B4ED077E81F2043515A5CA02EA2FFDEA72E1D32467899F4E7C3AA021E78` |
| `data/career_metadata.json` | Regular file, 4,319 bytes; modified and created `2026-10-13T21:57:27.8053791+05:30` | `238800FFFA961EB70FD70E028552BD05CC639215A0CCFD2ADDA8DFC1CEE36629` |

The two present canonical files have the same hashes as the Phase 2.2C report’s baseline/final readings. This confirms their current contents match those recorded values; it does not establish the pointer files’ prior contents.

## 2. Historical evidence

The earlier report, [`phase2_2c_integration_verification_report.md`](phase2_2c_integration_verification_report.md), records:

- Initial baseline: each pointer/marker path appeared as a file of length 1 byte.
- Final check: both paths were absent.
- It explicitly says no initial pointer hash/content was retained and did not attribute the change.
- Its test inventory lists focused 2.2A/2.2B tests, catalog validation, startup/setup safety, selected recommendation tests, frontend tests, and a Vite build. It says tests that initialize/seed SQLite or mutate catalog releases were skipped.

A one-byte length alone does not reveal whether the file contained a newline, whitespace, JSON, or other bytes. There is no historical file hash, timestamp, backup, copy, or event record in the report to refine that observation.

### Phase 2.1 intent

The versioned-release design [`phase2_1_versioned_catalog_design.md`](phase2_1_versioned_catalog_design.md) describes:

- `career_active.json` as the sole active-release pointer.
- `career_catalog_managed.json` as a fail-closed marker created after versioned catalog activation begins.
- The canonical CSV/metadata pair as bootstrap inputs only before pointer/marker versioned mode is established.
- Release directories as immutable content-addressed CSV/metadata pairs with their own release manifest.

The Phase 2.1 acceptance and implementation reports document release behavior and test results, but do not provide a hash or timestamp for these two files at the Phase 2.2C baseline. Thus they do not independently resolve the one-byte-to-absent transition.

## 3. Reader behavior from source inspection

`backend/services/catalog_releases.py::load_active_catalog` (lines 133–167) implements these branches:

1. If a pointer file can be read, it parses strict JSON, requires exactly `schema_version` and `release_id` with the supported version, then loads and validates that release. Empty/malformed or incomplete pointer content is rejected; it does not fall through to canonical files.
2. If the pointer is absent and the managed marker exists, it parses and validates the marker. A valid marker with a missing pointer raises `CatalogReleaseError("Active catalog manifest is missing after versioned catalog activation")`; invalid marker data also fails closed.
3. If both paths are absent, it reads the canonical CSV and metadata pair, double-reads to detect concurrent change, validates the pair, and returns that snapshot.

`catalog_read_context` (lines 170–176) pins one loaded snapshot while a recommendation run executes. `backend/services/recommendation_engine.py::recommend` calls this context. These are source-level conclusions; the application was not started and the reader was not invoked during this investigation.

`list_releases` (lines 374–390) likewise rejects a missing pointer if the managed marker exists. With both absent, it may enumerate an existing release directory, but that directory is absent in the current filesystem.

## 4. Writer and removal paths

Source search identified these relevant paths in `backend/services/catalog_releases.py`:

- `_atomic_replace_manifest` (lines 251–267) writes a temporary manifest, switches the pointer with `os.replace`, and unlinks only its temporary staging filename in `finally`. It contains no operation that deletes the active pointer.
- `_ensure_managed_marker` (lines 295–312) writes a temporary marker, switches it with `os.replace`, and unlinks only its temporary staging filename. It contains no operation that deletes the managed marker.
- `_prepare_release` (lines 218–248) creates a staging release directory and, on a construction failure, removes files inside that staging directory. It does not remove the active pointer or managed marker.
- `publish_catalog` (lines 315–347) and `restore_release` (lines 349–371) can replace the pointer after validation under the activation lock. They are mutating catalog operations, and neither was run during Phase 2.2C or this investigation.

In `backend/app.py`, `admin_publish_career_draft` removes the processed draft file after a publish result; `admin_discard_career_draft` removes only the addressed draft. `_remove_career_draft` and the create/edit/deactivate error handlers likewise concern draft paths. No pointer or managed-marker deletion was found in these handlers. They were not invoked in either task.

`backend/setup.py` has explicit setup subcommands; normal `backend/app.py` import does not invoke schema initialization, seed, admin bootstrap, or catalog writers. `if __name__ == '__main__'` starts Flask only. Startup/setup code inspection found no pointer or marker cleanup operation. The Phase 2.2C startup-safety test also asserts that importing `backend.app` does not connect, seed, or bootstrap; that test did not report catalog path changes.

The Vite build used a new output directory outside the frontend source tree and failed while resolving `frontend/src/main.jsx`; the Phase 2.2C report states the output directory was not created. Vite configuration/scripts found in the project do not target the two catalog paths. The build was not rerun here.

## 5. Phase 2.2C commands and causation

The Phase 2.2C report records these successful backend commands:

- `python -B -m unittest discover -s tests -p test_phase2_2a_catalog_and_model_selection.py -v`
- `python -B -m unittest discover -s tests -p test_phase2_2b_recommendation_quality.py -v`
- `python -B -m unittest discover -s tests -p test_catalog_validation.py -v`
- `python -B -m unittest discover -s tests -p test_startup_safety.py -v`
- `python -B -m unittest discover -s tests -p test_setup_safety.py -v` (the successful rerun redirected temporary paths to a workspace-local temporary directory)
- `python -B -m unittest discover -s tests -p test_recommendation_engine.py -k school_gap -v`
- `python -B -m unittest discover -s tests -p test_recommendation_engine.py -k class10_roadmap -v`
- `npm test`
- `npm run build -- --outDir C:/Users/THANAY/Documents/Codex/.phase2_2c_frontend_build` (failed with `EPERM`; no output directory was created)

The 2.2A generator regression test redirects `ROOT` and `OUT` to a temporary fixture and checks only temporary catalog/metadata hashes; it does not target project `data/`. Catalog validation reads and compares the canonical career CSV, and the selected recommendation tests exercise pure gap/roadmap functions. Startup/setup safety tests use temporary paths or mocked setup calls. The report explicitly skipped API, release mutation, legacy schema initialization, and model-loading/training suites.

No command transcript, process monitor output, filesystem journal, or per-file event log is present in the inspected reports/project. The commands above and their results are historical evidence from the Phase 2.2C report, not a complete operating-system audit trail.

## 6. Git/history evidence

Read-only `git log -1 --oneline` reports that `master` has no commits. The Phase 2.2C report also records “No commits yet” and that project files were untracked. There is therefore no committed version of the pointer/marker files or Git history from which to recover their prior bytes, dates, or deletion event. No Git configuration or working-tree operation was performed for this investigation.

## 7. Facts, plausible explanations, and unknowns

### Verified current facts

- Both pointer/marker files and the `data/career_releases/` directory are absent now.
- The canonical CSV and metadata are present and their current hashes match the Phase 2.2C report.
- Current source uses canonical fallback when both pointer and managed marker are absent; it fails closed when the marker exists but the pointer does not.
- The project source cleanup operations found by search target temporary release staging files or Admin draft files, not the two named pointer paths.
- Git has no commits, and there is no release directory to inspect.

### Historical facts from the previous report

- It observed one-byte files at the pointer and marker paths during its initial baseline and absence at its final check.
- It retained no content/hash/timestamp for the one-byte files and did not identify the actor or operation.

### Plausible but unproven explanations

- The one-byte files may have been empty/placeholder artifacts, but their bytes were not captured, so even that cannot be confirmed.
- They may have been removed by an external cleanup, workspace replacement/synchronization, or an unrecorded command/process. No evidence identifies any of these as the cause.
- The prior read may have observed transient filesystem state. There is no observation history to test this possibility.

### Unknowns

- Exact prior file contents, hashes, creation/modification timestamps, and attributes.
- Whether the one-byte files were valid JSON, invalid placeholders, or transient entries.
- Whether versioned catalog activation had ever successfully occurred in this exact workspace.
- Which process, command, user action, or synchronization event—if any—removed the files.
- Whether the deployment environment resolves these relative paths to this same workspace.

## 8. Recommendation and safety confirmation

Do not restore or recreate either file based on the one-byte observation. First have the project owner confirm whether this checkout is expected to be in canonical-bootstrap mode or to have an active versioned release. If versioned mode is expected, the next authorized action should be a separately approved, read-only inventory of an authoritative backup/deployment copy or workspace history; only after identifying a validated release and approval should any restoration be considered. If canonical-bootstrap mode is intended, the current source path would validate the present CSV/metadata pair at runtime, but that runtime read was deliberately not performed here.

**Safety:** This investigation read files, metadata, hashes, and source only. It did not start the app, run tests or setup, connect to MySQL, or modify any pointer, marker, release, canonical catalog, metadata file, source, configuration, permission, or Git setting. The only planned write is this new report, created because the target path was absent.
