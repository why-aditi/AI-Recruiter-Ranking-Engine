# AI Recruiter Ranking Engine

Multi-signal, ML-ranked candidate shortlisting system. **Rank, don't filter.**

## Architecture

```
Stage 1: JD Understanding (Groq LLM, cached)
Stage 3: Vector retrieval (pgvector, top ~200)
Stage 4: Feature engineering (~15 features)
Stage 5: LightGBM LambdaMART ranking
Stage 6: Groq LLM re-rank + explanation (top 20 → top 10)
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- **Python 3.11** (recommended; Docker backend uses 3.11-slim)
- Node.js 20+ (for frontend)
- Groq API key → [console.groq.com](https://console.groq.com)

### 1. Configure

```bash
cp .env.example .env
# Set GROQ_API_KEY in .env
```

### 2. Install Python dependencies

**Windows (Git Bash — no `make` required):**

```bash
bash scripts/setup.sh
```

**Windows (PowerShell):**

```powershell
powershell -File scripts/setup.ps1
```

**Manual install (any OS):**

```bash
python -m venv .venv
source .venv/Scripts/activate   # Git Bash on Windows
pip install --upgrade pip wheel
pip install -r requirements-core.txt
pip install -r requirements-ml.txt
```

> **Python 3.14 on Windows:** The pinned `pandas==2.2.3` has no wheel for 3.14 and will fail to compile. Use `requirements-core.txt` + `requirements-ml.txt` (they auto-select `pandas>=3.0.3`). For fewest issues, use **Python 3.11** (matches Docker).

### 3. Start infrastructure (requires Docker Desktop)

Docker Postgres listens on **host port 5433** (not 5432) so it won't clash with a local PostgreSQL install.

```bash
bash scripts/up.sh          # Git Bash
# or: powershell -File scripts/up.ps1
# or: docker compose -f infra/docker-compose.yml up -d postgres redis mlflow
```

Ensure `.env` uses port **5433**:
```
DATABASE_URL=postgresql+asyncpg://recruiter:recruiter@localhost:5433/recruiter_ranking
DATABASE_URL_SYNC=postgresql://recruiter:recruiter@localhost:5433/recruiter_ranking
```

### 4. Run migrations & seed

```bash
bash scripts/check-db.sh    # verify connection first
bash scripts/migrate.sh     # uses: python -m alembic upgrade head
python scripts/seed_db.py
```

**Do not run bare `alembic`** — use `python -m alembic` from the activated venv, or the scripts above.

### 5. Prepare data

```bash
# Synthetic seed (works offline)
python scripts/prepare_data.py --seed-only

# Or download Kaggle datasets (requires kaggle CLI + credentials)
python scripts/prepare_data.py
```

**Kaggle datasets:**
- Candidates: `hadikp/resume-data-pdf`
- Job descriptions: `adityarajsrv/job-descriptions-2025-tech-and-non-tech-roles`

### 6. Ingest into Postgres

```bash
python -m ml.ingestion --seed-only
```

### 7. Train ranker (optional — heuristic fallback works without training)

```bash
python -m ml.labeling --max-pairs 50
python -m ml.training
python -m ml.evaluation
```

### 8. Start backend

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

### 9. Start frontend

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:3000

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/search` | POST | Rank candidates for a JD |
| `/api/v1/candidates/{id}` | GET | Candidate detail |
| `/api/v1/feedback` | POST | 👍/👎 feedback |
| `/api/v1/jobs` | GET | List ingested JDs |
| `/api/v1/audit` | GET | Audit records (admin) |
| `/api/v1/auth/login` | POST | JWT login |
| `/health` | GET | Health check |

## Default credentials

- Email: `admin@recruiter.local`
- Password: `admin123`

## Data labeling

All **behavioral signals are simulated** and labeled as such in the UI.
Resume data source is indicated per candidate (`synthetic` | `kaggle`).

## Fairness

Protected/proxy attributes (gender, age, ethnicity, photo) are **excluded** from the feature vector by design. See `backend/app/services/fairness.py`.

## Ops

See [docs/runbooks.md](docs/runbooks.md) for LLM outage, model rollback, and latency runbooks.

## Troubleshooting

### `password authentication failed for user "recruiter"`

Port **5432** on your machine is almost certainly a **local PostgreSQL** install, not this project's Docker database. The app expects user `recruiter` / password `recruiter`.

**Option A — Docker (recommended):** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), then:

```bash
bash scripts/up.sh
```

Update `.env` to use port **5433** (see `.env.example`), then:

```bash
bash scripts/check-db.sh
bash scripts/migrate.sh
```

**Option B — Use local Postgres on 5432:** Create the app user/database (requires [pgvector](https://github.com/pgvector/pgvector) installed locally):

```bash
psql -U postgres -f scripts/init-local-postgres.sql
```

Keep `.env` on port 5432 with `recruiter`/`recruiter`.

**Option C — Your own credentials:** Set `DATABASE_URL` and `DATABASE_URL_SYNC` in `.env` to match your existing Postgres user, password, and database.

## Project structure

```
backend/     FastAPI online pipeline + API
ml/          Offline ingestion, labeling, training, evaluation
frontend/    Next.js + Tailwind recruiter UI
infra/       Docker Compose (Postgres+pgvector, Redis, MLflow)
scripts/     Data prep and DB seed
data/        Raw datasets and model artifacts (gitignored)
```
