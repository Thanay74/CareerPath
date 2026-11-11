# Setup guide

## Requirements

- Python 3.10 or later
- Node.js 18 or later and npm/pnpm
- MySQL 8 for persistent deployment (SQLite is supported for local development and automated tests)

## Install and train

Run from the project root:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
pip install -r backend/requirements.txt
python data/generate_synthetic_data.py
python data/generate_career_training_data.py
python -m backend.ml.train_career_models
python -m backend.ml.diagnose_career_models
```

The last two commands create the training fixture and stage-specific model pipelines. Synthetic model records are explicitly labeled and do not overwrite `data/raw/`. To rerun the separate public UCI grade-band experiment, use `python -m backend.ml.train_model` after the UCI source files are available.

### Optional Kaggle benchmark

Install `backend/requirements.txt`, configure Kaggle CLI credentials in your user profile (outside this repository), then run from the project root:

```powershell
kaggle datasets download -d mobeenfatimah/student-career-success-prediction-dataset -p data/raw/kaggle_student_career_success
python -m backend.ml.preprocess_kaggle_career
python -m backend.ml.train_kaggle_career_model
```

The Kaggle data card identifies these records as synthetic and licenses them CC BY-SA 4.0. The benchmark predicts one of its 16 placed university career-field labels. It is separate from the production recommender because the dataset does not represent all four CareerPath education stages or the student assessment feature contract. See [MODEL_REPORT.md](MODEL_REPORT.md) for limitations and measured results.

## MySQL setup

1. Review and run `backend/schema.sql` in MySQL as an administrator. It creates the database and relational tables.
   For an existing CareerPath database, run `backend/migrations/001_education_and_aptitude.sql` and then `backend/migrations/002_admin_observability.sql`; both migrations add schema elements and preserve existing student and recommendation rows.
2. Create a dedicated account with a unique password in your MySQL administration console: `CREATE USER 'careerpath_app'@'127.0.0.1' IDENTIFIED BY '<unique-password>'; GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX ON careerpath.* TO 'careerpath_app'@'127.0.0.1';`. Adapt the host for your deployment.
3. Copy `.env.example` to `.env` and configure a URL for that dedicated account, for example `DATABASE_URL=mysql+pymysql://careerpath_app:YOUR_PASSWORD@127.0.0.1:3306/careerpath`.
4. Set a valid `ADMIN_EMAIL` and a unique `ADMIN_PASSWORD` of at least 12 characters. Create the first admin only through the explicit, target-confirmed setup workflow; normal API startup does not bootstrap an admin. Do not commit `.env` or use MySQL root for application access.
5. If `DATABASE_URL` is absent, the app uses local SQLite at `CAREERPATH_DB` (defaults to `careerpath.sqlite3`).

Persistent student/profile/assessment/recommendation records are stored in relational tables with foreign keys. Assessment dimensions are rows with a composite student/type/feature key; academic marks are rows keyed by student and subject; aptitude questions, ordered attempts, responses, and domain scores are linked by foreign keys. Runtime model files are read from the local project and are not stored in MySQL.

## Career catalog modes

For local development, if both `data/career_active.json` and `data/career_catalog_managed.json` are absent, CareerPath reads and validates the canonical `data/career_knowledge_base.csv` and `data/career_metadata.json` pair. This is canonical-bootstrap mode. A present active pointer must be valid and select a complete validated release. If the managed marker is present while the pointer is missing, or a present pointer/marker is malformed, the reader fails closed rather than falling back. Never create or delete these files manually.

Admin career edits are staged. Publishing is a separate, controlled catalog transition to an immutable versioned release; the first publish retains the canonical pair as a rollback release. Review the proposed changes and validation results before publishing.

Canonical-bootstrap mode for local development does not approve production use. Production must have an explicitly approved catalog mode, validated artifacts, persistent/shared release storage where required, controlled activation, and a tested rollback/recovery procedure. Do not call production ready until the deployment's catalog state and recovery process have been verified.

## Run the application

Terminal 1:

```powershell
python -m backend.app
```

Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Open Vite's local URL. It calls the Flask API at `http://localhost:5000/api` unless `VITE_API_URL` is set. Students can create accounts and save profiles. Admins use the regular login form with the configured bootstrap credentials.

## Tests

```powershell
python -m unittest discover -s tests -v
cd frontend
npm run build
```

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md), [DATA_SOURCES.md](DATA_SOURCES.md), [MODEL_REPORT.md](MODEL_REPORT.md), and [ARCHITECTURE.md](ARCHITECTURE.md) for endpoint, provenance, evaluation, and design details.
