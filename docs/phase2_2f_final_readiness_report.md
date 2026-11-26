# Phase 2.2F — Student Workflow and Readiness Report

Date: 2026-11-14

## Result

**NOT READY for release sign-off.** The isolated student workflows, test suites, and separate-directory production build have supporting evidence. The live browser console/network audit, full comparison accordion inspection, and runtime responsive/keyboard checks remain unverified because browser automation stopped when it could not confidently establish the current browser URL.

## Roadmap defect and change

The Class 10 roadmap built Stage 3 course options by collecting every undergraduate degree name from career records whose *career* `suitable_streams` included the selected route. The catalog does not associate individual degrees with Class 11–12 subject prerequisites. As a result, a Science roadmap could list a mixed set of Science, Commerce, and Arts course names as if they were Science-pathway options.

Stage 3 now leaves the course list empty and explains that the maintained records do not establish course eligibility for the selected pathway. It directs students to the catalog-backed, pathway-filtered career directions in Stage 4 and to verify specific course requirements with institutions. Stage 4 career directions remain sourced from career records matching the selected route. No canonical data was changed.

Regression coverage checks that Stage 3 does not label unverified degrees as pathway-eligible for Science, Commerce, Arts/Humanities, or Diploma/Vocational, while preserving the four-stage roadmap and the existing pathway-filtered career lists.

## Recommendation evidence across education levels

Live UI results were observed in the authenticated synthetic student session in the approved isolated SQLite runtime:

| Education level | Observed result |
|---|---|
| Class 10 | Science shown as a provisional option at 92 exploratory fit; Commerce 67 and Diploma/Vocational 66 also appeared. The UI described the estimate as exploratory and not a success/admission probability. |
| Class 12 (Commerce) | Data Analyst 87, Software Developer 87, Web Developer 87, Lawyer 85, and Public Administration Officer 85. |
| Bachelor's (BCA) | Cybersecurity Analyst 94, Data Analyst 94, Software Developer 94, Web Developer 94, Civil Engineer 76. |
| Master's (MCA) | AI Engineer 83, Software Developer 83, Web Developer 83, Civil Engineer 75, Cybersecurity Analyst 75. |

The observed cards separated 90% profile compatibility from the 10% experimental synthetic-data model-family signal, and showed related-pathway or further-education notes where applicable. These outcomes verify requests for the tested synthetic profile, not recommendation quality for real students. The backend suite also passed its all-four-stage recommendation-profile test.

### Compare all pathways

The current React implementation renders the full comparison by mapping the complete recommendation `results` array inside the “Compare all pathways” disclosure. Backend regression coverage confirms Class 10 recommendations return all four pathways in score order even when the requested top-N is small. The live accordion was visible in the observed page but remained collapsed; I could not open and inspect each rendered pathway card in the browser after the browser tool stopped. Therefore, full rendered accordion content is **PARTIALLY VERIFIED** (source and ranking test passed; live expansion not verified).

## Qualification-source review

The maintained career catalog does not provide institution-specific undergraduate admissions requirements for each listed degree. The official UGC 2025 regulations state that Class 12 or equivalent supports undergraduate eligibility and describe cross-discipline undergraduate eligibility when the student qualifies in a relevant national or university entrance examination; institutions may require bridge courses. This does not settle each institution's criteria. The official NTA engineering exam page lists Physics and Mathematics as compulsory subjects, plus one of Chemistry/Biotechnology/Biology/Technical Vocational, for specified B.E./B.Tech admissions to NITs, IIITs, and participating CFTIs. That rule is specific to those admissions and is not a universal requirement for every engineering institution. ([UGC regulations, 2025](https://www.ugc.gov.in/pdfnews/5576784_UG-and-PG-Regulations-2025.pdf), [NTA Engineering Exam](https://www.nta.ac.in/Engineeringexam))

Accordingly, this project does not claim that a student is eligible for a particular degree. A reliable per-course eligibility catalog would need institution/program-level sources and a maintenance process; none was invented for this fix.

## Responsive and accessibility review

Static source inspection found responsive CSS breakpoints at 700px and 560px, explicit accessible names on score and subject controls, `aria-live` score labels, semantic labels, native `<details>/<summary>` comparison disclosure, and visible `:focus-visible` styles for pathway links and the comparison control. These are code-level indicators only. Mobile viewport behavior, keyboard tab/activation flow, and screen-reader interaction were **NOT VERIFIED** in a running browser.

## Browser console and network audit

**NOT VERIFIED.** The browser automation tool stopped after a request because it could not determine the current browser URL with enough confidence to continue under its safety policy. No console export, Network-tab review, or comprehensive 4xx/5xx audit was captured in this run. API integration coverage in automated tests is not a substitute for the requested browser console/network audit.

## Automated verification

- Focused backend recommendation tests: `python -m unittest discover -s tests -p 'test_recommendation_engine.py' -v` — **15 passed**.
- Full backend suite: `python -m unittest discover -s tests -p 'test_*.py' -v` — **92 passed**, using a fresh temporary directory under the workspace for `TEMP`, `TMP`, and `TMPDIR`, and an explicit isolated SQLite test target. MySQL integration was not run.
- Frontend suite: `npm.cmd test` — **30 passed, 0 failed**.
- Production build: `npm.cmd run build -- --outDir C:\Users\THANAY\Documents\Codex\.phase2f_final_build_20261114` — **PASS**, Vite 5.4.21; 36 modules transformed; output included `index.html` and `assets/`. The output directory is outside `frontend/dist`.
- The initial sandbox build failed with Vite `EPERM` resolving `frontend/src/main.jsx`; the successful build ran with approved filesystem access and did not change application source to bypass the error.
- An initial full-suite attempt using the sandbox AppContainer temp root failed due temp-directory access restrictions. The complete rerun with a workspace-local temp root passed.

## Isolation and data preservation

- Backend tests used a fresh temporary SQLite target and test-owned temporary fixtures. MySQL integration was not enabled.
- The approved Phase 2.2F student runtime was used for the observed UI workflows. No setup, migration, seed, or Admin publishing command was run during this verification.
- Canonical career catalog files, metadata, active release pointer, model artifacts, and live MySQL were not modified or accessed in this run.
- Existing user changes in the working tree were preserved.

## Files changed in this work

- `backend/services/school_roadmap.py` — stopped deriving pathway-eligible course lists from career-level stream labels that lack degree prerequisites.
- `frontend/src/main.jsx` — changed the Stage 3 empty state to explain the missing course-to-prerequisite mapping.
- `tests/test_recommendation_engine.py` — added/updated roadmap regression assertions for all four Class 10 pathways.
- `docs/phase2_2f_final_readiness_report.md` — this report.

Other modified files were already present in the working tree before this task and were not changed as part of this report.

## Remaining gates

1. Re-open or re-establish the local browser page so an approved browser tool can verify the expanded full-pathway comparison, console, and Network tab.
2. Verify mobile layouts and keyboard/screen-reader behavior at actual viewport sizes.
3. Add verified institution/program-level prerequisite references before presenting any degree as eligible for a particular Class 12 stream.
4. Keep MySQL integration, Admin publishing, and production deployment readiness separate; none is established by this report.
