import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.config import settings
from app.db.base import Base


class UserRole(str, enum.Enum):
    recruiter = "recruiter"
    hiring_manager = "hiring_manager"
    admin = "admin"
    ml = "ml"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="tenant")
    jobs: Mapped[list["Job"]] = relationship(back_populates="tenant")
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.recruiter)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="users")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(100))  # tech / non-tech
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    job_profile: Mapped[dict | None] = mapped_column(JSONB)
    jd_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    embedding = mapped_column(Vector(settings.embedding_dim), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="jobs")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(100))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    embedding = mapped_column(Vector(settings.embedding_dim), nullable=True)
    # Precomputed feature columns for fast serving
    skills: Mapped[list | None] = mapped_column(JSONB)
    years_experience: Mapped[float | None] = mapped_column(Float)
    seniority_level: Mapped[str | None] = mapped_column(String(50))
    career_metadata: Mapped[dict | None] = mapped_column(JSONB)
    behavioral: Mapped[dict | None] = mapped_column(JSONB)
    data_source: Mapped[str] = mapped_column(String(50), default="synthetic")  # synthetic | kaggle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="candidates")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id"))
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    is_positive: Mapped[bool] = mapped_column(Boolean, nullable=False)
    search_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    search_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    job_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    job_profile: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    input_summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    results: Mapped[list] = mapped_column(JSONB, nullable=False)
    latency_ms: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(100))
    ndcg_at_10: Mapped[float | None] = mapped_column(Float)
    is_champion: Mapped[bool] = mapped_column(Boolean, default=False)
    artifact_path: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
