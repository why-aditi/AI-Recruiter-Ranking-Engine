from pydantic import BaseModel, EmailStr

from app.models import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.recruiter
    tenant_id: str | None = None


class UserOut(BaseModel):
    id: str
    email: str
    role: UserRole
    tenant_id: str

    model_config = {"from_attributes": True}
