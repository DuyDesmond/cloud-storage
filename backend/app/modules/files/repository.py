from __future__ import annotations

from datetime import datetime, timezone
import asyncpg
import uuid
from typing import Any, Optional

from app.modules.files import queries


class FileOperationsRepository:
    @staticmethod
    def _row_to_dict(row: asyncpg.Record | None) -> Optional[dict[str, Any]]:
        return dict(row) if row else None

    async def get_folder_by_id(self, conn: asyncpg.Connection, folder_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.GET_FOLDER_BY_ID, folder_id)
        return self._row_to_dict(row)

    async def get_file_by_id(self, conn: asyncpg.Connection, file_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.GET_FILE_BY_ID, file_id)
        return self._row_to_dict(row)

    async def create_folder(
        self,
        conn: asyncpg.Connection,
        owner_id: uuid.UUID,
        parent_folder_id: uuid.UUID | None,
        folder_name: str,
    ) -> dict[str, Any]:
        row = await conn.fetchrow(queries.CREATE_FOLDER, owner_id, parent_folder_id, folder_name)
        if not row:
            raise RuntimeError("Failed to insert folder row into database.")
        return dict(row)

    async def create_file(
        self,
        conn: asyncpg.Connection,
        file_id: uuid.UUID,
        owner_id: uuid.UUID,
        parent_folder_id: uuid.UUID | None,
        storage_key: str,
        file_name: str,
        size_bytes: int,
        mime_type: str | None,
        content_hash: str | None,
    ) -> dict[str, Any]:
        row = await conn.fetchrow(
            queries.CREATE_FILE,
            file_id,
            owner_id,
            parent_folder_id,
            storage_key,
            file_name,
            size_bytes,
            mime_type,
            content_hash,
        )
        if not row:
            raise RuntimeError("Failed to insert file row into database.")
        return dict(row)

    async def move_folder(
        self,
        conn: asyncpg.Connection,
        folder_id: uuid.UUID,
        parent_folder_id: uuid.UUID | None,
    ) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.MOVE_FOLDER, folder_id, parent_folder_id)
        return self._row_to_dict(row)

    async def move_file(
        self,
        conn: asyncpg.Connection,
        file_id: uuid.UUID,
        parent_folder_id: uuid.UUID | None,
    ) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.MOVE_FILE, file_id, parent_folder_id)
        return self._row_to_dict(row)

    async def trash_folder(self, conn: asyncpg.Connection, folder_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.TRASH_FOLDER, folder_id, datetime.now(timezone.utc))
        return self._row_to_dict(row)

    async def trash_file(self, conn: asyncpg.Connection, file_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.TRASH_FILE, file_id, datetime.now(timezone.utc))
        return self._row_to_dict(row)

    async def get_acl_entry(self, conn: asyncpg.Connection, acl_entry_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.GET_FOLDER_ACL, acl_entry_id)
        return self._row_to_dict(row)

    async def create_acl_entry(
        self,
        conn: asyncpg.Connection,
        *,
        file_id: uuid.UUID | None,
        folder_id: uuid.UUID | None,
        principal_type: str,
        grantee_id: uuid.UUID | None,
        share_token: str | None,
        password_hash: str | None,
        permission: str,
        created_by: uuid.UUID | None,
    ) -> dict[str, Any]:
        row = await conn.fetchrow(
            queries.CREATE_ACL_ENTRY,
            file_id,
            folder_id,
            principal_type,
            grantee_id,
            share_token,
            password_hash,
            permission,
            created_by,
        )
        if not row:
            raise RuntimeError("Failed to insert ACL row into database.")
        return dict(row)

    async def update_acl_entry_permission(
        self,
        conn: asyncpg.Connection,
        acl_entry_id: uuid.UUID,
        permission: str,
    ) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(
            queries.UPDATE_ACL_ENTRY_PERMISSION,
            acl_entry_id,
            permission,
        )
        return self._row_to_dict(row)

    async def update_live_public_link(
        self,
        conn: asyncpg.Connection,
        acl_entry_id: uuid.UUID,
        *,
        share_token: str,
        password_hash: str | None,
        permission: str,
    ) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(
            queries.UPDATE_LIVE_PUBLIC_LINK,
            acl_entry_id,
            share_token,
            password_hash,
            permission,
        )
        return self._row_to_dict(row)

    async def revoke_acl_entry(
        self,
        conn: asyncpg.Connection,
        acl_entry_id: uuid.UUID,
    ) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(
            queries.REVOKE_ACL_ENTRY,
            acl_entry_id,
        )
        return self._row_to_dict(row)

    async def get_live_user_share(
        self,
        conn: asyncpg.Connection,
        *,
        file_id: uuid.UUID | None,
        folder_id: uuid.UUID | None,
        grantee_id: uuid.UUID,
    ) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(
            queries.GET_LIVE_USER_SHARE,
            file_id,
            folder_id,
            grantee_id,
        )
        return self._row_to_dict(row)

    async def get_live_public_link(
        self,
        conn: asyncpg.Connection,
        *,
        file_id: uuid.UUID | None,
        folder_id: uuid.UUID | None,
    ) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(
            queries.GET_LIVE_PUBLIC_LINK,
            file_id,
            folder_id,
        )
        return self._row_to_dict(row)