import asyncpg
import uuid
from datetime import datetime
from typing import Optional, Any
from app.modules.auth import queries

class AuthRepository:
    
    async def get_by_email(self, conn: asyncpg.Connection, email: str) -> Optional[dict[str, Any]]:
        """Queries user by email using raw SQL and parameterized bindings."""
        row = await conn.fetchrow(queries.GET_USER_BY_EMAIL, email)
        return dict(row) if row else None
    
    async def get_by_id(self, conn: asyncpg.Connection, user_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.GET_USER_BY_ID, user_id)
        return dict(row) if row else None
    
    async def create_user(
        self, 
        conn: asyncpg.Connection,
        email: str,
        hashed_password: str,
        full_name: Optional[str],
    ) -> dict[str, Any]:
        row = await conn.fetchrow(queries.CREATE_USER, email, hashed_password, full_name)
        if not row:
            raise RuntimeError("Failed to insert user row into database.")
        return dict(row)
    
    async def delete_user(self, conn: asyncpg.Connection, user_id: uuid.UUID) -> bool:
        """Permanently deletes a user from the database."""
        result = await conn.execute(queries.DELETE_USER, user_id)
        # Returns True if a row was actually deleted
        return result == "DELETE 1"

    async def create_reset_token(
        self, 
        conn: asyncpg.Connection, 
        user_id: uuid.UUID, 
        token: str, 
        expires_at: datetime
    ) -> None:
        """Stores a new password reset token."""
        await conn.execute(queries.CREATE_RESET_TOKEN, user_id, token, expires_at)

    async def get_valid_reset_token(
        self, 
        conn: asyncpg.Connection, 
        token: str
    ) -> Optional[dict[str, Any]]:
        """Retrieves a token record if it exists, is unused, and hasn't expired."""
        row = await conn.fetchrow(queries.GET_VALID_RESET_TOKEN, token)
        return dict(row) if row else None
    
    async def update_password_and_invalidate_token(
        self, 
        conn: asyncpg.Connection, 
        user_id: uuid.UUID,
        new_hashed_password: str, 
        token_id: uuid.UUID
    ) -> None:
        """Updates user password and marks the token as used in a single transaction."""
        async with conn.transaction():
            await conn.execute(
                queries.UPDATE_USER_PASSWORD,
                new_hashed_password,
                user_id,
            )
            await conn.execute(
                queries.INVALIDATE_RESET_TOKEN,
                token_id,
            )
    
    async def get_password_by_id(self, conn: asyncpg.Connection, user_id: uuid.UUID) -> Optional[str]:
        row = await conn.fetchrow(queries.GET_CURRENT_PASSWORD, user_id)
        return row["hashed_password"] if row else None
    
    async def update_password(self, conn: asyncpg.Connection, user_id: uuid.UUID, new_hashed_password: str) -> None:
        await conn.execute(queries.UPDATE_USER_PASSWORD, new_hashed_password, user_id)

    async def update_user_storage(self, conn: asyncpg.Connection, user_id: uuid.UUID, storage_used: int) -> None:
        await conn.execute(queries.UPDATE_USER_STORAGE, storage_used, user_id)