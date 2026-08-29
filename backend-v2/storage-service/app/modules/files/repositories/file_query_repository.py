from typing import Any, Optional
from datetime import datetime, timezone
import uuid
import asyncpg
import json
from app.modules.files import queries
from .base import BaseRepository, map_db_errors

class FileQueryRepository(BaseRepository):
    @map_db_errors
    async def get_folder_by_id(self, folder_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(queries.GET_FOLDER_BY_ID, folder_id)
        return self._row_to_dict(row)

    @map_db_errors
    async def get_file_by_id(self, file_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(queries.GET_FILE_BY_ID, file_id)
        return self._row_to_dict(row)

    @map_db_errors
    async def list_user_folders(
        self, owner_id: uuid.UUID, parent_folder_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(queries.GET_USER_FOLDERS, owner_id, parent_folder_id)
        return [dict(r) for r in rows]

    @map_db_errors
    async def list_user_files(
        self, owner_id: uuid.UUID, parent_folder_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(queries.GET_USER_FILES, owner_id, parent_folder_id)
        return [dict(r) for r in rows]

    @map_db_errors
    async def list_folders_by_parent(
        self, parent_folder_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(queries.GET_FOLDERS_BY_PARENT, parent_folder_id)
        return [dict(r) for r in rows]

    @map_db_errors
    async def list_files_by_parent(
        self, parent_folder_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(queries.GET_FILES_BY_PARENT, parent_folder_id)
        return [dict(r) for r in rows]

    @map_db_errors
    async def get_folder_by_parent_and_name(
        self,
        parent_folder_id: uuid.UUID | None,
        folder_name: str,
        owner_id: uuid.UUID,
    ) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(
            queries.GET_FOLDER_BY_PARENT_AND_NAME, parent_folder_id, folder_name, owner_id
        )
        return self._row_to_dict(row)

    @map_db_errors
    async def get_file_by_parent_and_name(
        self,
        parent_folder_id: uuid.UUID | None,
        file_name: str,
        owner_id: uuid.UUID,
    ) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(
            queries.GET_FILE_BY_PARENT_AND_NAME, parent_folder_id, file_name, owner_id
        )
        return self._row_to_dict(row)

    @map_db_errors
    async def get_acl_entry(self, acl_entry_id: uuid.UUID) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(queries.GET_FOLDER_ACL, acl_entry_id)
        return self._row_to_dict(row)

    @map_db_errors
    async def get_live_user_share(
        self,
        *,
        file_id: uuid.UUID | None,
        folder_id: uuid.UUID | None,
        grantee_id: uuid.UUID,
    ) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(
            queries.GET_LIVE_USER_SHARE,
            file_id,
            folder_id,
            grantee_id,
        )
        return self._row_to_dict(row)

    @map_db_errors
    async def get_live_public_link(
        self,
        *,
        file_id: uuid.UUID | None,
        folder_id: uuid.UUID | None,
    ) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(
            queries.GET_LIVE_PUBLIC_LINK,
            file_id,
            folder_id,
        )
        return self._row_to_dict(row)

    @map_db_errors
    async def list_files_by_owner(
        self, 
        owner_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(
            queries.GET_FILES_BY_OWNER, 
            owner_id)
        return [dict(r) for r in rows]

    @map_db_errors
    async def list_files_under_path(
        self, 
        path
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(
            queries.GET_FILES_UNDER_PATH, 
            path)
        return [dict(r) for r in rows]

    @map_db_errors
    async def get_path_for_file(
        self, 
        file_id: uuid.UUID
    ) -> str | None:
        return await self.conn.fetchval(queries.GET_PATH_FOR_FILE, file_id)

    @map_db_errors
    async def get_path_for_folder(
        self,
        folder_id: uuid.UUID
    ) -> str | None:
        return await self.conn.fetchval(queries.GET_PATH_FOR_FOLDER, folder_id)

    @map_db_errors
    async def get_owner_and_trashed_for_file(
        self, 
        file_id: uuid.UUID
    ) -> asyncpg.Record | None:
        return await self.conn.fetchrow(queries.GET_OWNER_AND_TRASHED_FOR_FILE, file_id)

    @map_db_errors
    async def get_owner_and_trashed_for_folder(
        self, 
        folder_id: uuid.UUID
    ) -> asyncpg.Record | None:
        return await self.conn.fetchrow(queries.GET_OWNER_AND_TRASHED_FOR_FOLDER, folder_id)

    @map_db_errors
    async def get_effective_acl(
        self, 
        path: str, 
        is_file: bool, 
        target_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> dict | None:
        row = await self.conn.fetchrow(queries.GET_EFFECTIVE_ACL, path, is_file, target_id, user_id)
        return dict(row) if row else None

    @map_db_errors
    async def file_exists_by_name(
        self,
        parent_folder_id: uuid.UUID | None,
        owner_id: uuid.UUID,
        file_name: str,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        result = await self.conn.fetchval(
            queries.NAME_EXISTS,
            True,  # p_is_file
            parent_folder_id,
            owner_id,
            file_name,
            exclude_id,
        )
        return bool(result)

    @map_db_errors
    async def folder_exists_by_name(
        self,
        parent_folder_id: uuid.UUID | None,
        owner_id: uuid.UUID,
        folder_name: str,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        result = await self.conn.fetchval(
            queries.NAME_EXISTS,
            False,  # p_is_file = False checks storage.folders
            parent_folder_id,
            owner_id,
            folder_name,
            exclude_id,
        )
        return bool(result)

    @map_db_errors
    async def list_shared_with_me_folders(
        self,
        user_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(queries.GET_SHARED_WITH_ME_FOLDERS, user_id)
        return [dict(r) for r in rows]

    @map_db_errors
    async def list_shared_with_me_files(
        self, 
        user_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(queries.GET_SHARED_WITH_ME_FILES, user_id)
        return [dict(r) for r in rows]

    @map_db_errors
    async def get_folders_by_ids(
        self, 
        folder_ids: list[uuid.UUID]
    ) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(queries.GET_FOLDERS_BY_IDS, folder_ids)
        return [dict(r) for r in rows]
