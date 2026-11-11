# CareerPath Phase 2.1 — Catalog Architecture and Safe Startup Plan

**Planning date:** 2026-10-22  
**Scope:** Source review and planning only. No app, test suite, database, migration, seed, data file, model, or configuration was executed or changed.

## 1. Recommendation summary

Use a per-domain ownership model instead of moving every catalog into MySQL at once.

- Keep curated education choices, subjects, school pathways, career records, skill requirements, qualification notes and family mappings in their current version-controlled project files. These are the current sources consumed by APIs, validation, roadmaps, and recommendation logic.
- Keep aptitude questions in MySQL as the runtime and Admin-managed authority. The assessment API reads MySQL and Admin CRUD changes MySQL. Treat backend/aptitude_bank.py only as a versioned initial seed/test fixture, run explicitly—not on every startup.
- Keep student accounts, profiles, assessments, aptitude attempts, recommendation snapshots, events and audit/error records in MySQL.
- Make ordinary Flask startup read-only for schema/catalog data. Move migrations, seeds, and first-admin creation into explicit reviewed commands. The empty career/skill tables should remain empty unless an approved catalog adoption plan defines their use.
- Consider a controlled, validated catalog import only if MySQL authority is later approved. That would need data-contract mapping, dry-run diff, versioning, rollback, and a student-data-preserving migration plan.

This best fits the existing code with the least migration risk. It resolves ownership by category and avoids changing existing student records or API shapes.

## 2. Current architecture and data flow

