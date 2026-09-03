from typing import Any
from fastapi import Depends
import uuid
import asyncio
from app.core.exceptions import ItemNotFoundError, InvalidOperationError, DuplicateRecordError, InfrastructureError, QuotaExceededError, AccessDeniedError
from app.modules.files import schemas
from app.modules.files.utils.sanitization import sanitize_filename
from app.modules.files.utils.db_retry import with_db_retry
from app.core.object_bucket import StorageGateway, R2StorageGateway
from app.modules.files.repositories import FileQueryRepository, StorageQuotaRepository, TrashRepository, FileManagementRepository
from .base import BaseFileService

class FileQueryService(BaseFileService):
    def __init__(
        self,
        query_repo: FileQueryRepository = Depends(FileQueryRepository),
        quota_repo: StorageQuotaRepository = Depends(StorageQuotaRepository),
        trash_repo: TrashRepository = Depends(TrashRepository),
        management_repo: FileManagementRepository = Depends(FileManagementRepository),
        storage: StorageGateway = Depends(R2StorageGateway),
    ):
        super().__init__(query_repo, quota_repo, trash_repo, management_repo, storage)

    async def get_storage_contents(
            self,
            current_user: dict[str, Any] | None,
            parent_folder_id: uuid.UUID | None = None,
        ) -> schemas.StorageContentResponse:
            if not current_user and not parent_folder_id:
                raise AccessDeniedError("Anonymous users cannot list the root directory.")

            if parent_folder_id:
                await self._require_view_access(
                    target_type="folder", target_id=parent_folder_id, current_user_id=current_user["id"] if current_user else None
                )
                folders_raw = await self.query_repo.list_folders_by_parent(parent_folder_id)
                files_raw = await self.query_repo.list_files_by_parent(parent_folder_id)
            else:
                folders_raw = await self.query_repo.list_user_folders(current_user["id"], None)
                files_raw = await self.query_repo.list_user_files(current_user["id"], None)
    
            return schemas.StorageContentResponse(
                folders=[self._as_folder_response(f) for f in folders_raw],
                files=[self._as_file_response(f) for f in files_raw],
            )

    async def get_shared_with_me_contents(
            self,
            current_user: dict[str, Any],
        ) -> schemas.StorageContentResponse:
            owner_id = current_user["id"]
            folders_raw = await self.query_repo.list_shared_with_me_folders(owner_id)
            files_raw = await self.query_repo.list_shared_with_me_files(owner_id)
            
            shared_folder_ids = {f["id"] for f in folders_raw}
            
            def is_outermost(item: dict[str, Any]) -> bool:
                path_str = item.get("path")
                if not path_str:
                    return True
                path_uuids_str = path_str.replace('_', '-')
                parts = path_uuids_str.split('.')
                for part in parts:
                    try:
                        part_uuid = uuid.UUID(part)
                        if part_uuid != item["id"] and part_uuid in shared_folder_ids:
                            return False
                    except ValueError:
                        pass
                return True
    
            folders_filtered = [f for f in folders_raw if is_outermost(f)]
            files_filtered = [f for f in files_raw if is_outermost(f)]
    
            return schemas.StorageContentResponse(
                folders=[self._as_folder_response(f) for f in folders_filtered],
                files=[self._as_file_response(f) for f in files_filtered],
            )

    async def get_breadcrumbs(
            self,
            target_id: uuid.UUID,
            is_file: bool,
            current_user: dict[str, Any] | None = None,
        ) -> list[dict[str, str]]:
            await self._require_view_access(
                target_type="file" if is_file else "folder", target_id=target_id, current_user_id=current_user["id"] if current_user else None
            )
            path_str = await (self.query_repo.get_path_for_file(target_id) if is_file else self.query_repo.get_path_for_folder(target_id))
            if not path_str:
                return []
                
            path_uuids_str = path_str.replace('_', '-')
            parts = path_uuids_str.split('.')
            uuids = []
            for part in parts:
                try:
                    uuids.append(uuid.UUID(part))
                except ValueError:
                    pass
                    
            if not uuids:
                return []
                
            folders = await self.query_repo.get_folders_by_ids(uuids)
            folder_dict = {f["id"]: f["folder_name"] for f in folders}
            
            result = []
            for u in uuids:
                if u in folder_dict:
                    result.append({"id": str(u), "name": folder_dict[u]})
            return result
