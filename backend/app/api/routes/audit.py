from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user, require_role
from app.config import settings
from app.db.session import get_db
from app.models import AuditRecord, Job, User, UserRole

router = APIRouter(tags=["audit", "jobs"])


@router.get("/audit")
async def list_audit_records(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.admin, UserRole.ml)),
):
    result = await db.execute(
        select(AuditRecord).where(AuditRecord.tenant_id == user.tenant_id).order_by(AuditRecord.created_at.desc()).limit(limit)
    )
    records = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "search_id": r.search_id,
            "model_version": r.model_version,
            "latency_ms": r.latency_ms,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.get("/jobs")
async def list_jobs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    tenant_id = UUID(settings.default_tenant_id)
    result = await db.execute(
        select(Job).where(Job.tenant_id == tenant_id).limit(limit)
    )
    jobs = result.scalars().all()
    return [
        {
            "id": str(j.id),
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "category": j.category,
            "raw_text": j.raw_text[:500] + "..." if len(j.raw_text) > 500 else j.raw_text,
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}")
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": str(job.id),
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "category": job.category,
        "raw_text": job.raw_text,
        "job_profile": job.job_profile,
    }
