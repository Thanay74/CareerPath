# CareerPath Phase 2 — Read-Only Database and Data Quality Audit

**Audit date:** 2026-10-22  
**Project:** outputs/CareerPath  
**Status:** Findings and recommendations only; no fixes implemented.

## 1. Executive summary

Read-only metadata and aggregate SELECT queries successfully connected to MySQL 8.0.46, schema careerpath, through the configured mysql+pymysql driver. All 27 tables use InnoDB. Targeted foreign-key orphan checks returned zero for users/students, academic records, assessments, aptitude attempts, and recommendations. No student row values, names, email addresses, passwords, tokens, or credentials are disclosed.

The major finding is a split catalog source of truth. MySQL has populated education lookup data (24 programs, 74 specializations, 113 subjects), but all seven relational career/skill tables are empty. The education API reads Python configuration; career recommendations read a local CSV plus JSON metadata; admin career edits rewrite those files and separately log to MySQL. Current recommendations can therefore work while MySQL catalog reports and future deploy/backup/integration workflows see empty or stale career data.

Career-family ML uses locally generated synthetic labels: the generator selects a family first, then generates profile data from that family’s hand-authored score archetype. Near-perfect reported test metrics are evidence of agreement with that generator, not validity for actual students. The Kaggle-published dataset is also documented as synthetic; its separate 16-class benchmark has 39.5% XGBoost holdout accuracy and is not connected to the live recommender. No user-collected survey data was found.

Previously named files indian_education_full_dataset_with_interests_5000.csv, age_interest_career_dataset.csv, and CareerPath.ipynb were not found in this project tree. Their prior missing-value counts cannot be re-verified. No P0 incident was confirmed. P1 priorities are agreeing on catalog ownership, protecting production startup from implicit schema writes, and maintaining truthful synthetic-model claims.

## 2. Scope and safety

Inspected project code, schema and migrations, API/frontend catalog flow, recommendation and skill-gap logic, model training/evaluation/explainability code, data documentation, listed CSVs, model artifact inventory, and the configured live MySQL metadata/aggregate data.

No MySQL writes were executed. I did not import the Flask app because module initialization invokes init_db(), which can execute DDL and seed catalogs. No migrations, seeds, tests, model training, app startup, or browser workflows were run. No source, data, notebook, model artifact, dependency, or configuration file was modified. The only new file is this report.

The project directory has no Git repository metadata, so git status could not be obtained. No CareerPath.ipynb or the two historically cited CSVs were found in this project.

Evidence labels: **Confirmed** = directly seen in files or queried; **Suspected** = structural risk not demonstrated as runtime failure; **Not verified** = needs external evidence, additional access, or execution outside this audit.

## 3. Project and database inventory

| Area | Relevant implementation |
|---|---|
| Flask API and direct SQL adapter | backend/app.py: connect_db, init_db, valid_profile, education/profile/assessment/recommendation/admin routes |
| Education catalog | backend/education_catalog.py; returned directly by GET /api/education/catalog |
| Career compatibility and gaps | backend/services/recommendation_engine.py; reads data/career_knowledge_base.csv and data/career_metadata.json |
| Class 10 pathways | backend/services/school_pathways.py |
| Career-family ML | backend/ml/career_data_loader.py, feature_engineering.py, career_preprocessing.py, train_career_models.py, career_evaluation.py, predict.py, explain.py |
| Kaggle benchmark | backend/ml/kaggle_career_features.py, preprocess_kaggle_career.py, train_kaggle_career_model.py |
| Public academic experiment | backend/ml/data_loader.py, preprocessing.py, train_model.py, evaluate_model.py |
| Schema | backend/schema.sql and backend/migrations; DDL/seed logic also exists in backend/app.py:init_db |
| Frontend | frontend/src/main.jsx, frontend/src/educationCatalog.js, frontend/src/ModelExplanation.jsx |
| Provenance/evaluation documentation | DATA_SOURCES.md, DATA_DICTIONARY.md, MODEL_REPORT.md, ARCHITECTURE.md, docs/career-references.md |
| Tests | tests/test_api.py, test_career_ml.py, test_kaggle_benchmark.py, test_ml_pipeline.py, test_recommendation_engine.py; frontend tests under frontend |

There is no SQLAlchemy layer; database access is direct SQL through a SQLite/MySQL adapter. The configured database target was parsed in memory; schema careerpath and driver mysql+pymysql were confirmed, and MySQL version 8.0.46 was queried. Credentials and connection string were not printed. The report uses aggregate counts only.

