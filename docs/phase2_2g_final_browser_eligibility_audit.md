# CareerPath Phase 2.2G — Final Browser Verification and Eligibility Audit

Date: 2026-11-14  
Environment: Brave on Windows; local React/Vite at `http://127.0.0.1:5173`; isolated student runtime previously approved for `careerpath_phase22f_student_1tftni0k` (SQLite only). No MySQL or deployment access was used.

## Summary

**NOT READY for release sign-off.** The live Class 10 Compare All disclosure and its keyboard toggle were inspected. Its four pathway cards clearly distinguish unavailable profile compatibility from experimental model-family signals. However, the rendered Stage 3 roadmap contradicts the inspected current backend source: the page shows 13 general degree names under Arts/Humanities while the current `build_pathway_roadmap()` returns an empty `program_options` list. This is a confirmed runtime/source mismatch and means the Science course-filtering correction is **not verified in the running application**. Console/network coverage, all-four-level live reruns, full responsive checks, and comprehensive eligibility verification remain incomplete.

No application source, catalog, release pointer, model artifact, or database schema was changed for this audit. The authorized browser journey used the isolated synthetic student account already created for this phase. No MySQL connection or deployment action occurred.

## Checks and evidence

| Check | Status | Evidence and limitations |
|---|---|---|
| Browser URL established before interaction | **PASS** | Brave address bar showed `http://127.0.0.1:5173/#results` before the new Class 10 recommendation request. After submitting, the address remained on the assessment hash route and the results region rendered. |
| Compare All disclosure expands and collapses | **PASS** | Visually expanded “Compare all pathways”; collapsed and reopened it by clicking the native disclosure, then collapsed/reopened with the focused summary’s Space key. The focus outline remained visible. |
| All four Class 10 pathways appear in the rendered disclosure | **PASS** | Expanded page showed Arts/Humanities, Commerce, Diploma/Vocational, and Science in four separate numbered cards. No duplicate or missing pathway name was observed. |
| Scores and explanations in the rendered disclosure | **PASS, with caveat** | For this synthetic account with all profile ratings unassessed, each card showed profile compatibility `—` at 90% weight and a separately labeled grouped experimental ML signal at 10%: Arts 19.2/100 (displayed 19%), Commerce 31.7/100 (32%), Diploma/Vocational 17.1/100 (17%), Science 14.7/100 (15%). Cards said “More information needed,” listed the missing subject and aptitude evidence as factors to consider, and described the synthetic label limitation. No fit score was presented as probability of admission or success. |
| Compare All matches the actual backend response | **NOT VERIFIED** | The browser Network response body for `POST /api/recommend` was not captured, so UI-to-response equality cannot be proven. The visible result is internally consistent with the page’s inconclusive-profile explanation, but this is not a response parity check. |
| Science roadmap course filtering in the live application | **FAIL** | The inspected current code in `backend/services/school_roadmap.py::build_pathway_roadmap()` sets Stage 3 `program_options` to `[]` (lines 69–70, 88), and `frontend/src/main.jsx::PathwayRoadmap()` renders a no-course mapping explanation when that list is empty. The actual rendered Arts/Humanities Stage 3 instead displayed 13 names: BA Communications, BA Design, BA English/Media, BA Journalism, BBA, BBA Marketing, BCA, BCom, BDes, BSc, BSc Computer Science, BSc Design, and Bachelor degree. This is unrelated to the selected Arts/Humanities stream as a verified eligibility list. The current source and the active runtime disagree. A stale Flask process is a plausible explanation, but was not established; the response body/process import state was not captured. Do not treat the earlier code fix as live-verified. |
| Duplicate/missing/unrelated courses in the Stage 3 list | **FAIL** | The visible Arts/Humanities list contained broad records, including BCom and BSc/Computer Science, without course-specific subject eligibility. Each line did carry a provider-verification caveat, but the list’s placement still implies it is a selected pathway’s course set. No exact duplicate name was visible. |
| Desktop layout | **PASS (visual spot check)** | At the maximized Brave viewport (1536×816 screenshot), the main content and result cards displayed in a readable multi-column layout; no horizontal clipping was seen in the inspected results/disclosure area. This is a spot check, not a full-page visual audit. |
| Tablet layout | **FAIL (prior observed viewport)** | The prior live browser observation at approximately 769 px showed crowded navigation, a wrapped “Build my path” button, and clipped account identity. That viewport issue remains unresolved. |
| Mobile layout | **NOT TESTED** | No reliable mobile-width browser emulation was completed in this run. |
| Keyboard interaction and focus | **PARTIAL PASS** | The disclosure was toggled by keyboard Space and displayed a visible focus outline. Full tab-order traversal across navigation, forms, aptitude, cards, and account controls was not completed. |
| Semantic/accessibility tree | **PARTIAL PASS** | The live accessibility tree exposed headings, named education/subject controls, the recommendation region, and native details/summary disclosure. No screen reader was run; screen-reader behavior is **NOT TESTED**. |
| Browser console errors/warnings | **NOT TESTED** | DevTools Console output was not captured for the complete student journey. Therefore no claim of a clean console is made. |
| Network failures/statuses/duplicates | **PARTIAL / NOT VERIFIED** | An earlier page-load observation in this verification session recorded `GET /api/education/catalog` as HTTP 200 and Vite asset/module requests as successful (304/200); Vite’s websocket connected (101). Recommendation results rendered after submission, but the recommendation request’s status/body, failed-request list, duplicate requests, authentication request history, and all 4xx/5xx results were not captured. Missing-asset and runtime-error absence is not established. |
| Live recommendations across all four education levels | **PARTIAL PASS** | The current browser run re-requested Class 10 recommendations only. Existing Phase 2.2F report records prior live synthetic-profile observations for Class 12 Commerce, Bachelor’s BCA, and Master’s MCA; those are historical evidence and were not rerun for this audit. Full four-level current-runtime consistency is **NOT VERIFIED**. |
| Profile compatibility vs. experimental model signal | **PASS for rendered Class 10 case** | The UI separately labeled profile compatibility (90%) and the grouped experimental ML family signal (10%; synthetic labels). With an unassessed profile it showed compatibility as unavailable rather than substituting the ML value. Model explanation text says it describes grouped family prediction and does not independently explain a specific pathway or prove eligibility/success. |
| Automated backend regression suite | **PASS** | `python -m unittest discover -s tests -p 'test_*.py' -v` — 92 passed, 0 failures. Test setup used isolated SQLite/temp fixtures; MySQL integration was not run. |
| Automated frontend suite | **PASS** | `npm.cmd test` — 30 passed, 0 failures. |
| Separate-output production build | **PASS** | `npm.cmd run build -- --outDir C:\Users\THANAY\Documents\Codex\.phase2_2g_build_95260b9c547e495c9eef646506e40efc` — Vite 5.4.21, 36 modules transformed, 1.10 s. Output was outside `frontend/dist`. The sandboxed build attempt failed with Vite `EPERM`; the successful run used approved filesystem access. This does not verify browser behavior or deployment. |

