from typing import Any, Optional
from datetime import datetime, timezone
import uuid
import json
from app.modules.files import queries
from .base import BaseRepository, map_db_errors

class TrashRepository(BaseRepository):
    @map_db_errors
    async def trash_folder(self, folder_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(queries.TRASH_FOLDER, folder_id, datetime.now(timezone.utc))
        return self._row_to_dict(row)

    @map_db_errors
    async def trash_file(self, file_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(queries.TRASH_FILE, file_id, datetime.now(timezone.utc))
        return self._row_to_dict(row)

    @map_db_errors
    async def list_trashed_files_before(
        self,
        cutoff: datetime
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(
            queries.GET_TRASHED_FILES_BEFORE, 
            cutoff)
        return [dict(r) for r in rows]

    @map_db_errors
    async def list_trashed_folders_before(
        self, 
        cutoff: datetime
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(
            queries.GET_TRASHED_FOLDERS_BEFORE, 
            cutoff)
        return [dict(r) for r in rows]

    @map_db_errors
    async def list_trashed_files_by_owner(
        self, 
        owner_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(
            queries.GET_ALL_TRASHED_FILES_BY_OWNER, 
            owner_id)
        return [dict(r) for r in rows]

    @map_db_errors
    async def list_trashed_folders_by_owner(
        self, 
        owner_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(
            queries.GET_ALL_TRASHED_FOLDERS_BY_OWNER, 
            owner_id)
        return [dict(r) for r in rows]

    @map_db_errors
    async def delete_file_by_id(
        self, 
        file_id: uuid.UUID
    ) -> bool:
        result = await self.conn.execute(
            queries.DELETE_FILE_BY_ID,
            file_id)
        return result == "DELETE 1"

    @map_db_errors
    async def delete_folder_by_id(
        self, 
        folder_id: uuid.UUID
    ) -> bool:
        result = await self.conn.execute(
            queries.DELETE_FOLDER_BY_ID,
            folder_id)
        return result == "DELETE 1"

    @map_db_errors
    async def delete_files_under_path(
        self, 
        path
    ) -> None:
        await self.conn.execute(queries.DELETE_FILES_UNDER_PATH, path)

    @map_db_errors
    async def delete_folders_under_path(
        self, 
        path
    ) -> None:
        await self.conn.execute(queries.DELETE_FOLDERS_UNDER_PATH, path)

    @map_db_errors
    async def delete_trashed_files_by_owner(
        self, 
        owner_id: uuid.UUID
    ) -> None:
        await self.conn.execute(queries.DELETE_TRASHED_FILES_BY_OWNER, owner_id)

    @map_db_errors
    async def delete_trashed_folders_by_owner(
        self,
        owner_id: uuid.UUID
    ) -> None:
        await self.conn.execute(queries.DELETE_TRASHED_FOLDERS_BY_OWNER, owner_id)

    @map_db_errors
    async def delete_all_user_data(self, owner_id: uuid.UUID) -> None:
        async with self.conn.transaction():
            await self.conn.execute("DELETE FROM storage.acl_entries WHERE grantee_id = $1", owner_id)
            await self.conn.execute("DELETE FROM storage.files WHERE owner_id = $1", owner_id)
            await self.conn.execute("DELETE FROM storage.folders WHERE owner_id = $1", owner_id)

    @map_db_errors
    async def resolve_restored_file_name(
        self, 
        parent_folder_id: uuid.UUID | None, 
        owner_id: uuid.UUID, 
        file_name: str
    ) -> str | None:
        return await self.conn.fetchval(queries.RESOLVE_RESTORED_FILE_NAME, parent_folder_id, owner_id, file_name)

    @map_db_errors
    async def resolve_restored_folder_name(
        self, 
        parent_folder_id: uuid.UUID | None, 
        owner_id: uuid.UUID, 
        folder_name: str
    ) -> str | None:
        return await self.conn.fetchval(queries.RESOLVE_RESTORED_FOLDER_NAME, parent_folder_id, owner_id, folder_name)

    @map_db_errors
    async def restore_file(
        self, 
        file_id: uuid.UUID, 
        new_file_name: str
    ) -> dict[str, Any] | None:
        row = await self.conn.fetchrow(queries.RESTORE_FILE, file_id, new_file_name)
        return dict(row) if row else None

    @map_db_errors
    async def restore_folder(
        self, 
        folder_id: uuid.UUID, 
        new_folder_name: str
    ) -> dict[str, Any] | None:
        row = await self.conn.fetchrow(queries.RESTORE_FOLDER, folder_id, new_folder_name)
        return dict(row) if row else None

    @map_db_errors
    async def get_folder_trashed_size(self, folder_path: str) -> int:
        return await self.conn.fetchval(queries.GET_FOLDER_TRASHED_SIZE, folder_path) or 0

