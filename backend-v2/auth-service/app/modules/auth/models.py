from dataclasses import dataclass
from datetime import datetime
import uuid

@dataclass
class UserModel:
    """Internal domain entity representing a user row in PostgreSQL."""
    id: uuid.UUID
    email: str
    hashed_password: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    token_version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: dict) -> "UserModel":
        """Factory method to map an asyncpg record dictionary to a domain object."""
        return cls(
            id=row["id"],
            email=row["email"],
            hashed_password=row["hashed_password"],
            full_name=row.get("full_name"),
            is_active=row["is_active"],
            is_superuser=row["is_superuser"],
            token_version=row.get("token_version", 1),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

# Raw DDL statement used during database setup/migrations
CREATE_USERS_TABLE_SQL = """
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_superuser BOOLEAN DEFAULT FALSE NOT NULL,
    token_version INT DEFAULT 1 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_email ON auth.users(email);

CREATE TABLE IF NOT EXISTS auth.password_resets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_used BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reset_token ON auth.password_resets(token);
"""