This is a source-derived map, not runtime verification.

    React + Vite
      ├─ education catalog request ──> Flask API ──> backend/education_catalog.py
      │                                  ├─ profile validation ──> Python catalog
      │                                  └─ school roadmap ──> Python catalog + school_roadmap.py
      ├─ assessment/profile requests ─> Flask API ──> MySQL student/profile/assessment tables
      └─ recommendations request ────> Flask API
                                           ├─ recommendation_engine.py
                                           │    ├─ data/career_knowledge_base.csv
                                           │    ├─ data/career_metadata.json
                                           │    └─ school_pathways.py
                                           ├─ stage family inference ─> feature_engineering.py
                                           │                              └─ backend/models/career/*.joblib
                                           └─ persisted result ────────> MySQL recommendations/events

    backend/aptitude_bank.py ──startup INSERT IGNORE──> MySQL aptitude_questions
    MySQL aptitude_questions ──assessment/Admin CRUD──> Flask API
    Admin career endpoints ──read/write──> career CSV + metadata JSON
    ML training scripts ──read──> public/synthetic data
                       └──write──> model artifacts + processed metric JSON

## 3. Catalog ownership matrix

| Data category | Current sources and duplicates | Actual consumer/source | Recommended single authority | What changing it affects |
|---|---|---|---|---|
| Education levels, streams, degrees/courses | backend/education_catalog.py and separately seeded MySQL education_programs | GET /api/education/catalog returns Python config; backend valid_profile also checks Python config; frontend/src/educationCatalog.js and main.jsx use the API | Python catalog for now: it is already the API/validation source and is compact, reviewable configuration. Treat SQL rows as legacy/derived until approved migration. | Python changes affect selectors, validation, and subject/profile flow. Editing SQL alone currently does not change selector results. |
| Academic subject options | Python catalog; MySQL education_subjects and join tables; student-entered custom subjects in academic records | API/UI and validators use Python. Recommender maps profile subject keys and aliases. | Python catalog for maintained options. Keep custom student-subject values explicitly marked as custom; do not map unknown to zero. | A key change affects UI sliders, validation, roadmaps, compatibility scoring and education subject associations. |
| School pathways and stream routes | education_catalog.py; school_pathways.py rules; school_roadmap.py; prior audit found matching but separate SQL lookup rows | UI dropdown uses education API; Class 10 ranking uses PATHWAY_RULES; roadmap reads Python sources | Python files, with catalog keys as identifiers. Add parity tests in a later approved phase. | Label/key mismatch can break validation, alter evidence, or cause a missing roadmap route. |
| Degree specializations and related subjects | Python catalog plus education_specializations and subject join tables | API/UI and backend validator read Python catalog; frontend filters dependent subject list from it. | Python catalog, same as course choices. Maintain explicit Other/custom support. | Impacts course choice, validation, assessment subjects, and degree fit. |
| Career records and family labels | data/career_knowledge_base.csv + data/career_metadata.json; SQL careers and related tables exist but prior audit found them empty | recommendation_engine.careers() reads CSV and overlays JSON. Admin career endpoints also read/write those files. | CSV/JSON remain canonical for current runtime; consider consolidating to one versioned data artifact later, with approval. | Impacts ranking, education-stage eligibility, evidence, recommendations, roadmaps, Admin views, and family mapping to models. |
| Skill requirements | Inline score maps in career CSV; SQL skills/career_skills tables empty | Skill-gap calculation parses CSV maps; Admin skills endpoint flattens the same career maps | Keep inline maps canonical until a reviewed skill-ID contract exists. Do not populate empty tables merely for appearance. | Key changes affect gap detection, current/required score rendering, action suggestions, and mapping coverage. |
| Qualification routes and notes | recommended_degrees / optional_certifications in CSV; notes/source URLs in JSON; Class 10/12 route logic in Python | recommendation engine and school roadmap; frontend presents routes with local-verification caveats | Reviewed project files for suggested guidance only. Formal eligibility remains unverified until official-source review. | A route text change can imply eligibility; must distinguish guidance from official requirements. |
| Aptitude questions/answers | backend/aptitude_bank.py seed; MySQL aptitude_questions live/admin copy | Assessment API reads MySQL; Admin CRUD writes MySQL. Startup uses INSERT IGNORE by question ID. | MySQL as live authority. Python bank is initial reviewed seed/test fixture only, run explicitly. | DB changes affect active assessments; changes to seed alone do not update existing IDs. Changes must preserve interpretation of attempts and answer keys. |
| Assessment feature names | Constants in frontend/src/main.jsx; backend/ml/feature_engineering.py; aptitude_bank.py domains; skill keys in CSV | Frontend sends dimension-keyed inputs; backend/recommender/model feature contract filters keys | Define stable namespaced keys by dimension. Identical terms like communication may represent different concepts across interest and proficiency. | Renames can silently drop profile/model inputs or hide gaps. |
| Model family probabilities / SHAP | synthetic training CSV; stage joblib artifacts; metric JSON; ML source | prediction/explanation modules load saved artifacts; recommender uses family signal | Treat saved artifacts/metrics as immutable generated release outputs tied to data hash, seed and feature contract—not catalog authority or real outcome evidence. | Changing feature/family names requires coordinated model retraining and explanation validation. |
| Public/Kaggle/synthetic datasets | data/raw, data/processed, data/synthetic; provenance in DATA_SOURCES.md and data_registry.py | Training/benchmark scripts read declared source; runtime recommendations do not train on users’ submissions | Preserve raw inputs, derived outputs, and synthetic data separately; registry records source, license, hash and purpose. | Replacement alters reproducibility and provenance claims. Never overwrite raw originals. |

Education also has a frontend adapter, but its options come from Flask API; feature-name arrays remain independently declared in the frontend and model contract. API JSON response compatibility should be retained during any approved change.

### Ownership-specific implications

- Education lookup SQL tables are duplicate/derived from Python config; current API ignores them. No deletion or cleanup is proposed.
- Career relational tables are not current recommendation source. Their empty state does not mean recommendations have no career knowledge; it means career data is file-backed.
- Aptitude is the reverse: MySQL is the live runtime source, while the Python question bank is a seed copy. Existing database question IDs win over changed seed data.
- Admin career edits are currently persisted to the app filesystem through temporary CSV/JSON files and atomic replacement, while audit events are stored in MySQL. This can differ across app instances or disappear with ephemeral deployments.

## 4. Startup write inventory

### Startup call path

backend/app.py loads environment configuration and calls init_db() at module line 189. Thus normal module/WSGI import and python -m backend.app both invoke initialization. This is a static code trace; the app was not imported or run for this task.

MySQL DDL may implicitly commit. The end-of-init explicit commit cannot make all prior DDL a single rollbackable migration. There is no schema migration ledger in the startup path.

| Operation / source | When and affected tables | Idempotency / overwrite risk | Permission and risk |
|---|---|---|---|
| CREATE TABLE IF NOT EXISTS in init_db() | Every import/startup for users, students, academic_records, assessments, recommendations, aptitude_questions/attempts/responses/domain scores, education programs/specializations/subjects and joins, recommendation_events, application_errors, admin_audit_logs | Idempotent if table exists; does not reconcile its existing definition. No rows intentionally overwritten. Event/error CREATE statements are duplicated in this function. | Requires CREATE at normal startup. MySQL DDL can commit implicitly. |
| Conditional ALTER users | Adds role, is_active, created_at when missing | Conditional and repeat-safe after add; defaults can populate old rows when adding non-null columns. No explicit updates/deletes. | Requires ALTER on startup. |
| Conditional ALTER students | Adds profile_updated_at and profile fields; modifies legacy profile_json to JSON NULL if present | Adds are conditional. MODIFY can convert/change an existing column and should be reviewed against actual legacy data. | Requires ALTER; DDL may commit. |
| Legacy assessment rename | If assessments exists without assessment_type, renames it to assessments_legacy_json, then creates normalized assessments | Conditional once the legacy shape is gone. Rename retains the old table but code does not copy its legacy JSON values into normalized records; current APIs then use new table. This may make legacy values inaccessible. | Requires ALTER; highest-risk startup migration item. |
| Conditional ALTER aptitude_questions | Adds is_active if absent | Additive/repeat-safe | Requires ALTER. |
| seed_education_catalog(conn) | Every startup may INSERT missing education_programs, education_specializations, education_subjects and relationship rows | Select-before-insert/unique keys make same seed repeat-safe; never updates changed entries or removes obsolete ones, so stale rows remain. | Requires SELECT/INSERT at startup. |
| seed_aptitude_questions(conn) | Every startup may INSERT missing aptitude_questions IDs via INSERT IGNORE | Repeat-safe; existing IDs are not refreshed from Python seed, even if question data changes. No deletion. | Requires INSERT at startup. |
| commit then bootstrap_admin() | Every successful initialization; users table if configured email absent and password meets length | Inserts a salted/hash admin and token only when no matching email exists. Does not overwrite existing account. Conditional and repeat-safe for same email. | Requires SELECT/INSERT; normal startup may create an account. |
| SQLite init branch | Same import path when MySQL URL is absent | Creates tables, runs conditional ALTER/rename, seeds catalog/question rows, optional admin insert. | Local SQLite file is mutated during import too. |

No startup DELETE statement was found. Runtime writes outside startup include normal student profile/assessment/recommendation operations, Admin account/question operations, CSV/JSON career edits, audit logging, and application_errors inserts for failed API requests.

**Finding START-01 — P1 / High / Confirmed:** normal module startup can create/alter schema and insert catalog/admin rows. MySQL application account needs DDL privileges just to import/start. DDL may partially commit on failure, and a legacy assessment rename does not migrate values into the new record structure.

**Target:** module import should only construct the app/routes. Migrations and seeds should be explicit reviewed commands. The normal runtime account should not require CREATE or ALTER.

### Safe future tests

1. Unit-test migration planning without connecting to the live application DB.
2. Provision a disposable MySQL database and scoped user.
3. Record schema and aggregate counts before; run migration; record exact changes; repeat and confirm no-op.
4. Use synthetic fixtures only; check legacy assessment values preserved/mapped before switching.
5. Run app with a runtime account that lacks CREATE/ALTER.
6. Test startup/admin/user flows only in that disposable database; delete only test records created there.
7. Never reset the live careerpath database.

## 5. Catalog strategy comparison

| Approach | Benefits | Tradeoffs and risks | Fit |
|---|---|---|---|
| A. Files remain maintained catalogs; backend validates/exposes them | Fits current education and recommender sources, enables code review/diffs, avoids migration and keeps startup read-only. | Admin career edits mutate local files; multi-instance/ephemeral deployments need shared/versioned publishing. Duplicate unused SQL tables need an explicit legacy/derived status. | Best near-term fit for education, school routes, careers, requirements and qualification guidance. |
| B. MySQL authoritative for every catalog | Shared transactional Admin changes, central read path and FK support. | Requires all API, validator, UI, roadmap and recommendation reads to move; SQL schema may not encode all file metadata/family/source semantics. Empty relational career tables need an approved import; migration and compatibility risk is significant. | Not a direct next step. Consider only after owner approves target schema and data contract. |
| C. Controlled validated import/synchronization | Dry-run diff, review, version/checksum and explicit publish; can bridge files to DB safely. | Without one named authority, it creates two writable sources and conflicts. Needs audit trail, conflict policy and rollback. | Use only as a future transition if MySQL adoption is approved. Until then, no background sync or startup import. |

### Recommended target ownership

- Version-controlled Python/CSV/JSON remains the canonical source for education, school pathway rules, career descriptions/families, inline skill requirements and qualification guidance.
- MySQL remains authoritative for student/application data and aptitude questions.
- The Python aptitude bank becomes only an initial seed fixture; no startup refresh.
- Model files/metrics are derived release artifacts tagged with source hash, feature contract, seed and training code version.
- Do not drop or populate catalog tables in this planning phase. Later, decide whether education lookup tables are retained as derived rows or retired through a reviewed migration.

## 6. Model, dataset, qualification and skill recommendations

### Model labels and explanation

- Keep profile compatibility separate from model-family likelihood in API results and UI.
- Describe the 90/10 combined score as an exploratory rank, never admission/success probability.
- Label model-family outputs and SHAP as experimental synthetic-data signals; SHAP explains model family only, not rule-based career compatibility.
- Keep null/unassessed values distinct from numeric zero; preserve missing indicators in preprocessing.
- Record source hash, feature-contract version, seed and artifact version with metrics. Do not retrain or change weights in this plan.
- Reconcile ARCHITECTURE.md component weights with current implementation only after approval.

### Missing datasets and notebook

The earlier named datasets and CareerPath.ipynb were not present in the inspected project. Ask the owner to locate original copies in prior project folders, Downloads, cloud storage, or original delivery attachments. Preserve originals and record path/hash before read-only review. Do not invent or generate replacements. This review did not search outside the project tree.

### Dataset provenance and licenses

Verify primary UCI/Kaggle source pages, file version, license/attribution and reuse terms in a separate task. Local documentation is evidence of what the project claims, not independent license verification. Maintain source URL/provider/access date/license/hash/purpose/derived-from records. Do not redistribute until license terms are verified. Keep Kaggle records identified as synthetic, not real student/placement data.

### Official qualification rules

A separately approved verification task should use the applicable official school board, institution, regulator or licensing authority. Record source, jurisdiction, effective date, exact prerequisites and reviewer. Distinguish suggestion from formal eligibility; until verified, clearly say requirements need local confirmation.

### Skill identifiers and zero-vs-unassessed

- Define stable lowercase snake_case IDs and a reviewed alias map.
- Namespace by concept: subject, aptitude, interest, technical proficiency, employability proficiency.
- Do not merge similar labels like UI/UX and UI UX or Data Analysis and Data Analytics without domain review. Communication interest and communication proficiency remain separate.
- Only calculate a gap where an assessed value and an explicit matching-dimension requirement both exist.
- Null/absent remains unassessed; 0 remains a real score. Do not turn missing or non-applicable values into zero.

## 7. Incremental remediation plan (not implemented)

| Step | Scope | Verification gate |
|---|---|---|
| 0. Baseline/approval | Capture API schemas, catalog hashes, feature contracts and DB schema/counts; approve ownership choices. | Read-only baseline signed off. |
| 1. Catalog validators | Add pure validation for unique keys, stage links, degree-specialization-subject combinations, career IDs/families/score maps, requirement keys and source metadata. | Unit fixtures reject duplicate/malformed values without modifying files. |
| 2. Startup isolation | Move DDL, education seed, question seed and admin bootstrap out of module import; add explicit versioned migration/seed commands. | Import test blocks DB access; disposable MySQL migration is repeatable; normal runtime user lacks DDL rights. |
| 3. Catalog source declaration | Keep current file-backed catalogs as canonical; document SQL education tables as legacy/derived; declare aptitude DB authority. | API/UI values match approved catalog hashes; no stale seed overwrites Admin-edited aptitude questions. |
| 4. Admin publishing | Decide whether career file changes remain live or become validated draft→review→publish versions. Ensure persistence is shared across app instances. | Invalid edit cannot publish; prior catalog version can be restored; audit records version/hash. |
| 5. Skill contract | Add canonical namespaced IDs/aliases and provenance while keeping existing API adapters during transition. | Coverage report maps every current requirement or marks it unavailable; dimensions do not merge. |
| 6. Model display/document consistency | Align wording/docs and attach feature/data/artifact provenance. No model retraining without approval. | UI/API/docs consistent; synthetic performance never presented as real outcome accuracy. |
| 7. External-source review | Verify dataset license/provenance and official qualification sources in a separate approved task. | Every external claim has authoritative source/version or explicit unverified label. |
| 8. Integration regression | Run backend/frontend tests and authenticated flows on an isolated MySQL environment. | No live rows touched; exact before/after counts and test results documented. |

## 8. Risks and rollback

- Never truncate/recreate student tables. Any approved schema change needs a reviewed backup and exact pre/post aggregate counts.
- MySQL DDL may implicitly commit; migration rollback must be planned, not assumed. Use one migration at a time, explicit migration versions, and a disposable clone first.
- Keep the legacy assessment table/field until mapped values are verified and an owner approves cleanup. Rename alone preserves bytes but does not guarantee application usability.
- Do not change question seed from INSERT IGNORE to upsert without ownership decision; upsert could overwrite live Admin content.
- File-backed edits can be lost or diverge on ephemeral/multi-instance deployments. Use versioned/shared publishing or approve MySQL ownership before production scaling.
- Catalog API changes touch frontend fields, validation, roadmaps and scoring together. Keep API contracts until parity/regression gates pass.
- Family/feature key changes can break model artifacts and explanations. Version the contract and artifact as a unit.
- Qualification references are not proof of eligibility. Maintain verification notices until reviewed.

## 9. Decisions requiring your approval

1. Approve files as the near-term authority for education/career/skill catalogs and MySQL as authority for student data and aptitude question runtime records?
2. Should Admin career edits take effect immediately on the host or be staged and published as versioned catalog releases?
3. Should education SQL tables remain as a derived mirror, or stop being maintained through an approved migration? This plan proposes no deletion.
4. Approve MySQL as formal aptitude-question authority, with Python bank used only for explicit initial seed/test fixtures?
5. Would you like a separate task to locate the missing files/notebook and verify licenses/official qualification sources?
6. Can a DBA later provide an isolated MySQL test schema for safe migrations and integration checks?

## 10. Limitations and completion

This is based on source inspection and the facts supplied from the earlier Phase 2 audit. The database was not queried in this planning task, and the application/tests were not run. External dataset cards, licenses, qualification rules, private files outside the project, and individual student records were not inspected. The described writes are static code paths, not writes executed in this task.

The report is new and was created only after confirming the target path was absent. No source, dataset, notebook, model artifact, config, dependency, credential, permission, MySQL table, or existing student record was changed. No tests are claimed to have passed. **Wait for approval before implementing any changes.**
