# Data dictionary

All scores are 0–100 unless stated. Student identifiers are synthetic UUID-like development IDs or authenticated application IDs.

| Dataset/feature | Type | Range | Meaning | Source |
|---|---|---:|---|---|
| students: student_id | string | — | Profile key | Application / synthetic |
| education_level | category | 10th, 12th, Bachelor's, Master's | Current education stage | User questionnaire |
| age | integer | 13–80 | Age (optional) | User questionnaire / synthetic |
| gender, stream | category | nullable | Optional demographic / study stream | User questionnaire / synthetic |
| subject columns | numeric | 0–100 or NULL | Academic performance by subject | User questionnaire / synthetic |
| aptitude_scores | numeric | 0–100 | Seven aptitude dimensions | Questionnaire / synthetic |
| interest_scores | numeric | 0–100 | Eleven interest dimensions | Questionnaire / synthetic |
| technical_skills | numeric | 0–100 | Skill proficiency; N/A stored as NULL | Questionnaire / synthetic |
| employability_skills | numeric | 0–100 | Ten workplace skill scores | Questionnaire / synthetic |
| career_knowledge_base | text/category/JSON | — | Career requirements and pathways | Curated knowledge base |
| UCI `G1`, `G2`, `G3` | integer | 0–20 | Period grades and final target grade | UCI public dataset |
| UCI context features | mixed | source defined | School, demographics, study/life context | UCI public dataset |

The generated tables have separate CSVs under `data/synthetic/`. For exact fields, see their headers. UCI columns are preserved in the downloaded originals and described in `DATA_SOURCES.md`.

## Exact generated fields

| File | Fields (each score has type `number`, range 0–100, source synthetic generator; blank means not assessed/not applicable) |
|---|---|
| `students.csv` | `student_id` (string key); `education_level` (10th/12th/Bachelor's/Master's); `age` (integer years); `gender` (category); `stream` (Science/Commerce/Arts-Humanities); `physics`, `chemistry`, `biology`, `mathematics`, `computer_science`, `english`, `accountancy`, `business_studies`, `economics`, `history`, `geography`, `political_science`, `sociology` |
| `aptitude_scores.csv` | `student_id`; `logical_reasoning`, `numerical_reasoning`, `verbal_reasoning`, `spatial_reasoning`, `analytical_reasoning`, `problem_solving`, `attention_to_detail` |
| `interest_scores.csv` | `student_id`; `technology`, `research`, `creativity`, `entrepreneurship`, `leadership`, `healthcare`, `business`, `social_service`, `communication`, `design`, `innovation` |
| `technical_skills.csv` | `student_id`; `programming`, `python`, `java`, `javascript`, `sql`, `data_analysis`, `machine_learning`, `web_development`, `cybersecurity`, `cloud_computing`, `accounting`, `finance`, `graphic_design`, `ui_ux`, `electronics`, `hardware`, `research_methods` |
| `employability_skills.csv` | `student_id`; `communication`, `teamwork`, `leadership`, `adaptability`, `time_management`, `problem_solving`, `critical_thinking`, `presentation`, `decision_making`, `professionalism` |

`career_training_profiles.csv` is a separate synthetic-only classifier dataset, not a real student dataset and not the source of the curated requirements table. It has `synthetic_id`, `education_level`, `stream`, stage-specific subject and profile dimensions (scores 0–100, blanks mean nonapplicable), and `career_family` (synthetic target). See the generator for the family-conditioned score distributions. Training feature subsets are stage-specific and exclude `career_family`.

## Career knowledge base fields

`data/career_knowledge_base.csv`: `career_id` (string key); `career_name` and `description` (text); `minimum_education_level` (10th/12th/Bachelor's/Master's stage floor); `suitable_streams`, `required_subjects`, `recommended_degrees`, and `optional_certifications` (semicolon-delimited text); `aptitude_requirements`, `technical_skills`, `employability_skills`, and `interest_requirements` (semicolon-delimited `dimension:minimum_score` pairs). Source: curated CareerPath reference values, with regulator and occupation references listed in `docs/career-references.md`.

## Public-data and runtime fields

UCI's exact original 33 columns and definitions are listed in `DATA_SOURCES.md`; UCI's `G1`, `G2`, and `G3` are 0–20 grades. `G3` is the academic grade-band target. `G1` and `G2` are not included as model inputs. Runtime questionnaire data uses the same profile dimensions above and is sourced from a student's own submitted assessment answers.

## Assessment and education database tables

| Table | Purpose and key relationships |
|---|---|
| `education_programs` | Education level and available stream/degree choices; unique by level and program name. |
| `education_specializations` | Specializations with a foreign key to their degree program. |
| `education_subjects` | Canonical subject key and display name. |
| `education_program_subjects` | Many-to-many subject mapping for streams/degrees. |
| `education_specialization_subjects` | Many-to-many subject mapping for specializations. |
| `aptitude_questions` | Question text/options and server-only answer key, explanation, domain, difficulty, and eligible education levels. |
| `aptitude_attempts` | Student-owned attempt with status and start/completion timestamps and overall score. |
| `aptitude_attempt_questions` | Ordered question membership for each attempt. |
| `aptitude_responses` | Selected option and server-calculated correctness for each attempt question. |
| `aptitude_domain_scores` | Correct/total counts and derived domain score for each attempt. |

`students` also stores degree, specialization, study period, academic performance plus its `percentage`/`cgpa10` scale, research interests, and career/education preferences. CGPA on a 0–10 scale is normalized to a 0–100 compatibility input by multiplying by ten; this normalization is not an institutional grade conversion. `academic_records` stores relevant/custom subject marks; aptitude attempt results remain separately associated with attempt history and are projected into the legacy assessment feature rows for recommendation inputs.
