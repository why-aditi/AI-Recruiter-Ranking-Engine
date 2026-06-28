-- Run as PostgreSQL superuser (e.g. psql -U postgres -f scripts/init-local-postgres.sql)
-- Requires pgvector extension installed on your local PostgreSQL.
-- Prefer Docker: bash scripts/up.sh (uses port 5433 to avoid conflicting with local Postgres)

CREATE USER recruiter WITH PASSWORD 'recruiter';
CREATE DATABASE recruiter_ranking OWNER recruiter;
GRANT ALL PRIVILEGES ON DATABASE recruiter_ranking TO recruiter;

\c recruiter_ranking
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
