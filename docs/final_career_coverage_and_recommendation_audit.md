# CareerPath — Comprehensive Career Coverage, Eligibility and Recommendation Audit

**Audit date:** 2026-11-15  
**Overall status: NOT READY.** The audit found and corrected one general degree-fit defect. The current project does not have enough degree-specific, subject-level, institution-specific eligibility data to claim a complete two-stage eligibility-and-ranking system. Expanding that safely requires a defined admission jurisdiction/institution scope and validated catalog evidence; no canonical data was fabricated or changed.

## A. Project coverage

### Source-of-truth map

| Concern | Current source | Audit finding |
|---|---|---|
| Career role names, descriptions, broad streams, minimum education stage, score requirements and suggested degree routes | `data/career_knowledge_base.csv` | 25 records; 12 columns. This is project guidance, not a complete admission or licensing database. |
| Family labels, search keywords, some qualification notes and a few source URLs | `data/career_metadata.json` | One metadata record for each of 25 career IDs. Only 4 records have source URLs; the file has no last-verified date. |
| Education stages, streams, degrees, specializations and student-assessment subject choices | `backend/education_catalog.py::EDUCATION_CATALOG` | Static Python mapping, not institution admission rules. It does not record subjects actually taken/passed separately from self-assessed ratings. |
| Stage/career score and explanations | `backend/services/recommendation_engine.py` | Rule/profile score plus experimental family-model contribution. |
| Class 10 pathway guidance | `backend/services/school_pathways.py`, `backend/services/school_roadmap.py` | Four pathways; course eligibility is deliberately not inferred from broad career-stream tags. |
| Career-family model | `backend/ml/train_career_models.py`, `backend/ml/predict.py`, `backend/ml/feature_engineering.py` | Four stage-specific model artifacts predict one of five broad synthetic career families. This signal supplements, rather than validates, individual role eligibility. |
| Saved-result freshness | `backend/recommendation_snapshots.py`, `backend/app.py`, `frontend/src/studentWorkspace.js` | Profile and catalog fingerprints; current-only restore is covered by isolated regression tests. |

The career CSV has 25 unique IDs and 25 unique titles. It currently covers software development, web development, data science, AI, cybersecurity, data analysis, UI/UX, mechanical/civil/electrical engineering, medicine, pharmacy, biotechnology, accounting/CA, finance, business analysis, entrepreneurship, teaching, research, psychology, law, journalism, graphic design, digital marketing and public administration. It does not provide broad coverage of all the requested IT sub-roles. In particular, separate Frontend/Backend/Full Stack/Mobile/QA Automation, BI Analyst, Data Engineer, SOC Analyst, Penetration Tester, Cloud Engineer, DevOps Engineer, Network Engineer, Database Administrator, Systems Analyst and IT Project Coordinator records are absent. “Web Developer” and “Data Analyst” are not enough evidence to claim those distinct roles are covered.

### Education choices present in code

- **Class 10:** Science, Commerce, Arts/Humanities, Diploma/Vocational. Class 10 recommendation code returns the four pathway comparisons; the roadmap uses the maintained Class 12 stream/subject catalog and gives later-stage career directions as exploratory guidance.
- **Class 12:** Science PCM, Science PCB, Commerce, Arts/Humanities, Vocational/Diploma. PCMB is not separately represented. Commerce Mathematics cannot be distinguished from Commerce without Mathematics as an actual taken/passed subject combination. The current subject rating values express self-assessment and cannot stand in for transcripts or subject completion.
- **Bachelor’s:** BCA, B.Com, BBA, B.Sc, B.Tech/BE, BA, B.Pharm, Other. Selected specializations and subject lists exist for BCA, B.Com, BBA, several B.Sc/B.Tech areas, B.Pharm, BA and Other. BA does not have separate mapped English, Journalism, Economics, Psychology and Political Science subject contracts. B.Des and several listed example programs are not selectable as explicit degrees.
- **Master’s:** MCA, M.Com, MBA, M.Sc, M.Tech/ME, MA, Other. Specializations include MCA Cybersecurity/Data Science, M.Sc science disciplines, MBA options and other subsets. M.Sc Data Science is not an explicit degree choice, though Data Science appears as an MCA specialization.

