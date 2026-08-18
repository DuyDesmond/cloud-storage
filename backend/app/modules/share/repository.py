import asyncpg
import uuid
from typing import Optional, Any
from app.modules.share import queries

class ShareRepository:
    async def check_is_owner(
        self, 
        conn: asyncpg.Connection, 
        target_id: uuid.UUID, 
        is_file: bool, user_id: 
        uuid.UUID
    ) -> bool:
        query = queries.CHECK_OWNER_FILE if is_file else queries.CHECK_OWNER_FOLDER
        row = await conn.fetchrow(query, target_id, user_id)
        return row is not None

    async def upsert_user_share(
        self, 
        conn: asyncpg.Connection, 
        target_id: uuid.UUID, 
        is_file: bool, 
        grantee_id: uuid.UUID, 
        permission: str, 
        created_by: uuid.UUID
    ) -> None:
        query = queries.UPSERT_USER_SHARE_FILE if is_file else queries.UPSERT_USER_SHARE_FOLDER
        await conn.execute(query, target_id, grantee_id, permission, created_by)

    async def revoke_user_share(
        self, 
        conn: asyncpg.Connection, 
        target_id: uuid.UUID, 
        is_file: bool, 
        grantee_id: uuid.UUID
    ) -> None:
        query = queries.REVOKE_USER_SHARE_FILE if is_file else queries.REVOKE_USER_SHARE_FOLDER
        await conn.execute(query, target_id, grantee_id)

    async def upsert_public_link(
        self, 
        conn: asyncpg.Connection, 
        target_id: uuid.UUID, 
        is_file: bool, 
        share_token: str, 
        password_hash: Optional[str], 
        permission: str, 
        created_by: uuid.UUID
    ) -> str:
        query = queries.UPSERT_PUBLIC_LINK_FILE if is_file else queries.UPSERT_PUBLIC_LINK_FOLDER
        row = await conn.fetchrow(query, target_id, share_token, password_hash, permission, created_by)
        return row['share_token'] if row else share_token

    async def revoke_public_link(
        self, 
        conn: asyncpg.Connection, 
        target_id: uuid.UUID, 
        is_file: bool
    ) -> None:
        query = queries.REVOKE_PUBLIC_LINK_FILE if is_file else queries.REVOKE_PUBLIC_LINK_FOLDER
        await conn.execute(query, target_id)

    async def get_share_state(
        self, 
        conn: asyncpg.Connection, 
        target_id: uuid.UUID, 
        is_file: bool
    ) -> list[dict[str, Any]]:
        query = queries.GET_SHARE_STATE_FILE if is_file else queries.GET_SHARE_STATE_FOLDER
        rows = await conn.fetch(query, target_id)
        return [dict(row) for row in rows]