## 4. MySQL schema and integrity

All 27 tables use InnoDB. Exact row counts explicitly queried:

| Table(s) | Exact count |
|---|---:|
| users / students | 9 / 8 |
| academic_records / assessments | 31 / 215 |
| recommendations / recommendation_events | 5 / 7 |
| aptitude_questions / aptitude_attempts | 25 / 6 |
| aptitude_attempt_questions / aptitude_responses / aptitude_domain_scores | 150 / 150 / 42 |
| education_programs / education_specializations / education_subjects | 24 / 74 / 113 |
| careers, career_pathways, career_requirements, career_skills, career_streams, career_subjects, skills | **0 each** |
| skill_gaps / improvement_plans / admin_audit_logs | 0 / 0 / 0 |
| application_errors | 8 |

Information_schema TABLE_ROWS estimates are approximate and differ from exact counts (for example, recommendation_events estimated 10; exact SELECT COUNT(*) was 7).

Primary, unique, foreign-key, and check constraints exist on the core relational records. Foreign keys connect users/students, student records/assessments, recommendations, aptitude attempts/responses/questions, education programs/specializations/subjects, and career/skill mappings. Tested delete rules include cascade for owned records, set-null for event/audit references, and restrict for referenced skills/subjects. Targeted orphan aggregates were 0 for academic_records.student_id, assessments.student_id, students.user_id, aptitude_attempts.student_id, and recommendations.student_id.

One academic_records.subject_name did not match education_subjects.subject_key or subject_name. Custom subjects are allowed, so this is not confirmed invalid; its value was not inspected. Most subject/stream fields are text rather than canonical FK identifiers. Student academic_performance lacks a DB range CHECK (application validation exists); assessment and academic record scores have 0–100 checks. students.education_level is an ENUM, while education_programs.education_level is unconstrained VARCHAR. Active state is inconsistent across catalogs: users and aptitude questions have relational flags; career active status is in JSON; most education catalog rows have no soft-deactivation column.

Aptitude aggregate checks: 25 questions, all active; all had nonempty education-level mappings and an answer-key key present in their options object; seven domains each had 3–4 questions. No answer key or question text was read.

Class/level group counts: programs are 4 Class 10 streams, 5 Class 12 streams, 8 Bachelor’s degrees, and 7 Master’s degrees. Saved students: 5 Class 10, 0 Class 12, 2 Bachelor’s, 1 Master’s. For the five Class 10 profiles, three lacked a stream and all lacked degree/specialization/performance values. Degree absence may be correct at Class 10; stream/performance incompleteness requires owner interpretation. Two Bachelor’s and one Master’s profiles had these fields. This snapshot does not identify whether users are real, tests, or representative.

### Finding DB-01 — P1 / High / Confirmed: split career catalog persistence

The career/skill tables in MySQL are empty, while 25 active career rows are read from CSV and metadata JSON. The education API returns Python config despite separately seeded education tables. Admin create/update/deactivate career flows write CSV/JSON and separately log events to MySQL. The running recommender is file-based; this is not proof recommendations currently fail. It does mean DB-facing counts, backups, deployments, and integrations can disagree with what the engine uses; file changes may not replicate across containers or instances.

**Recommendation:** decide and document one authoritative catalog store. If moving to MySQL, plan reviewed reconciliation and a reversible migration. Project owner and DBA approval are required before catalog writes/migration.

## 5. Datasets and provenance

SHA-256 values identify the exact local files inspected; hashes do not prove source authenticity.

