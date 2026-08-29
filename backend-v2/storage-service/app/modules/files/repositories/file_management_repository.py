from typing import Any, Optional
from datetime import datetime, timezone
import uuid
import json
from app.modules.files import queries
from .base import BaseRepository, map_db_errors

class FileManagementRepository(BaseRepository):
    @map_db_errors
    async def create_folder(
        self,
        owner_id: uuid.UUID,
        parent_folder_id: uuid.UUID | None,
        folder_name: str,
    ) -> dict[str, Any]:
        row = await self.conn.fetchrow(queries.CREATE_FOLDER, owner_id, parent_folder_id, folder_name)
        if not row:
            raise RuntimeError("Failed to insert folder row into database.")
        return dict(row)

    @map_db_errors
    async def create_file(
        self,
        file_id: uuid.UUID,
        owner_id: uuid.UUID,
        parent_folder_id: uuid.UUID | None,
        storage_key: str,
        file_name: str,
        size_bytes: int,
        mime_type: str | None,
        content_hash: str | None,
    ) -> dict[str, Any]:
        row = await self.conn.fetchrow(
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

    @map_db_errors
    async def move_folder(
        self,
        folder_id: uuid.UUID,
        dest_parent_folder_id: uuid.UUID | None,
        *,
        on_collision: str | None = "keep_duplicate",  # 'merge' | 'keep_duplicate' | None
        file_mode: str = "keep_both",
        file_decisions: dict[str, Any] | None = None,
    ) -> None:
        import json
        await self.conn.fetchval(
            queries.CALL_MOVE_FOLDER,
            folder_id,
            dest_parent_folder_id,
            on_collision,
            file_mode,
            json.dumps(file_decisions or {}),
        )

    @map_db_errors
    async def move_file(
        self,
        file_id: uuid.UUID,
        dest_parent_folder_id: uuid.UUID | None,
        *,
        on_collision: str | None = "keep_duplicate",  # 'replace' | 'keep_duplicate' | None
    ) -> None:
        await self.conn.fetchval(queries.CALL_MOVE_FILE, file_id, dest_parent_folder_id, on_collision)

    @map_db_errors
    async def resolve_file_name_collision(
        self, 
        parent_folder_id: uuid.UUID | None, 
        owner_id: uuid.UUID, file_name: str
    ) -> str | None:
        return await self.conn.fetchval(queries.RESOLVE_FILE_NAME_COLLISION, parent_folder_id, owner_id, file_name)

    @map_db_errors
    async def call_lock_naming_scope(
        self,
        parent_folder_id: uuid.UUID | None, 
        owner_id: uuid.UUID
    ) -> None:
        await self.conn.fetchval(queries.CALL_LOCK_NAMING_SCOPE, parent_folder_id, owner_id)

    @map_db_errors
    async def create_acl_entry(
        self,
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
        row = await self.conn.fetchrow(
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

    @map_db_errors
    async def update_acl_entry_permission(
        self,
        acl_entry_id: uuid.UUID,
        permission: str,
    ) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(
            queries.UPDATE_ACL_ENTRY_PERMISSION,
            acl_entry_id,
            permission,
        )
        return self._row_to_dict(row)

    @map_db_errors
    async def update_live_public_link(
        self,
        acl_entry_id: uuid.UUID,
        *,
        share_token: str,
        password_hash: str | None,
        permission: str,
    ) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(
            queries.UPDATE_LIVE_PUBLIC_LINK,
            acl_entry_id,
            share_token,
            password_hash,
            permission,
        )
        return self._row_to_dict(row)

    @map_db_errors
    async def revoke_acl_entry(
        self,
        acl_entry_id: uuid.UUID,
    ) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(
            queries.REVOKE_ACL_ENTRY,
            acl_entry_id,
        )
        return self._row_to_dict(row)

