"""Initial schema with pgvector and RLS scaffolding

Revision ID: 001
Revises:
Create Date: 2026-06-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    user_role = postgresql.ENUM("recruiter", "hiring_manager", "admin", "ml", name="userrole")
    user_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("company", sa.String(255)),
        sa.Column("location", sa.String(255)),
        sa.Column("category", sa.String(100)),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("job_profile", postgresql.JSONB()),
        sa.Column("jd_hash", sa.String(64), index=True),
        sa.Column("embedding", Vector(384)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("external_id", sa.String(255), index=True),
        sa.Column("name", sa.String(255)),
        sa.Column("title", sa.String(255)),
        sa.Column("location", sa.String(255)),
        sa.Column("category", sa.String(100)),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("profile", postgresql.JSONB(), nullable=False),
        sa.Column("embedding", Vector(384)),
        sa.Column("skills", postgresql.JSONB()),
        sa.Column("years_experience", sa.Float()),
        sa.Column("seniority_level", sa.String(50)),
        sa.Column("career_metadata", postgresql.JSONB()),
        sa.Column("behavioral", postgresql.JSONB()),
        sa.Column("data_source", sa.String(50), server_default="synthetic"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id")),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("is_positive", sa.Boolean(), nullable=False),
        sa.Column("search_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("search_id", sa.String(64), nullable=False, index=True),
        sa.Column("job_text_hash", sa.String(64), nullable=False),
        sa.Column("job_profile", postgresql.JSONB(), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("input_summary", postgresql.JSONB(), nullable=False),
        sa.Column("results", postgresql.JSONB(), nullable=False),
        sa.Column("latency_ms", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("mlflow_run_id", sa.String(100)),
        sa.Column("ndcg_at_10", sa.Float()),
        sa.Column("is_champion", sa.Boolean(), server_default="false"),
        sa.Column("artifact_path", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # RLS scaffolding
    for table in ("users", "jobs", "candidates", "feedback", "audit_records"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                tenant_id = COALESCE(
                    NULLIF(current_setting('app.current_tenant_id', true), '')::uuid,
                    tenant_id
                )
            )
        """)

    op.execute("""
        INSERT INTO tenants (id, name, slug)
        VALUES ('00000000-0000-0000-0000-000000000001', 'Default Tenant', 'default')
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    for table in ("audit_records", "feedback", "candidates", "jobs", "users"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_table("model_versions")
    op.drop_table("audit_records")
    op.drop_table("feedback")
    op.drop_table("candidates")
    op.drop_table("jobs")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.drop_table("tenants")
