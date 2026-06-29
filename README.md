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

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Postgres + pgvector, Redis, MLflow)
- **Python 3.11** (recommended; Docker backend uses 3.11-slim)
- Node.js 20+ (for frontend)
- Groq API key → [console.groq.com](https://console.groq.com)

**Windows:** Git Bash or PowerShell both work. You do **not** need `make`, `psql`, or `alembic` on your PATH — use the `scripts/` helpers below. If you have local PostgreSQL installed, note typical ports: **5432** (PG16) and **5433** (PG18). This project’s Docker Postgres uses **5434** to avoid those conflicts.

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

Docker Postgres uses **`pgvector/pgvector:pg18`** on **host port 5434** (avoids local PostgreSQL on 5432 and 5433).

**Full stack (Postgres, Redis, MLflow):**

```bash
bash scripts/up.sh          # Git Bash
```

```powershell
.\scripts\up.ps1            # PowerShell (recommended on Windows)
```

**Postgres only (fresh container + volume):**

```bash
bash scripts/reset-docker-postgres.sh   # Git Bash
```

```cmd
scripts\reset-docker-postgres.cmd       # CMD / Docker Desktop terminal
```

Use the reset script when credentials seem wrong after changing `POSTGRES_*` in `.env` — Postgres only applies those values on **first** volume init.

Ensure `.env` uses port **5434**:

```
DATABASE_URL=postgresql+asyncpg://recruiter:recruiter@localhost:5434/recruiter_ranking
DATABASE_URL_SYNC=postgresql://recruiter:recruiter@localhost:5434/recruiter_ranking
```

**Verify from host (Git Bash):**

```bash
PGPASSWORD=recruiter "/c/Program Files/PostgreSQL/16/bin/psql.exe" \
  -h 127.0.0.1 -p 5434 -U recruiter -d recruiter_ranking -c "SELECT 1;"
```

(Any `psql` client works; adjust the path if yours differs.)

### 4. Run migrations & seed

```bash
bash scripts/check-db.sh    # verify connection first
bash scripts/migrate.sh     # runs .venv python -m alembic upgrade head
python scripts/seed_db.py
```

Activate the venv first if running Python commands manually (`source .venv/Scripts/activate` on Git Bash). **Do not run bare `alembic`** — use `python -m alembic` or `bash scripts/migrate.sh`.

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
bash scripts/backend.sh
```

Or manually: `cd backend && uvicorn app.main:app --reload --port 8000` (with venv active).

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

### `docker-credential-desktop` not found (Git Bash)

Docker Desktop is installed but Git Bash cannot pull images. Our scripts source `scripts/docker-env.sh`, which adds Docker’s bin directory to `PATH`. Use:

```bash
bash scripts/reset-docker-postgres.sh
bash scripts/up.sh
```

Or add `C:\Program Files\Docker\Docker\resources\bin` to your system PATH permanently.

### `password authentication failed for user "recruiter"`

**Most common cause on Windows:** something other than this project’s Docker container is listening on the port in `.env`.

| Port | Typical listener |
|------|------------------|
| 5432 | Local PostgreSQL 16 |
| 5433 | Local PostgreSQL 18 |
| **5434** | **This project’s Docker Postgres** |

Check what is bound to the port:

```powershell
netstat -ano | findstr ":5434"
```

If you see a `postgres` process (not `com.docker.backend`) on 5434, pick another free port: set `DOCKER_PG_HOST_PORT=5435` in your shell, update `.env` and `infra/docker-compose.yml`, then re-run `bash scripts/reset-docker-postgres.sh`.

**Stale Docker volume:** If you changed `POSTGRES_PASSWORD` after the database was first created, reset the volume:

```bash
bash scripts/reset-docker-postgres.sh
bash scripts/migrate.sh
```

**Wrong port in `.env`:** Port **5432** is almost certainly a **local PostgreSQL** install, not this project’s Docker database. The app expects user `recruiter` / password `recruiter` on port **5434** when using Docker.

**Option A — Docker (recommended):** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), then:

```bash
bash scripts/reset-docker-postgres.sh   # or: bash scripts/up.sh
```

Ensure `.env` uses port **5434** (see `.env.example`), then:

```bash
bash scripts/check-db.sh
bash scripts/migrate.sh
```

**Option B — Use local Postgres on 5432 or 5433:** Create the app user/database (requires [pgvector](https://github.com/pgvector/pgvector) installed locally):

```bash
bash scripts/init-local-postgres.sh
# or PowerShell: .\scripts\init-local-postgres.ps1
# or full path if needed:
# "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -f scripts/init-local-postgres.sql
```

Keep `.env` on the port your local instance uses (5432 or 5433) with `recruiter`/`recruiter`.

**If `extension "vector" is not available`:** pgvector is not installed on local Postgres. Easiest fix — open **PowerShell as Administrator**, then:

```powershell
cd "D:\Projects\AI Recruiter Ranking Engine"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-pgvector-windows.ps1
```

(You are already in PowerShell — do **not** prefix with `powershell`. Run from the project directory, not `C:\Windows\System32`.)

Or install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and use `bash scripts/reset-docker-postgres.sh` with `.env` port **5434** (`pgvector/pgvector:pg18` included).

**Option C — Your own credentials:** Set `DATABASE_URL` and `DATABASE_URL_SYNC` in `.env` to match your existing Postgres user, password, and database.

### Docker vs local Postgres quick reference

| Setup | `.env` port | Start command |
|-------|-------------|---------------|
| Docker (default) | 5434 | `bash scripts/up.sh` or `bash scripts/reset-docker-postgres.sh` |
| Local PG16 | 5432 | `bash scripts/init-local-postgres.sh` |
| Local PG18 | 5433 | `bash scripts/init-local-postgres.sh` |

## Project structure

```
backend/     FastAPI online pipeline + API
ml/          Offline ingestion, labeling, training, evaluation
frontend/    Next.js + Tailwind recruiter UI
infra/       Docker Compose (Postgres+pgvector, Redis, MLflow)
scripts/     Setup, DB reset, migrations, data prep, dev servers
data/        Raw datasets and model artifacts (gitignored)
```

## Scripts reference

| Script | Purpose |
|--------|---------|
| `scripts/setup.sh` / `setup.ps1` | Install Python deps into `.venv` |
| `scripts/up.sh` / `up.ps1` | Start Docker Compose (Postgres, Redis, MLflow) |
| `scripts/reset-docker-postgres.sh` / `.cmd` | Recreate Postgres container + volume on port 5434 |
| `scripts/check-db.sh` | Test `DATABASE_URL_SYNC` from `.env` |
| `scripts/migrate.sh` / `migrate.ps1` | Run Alembic migrations |
| `scripts/seed_db.py` | Seed tenant, admin user, sample data |
| `scripts/prepare_data.py` | Download/prepare Kaggle or synthetic datasets |
| `scripts/backend.sh` / `backend.ps1` | Start FastAPI with reload |
| `scripts/init-local-postgres.sh` | Create `recruiter` user/DB on local Postgres |
| `scripts/install-pgvector-windows.ps1` | Install pgvector into local PostgreSQL (Windows) |
| `scripts/diagnose-docker-postgres.cmd` | Compare in-container vs host DB connectivity |
