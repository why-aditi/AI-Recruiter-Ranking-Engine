"""Seed default tenant user for development."""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine, text
from app.auth.jwt import hash_password
from app.config import settings

DEFAULT_TENANT = settings.default_tenant_id


def seed():
    engine = create_engine(settings.database_url_sync)
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO tenants (id, name, slug)
            VALUES (:id::uuid, 'Default Tenant', 'default')
            ON CONFLICT DO NOTHING
        """), {"id": DEFAULT_TENANT})

        existing = conn.execute(
            text("SELECT id FROM users WHERE email = 'admin@recruiter.local'")
        ).fetchone()
        if not existing:
            conn.execute(
                text("""
                    INSERT INTO users (id, tenant_id, email, hashed_password, role)
                    VALUES (:id::uuid, :tenant_id::uuid, :email, :password, 'admin')
                """),
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": DEFAULT_TENANT,
                    "email": "admin@recruiter.local",
                    "password": hash_password("admin123"),
                },
            )
            print("Created admin@recruiter.local / admin123")
        conn.commit()
    print("Seed complete")


if __name__ == "__main__":
    seed()
