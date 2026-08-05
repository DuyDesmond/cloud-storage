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

    async def list_trashed_files_before(self, conn: asyncpg.Connection, cutoff: datetime) -> list[dict[str, Any]]:
        rows = await conn.fetch(queries.GET_TRASHED_FILES_BEFORE, cutoff)
        return [dict(r) for r in rows]

    async def list_trashed_folders_before(self, conn: asyncpg.Connection, cutoff: datetime) -> list[dict[str, Any]]:
        rows = await conn.fetch(queries.GET_TRASHED_FOLDERS_BEFORE, cutoff)
        return [dict(r) for r in rows]

    async def list_files_by_owner(self, conn: asyncpg.Connection, owner_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = await conn.fetch(queries.GET_FILES_BY_OWNER, owner_id)
        return [dict(r) for r in rows]

    async def list_files_under_path(self, conn: asyncpg.Connection, path) -> list[dict[str, Any]]:
        rows = await conn.fetch(queries.GET_FILES_UNDER_PATH, path)
        return [dict(r) for r in rows]

    async def list_trashed_files_by_owner(self, conn: asyncpg.Connection, owner_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = await conn.fetch(queries.GET_ALL_TRASHED_FILES_BY_OWNER, owner_id)
        return [dict(r) for r in rows]

    async def list_trashed_folders_by_owner(self, conn: asyncpg.Connection, owner_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = await conn.fetch(queries.GET_ALL_TRASHED_FOLDERS_BY_OWNER, owner_id)
        return [dict(r) for r in rows]

    async def delete_file_by_id(self, conn: asyncpg.Connection, file_id: uuid.UUID) -> bool:
        result = await conn.execute(queries.DELETE_FILE_BY_ID, file_id)
        return result == "DELETE 1"

    async def delete_folder_by_id(self, conn: asyncpg.Connection, folder_id: uuid.UUID) -> bool:
        result = await conn.execute(queries.DELETE_FOLDER_BY_ID, folder_id)
        return result == "DELETE 1"

    async def delete_files_under_path(self, conn: asyncpg.Connection, path) -> None:
        await conn.execute(queries.DELETE_FILES_UNDER_PATH, path)

    async def delete_folders_under_path(self, conn: asyncpg.Connection, path) -> None:
        await conn.execute(queries.DELETE_FOLDERS_UNDER_PATH, path)

    async def delete_trashed_files_by_owner(self, conn: asyncpg.Connection, owner_id: uuid.UUID) -> None:
        await conn.execute(queries.DELETE_TRASHED_FILES_BY_OWNER, owner_id)

    async def delete_trashed_folders_by_owner(self, conn: asyncpg.Connection, owner_id: uuid.UUID) -> None:
        await conn.execute(queries.DELETE_TRASHED_FOLDERS_BY_OWNER, owner_id)

    async def get_path_for_file(self, conn: asyncpg.Connection, file_id: uuid.UUID) -> str | None:
        return await conn.fetchval(queries.GET_PATH_FOR_FILE, file_id)

    async def get_path_for_folder(self, conn: asyncpg.Connection, folder_id: uuid.UUID) -> str | None:
        return await conn.fetchval(queries.GET_PATH_FOR_FOLDER, folder_id)

    async def get_owner_and_trashed_for_file(self, conn: asyncpg.Connection, file_id: uuid.UUID) -> asyncpg.Record | None:
        return await conn.fetchrow(queries.GET_OWNER_AND_TRASHED_FOR_FILE, file_id)

    async def get_owner_and_trashed_for_folder(self, conn: asyncpg.Connection, folder_id: uuid.UUID) -> asyncpg.Record | None:
        return await conn.fetchrow(queries.GET_OWNER_AND_TRASHED_FOR_FOLDER, folder_id)

    async def get_effective_permission(self, conn: asyncpg.Connection, path: str, is_file: bool, target_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
        return await conn.fetchval(queries.GET_EFFECTIVE_PERMISSION, path, is_file, target_id, user_id)

    async def call_lock_naming_scope(self, conn: asyncpg.Connection, parent_folder_id: uuid.UUID | None, owner_id: uuid.UUID) -> None:
        await conn.fetchval(queries.CALL_LOCK_NAMING_SCOPE, parent_folder_id, owner_id)

    async def resolve_restored_file_name(self, conn: asyncpg.Connection, parent_folder_id: uuid.UUID | None, owner_id: uuid.UUID, file_name: str) -> str:
        return await conn.fetchval(queries.RESOLVE_RESTORED_FILE_NAME, parent_folder_id, owner_id, file_name)

    async def resolve_restored_folder_name(self, conn: asyncpg.Connection, parent_folder_id: uuid.UUID | None, owner_id: uuid.UUID, folder_name: str) -> str:
        return await conn.fetchval(queries.RESOLVE_RESTORED_FOLDER_NAME, parent_folder_id, owner_id, folder_name)

    async def restore_file(self, conn: asyncpg.Connection, file_id: uuid.UUID, new_file_name: str) -> dict[str, Any] | None:
        row = await conn.fetchrow(queries.RESTORE_FILE, file_id, new_file_name)
        return dict(row) if row else None

    async def restore_folder(self, conn: asyncpg.Connection, folder_id: uuid.UUID, new_folder_name: str) -> dict[str, Any] | None:
        row = await conn.fetchrow(queries.RESTORE_FOLDER, folder_id, new_folder_name)
        return dict(row) if row else None
    # Outbox-related repository methods removed: using synchronous deletion flow instead.