| Dataset | Local result | Provenance/role and caveat |
|---|---|---|
| data/raw/student_performance/extracted/student-mat.csv | 395 rows × 33 columns; 0 missing cells; 0 exact duplicate rows; SHA-256 e47f9ee225e1ee6e69b7564e6dac7123e80b8486677fe111f351964cef5dec80 | UCI math-course academic data per local DATA_SOURCES.md. G3-derived grade-band experiment only; not career outcomes. Ages observed 15–22. External source/license not independently checked here. |
| data/raw/student_performance/extracted/student-por.csv | 649 × 33; 0 missing; 0 exact duplicates; SHA-256 a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f | UCI Portuguese-course cohort per local docs; may overlap math cohort, so do not sum as unique people. |
| data/raw/kaggle_student_career_success/student_career_success_dataset.csv | 50,000 × 29; 0 missing; 0 exact duplicates; SHA-256 b235b3e0acef6a990d2906214f23fb4e4cb78907ae9ecdea62a32bdaac5fc8c0 | DATA_SOURCES.md attributes this to Kaggle contributor Mobeen Fatima and records synthetic provenance and CC BY-SA 4.0. Source card/license not independently browsed during audit. Target Career_Field includes 10,960 Not Placed and 39,040 placed. Near duplicates and ID uniqueness were not tested. |
| data/processed/kaggle_student_career_success/career_field_training.csv | 39,040 × 16; 0 missing; 0 exact duplicates; SHA-256 2634ce25d13fd56f934aae4f57a93063a959926e839bcad078edf4721b5a7550 | 15 feature fields plus Career_Field, conditional on synthetic placement. Not connected to live recommendation service. |
| data/synthetic/career_training_profiles.csv | 1,600 × 59; 0 exact duplicates; SHA-256 8f7ffe1706f88f443f345b8caba7c7a3497c1b099a12c00d64279e19f83274de | 400 generated profiles per stage, five family labels, seed 20260929. Eleven subject columns have blanks (39.69–72.19% per field); generator intentionally blanks stream-inapplicable subjects. |
| data/synthetic/students.csv | 240 × 18; 0 exact duplicates; SHA-256 11db59a6f6be86f997e08339d8f5fa56eb8754a3271e309128dcf185faf0de3c | Synthetic development profiles, 56–64 per stage; subject blanks 9.17–62.92%. Not survey data. |
| data/career_knowledge_base.csv | 25 × 12; 0 exact duplicates; no blank cells; SHA-256 229d6b4ed077e81f2043515a5ca02ea2ffdea72e1d32467899f4e7c3aa021e78 | Curated requirements, not observed student outcomes. Qualification source claims still need official verification. |

The locally documented Kaggle Employability_Score ranges 82.3–279.05, not the application’s 0–100 scale. Its CGPA is 2.0–4.0, unlike the app’s 0–10 scale. Both are excluded from the live service; the training feature code excludes Employability_Score and CGPA remains on source scale in the separate benchmark. The raw Kaggle source includes post-outcome fields (interview, placement/company/salary/mode); documented training excludes them. It is documented as synthetic and cannot support real placement claims.

The older reported 40,000/900 missing-cell findings cannot be verified because those two referenced CSVs are absent. No user-collected survey dataset was found. The CareerPath.ipynb notebook is also absent and was not audited. License and provenance statements are present in project documentation, but external dataset cards were not checked during this audit.

### Missingness interpretation

UCI files contain no missing cells locally. Generated career profiles contain deliberate stream-dependent non-applicability blanks; do not replace these with zero. The training pipeline fits median imputation and missing indicators inside the model pipeline. Kaggle raw fields have no missing cells locally. No cleaning, imputation, normalization, or rewrite was performed.

## 6. Education catalog and qualification pathways

The maintained Python catalog includes:
- 10th: Science, Commerce, Arts/Humanities, Diploma/Vocational; default subjects.
- 12th: Science PCB, Science PCM, Commerce, Arts/Humanities, Vocational/Diploma; stream-specific subjects.
- Bachelor’s: 8 course choices, specialization and subject mappings.
- Master’s: 7 course choices, specialization and subject mappings.

Backend valid_profile checks values against the Python catalog and custom Other route; frontend receives catalog data through the API and uses dependent options. Changing degrees/specializations updates dependent subjects. Database catalog values are seeded separately. This audit checked counts, not a live API round trip. One unmatched academic subject may be a supported custom subject.

### Finding CAT-01 — P2 / Medium / Confirmed

Education has duplicate representations: Python config is the API/validation source and MySQL has separately seeded lookup tables. Course/program labels match expected counts, but ongoing parity is not guaranteed. Some records permit free-text/custom subjects.

**Recommendation:** define an explicit authority and reconciliation procedure; preserve custom values as custom. Do not claim a course, qualification, or Other entry is officially recognized without verification.

Qualification references/caveats exist in docs/career-references.md and career metadata, but no regulator, school board, institution, licensing or admissions source was externally checked. All eligibility and recognition claims remain **not verified**. At the career CSV level, 20 careers have minimum Bachelor's and 5 Master’s; none is a direct Class 10 or 12 occupational qualification record. School-stage guidance is separate, rule-based pathway exploration.

## 7. Career catalog and skill gaps

The service loads 25 career records from data/career_knowledge_base.csv and family/keywords/active/qualification notes/source metadata from data/career_metadata.json. Class 10 uses four explicitly defined pathway rules. Career rows are file-backed, with text lists and inline numeric score maps.

