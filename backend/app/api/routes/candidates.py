from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.models import Candidate
from app.schemas.search import CandidateDetail

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("/{candidate_id}", response_model=CandidateDetail)
async def get_candidate(candidate_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CandidateDetail(
        id=str(c.id),
        name=c.name,
        title=c.title,
        location=c.location,
        profile=c.profile or {},
        data_source=c.data_source,
        career_metadata=c.career_metadata,
        behavioral=c.behavioral,
    )


@router.get("")
async def list_candidates(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = UUID(settings.default_tenant_id)
    result = await db.execute(
        select(Candidate).where(Candidate.tenant_id == tenant_id).limit(limit)
    )
    candidates = result.scalars().all()
    return [
        {"id": str(c.id), "name": c.name, "title": c.title, "data_source": c.data_source}
        for c in candidates
    ]
