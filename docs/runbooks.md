# Runbooks — AI Recruiter Ranking Engine

## LLM Provider Outage

**Symptoms:** Stage 6 errors, `degraded: true` in search response, elevated latency on Stage 1.

**Action:**
1. System auto-degrades to Stage-5 LightGBM ranking (no LLM re-rank).
2. Check Groq status: https://status.groq.com
3. Verify `GROQ_API_KEY` in `.env`.
4. Gateway retries 3x with exponential backoff; falls back to `llama-3.1-8b-instant`.
5. JD parse cache (Redis) serves repeated searches without LLM calls.

## Vector Store Latency

**Symptoms:** Stage 3 retrieval > 500ms.

**Action:**
1. Check pgvector index: `CREATE INDEX ON candidates USING ivfflat (embedding vector_cosine_ops);`
2. Verify candidate count and connection pool settings.
3. Scale Postgres read replicas if needed.

## Model Rollback

**Symptoms:** NDCG@10 regression, recruiter feedback disagreement spike.

**Action:**
1. Check MLflow registry for previous champion run.
2. Copy previous artifact: `cp data/models/ranker.challenger.txt data/models/ranker.txt`
3. Restart backend to reload model.
4. Review `audit_records` for affected searches.

## Rate Limiting (Groq 429)

**Action:**
1. Respect `Retry-After` header (handled by tenacity retry).
2. Enable JD hash caching (default on).
3. Reduce concurrent search load.
