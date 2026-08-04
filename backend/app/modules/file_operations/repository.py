from __future__ import annotations

from datetime import datetime, timezone
import asyncpg
import uuid
from typing import Any, Optional

from app.modules.file_operations import queries


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
        expires_at: datetime | None,
        permission: str,
        created_by: uuid.UUID | None,
    ) -> dict[str, Any]:
        row = await conn.fetchrow(
            """
            INSERT INTO nephos.acl_entries (
                file_id, folder_id, principal_type, grantee_id, share_token,
                password_hash, expires_at, permission, created_by
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
                      revoked_at, created_by, created_at, updated_at
            """,
            file_id,
            folder_id,
            principal_type,
            grantee_id,
            share_token,
            password_hash,
            expires_at,
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
            """
            UPDATE nephos.acl_entries
            SET permission = $2
            WHERE id = $1 AND revoked_at IS NULL
            RETURNING id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
                      revoked_at, created_by, created_at, updated_at
            """,
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
        expires_at: datetime | None,
        permission: str,
    ) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(
            """
            UPDATE nephos.acl_entries
            SET share_token = $2,
                password_hash = $3,
                expires_at = $4,
                permission = $5
            WHERE id = $1 AND revoked_at IS NULL
            RETURNING id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
                      revoked_at, created_by, created_at, updated_at
            """,
            acl_entry_id,
            share_token,
            password_hash,
            expires_at,
            permission,
        )
        return self._row_to_dict(row)

    async def revoke_acl_entry(
        self,
        conn: asyncpg.Connection,
        acl_entry_id: uuid.UUID,
    ) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(
            """
            UPDATE nephos.acl_entries
            SET revoked_at = COALESCE(revoked_at, NOW())
            WHERE id = $1
            RETURNING id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
                      revoked_at, created_by, created_at, updated_at
            """,
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
            """
            SELECT id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
                   revoked_at, created_by, created_at, updated_at
            FROM nephos.acl_entries
            WHERE principal_type = 'user'
              AND revoked_at IS NULL
              AND grantee_id = $3
              AND file_id IS NOT DISTINCT FROM $1
              AND folder_id IS NOT DISTINCT FROM $2
            """,
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
            """
            SELECT id, file_id, folder_id, principal_type, grantee_id, share_token, permission,
                   revoked_at, created_by, created_at, updated_at
            FROM nephos.acl_entries
            WHERE principal_type = 'public_link'
              AND revoked_at IS NULL
              AND file_id IS NOT DISTINCT FROM $1
              AND folder_id IS NOT DISTINCT FROM $2
            """,
            file_id,
            folder_id,
        )
        return self._row_to_dict(row)