### Finding CAT-02 — P1 / High / Confirmed

Relational careers/skills and their pathway/requirement tables are empty, although the local career file feeds recommendations and admin edits. File subject/stream/skill identifiers do not benefit from relational FK enforcement.

**Recommendation:** resolve catalog authority and deployment/backup semantics before treating MySQL career tables or admin counts as current.

| Assessment field | Career requirement source | Gap behavior | Action source |
|---|---|---|---|
| Subjects | required_subjects list / Class 10 rule tuples | Relevant assessed subjects compared to project marker for Class 10; later career skill gaps do not treat subjects as technical skills | Subject practice prompts |
| Aptitude | aptitude_requirements map / Class 10 domain rules | Class 10 project marker; later compatibility input, not technical skill deficiency | Aptitude practice prompts |
| Interests | interest_requirements map | Compatibility evidence only, separate from proficiency | Exploration, not deficit action |
| Technical skills | technical_skills inline map | max(0, required-current), only where assessed and explicitly required | Skill-key action templates |
| Employability | employability_skills inline map | Same; missing ratings are unknown, not zero | Skill-key action templates |

### Finding SKILL-01 — P2 / Medium / Confirmed

Career requirement keys are free-text values; the normalized MySQL skills/career_skills tables are empty. Alias/canonical resolution is incomplete (e.g. punctuation/case variants such as UI/UX versus UI UX are not a central canonical key registry). Communication as an interest and as a proficiency are intentionally different dimensions and must not be merged automatically.

**Recommendation:** domain-review canonical IDs and aliases, while keeping interest and assessed skill separate. Approval is needed before changing requirement records or database mappings.

### Finding SKILL-02 — P2 / Medium / Confirmed

The app distinguishes unknown from zero and uses only defined, assessed career skills for later-stage gaps; however the relational requirement catalog has no rows and file requirement scales are curated project thresholds, not externally validated standards. Class 10 uses a stated 60-point practice marker, expressly not an admission or psychometric threshold.

**Recommendation:** record source, scale meaning, stage, assessment mapping, and action provenance for each requirement; do not invent missing requirements.

## 8. Recommendation and model consistency

### Current implementation

The later-stage service uses ML_SCORE_WEIGHT 0.10 in backend/services/recommendation_engine.py, combining 90% profile compatibility and 10% scaled career-family probability when both are available; missing inputs are omitted and remaining profile dimensions are renormalized. Class 10 uses 40% relevant subjects, 25% scored aptitude, 25% interests, and 10% stated preferences (renormalized to available evidence), and combines a broad family signal at 90/10 when available. It calls the result an exploratory compatibility estimate, not a probability of success/admission, and avoids a clear leader when evidence or score margin is insufficient. ML/SHAP explanations are scoped to broad model-family signals, not the rule-based career-specific compatibility.

### Finding REC-01 — P1 / High / Confirmed

data/generate_career_training_data.py chooses career_family first, samples stage/stream and profile scores from family-specific archetypes, and writes synthetic labels. Splitting is stratified and preprocessing is fitted in pipelines, so the procedure avoids ordinary train/test preprocessing leakage; nevertheless train, CV, and test all come from the same label-generating mechanism. Very high scores measure generator-rule recovery, not real student career accuracy.

### Finding REC-02 — P2 / Medium / Confirmed

ARCHITECTURE.md lists stage-specific later-stage compatibility weights that disagree with the current generic WEIGHTS in recommendation_engine.py; current code renormalizes the same component weights over available inputs. Documentation is stale or inconsistent. The audit treated current code as runtime authority.

### Finding REC-03 — P1 / High / Confirmed

MODEL_REPORT.md records 0.975–1.000 stage-model test accuracy on synthetic career-family labels and clearly disclaims real-world validity. The separate Kaggle synthetic 16-class benchmark reports RF 0.392 and XGBoost 0.395 holdout accuracy; it does not meet the requested 90% goal and is not used for live recommendations. No real outcome validity is demonstrated.

### Finding REC-04 — P2 / Medium / Not verified

SHAP is attempted when available/compatible and documented for model-family predictions, but live explanations were not executed in this read-only audit. It must not be presented as explaining profile compatibility.

**Recommendation:** preserve experimental labels and metric scope; reconcile architecture documentation; independently validate with a suitable real, consented outcome dataset before claiming learner prediction performance or tuning weights.

### Reproducibility

