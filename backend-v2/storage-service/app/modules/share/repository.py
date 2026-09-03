import asyncpg
import uuid
from typing import Optional, Any
from app.modules.share import queries

from fastapi import Depends
from app.core.database import get_db_connection

class ShareRepository:
    def __init__(self, conn: asyncpg.Connection = Depends(get_db_connection)):
        self.conn = conn

    async def get_user_by_email(self, email: str) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow("SELECT id, email, full_name FROM storage.users WHERE email = $1", email)
        return dict(row) if row else None
    
    async def check_is_owner(
        self, 
        target_id: uuid.UUID, 
        is_file: bool, user_id: 
        uuid.UUID
    ) -> bool:
        query = queries.CHECK_OWNER_FILE if is_file else queries.CHECK_OWNER_FOLDER
        row = await self.conn.fetchrow(query, target_id, user_id)
        return row is not None

    async def upsert_user_share(
        self, 
        target_id: uuid.UUID, 
        is_file: bool, 
        grantee_id: uuid.UUID, 
        permission: str, 
        created_by: uuid.UUID,
        password_hash: Optional[str] = None
    ) -> None:
        query = queries.UPSERT_USER_SHARE_FILE if is_file else queries.UPSERT_USER_SHARE_FOLDER
        await self.conn.execute(query, target_id, grantee_id, permission, created_by, password_hash)

    async def revoke_user_share(
        self, 
        target_id: uuid.UUID, 
        is_file: bool, 
        grantee_id: uuid.UUID
    ) -> None:
        query = queries.REVOKE_USER_SHARE_FILE if is_file else queries.REVOKE_USER_SHARE_FOLDER
        await self.conn.execute(query, target_id, grantee_id)

    async def upsert_public_link(
        self, 
        target_id: uuid.UUID, 
        is_file: bool, 
        share_token: str, 
        password_hash: Optional[str], 
        permission: str, 
        created_by: uuid.UUID
    ) -> str:
        query = queries.UPSERT_PUBLIC_LINK_FILE if is_file else queries.UPSERT_PUBLIC_LINK_FOLDER
        row = await self.conn.fetchrow(query, target_id, share_token, password_hash, permission, created_by)
        return row['share_token'] if row else share_token

    async def revoke_public_link(
        self, 
        target_id: uuid.UUID, 
        is_file: bool
    ) -> None:
        query = queries.REVOKE_PUBLIC_LINK_FILE if is_file else queries.REVOKE_PUBLIC_LINK_FOLDER
        await self.conn.execute(query, target_id)

    async def get_share_state(
        self, 
        target_id: uuid.UUID, 
        is_file: bool
    ) -> list[dict[str, Any]]:
        query = queries.GET_SHARE_STATE_FILE if is_file else queries.GET_SHARE_STATE_FOLDER
        rows = await self.conn.fetch(query, target_id)
        return [dict(row) for row in rows]

    async def get_acl_by_token(
        self,
        share_token: str
    ) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(queries.GET_ACL_BY_TOKEN, share_token)
        return dict(row) if row else None

    async def upsert_public_link_visitor(
        self,
        user_id: uuid.UUID,
        acl_entry_id: uuid.UUID
    ) -> None:
        await self.conn.execute(queries.UPSERT_PUBLIC_LINK_VISITOR, user_id, acl_entry_id)
