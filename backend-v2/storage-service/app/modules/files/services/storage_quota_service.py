from app.core.config import settings
from typing import Any, Literal
from fastapi import Depends
import uuid
import asyncio
from app.core.exceptions import ItemNotFoundError, InvalidOperationError, DuplicateRecordError, InfrastructureError, QuotaExceededError
from app.modules.files import schemas
from app.modules.files.utils.sanitization import sanitize_filename
from app.modules.files.utils.db_retry import with_db_retry
from app.core.object_bucket import StorageGateway, R2StorageGateway
from app.modules.files.repositories import FileQueryRepository, StorageQuotaRepository, TrashRepository, FileManagementRepository
from .base import BaseFileService

class StorageQuotaService(BaseFileService):
    def __init__(
        self,
        query_repo: FileQueryRepository = Depends(FileQueryRepository),
        quota_repo: StorageQuotaRepository = Depends(StorageQuotaRepository),
        trash_repo: TrashRepository = Depends(TrashRepository),
        management_repo: FileManagementRepository = Depends(FileManagementRepository),
        storage: StorageGateway = Depends(R2StorageGateway),
    ):
        super().__init__(query_repo, quota_repo, trash_repo, management_repo, storage)

    async def _get_user_storage_quota(self, owner_id) -> dict:
            return await self.quota_repo.get_user_storage_quota(owner_id)

    async def get_storage_usage(
            self,
            current_user: dict[str, Any],
        ) -> schemas.StorageUsageResponse:
            used = await self.quota_repo.get_storage_usage(current_user["id"])
            quota_row = await self._get_user_storage_quota(current_user["id"])
            total = quota_row["storage_quota"] if quota_row else getattr(settings, "STORAGE_QUOTA_BYTES", 20 * 1024 ** 3)
            return schemas.StorageUsageResponse(used_bytes=used, total_bytes=total)
