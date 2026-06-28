from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, get_current_user, hash_password, verify_password
from app.config import settings
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user.id), str(user.tenant_id), user.role.value)
    return Token(access_token=token)


@router.post("/register", response_model=UserOut)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    tenant_id = UUID(body.tenant_id) if body.tenant_id else UUID(settings.default_tenant_id)
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
        tenant_id=tenant_id,
    )
    db.add(user)
    await db.flush()
    return UserOut(id=str(user.id), email=user.email, role=user.role, tenant_id=str(user.tenant_id))


@router.get("/me", response_model=UserOut)
async def me(user: User | None = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserOut(id=str(user.id), email=user.email, role=user.role, tenant_id=str(user.tenant_id))
