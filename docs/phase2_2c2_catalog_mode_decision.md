# CareerPath Phase 2.2C2 — Catalog Mode Decision

**Date:** 2026-10-22  
**Scope:** Read-only decision for the current development checkout. No catalog mode was changed or activated.

## Decision

**Recommendation: Canonical-bootstrap mode for this development checkout.**

This recommendation follows the existing versioned catalog design: canonical CSV/metadata are the bootstrap source until versioned mode has been established. In the current checkout, both pointer and managed marker are absent, and no release directory exists. The current reader therefore selects the canonical-pair branch. The canonical CSV and metadata hashes match those recorded in the Phase 2.2C verification report.

This is conditional on the owner confirming that this checkout is meant to be in its pre-versioned development state. The earlier one-byte pointer/marker observations remain unexplained. They are not evidence of a valid active release: their bytes were not retained, and one byte cannot hold the current JSON manifest/marker structures. No recovery or activation was performed.

**Production is not approved by this decision.** Before production use, the deployment owner must decide whether catalog releases are a deployment gate, validate the exact catalog pair and provenance, ensure persistent shared storage and rollback/recovery procedures, and explicitly activate or recover a validated versioned release through an approved operational task. The current setup/deployment documentation describes MySQL setup but does not specify a production catalog-mode gate.

## Evidence inspected

Read-only inspection covered:

- `docs/phase2_2c1_catalog_pointer_investigation.md`
- `docs/phase2_2c_integration_verification_report.md`
- `docs/phase2_1_catalog_architecture_plan.md`
- `docs/phase2_1_versioned_catalog_design.md`
- `docs/phase2_1_final_acceptance_audit.md`
- `docs/phase2_1_build_recovery_and_catalog_release_report.md`
- `docs/phase2_1_implementation_report.md` and `docs/phase2_1_safety_review.md`
- `README.md`, `SETUP_GUIDE.md`, and `ARCHITECTURE.md`
- `backend/services/catalog_releases.py`, `backend/catalog_validation.py`, `backend/data_registry.py`, `backend/database_config.py`, and `backend/setup.py`

The investigation report says the source catalog pair remained hash-identical to the Phase 2.2C baseline. This pass independently reread the current filesystem metadata and hashes:

| Path | Current state | SHA-256 |
|---|---|---|
| `data/career_active.json` | Absent | — |
| `data/career_catalog_managed.json` | Absent | — |
| `data/career_releases/` | Absent | — |
| `data/career_knowledge_base.csv` | Regular file, 10,109 bytes | `229D6B4ED077E81F2043515A5CA02EA2FFDEA72E1D32467899F4E7C3AA021E78` |
| `data/career_metadata.json` | Regular file, 4,319 bytes | `238800FFFA961EB70FD70E028552BD05CC639215A0CCFD2ADDA8DFC1CEE36629` |

No application, setup command, test, database connection, catalog writer, or catalog validator was run in this task.

## Architecture and development behavior

`docs/phase2_1_versioned_catalog_design.md` explicitly defines the canonical CSV and metadata as bootstrap files and says they are used before versioned mode has been established. The same document describes `career_active.json` as the single active-release pointer and `career_catalog_managed.json` as the fail-closed marker created after versioning begins. The architecture does not require a release pointer merely to read a maintained catalog in the pre-versioned state.

In `backend/services/catalog_releases.py::load_active_catalog` (lines 133–167):

1. A present pointer is parsed strictly and must select a valid release. Malformed or incomplete pointer data fails; it does not fall through to canonical files.
2. With no pointer but a present marker, the marker must be valid; a valid marker plus a missing pointer raises an error rather than using canonical files.
3. With both pointer and marker absent, the reader reads the canonical CSV and metadata, checks for change during the read, validates the pair, and returns it.

`catalog_read_context` pins that loaded pair during recommendation computation. `backend/services/recommendation_engine.py::recommend` uses the context. These conclusions are from source inspection, not an application run.

### Local Admin publishing

The versioned design and current `backend/app.py` Admin routes describe staged career changes followed by validated versioned publication. The first publication from canonical mode preserves the canonical pair as a content-addressed rollback release, then establishes a pointer and managed marker before activating the new release (`publish_catalog` and `_ensure_managed_marker`). Thus local development may read canonical data without publishing. If an administrator publishes, the workflow transitions the checkout into managed/versioned mode; that transition was not tested or performed here. Missing an active release afterward should fail closed if the managed marker remains present.