Degree major/minor are not separate profile dimensions. Most inputs that resemble subject knowledge are ratings, where missing/null means “not assessed”; they do not establish that a prerequisite subject was studied or passed.

## B. Eligibility correctness

### Actual logic and defect

For non-Class-10 roles, `backend/services/recommendation_engine.py::_stage_eligible` is the only candidate filter. It checks the current education stage against the row’s `minimum_education_level`; it does not filter candidates by `suitable_streams`, `required_subjects`, an actual degree prerequisite, licensing, or a verified alternative route. Stream, subjects, degree and specialization mainly affect the score and explanation. `required_subjects` feeds `_subject_score`; it is not treated as a formal admissions prerequisite.

Before this audit’s correction, `_degree_score` awarded 48/100 whenever a degree and a role shared a broad family such as `technology_engineering`. That family contains both IT and civil/mechanical/electrical engineering, so MCA/Cybersecurity received a “related pathway” degree score for Civil Engineer. A read-only model inference using an MCA/Cybersecurity synthetic profile returned Civil Engineer in its top five at 42.5 with “Related pathway; verify qualifications.” This was a real current-code/catalog defect, not an institution-specific eligibility finding.

### Corrective change

Removed broad model-family membership as degree-route evidence. A degree fit now requires a catalog-listed degree match or an explicit specialization-to-role text match; otherwise the degree component remains low. Non-direct labels now state that eligibility is unverified, and catalog-list matches explicitly say admission eligibility is still unverified. The existing ranking weights were not changed. A general regression in `tests/test_recommendation_engine.py::test_broad_model_family_does_not_create_an_unrelated_degree_route` confirms the civil route has no broad-family degree credit and no longer appears in that test profile’s top five; the cybersecurity result remains explicitly unverified.

This correction addresses the identified mechanism, but it does not turn the remaining recommender into a comprehensive eligibility engine. It still ranks some unverified directions for exploration. No institution-specific subject, entrance, bridge-course or license gate can be inferred reliably from the current catalog.

### Official evidence and jurisdiction limits

Official examples confirm that admission rules are program- and institution-specific:

