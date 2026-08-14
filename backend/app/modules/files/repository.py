from __future__ import annotations
from typing import Any, Optional, Union
from datetime import datetime, timezone
import asyncpg
from asyncpg.pool import PoolConnectionProxy
import uuid
from typing import Any, Optional
import logging

from fastapi import HTTPException,status

from app.modules.files import queries

AsyncConn = Union[asyncpg.Connection, PoolConnectionProxy]

class FileOperationsRepository:
    @staticmethod
    def _row_to_dict(row: asyncpg.Record | None) -> Optional[dict[str, Any]]:
        return dict(row) if row else None

    async def get_storage_usage(self, conn: AsyncConn, owner_id: uuid.UUID) -> int:
        return await conn.fetchval(queries.GET_STORAGE_USAGE, owner_id) or 0

    async def get_user_storage_quota(self, conn: AsyncConn, owner_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.GET_USER_STORAGE_QUOTA, owner_id)
        return self._row_to_dict(row)

    async def check_storage_available(
        self, conn: AsyncConn, owner_id: uuid.UUID, requested_bytes: int
    ) -> bool:
        return bool(await conn.fetchval(queries.CHECK_STORAGE_AVAILABLE, owner_id, requested_bytes))

    async def recalculate_user_storage(self, conn: AsyncConn, owner_id: uuid.UUID) -> int:
        return await conn.fetchval(queries.RECALCULATE_USER_STORAGE, owner_id) or 0

    async def get_folder_by_id(self, conn: AsyncConn, folder_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.GET_FOLDER_BY_ID, folder_id)
        return self._row_to_dict(row)

    async def get_file_by_id(self, conn: AsyncConn, file_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.GET_FILE_BY_ID, file_id)
        return self._row_to_dict(row)

    async def list_user_folders(
        self, conn: AsyncConn, owner_id: uuid.UUID, parent_folder_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        rows = await conn.fetch(queries.GET_USER_FOLDERS, owner_id, parent_folder_id)
        return [dict(r) for r in rows]

    async def list_user_files(
        self, conn: AsyncConn, owner_id: uuid.UUID, parent_folder_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        rows = await conn.fetch(queries.GET_USER_FILES, owner_id, parent_folder_id)
        return [dict(r) for r in rows]

    async def create_folder(
        self,
        conn: AsyncConn,
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
        conn: AsyncConn,
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
        conn: AsyncConn,
        folder_id: uuid.UUID,
        dest_parent_folder_id: uuid.UUID | None,
        *,
        on_collision: str | None = "keep_duplicate",  # 'merge' | 'keep_duplicate' | None
        file_mode: str = "keep_both",
        file_decisions: dict[str, Any] | None = None,
    ) -> None:
        import json
        await conn.fetchval(
            queries.CALL_MOVE_FOLDER,
            folder_id,
            dest_parent_folder_id,
            on_collision,
            file_mode,
            json.dumps(file_decisions or {}),
        )

    async def move_file(
        self,
        conn: AsyncConn,
        file_id: uuid.UUID,
        dest_parent_folder_id: uuid.UUID | None,
        *,
        on_collision: str | None = "keep_duplicate",  # 'replace' | 'keep_duplicate' | None
    ) -> None:
        await conn.fetchval(queries.CALL_MOVE_FILE, file_id, dest_parent_folder_id, on_collision)

    async def get_folder_by_parent_and_name(
        self,
        conn: AsyncConn,
        parent_folder_id: uuid.UUID | None,
        folder_name: str,
        owner_id: uuid.UUID,
    ) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(
            queries.GET_FOLDER_BY_PARENT_AND_NAME, parent_folder_id, folder_name, owner_id
        )
        return self._row_to_dict(row)

    async def get_file_by_parent_and_name(
        self,
        conn: AsyncConn,
        parent_folder_id: uuid.UUID | None,
        file_name: str,
        owner_id: uuid.UUID,
    ) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(
            queries.GET_FILE_BY_PARENT_AND_NAME, parent_folder_id, file_name, owner_id
        )
        return self._row_to_dict(row)

    async def trash_folder(self, conn: AsyncConn, folder_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.TRASH_FOLDER, folder_id, datetime.now(timezone.utc))
        return self._row_to_dict(row)

    async def trash_file(self, conn: AsyncConn, file_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.TRASH_FILE, file_id, datetime.now(timezone.utc))
        return self._row_to_dict(row)

    async def get_acl_entry(self, conn: AsyncConn, acl_entry_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(queries.GET_FOLDER_ACL, acl_entry_id)
        return self._row_to_dict(row)

    async def create_acl_entry(
        self,
        conn: AsyncConn,
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
        query = queries.CREATE_ACL_ENTRY if file_id is not None else queries.CREATE_ACL_ENTRY_FOLDER
        row = await conn.fetchrow(
            query,
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
        conn: AsyncConn,
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
        conn: AsyncConn,
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
        conn: AsyncConn,
        acl_entry_id: uuid.UUID,
    ) -> Optional[dict[str, Any]]:
        row = await conn.fetchrow(
            queries.REVOKE_ACL_ENTRY,
            acl_entry_id,
        )
        return self._row_to_dict(row)

    async def get_live_user_share(
        self,
        conn: AsyncConn,
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
        conn: AsyncConn,
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

    async def list_trashed_files_before(
        self,
        conn: AsyncConn, 
        cutoff: datetime
    ) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            queries.GET_TRASHED_FILES_BEFORE, 
            cutoff)
        return [dict(r) for r in rows]

    async def list_trashed_folders_before(
        self, 
        conn: AsyncConn, 
        cutoff: datetime
    ) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            queries.GET_TRASHED_FOLDERS_BEFORE, 
            cutoff)
        return [dict(r) for r in rows]

    async def list_files_by_owner(
        self, 
        conn: AsyncConn, 
        owner_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            queries.GET_FILES_BY_OWNER, 
            owner_id)
        return [dict(r) for r in rows]

    async def list_files_under_path(
        self, 
        conn: AsyncConn, 
        path
    ) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            queries.GET_FILES_UNDER_PATH, 
            path)
        return [dict(r) for r in rows]

    async def list_trashed_files_by_owner(
        self, 
        conn: AsyncConn, 
        owner_id: uuid.UUID,
        parent_folder_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            queries.GET_ALL_TRASHED_FILES_BY_OWNER, 
            owner_id, parent_folder_id)
        return [dict(r) for r in rows]

    async def list_trashed_folders_by_owner(
        self, 
        conn: AsyncConn, 
        owner_id: uuid.UUID,
        parent_folder_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        rows = await conn.fetch(
            queries.GET_ALL_TRASHED_FOLDERS_BY_OWNER, 
            owner_id, parent_folder_id)
        return [dict(r) for r in rows]

    async def delete_file_by_id(
        self, 
        conn: AsyncConn, 
        file_id: uuid.UUID
    ) -> bool:
        result = await conn.execute(
            queries.DELETE_FILE_BY_ID,
            file_id)
        return result == "DELETE 1"

    async def delete_folder_by_id(
        self, 
        conn: AsyncConn, 
        folder_id: uuid.UUID
    ) -> bool:
        result = await conn.execute(
            queries.DELETE_FOLDER_BY_ID,
            folder_id)
        return result == "DELETE 1"

    async def delete_files_under_path(
        self, 
        conn: AsyncConn, 
        path
    ) -> None:
        await conn.execute(queries.DELETE_FILES_UNDER_PATH, path)

    async def delete_folders_under_path(
        self, 
        conn: AsyncConn, 
        path
    ) -> None:
        await conn.execute(queries.DELETE_FOLDERS_UNDER_PATH, path)

    async def delete_trashed_files_by_owner(
        self, 
        conn: AsyncConn, 
        owner_id: uuid.UUID
    ) -> None:
        await conn.execute(queries.DELETE_TRASHED_FILES_BY_OWNER, owner_id)

    async def delete_trashed_folders_by_owner(
        self,
        conn: AsyncConn, 
        owner_id: uuid.UUID
    ) -> None:
        await conn.execute(queries.DELETE_TRASHED_FOLDERS_BY_OWNER, owner_id)

    async def get_path_for_file(
        self, 
        conn: AsyncConn, 
        file_id: uuid.UUID
    ) -> str | None:
        return await conn.fetchval(queries.GET_PATH_FOR_FILE, file_id)

    async def get_path_for_folder(
        self,
        conn: AsyncConn, 
        folder_id: uuid.UUID
    ) -> str | None:
        return await conn.fetchval(queries.GET_PATH_FOR_FOLDER, folder_id)

    async def get_owner_and_trashed_for_file(
        self, 
        conn: AsyncConn, 
        file_id: uuid.UUID
    ) -> asyncpg.Record | None:
        return await conn.fetchrow(queries.GET_OWNER_AND_TRASHED_FOR_FILE, file_id)

    async def get_owner_and_trashed_for_folder(
        self, 
        conn: AsyncConn, 
        folder_id: uuid.UUID
    ) -> asyncpg.Record | None:
        return await conn.fetchrow(queries.GET_OWNER_AND_TRASHED_FOR_FOLDER, folder_id)

    async def get_effective_permission(
        self, 
        conn: AsyncConn, 
        path: str, 
        is_file: bool, 
        target_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> str | None:
        return await conn.fetchval(queries.GET_EFFECTIVE_PERMISSION, path, is_file, target_id, user_id)

    async def file_exists_by_name(
        self,
        conn: asyncpg.Connection,
        parent_folder_id: uuid.UUID | None,
        owner_id: uuid.UUID,
        file_name: str,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        result = await conn.fetchval(
            queries.NAME_EXISTS,
            True,  # p_is_file
            parent_folder_id,
            owner_id,
            file_name,
            exclude_id,
        )
        return bool(result)

    async def folder_exists_by_name(
        self,
        conn: asyncpg.Connection,
        parent_folder_id: uuid.UUID | None,
        owner_id: uuid.UUID,
        folder_name: str,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        result = await conn.fetchval(
            queries.NAME_EXISTS,
            False,  # p_is_file = False checks nephos.folders
            parent_folder_id,
            owner_id,
            folder_name,
            exclude_id,
        )
        return bool(result)

    async def call_lock_naming_scope(
        self,
        conn: AsyncConn, 
        parent_folder_id: uuid.UUID | None, 
        owner_id: uuid.UUID
    ) -> None:
        await conn.fetchval(queries.CALL_LOCK_NAMING_SCOPE, parent_folder_id, owner_id)

    async def resolve_file_name_collision(
        self, 
        conn: asyncpg.Connection, 
        parent_folder_id: uuid.UUID | None, 
        owner_id: uuid.UUID, file_name: str
    ) -> str | None:
        return await conn.fetchval(queries.RESOLVE_FILE_NAME_COLLISION, parent_folder_id, owner_id, file_name)

    async def resolve_restored_file_name(
        self, 
        conn: AsyncConn, 
        parent_folder_id: uuid.UUID | None, 
        owner_id: uuid.UUID, 
        file_name: str
    ) -> str | None:
        return await conn.fetchval(queries.RESOLVE_RESTORED_FILE_NAME, parent_folder_id, owner_id, file_name)

    async def resolve_restored_folder_name(
        self, 
        conn: AsyncConn, 
        parent_folder_id: uuid.UUID | None, 
        owner_id: uuid.UUID, 
        folder_name: str
    ) -> str | None:
        return await conn.fetchval(queries.RESOLVE_RESTORED_FOLDER_NAME, parent_folder_id, owner_id, folder_name)

    async def restore_file(
        self, 
        conn: AsyncConn, 
        file_id: uuid.UUID, 
        new_file_name: str
    ) -> dict[str, Any] | None:
        row = await conn.fetchrow(queries.RESTORE_FILE, file_id, new_file_name)
        return dict(row) if row else None

    async def restore_folder(
        self, 
        conn: AsyncConn, 
        folder_id: uuid.UUID, 
        new_folder_name: str
    ) -> dict[str, Any] | None:
        row = await conn.fetchrow(queries.RESTORE_FOLDER, folder_id, new_folder_name)
        return dict(row) if row else None