### Production deployment

The reviewed docs discuss MySQL, explicit setup, and the file-backed career catalog, but do not clearly state that a versioned release is mandatory for production. The Phase 2.1 architecture plan identifies ephemeral storage and multi-instance divergence as risks of file-backed Admin edits. Therefore this development-mode decision must not be interpreted as a production-readiness decision. A production environment needs an explicit policy for catalog version, persistent shared storage, startup validation, deployment rollback, and recovery from a missing/corrupt pointer.

## Structural validation assessment — source inspection only

`backend/catalog_validation.py::validate_project_catalogs` (lines 136–149) is the validator invoked by the documented read-only catalog validation command. It combines education-catalog validation with the career CSV and metadata checks. This task did **not** execute that function, `setup.py`, or any validation command, as required.

The inspected checks require:

- Education levels match the supported level set; streams, degrees, specializations, and subjects use valid types, non-empty values, unique values, and recognized degree/stream references.
- Career records include required fields; career IDs use the stable `C<number>` pattern and are unique; names are non-empty and unique; minimum education levels are supported; record values are text; suitable streams refer to defined education streams; and score-map entries have unique keys and finite values in the 0–100 range.
- Metadata is an object keyed to known career IDs; supported family values and field types are enforced for active flags, qualification notes, keywords, and sources.

The current CSV/metadata hashes match the pair that the Phase 2.2C `test_catalog_validation.py` run reported as valid. This is supporting earlier test evidence for unchanged bytes, not a fresh execution in this phase. Existing acceptance documentation notes semantic gaps: for example, not every required-subject/degree token is checked against a complete authoritative registry, and score-map skill keys do not have a canonical skill-ID registry. “Structurally accepted under implemented checks” should not be expanded into a claim that every qualification, source, or skill meaning is authoritative.

## Documentation/configuration alignment

- **Consistent:** The Phase 2.1 design explicitly describes canonical bootstrap behavior and versioned activation; current reader branches match it.
- **Incomplete:** `README.md` and `SETUP_GUIDE.md` explain local SQLite and MySQL deployment setup but do not clearly label canonical-bootstrap mode for local development or define the production catalog-mode requirement.
- **Potentially confusing historical text:** The Phase 2.1 versioned design says career publishing is enabled through the validated release path. It does not state that a versioned release must already exist in every development checkout. The current code permits canonical reads before the first release and Admin publication is the transition.
- **No configuration override found:** `backend/services/catalog_releases.py` derives the three relevant paths under the project `data/` directory. The inspected current configuration does not declare a different active pointer/release path. No environment-specific production catalog path was established by these docs.

## Assumptions and limitations

- The present target directory is the intended development checkout and its current canonical files are the files to be read during development.
- The unexplained one-byte-to-absent transition remains unresolved; this decision does not identify a cause or establish that versioned mode was never activated in another deployment/workspace.
- The earlier Phase 2.2C validation test is relied on only because the canonical file hashes are unchanged; no tests or validator were run here.
- No active release, rollback directory, release manifest, or external deployment copy was available for inspection.
- No MySQL, browser, running application, or deployment environment was accessed.

## Conditions before production deployment

1. The deployment owner must explicitly approve the production catalog mode and identify the exact canonical/release artifact to deploy.
2. Run structural catalog validation in an approved pre-deployment workflow; separately review provenance, licenses, and qualification references.
3. If versioned mode is required, build or recover a complete validated release from an authoritative source and activate it through the approved release mechanism; preserve its rollback release and pointer. That is a separate authorized write task.
4. Confirm persistent shared storage for all application instances and define backup, rollback, and missing/corrupt-pointer recovery procedures.
5. Confirm runtime startup and Admin publication behavior against an isolated deployment-like environment before production. Do not use the live database/catalog for this check.
6. Update setup/deployment documentation to distinguish local canonical bootstrap from production release policy.

## Safety confirmation

This report is the only file created by this task. No source, config, catalog, pointer, marker, release, dataset, database, dependency, permission, or Git setting was changed. No application, test, setup, migration, seed, publishing, restoration, draft-management, or validation command was run.