The docs and scripts describe fixed seeds, stratified holdout, five-fold CV, train-fold preprocessing, accuracy/macro precision/recall/F1, confusion matrices, class reports, CV mean/SD, and saved artifacts. Four stage model artifacts and a separate Kaggle artifact are present. No model was retrained. Prior 32 backend/7 frontend tests are historical SQLite/frontend results; they were not run as part of this audit and do not verify MySQL integration.

## 9. API/frontend consistency

- GET /api/education/catalog returns Python EDUCATION_CATALOG, not SQL rows.
- Profile validation checks current level/stream/degree/specialization against that Python config, including supported Other handling.
- Frontend main.jsx loads the catalog and uses stage/course-dependent controls and subjects.
- Recommendation service reads local CSV/JSON, not MySQL careers.
- Admin career routes read/write CSV/JSON; audit entries are MySQL rows. Persistence locations differ.
- Recommendation snapshots are stored per student; catalog updates do not rewrite older snapshots.
- API/browser runtime and admin round trips were not exercised in this audit.
- Class 10 diploma recognition and local progression require external confirmation.

## 10. Prioritized issue register

| ID | Priority / severity | Status and evidence | Affected files/tables | Recommendation / approval | Verification criterion |
|---|---|---|---|---|---|
| DB-01 | P1 / High | Confirmed: DB career/skill tables empty while app reads files | MySQL careers/skills tables; app.py; recommender; CSV/JSON | Choose a catalog authority; owner and DBA approval before migration/write | DB/API/admin counts and catalog values agree across restart/deploy |
| REC-01 | P1 / High | Confirmed: synthetic label generated from matching score archetype | generator, career models, MODEL_REPORT.md | Maintain experimental scope; independent outcome protocol before validity claim | Independent holdout and documented label definition |
| REC-03 | P1 / High | Confirmed: no real-student validation; Kaggle ~39.5% and synthetic | MODEL_REPORT.md, Kaggle benchmark | Keep user/supervisor-facing claims accurate | No claim of real 90% accuracy without suitable evidence |
| DB-02 | P1 / High | Confirmed in code: init_db runs CREATE/conditional ALTER/seeds at import/startup | backend/app.py:init_db | Separate migration/seed from API import; DBA review for production | Import/API startup performs no schema writes |
| REC-02 | P2 / Medium | Confirmed: documented component weights differ from code | ARCHITECTURE.md, recommender | Reconcile docs after owner review | Hand calculations match runtime and docs |
| CAT-01 | P2 / Medium | Confirmed duplicate Python and SQL education catalogs | education_catalog.py, education tables | Declare authority; preserve custom entries | API, validation, DB catalog parity |
| SKILL-01 | P2 / Medium | Confirmed text skill keys, incomplete aliases, empty normalized table | career CSV, skills/career_skills | Domain-review canonical IDs/aliases | Required skills map without conflating interests/proficiency |
| SKILL-02 | P2 / Medium | Confirmed file requirements are curated; DB requirements empty | career CSV, career_skills, gap logic | Track evidence/scale/stage for every requirement | Every gap traces to assessed value and reviewed requirement |
| DATA-01 | P2 / Medium | Provenance/license only documented locally, not externally rechecked | DATA_SOURCES.md, raw files | Verify source card before redistribution | Source/version/hash/attribution/license evidence retained |
| DATA-02 | P2 / Medium | Confirmed historical CSVs and notebook absent | project data tree | Ask owner for original files if still in scope | File identity/path/hash confirmed before referencing old stats |
| CAT-02 | P2 / Medium | Confirmed career file minimum stage Bachelors/Masters only | career KB, school pathways | Keep career routes separate from verified school eligibility | Qualifications have official references or explicit unverified notes |
| DB-03 | P3 / Low | Confirmed free-text reference fields and uneven active flags | DB catalog tables | Define consistent lifecycle and semantic-key policy | Inactive filtering/reference checks consistent |
| TEST-01 | P3 / Low | MySQL authenticated integration not verified; no isolated DB | test suite/environment | DBA provisions isolated DB/user before test workflow | Non-destructive account/profile/relogin/isolation tests pass on MySQL |

No finding is labeled P0. Proposed priorities do not authorize changes.

## 11. Data quality scorecard

