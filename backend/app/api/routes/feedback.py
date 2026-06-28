from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.config import settings
from app.db.session import get_db
from app.models import Feedback, User
from app.schemas.search import FeedbackRequest

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("")
async def submit_feedback(
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    tenant_id = user.tenant_id if user else UUID(settings.default_tenant_id)
    fb = Feedback(
        tenant_id=tenant_id,
        user_id=user.id if user else None,
        candidate_id=UUID(body.candidate_id),
        job_id=UUID(body.job_id) if body.job_id else None,
        is_positive=body.is_positive,
        search_id=body.search_id,
    )
    db.add(fb)
    await db.flush()
    return {"status": "ok", "id": str(fb.id)}
