from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.config import settings
from app.db.session import get_db
from app.models import User
from app.schemas.search import SearchRequest, SearchResponse
from app.services.pipeline import run_search_pipeline

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    tenant_id = UUID(user.tenant_id) if user else UUID(settings.default_tenant_id)
    user_id = user.id if user else None
    return await run_search_pipeline(
        session=db,
        tenant_id=tenant_id,
        job_text=body.job_text,
        location_filter=body.location_filter,
        top_k=body.top_k,
        signal_weights=body.signal_weights,
        user_id=user_id,
    )
