# REST API

Base URL: `http://localhost:5000/api`; JSON throughout. Errors return `{ "error": "..." }` with a 4xx status. Runtime supports SQLite by default and MySQL via `DATABASE_URL` plus PyMySQL.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/register` | Create account `{email,password}` |
| POST | `/login` | Authenticate; returns bearer token |
| GET | `/auth/me` | Validate the current bearer token and return the authenticated user's email, role, and student ID |
| POST | `/auth/logout` | Revoke the current bearer token |
| POST | `/student/profile` | Save education level, stream, degree, specialization, year/semester, performance, preferences, and relevant/custom subjects |
| GET | `/student/profile?student_id=...` | Load the authenticated student's saved profile and assessments |
| POST | `/assessment/aptitude` | Backward-compatible verification route; accepts only scores that exactly match the latest server-scored attempt |
| POST | `/assessment/interests` | Save interest scores |
| POST | `/assessment/skills` | Save `{technical:{...}, employability:{...}}` |
| GET | `/education/catalog` | Education-specific streams, degrees, specializations, and subjects |
| GET | `/aptitude/questions?education_level=...` | Get questions without answer keys or explanations |
| POST | `/aptitude/attempts` | Start a randomized 25-question attempt for the authenticated student |
| POST | `/aptitude/attempts/<attempt_id>/submit` | Submit every answer; backend calculates and stores results |
| GET | `/aptitude/attempts/<attempt_id>?student_id=...` | Read owned attempt status/results after submission |
| GET | `/aptitude/history?student_id=...` | List the student's saved assessment history |
| POST | `/recommend` | Return ranked recommendations from submitted/current profile; Class 10 always returns all configured pathways in combined-score order, with evidence-sensitive guidance and a roadmap built from the education catalog and maintained career knowledge base |
| GET | `/recommendations` | Latest calculated recommendation list |
| GET | `/career/<career_id>` | Career detail |
| GET | `/skill-gap` | Gaps for latest ranking |
| GET | `/improvement-plan` | Actions generated from latest gaps |

`/register` returns a `student` role and a bearer token. `/login` returns the account role. Send `Authorization: Bearer <token>` for student operations; ownership is checked. Aptitude attempts require an authenticated student. Correct answers and explanations are withheld until submission; the backend requires every question and calculates `correct / total × 100` per domain and overall. This is a project-level exercise, not a professionally validated psychometric test. `/recommend` uses the authenticated student's saved profile and latest completed backend-scored attempt. Anonymous profile aptitude values are ignored. Every returned ranking includes the compatibility score, ML family probability, and combined score. Career family prediction uses the saved model for that education level.

Start an attempt with `{ "student_id": "STU000001", "education_level": "Bachelor's" }`, then submit `{ "student_id": "STU000001", "answers": { "APT001": "B", "APT002": "D" } }` with one answer for every question ID in the attempt. Student identity is checked against the bearer token. Domain and overall scores are ratios of correct answers to scored questions; empty domains are omitted as unavailable. The catalog is stored in normalized `education_programs`, `education_specializations`, `education_subjects`, and mapping tables.

Admin operations require a bearer token for an `admin` account:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/admin/dashboard` | Counts, recommendation/system statistics, and stage model evaluation metrics |
| GET | `/admin/users?q=...` | Search user/student list by email or student ID |
| GET | `/admin/users/<user_id>` | View account and education/profile details |
| PATCH | `/admin/users/<user_id>/role` | Change a user's role to `student` or `admin` |
| PATCH | `/admin/users/<user_id>/status` | Enable or disable an account |
| GET/POST | `/admin/careers` | List career pathways or add one to the knowledge base |
| PATCH/DELETE | `/admin/careers/<career_id>` | Update/deactivate career details and criteria; deactivation is soft and changes ranking eligibility |
| GET | `/admin/skills` | Skills referenced by career requirements |
| GET | `/admin/recommendations` | Recommendation run history |
| GET | `/admin/datasets` | Read-only dataset inventory and validation status from the source registry |
| GET | `/admin/models` | RF/XGBoost metrics, per-class reports, confusion matrices, stage artifacts, and stored majority-class baselines |
| GET/POST | `/admin/aptitude-questions` | List or add questions; admin responses include answer keys |
| PATCH/DELETE | `/admin/aptitude-questions/<question_id>` | Edit or soft-deactivate a question |
| GET | `/admin/errors` | Recent API error metadata; request content and tokens are not logged |
| GET | `/admin/audit` | Recent audited admin changes |

Admin changes to users, careers, and aptitude items are recorded in `admin_audit_logs`. Career pathways and aptitude questions are deactivated instead of physically deleted, preserving references/history. The dataset inventory is read-only; training data is not replaceable from the web UI.

Create the first admin through `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env`; the password must be at least 12 characters. Admin login uses the regular `/login` route. Do not expose or commit `.env`.

For an existing MySQL installation, apply the additive migration `backend/migrations/002_admin_observability.sql` after migration `001`; it adds only the new status/timestamp columns and admin/event tables. Do not run production schema changes against a database backup until the MySQL version and migration target have been confirmed.