- NTA’s JEE Main page states Physics and Mathematics requirements for the listed NIT/IIIT/CFTI B.E./B.Tech route and notes that states may use separate criteria. It is not a universal engineering rule. [NTA Engineering Exam](https://www.nta.ac.in/Engineeringexam)
- The University of Delhi’s 2026 UG FAQ says applicants must check program-specific eligibility and that required Class 12 subjects must have been studied/passed and included in the relevant CUET papers. This is a DU-specific admissions source, not a national rule. [University of Delhi UG 2026 FAQ](https://admission.uod.ac.in/userfiles/downloads/2026/17052026_Updated_FAQsUG%202026-final.pdf)
- JoSAA publishes 2026 Business Rules and separate institute/program restrictions, showing that route and institution constraints exist beyond broad stream labels. [JoSAA Business Rules](https://josaa.nic.in/information-bulletin/), [JoSAA program restrictions](https://josaa.nic.in/document-category/restrictions-at-institutes-academic-programs-level/)
- UPSC’s 2026 Civil Services notice requires a recognized graduate degree for the stated examination route. That does not make a student an immediately appointed Public Administration Officer; the competitive examination and other notification rules still apply. [UPSC CSE 2026 notice](https://www.upsc.gov.in/examinations/Civil%20Services%20%28Preliminary%29%20Examination%2C%202026)
- PCI identifies approved pharmacy qualifications and state pharmacy-council registration requirements. This is a regulated route, not a generic career-family inference. [PCI FAQs](https://www.pci.nic.in/FaQs.html), [PCI 2023 circular](https://pci.nic.in/pdf/12-1-2415-circular_04082023.pdf)
- The Bar Council of India publishes legal-education eligibility information and rules; its three-year and integrated law routes have distinct qualifying-degree rules. [BCI educational criteria](https://www.barcouncilofindia.org/info/educationa-de7va7%3F), [BCI Legal Education Rules](https://www.barcouncilofindia.org/info/comprehens-ku2hwr)
- Teacher qualification rules are regulated and role/state dependent. [NCTE minimum qualifications](https://ncte.gov.in/website/minimumqualifications.aspx/nmm/PDF/nmm/Hindi/Hindi/Hindi/TETguidelines.aspx)

These sources support the need for scoped, current evidence. They do not verify every current CareerPath course/career mapping. The catalog’s existing URLs are sparse and metadata has no verification date. No canonical catalog file was edited.

## C. Recommendation quality and coverage

The engine’s profile score compares assessed subject, aptitude, interest, technical and employability values with catalog markers, then considers stage, stream, degree, preferences and research interests. Missing assessment dimensions are excluded rather than set to zero. Class 10 uses pathway-specific evidence; its Stage 3 course list is empty because the existing data does not map Class 12 subject prerequisites to individual degrees. That is safer than labelling broad degree names as pathway-eligible.

The ordinary career ranking returns up to five rows. It combines the knowledge/profile compatibility score with a 10% experimental synthetic-family probability. The response labels this as experimental and separately explains that the family model does not prove role compatibility or eligibility. It is not job-success, admission, or employment probability.

`qualification_status` and `additional_qualifications` are advisory text. They are not backed by a structured per-program eligibility rule. There is no reliable way to classify each current entry as verified eligible now, verified after a named qualification, alternative route verified, not eligible, or unverified. The existing data lacks accepted/required subject combinations, actual qualifications held, degree-specific major/minor, named institutions/programs, exam/licensing detail for most records, sources for most records, and evidence verification dates.

### Required academic profile matrix

“Smoke test” means an existing automated test exercises API/profile/recommendation code and asserts a response, not that it verifies eligibility correctness. `Eligibility` is separately evaluated because the current profile/catalog cannot establish admission prerequisites.

| Synthetic case | Catalog representation / current test evidence | Eligibility decision |
|---|---|---|
| Class 10 Science | Four-pathway API/engine and Science roadmap tests; profile combinations exercised | **PARTIAL** — exploratory pathway behavior tested; local school admission not verified |
| Class 10 Commerce | Class 10 evidence-sensitive engine test and roadmap test | **PARTIAL** — pathway behavior tested; local school admission not verified |
| Class 10 Arts/Humanities | Class 10 evidence-sensitive engine test and roadmap test | **PARTIAL** — pathway behavior tested; local school admission not verified |
| Class 10 Diploma/Vocational | Roadmap route test | **PARTIAL** — recognition/provider progression is explicitly left for verification |
| Class 12 Science PCM | Existing isolated API scenario test | **NOT VERIFIED** — API response shape tested, not course eligibility |
| Class 12 Science PCB | Existing isolated API scenario test | **NOT VERIFIED** — API response shape tested, not course eligibility |
| Class 12 Science PCMB | Not a distinct education-catalog option | **BLOCKED** — unsupported combination cannot be distinguished/configured |
| Class 12 Commerce with Mathematics | UI/catalog exposes Commerce with Mathematics in its subject list | **BLOCKED** — taken/passed subjects are not separate from ratings |
| Class 12 Commerce without Mathematics | Same Commerce option; no “math not taken” state | **BLOCKED** — absence of a rating means unassessed, not absent from transcript |
| Class 12 Arts/Humanities | Catalog option exists; no scenario-specific eligibility assertion | **NOT TESTED** |
| Class 12 Vocational/Diploma | Catalog option exists; no scenario-specific eligibility assertion | **NOT TESTED** |
| Bachelor's BCA | Existing API scenario test | **NOT VERIFIED** — response smoke test only |
| Bachelor’s B.Sc. Computer Science | Existing API scenario test | **NOT VERIFIED** — response smoke test only |
| Bachelor’s B.Com | Existing API scenario test | **NOT VERIFIED** — response smoke test only |
| Bachelor’s BBA | Existing API scenario test | **NOT VERIFIED** — response smoke test only |
| Bachelor’s BA | Degree option exists, but no dedicated API scenario | **NOT TESTED** |
| Bachelor’s B.Sc. non-computing | Some specializations exist; no dedicated API scenario | **NOT TESTED** |
| Bachelor’s specialized B.Tech/BE Computer Science | Existing API scenario test | **NOT VERIFIED** — response smoke test only |
| Master’s MCA/Data Science | Existing API scenario test | **NOT VERIFIED** — response smoke test only |
| Master’s M.Sc. Computer Science | M.Sc. and specialization exist; no dedicated API scenario | **NOT TESTED** |
| Master’s M.Com | Degree exists; no dedicated API scenario | **NOT TESTED** |
| Master’s MBA | Existing API scenario test | **NOT VERIFIED** — response smoke test only |
| Master’s MA | Degree exists; no dedicated API scenario | **NOT TESTED** |
| Master’s MCA/Cybersecurity | New model-family regression test reproduces and closes broad-family Civil Engineer degree credit | **PASS for the specific defect; broader eligibility remains unverified** |

The existing API scenario test asserts nonempty results and result fields for ten profiles; it does not prove eligibility, ordering correctness, alternative-route correctness, absence of all unsupported results, explanation quality, saved restoration, and frontend parity for each matrix case. No output has been represented as a verified admissions decision.

## D. ML/model explanation for the final presentation

### What is actually running

CareerPath’s production recommendation path is a **hybrid**, not a purely ML recommender. `backend/services/recommendation_engine.py` computes rule/profile compatibility from the maintained CSV and the student’s profile, then adds a 10% broad-family model signal. Class 10 uses separate pathway rules and compares four streams.

### Career-family model

- Training code: `backend/ml/train_career_models.py`; fixed-seed synthetic examples are produced by `data/generate_career_training_data.py` and loaded by `backend/ml/career_data_loader.py`.
- Data: `data/synthetic/career_training_profiles.csv`, 1,600 records (400 per education stage), explicitly generated synthetic profiles; five labels: technology/engineering, business/finance, creative/communication, health/life sciences, public/social/research.
- Algorithms: Random Forest and XGBoost are candidate pipelines. Training code chooses by mean 5-fold training-partition CV macro-F1, then evaluates that winner on the held-out partition. The checked-in metrics table currently lists Random Forest as selected for all four stages. Inference is in `backend/ml/predict.py` and uses the checked-in per-stage pipeline files under `backend/models/career/`.
- Model inputs: stage-specific subject, aptitude, interest, technical-skill and employability features plus stream. `backend/ml/feature_engineering.py::feature_row` does not include degree or specialization. The rule/profile score handles degree/specialization separately.
- Prediction target: one of the five synthetic career-family labels—not a specific career, admission result, placement, salary, or likelihood of success.
- Live effect: family probability contributes 10% of the combined score; the compatibility rules contribute 90%. Missing fields are handled by the rule score as unknown, not zero. A high family signal cannot establish qualification.
- Evaluation caveat: `MODEL_REPORT.md` explicitly says the checked-in model artifacts and `data/processed/career_model_metrics.json` are legacy artifacts selected using holdout macro-F1 before the CV-only correction. Their very high synthetic-label agreement is selection-biased and not a corrected-protocol estimate. No corrected-protocol metric is available until the models are retrained into an approved isolated artifact destination. No model training was run, no artifacts were overwritten, and no real-student validity has been established.

### Other model files are separate experiments

- `grade_band_pipeline.joblib` is a UCI Student Performance Mathematics final-grade-band experiment. It is not used to rank career recommendations (`backend/ml/predict.py::predict_grade_band` is separate). `backend/models/MODEL_REPORT_RESULTS.md` reports its own benchmark.
- The Kaggle career-field artifact under `backend/models/kaggle/` is a separate synthetic university-only benchmark and is not connected to the four-stage live recommender. Its purpose/provenance and limitations are documented in `DATA_SOURCES.md` and `MODEL_REPORT.md`.

### Presentation-ready explanation

**Architecture (actual):**

```text
Student profile and assessments
        ↓
Coarse minimum-education-stage filter
        ↓
Rule/profile compatibility score (90%)
        + stage-specific synthetic career-family model signal (10%)
        ↓
Ranked career directions or four Class 10 pathways
        ↓
Reasons, qualification caveats, skill practice guidance and roadmap
```

This diagram does **not** show a complete verified eligibility gate: that feature is not present yet. A simple explanation for an examiner: “CareerPath compares the student’s assessed profile with a curated set of career requirements and uses a small, experimental classifier to add a broad career-family signal. The classifier was trained on generated profiles, so it is a prototype signal, not proof of real-world accuracy. The scores describe profile compatibility, not admission or job success. The catalog still needs institution-specific eligibility evidence.”

Example: a Class 10 student’s reported mathematics/computer-science strengths and technology interest can support the Science pathway, while missing evidence leaves other options open. The UI still compares all four Class 10 pathways and labels the result exploratory. For a Master’s MCA/Cybersecurity profile, cybersecurity may appear as a related direction but is labeled eligibility-unverified; the broad technology family no longer grants Civil Engineer degree compatibility.

## E. Verification and evidence

### Commands run and results

- `python -m unittest discover -s tests -p test_recommendation_engine.py -k broad_model_family -v` — **PASS**, 1 regression test. No database used. Model artifacts/catalogs were read only for inference.
- `python -m unittest discover -s tests -p 'test_*.py' -v` — **PASS**, 100 backend tests in 47.970 seconds. `DATABASE_URL` and `CAREERPATH_DB` were explicitly pointed at a newly created workspace-local temporary SQLite test target; `USE_MYSQL=false` and `CAREERPATH_ENABLE_MYSQL_INTEGRATION=0` were set. This does not prove MySQL integration.
- `npm.cmd test` — **PASS**, 38 tests, 0 failures.
- `npm.cmd run build -- --outDir C:\Users\THANAY\Documents\Codex\.phase2_2k_frontend_build_a6b99d04beba45239c6eba6678c219b8` — first attempt **FAILED** with sandbox Vite `EPERM` resolving `frontend/src/main.jsx`; approved Windows-permission retry **PASS**, Vite 5.4.21, 36 modules, 905 ms. `index.html` and `assets/` were confirmed. Output was outside `frontend/dist`.
- `git diff --check` — **PASS**; only line-ending normalization warnings were printed for pre-existing modified files.

### API and saved recommendation behavior

The full isolated backend suite includes the existing API scenario test for ten representative profiles, recommendation owner scoping, profile/assessment persistence, profile/catalog snapshot invalidation, legacy snapshot preservation and restore-freshness behavior. It also includes the new MCA/Cybersecurity regression. These tests use test-only SQLite fixtures. No live browser response body was captured for this audit.

Phase 2.2J already introduced a saved snapshot contract: deterministic profile-input hash plus catalog fingerprint, authenticated ownership, profile-first restore, and hidden stale/legacy results. Its automated tests passed as part of the 100-test backend suite and the 38-test frontend suite. The previously documented Phase 2.2J Brave session returned `ERR_CONNECTION_TIMED_OUT` at the local Vite origin. Browser refresh restoration and UI/API parity are therefore **BLOCKED**, not newly browser-verified here.

| Check | Status | Evidence |
|---|---|---|
| Backend regression suite | **PASS** | 100 passed, 0 failed; isolated SQLite config |
| Frontend unit suite | **PASS** | 38 passed, 0 failed |
| Production build | **PASS** | Separate output directory; first sandbox EPERM then approved retry |
| MCA/Cybersecurity → Civil Engineer regression | **PASS** | Reproduced pre-fix; targeted regression passes after general family-fallback removal |
| All matrix cases’ eligibility | **BLOCKED** | Missing evidence/subject-history model and verified per-program eligibility data |
| Live saved snapshot browser refresh | **BLOCKED** | Local app not reachable from available browser session |
| Browser API/UI parity across four stages | **BLOCKED** | No browser response bodies/card comparison in this audit |
| Responsive viewports and accessibility | **NOT TESTED in this audit** | No reachable browser runtime; Phase 2.2I has partial historical observations only |
| MySQL integration | **NOT TESTED** | No MySQL connection or operation performed |

### Database/catalog/model safety

- Tests used a workspace-local isolated SQLite target; MySQL integration was explicitly disabled. No live MySQL database was contacted.
- No database setup/migration/seed, catalog publication, release restore, account bootstrap, model training, or deployment was run.
- Canonical catalog contents and hashes were not modified by this audit. The relevant previous verified hashes remain: `career_knowledge_base.csv` `229d6b4ed077e81f2043515a5ca02ea2ffdea72e1d32467899f4e7c3aa021e78`; `career_metadata.json` `238800fffa961eb70fd70e028552bd05cc639215a0ccfd2adda8dfc1cee36629`.
- No model artifact, metric file, student record, credential, active release pointer, or runtime database was modified.
- The repository was already dirty before this work. Existing Phase 2.2F–J changes were preserved; no reset, stash, checkout, clean, or commit occurred.

## F. Final status and smallest remaining work

| Area | Status |
|---|---|
| Catalog inventory and current education input coverage | **PASS** for inspection; coverage gaps documented |
| Broad model-family degree-credit defect | **PASS** for correction/regression |
| Strict, institution-backed two-stage eligibility filtering | **BLOCKED** by missing subject history, structured prerequisite/alternative-route data, source dates, and institution scope |
| All requested academic-combination eligibility matrix | **BLOCKED / NOT TESTED** as itemized above |
| Model explanation and limitations | **PASS** for source-based explanation; model predictive validity **NOT VERIFIED** |
| Unit/backend/frontend/build verification | **PASS** for commands/results listed |
| Browser, responsive, and accessibility release gates | **BLOCKED / NOT TESTED** |
| Production readiness | **NOT READY** |

Smallest steps to finish safely:

1. Choose a jurisdiction and a small institution/program set for admission checks; then add structured evidence (required/accepted subjects, prior qualification, entrance exam, bridge route, license, source URL, effective/verification date) through a reviewed catalog format change. Do not infer subject completion from ratings.
2. Implement eligibility classification before ranking from those verified records. Keep uncertain routes labelled unverified and separate from immediately eligible results. Add matrix tests for the 24 cases above, including missing-versus-zero and course/major changes.
3. Add only supported career roles after verifying each route, avoiding title-only catalog growth. Do not present the current 25-row catalog as comprehensive coverage of every IT sub-role.
4. Re-run saved-recommendation browser restoration and all-stage API/UI parity in an accessible guarded runtime; perform responsive and keyboard/screen-reader checks.
5. If presenting corrected career-model metrics, train only into a separately approved isolated artifact destination, review metrics before promoting artifacts, and never describe synthetic-label agreement as real-world accuracy.

**Final decision: NOT READY.** The project has useful exploratory pathways and a tested hybrid scoring prototype, but a complete eligibility gate, validated breadth, live browser release checks, and corrected-protocol model results remain unresolved. No admission eligibility, career success, or production readiness claim is supported by the current evidence.
