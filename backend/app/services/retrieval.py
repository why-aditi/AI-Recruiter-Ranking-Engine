import uuid
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Candidate
from app.schemas.profiles import JobProfile


@dataclass
class RetrievedCandidate:
    candidate: Candidate
    semantic_score: float


async def retrieve_candidates(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    jd_embedding: list[float],
    job_profile: JobProfile,
    location_filter: str | None = None,
    top_k: int | None = None,
) -> list[RetrievedCandidate]:
    top_k = top_k or settings.retrieval_top_k
    embedding_str = "[" + ",".join(str(x) for x in jd_embedding) + "]"

    # Build optional location filter
    location_clause = ""
    params: dict = {"tenant_id": str(tenant_id), "top_k": top_k}
    if location_filter:
        location_clause = "AND location ILIKE :location"
        params["location"] = f"%{location_filter}%"
    elif job_profile.location:
        location_clause = "AND (location ILIKE :location OR location IS NULL)"
        params["location"] = f"%{job_profile.location}%"

    query = text(f"""
        SELECT id, external_id, name, title, location, category, raw_text, profile,
               skills, years_experience, seniority_level, career_metadata, behavioral,
               data_source, tenant_id, created_at,
               1 - (embedding <=> :embedding::vector) AS semantic_score
        FROM candidates
        WHERE tenant_id = :tenant_id::uuid
          AND embedding IS NOT NULL
          {location_clause}
        ORDER BY embedding <=> :embedding::vector
        LIMIT :top_k
    """)
    params["embedding"] = embedding_str

    result = await session.execute(query, params)
    rows = result.fetchall()

    retrieved = []
    for row in rows:
        candidate = Candidate(
            id=row.id,
            external_id=row.external_id,
            name=row.name,
            title=row.title,
            location=row.location,
            category=row.category,
            raw_text=row.raw_text,
            profile=row.profile,
            skills=row.skills,
            years_experience=row.years_experience,
            seniority_level=row.seniority_level,
            career_metadata=row.career_metadata,
            behavioral=row.behavioral,
            data_source=row.data_source,
            tenant_id=row.tenant_id,
            created_at=row.created_at,
        )
        retrieved.append(RetrievedCandidate(candidate=candidate, semantic_score=float(row.semantic_score)))

    # Fallback if no embeddings yet
    if not retrieved:
        stmt = select(Candidate).where(Candidate.tenant_id == tenant_id).limit(top_k)
        result = await session.execute(stmt)
        for c in result.scalars().all():
            retrieved.append(RetrievedCandidate(candidate=c, semantic_score=0.0))

    return retrieved