| Area | Status | Evidence/confidence | Risk and next action |
|---|---|---|---|
| Database integrity | **Needs Improvement** | InnoDB FKs and zero tested orphans; free-text semantic references and no DB performance range; high confidence | Reconcile canonical reference keys and app/DB validation |
| Dataset completeness | **Needs Improvement** | UCI/Kaggle no blanks; generated stage/stream blanks intentional; high confidence locally | Keep missingness distinct from zero; document applicability |
| Provenance/licensing | **Needs Improvement** | Local docs name sources/licenses; no independent source-card verification; medium confidence | Verify primary source/license before redistribution |
| Label quality | **High Risk** | Synthetic family labels generated from archetypes; high confidence | Do not claim actual career outcome prediction |
| Education catalog completeness | **Needs Improvement** | Four stages and choices present; duplicated source; high confidence | Establish one source of truth |
| Career catalog completeness | **Needs Improvement** | 25 file records, seven DB career/skill tables empty; high confidence | Align database, admin and deployment persistence |
| Qualification reliability | **Not Verified** | Local guidance references/caveats; no official requirements checked | Verify with board/institution before eligibility claims |
| Skill taxonomy | **Needs Improvement** | Free-text keys and no relational skill rows; high confidence | Canonical identifiers/aliases with domain review |
| Skill-gap mapping | **Needs Improvement** | Inline curated maps, no DB requirements, no external threshold validation | Measure mapping coverage; preserve unknown values |
| Explainability | **Needs Improvement** | Model family scoped separately, but docs weights conflict | Reconcile documentation and explainability scope |
| Education-stage suitability | **High Risk** | Stage-specific code exists, but model labels synthetic; no stored Class 12 profile in snapshot | Validate UX/data contracts separately from model validity |
| Testing/reproducibility | **Needs Improvement** | Seeds, pipelines and metrics exist; prior tests used SQLite, not MySQL; no test rerun now | Provision isolated MySQL integration environment |

## 12. Proposed remediation order

1. Decide career/skill and education catalog authority; review startup DDL/seed behavior (DB-01, DB-02, CAT-01).
2. Preserve synthetic-only metric labeling and clarify a real outcome validation plan (REC-01, REC-03).
3. Reconcile current score weights and docs with hand-computed examples (REC-02).
4. Obtain official qualification/recognition evidence in a separately approved verification phase (CAT-02).
5. Review canonical skill identifiers, requirement sources, score scales and stage mappings (SKILL-01, SKILL-02).
6. Obtain the missing historical datasets/notebook if they remain in scope; verify licenses before redistribution (DATA-01, DATA-02).
7. Provision isolated MySQL then run authenticated integration tests without touching careerpath live records (TEST-01).

## 13. Decisions/access needed

- Should MySQL or versioned project files be the authoritative career/skill catalog?
- Are the two historically referenced CSVs and CareerPath.ipynb stored elsewhere and required?
- Is the intended product claim exploratory guidance only, or is a consented real-outcome validation study planned?
- Should official qualification references be checked in a separate phase?
- Can a DBA provision an isolated MySQL test schema and scoped account? The live application account cannot create a schema and was not used for writes.

## 14. Limitations

No external browsing was done; source cards, licenses, board rules, admissions, recognition, and licensing claims remain unverified. No individual student row values were viewed or copied. No browser/API runtime or authenticated MySQL flow was exercised. The notebook and two historical datasets were absent. Exact duplicate rows were checked, but near-duplicates, ID uniqueness, full stratified missingness analysis, and independent synthetic target provenance were not. No tests, migrations, training, seeds, app startup, schema writes, or recommendation calls ran. Git status was unavailable because the directory is not a Git repository.

## 15. Read-only queries and commands

Connection values were parsed in memory; no credential or connection string was printed. Read-only query families included:

- SELECT VERSION(), DATABASE(), CURRENT_USER().
- SELECT over information_schema.tables, columns, statistics, table_constraints, key_column_usage, check_constraints, and referential_constraints.
- SELECT COUNT(*) per known table; aggregate GROUP BY counts for user role, education level, assessments, programs, aptitude domains, and error status.
- Aggregate LEFT JOIN orphan checks for student, assessment, academic, aptitude-attempt, and recommendation references.
- Aggregate aptitude JSON key/education mapping checks.
- SELECT comparisons of free-text academic subject names to subject dictionary key/name.

Local inspection used directory listing, file reads, Python standard-library csv/hashlib in memory, and source search. No stored procedure, trigger, migration, write SQL, or arbitrary SQL was invoked.

## Final verification

- **Report created:** this new Markdown file.
- **MySQL writes:** none.
- **Existing student records:** left untouched by this audit.
- **Source, datasets, notebook, model artifacts, environment, dependencies:** not modified.
- **Recommended fixes:** not implemented; awaiting approval.
