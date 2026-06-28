.PHONY: up down migrate seed ingest train eval test

up:
	docker compose -f infra/docker-compose.yml up -d postgres redis mlflow

down:
	docker compose -f infra/docker-compose.yml down

migrate:
	cd backend && alembic upgrade head

seed:
	python scripts/prepare_data.py --seed-only
	python -m ml.ingestion --seed-only

ingest:
	python scripts/prepare_data.py
	python -m ml.ingestion

train:
	python -m ml.labeling
	python -m ml.training

eval:
	python -m ml.evaluation

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest tests/ -v