## Institution-specific eligibility audit

The displayed catalog supplies generic degree names, not institution/program identifiers. The following official examples were checked to establish the boundary between national/entrance routes and university-specific rules; they do **not** validate every CareerPath course entry.

- **University-specific commerce example:** The University of Delhi’s 2026 UG FAQ says its B.Com. (Hons.) CUET combinations include one language plus Mathematics and two List B subjects, **or** one language plus Accountancy and two List B subjects. This is a University of Delhi program-specific condition, not a universal B.Com. requirement. [University of Delhi UG 2026 FAQ](https://admission.uod.ac.in/userfiles/downloads/2026/17052026_Updated_FAQsUG%202026-final.pdf)
- **NTA/JEE Main and NIT+/participating CFTI example:** NTA’s Engineering Exam page lists Physics and Mathematics as compulsory for B.E./B.Tech. qualifying exams along with one of Chemistry/Biotechnology/Biology/Technical Vocational. Its page describes the 75% or board top-20-percentile condition for NIT/IIIT/CFTI admissions (65% for SC/ST). It also says states and other institutions may use separate criteria; this is not a universal engineering-degree rule. [NTA Engineering Exam](https://www.nta.ac.in/Engineeringexam)
- **IIT/JEE Advanced example:** The official JEE Advanced 2027 criteria require Physics, Chemistry, and Mathematics in Class XII for the stated examination route and include additional attempt, JEE Main rank, age, and prior-admission conditions. These requirements apply to the IIT/JEE Advanced route, not every engineering program. [JEE Advanced 2027 eligibility](https://jeeadv.ac.in/eligibility.html)
- **Allocation-specific restrictions:** JoSAA publishes 2026 Business Rules and institution/program restrictions for NIT+ admissions, confirming that national counseling rules coexist with institute/program-specific conditions. [JoSAA Business Rules 2026](https://josaa.nic.in/information-bulletin/), [JoSAA institute/program restrictions (2026)](https://josaa.nic.in/restrictions-at-institutes-academic-programs-level/)

**Eligibility result: BLOCKED for comprehensive course verification.** The current roadmap does not consistently bind a displayed degree to a specific institution, current admission cycle, and subject/prerequisite record. Only the examples above have official evidence. Other course requirements, diploma recognition/progression, Arts/Commerce/Science program eligibility, and local board/school options remain unverified. Do not generalize the NTA/JEE or IIT rules to all universities or degrees. No canonical catalog was edited.

## Recommendation consistency across education stages

- **Class 10 — PARTIAL:** current live page returned an inconclusive comparison and correctly presented four pathway options with missing assessed data. Its roadmap course list contradicts the inspected current source, so end-to-end roadmap consistency fails for this runtime.
- **Class 12 — NOT RERUN:** the Phase 2.2F report records prior Commerce profile results; no current-run Class 12 submission was performed.
- **Bachelor’s — NOT RERUN:** prior BCA results are recorded in the Phase 2.2F report; not revalidated in this current browser run.
- **Master’s — NOT RERUN:** prior MCA results are recorded in the Phase 2.2F report; not revalidated in this current browser run.
- **Automated logic — PASS:** the 92-test backend suite includes the existing roadmap/recommendation tests, including the all-four education-stage profile contract. Automated tests do not prove the running Flask process has loaded the inspected code.

## Isolation and change accounting

- Browser testing used the local isolated student app and synthetic account shown in the page. The local runtime’s profile data may have been read/used by its normal authenticated workflow; no new profile save, aptitude submission, or Admin action was performed for this audit.
- No MySQL connection, migration, seed, production database operation, catalog publication/restore, or deployment was performed.
- No canonical catalog, metadata, active pointer, release, or model artifact was changed.
- The existing working-tree changes listed in the Phase 2.2F report were preserved.
- **File changed for this phase:** `docs/phase2_2g_final_browser_eligibility_audit.md` only. No application source or test file was changed in Phase 2.2G.

## Required follow-up before readiness

1. Re-establish the isolated Flask service from the current checkout, then make a fresh Class 10 recommendation request and capture the `POST /api/recommend` response. Confirm Stage 3 `program_options` is empty and the browser shows the current no-course-mapping explanation. The current source already expresses this behavior; diagnose the runtime/source mismatch before changing code.
2. Rerun Class 10, Class 12, Bachelor’s, and Master’s recommendation flows in the same isolated runtime and compare each rendered response to its API response.
3. Capture Console and Network logs through the complete login/profile/assessment/recommendation/logout flow, including status codes and duplicate/failed requests.
4. Repeat responsive checks at desktop, tablet, and phone widths; address the observed tablet header wrap/clipping. Complete keyboard tab-order review and a screen-reader pass with a suitable assistive technology.
5. Build a maintained, institution-and-program-specific eligibility mapping from current official admission sources before presenting any course as eligible for a stream. Keep all unverified requirements explicitly marked.
6. Re-run backend/frontend tests and separate-directory production build after any corrective changes. Production deployment and MySQL integration remain separate, unverified gates.

**Final readiness decision: NOT READY.** The live comparison disclosure works and displays all four pathways, but the runtime/course mismatch and outstanding browser, accessibility, all-stage rerun, and eligibility evidence prevent release sign-off.
