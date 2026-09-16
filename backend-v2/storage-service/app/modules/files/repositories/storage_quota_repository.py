from typing import Any, Optional
from datetime import datetime, timezone
import uuid
import json
from app.modules.files import queries
from .base import BaseRepository, map_db_errors

class StorageQuotaRepository(BaseRepository):
    @map_db_errors
    async def get_storage_usage(self, owner_id: uuid.UUID) -> int:
        return await self.conn.fetchval(queries.GET_STORAGE_USAGE, owner_id) or 0

    @map_db_errors
    async def get_user_storage_quota(self, owner_id: uuid.UUID) -> dict[str, Any]:
        row = await self.conn.fetchrow(queries.GET_USER_STORAGE_QUOTA, owner_id)
        if not row:
            # Lazy init
            row = await self.conn.fetchrow(queries.CREATE_USER_QUOTA, owner_id)
            if not row:
                row = await self.conn.fetchrow(queries.GET_USER_STORAGE_QUOTA, owner_id)
        return dict(row)

    @map_db_errors
    async def update_user_storage_usage(self, owner_id: uuid.UUID) -> int:
        await self.get_user_storage_quota(owner_id)
        return await self.conn.fetchval(queries.RECALCULATE_USER_STORAGE, owner_id)

    @map_db_errors
    async def check_storage_available(
        self, owner_id: uuid.UUID, requested_bytes: int
    ) -> bool:
        await self.get_user_storage_quota(owner_id)
        return bool(await self.conn.fetchval(queries.CHECK_STORAGE_AVAILABLE, owner_id, requested_bytes))

    @map_db_errors
    async def recalculate_user_storage(self, owner_id: uuid.UUID) -> int:
        await self.get_user_storage_quota(owner_id)
        return await self.conn.fetchval(queries.RECALCULATE_USER_STORAGE, owner_id) or 0

