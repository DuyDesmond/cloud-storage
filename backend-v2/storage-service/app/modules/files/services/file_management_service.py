from typing import Any
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

class FileManagementService(BaseFileService):
    def __init__(
        self,
        query_repo: FileQueryRepository = Depends(FileQueryRepository),
        quota_repo: StorageQuotaRepository = Depends(StorageQuotaRepository),
        trash_repo: TrashRepository = Depends(TrashRepository),
        management_repo: FileManagementRepository = Depends(FileManagementRepository),
        storage: StorageGateway = Depends(R2StorageGateway),
    ):
        super().__init__(query_repo, quota_repo, trash_repo, management_repo, storage)



    async def create_folder(
            self,
            current_user: dict[str, Any],
            payload: schemas.FolderCreateRequest,
        ) -> schemas.FolderResponse:
            await self._require_parent_access(payload.parent_folder_id, current_user["id"])
            owner_id = await self._resolve_owner_id(payload.parent_folder_id, current_user["id"])
    
            clean_name = sanitize_filename(payload.folder_name or "New Folder")
            on_col = getattr(payload, "on_collision", None)
    
            if on_col is None:
                collision = await self.query_repo.folder_exists_by_name(payload.parent_folder_id, owner_id, clean_name)
                if collision:
                    raise DuplicateRecordError("A folder with that name already exists. Resubmit with on_collision set to 'replace', 'keep_duplicate', or 'merge'.")
    
            async def _perform_operation():
                async with self.management_repo.conn.transaction():
                    await self.management_repo.call_lock_naming_scope(payload.parent_folder_id, owner_id)
                    
                    final_name = clean_name
                    if on_col == "keep_duplicate":
                        counter = 1
                        while await self.query_repo.folder_exists_by_name(payload.parent_folder_id, owner_id, final_name):
                            final_name = f"{clean_name} ({counter})"
                            counter += 1
                    elif on_col in ("replace", "merge"):
                        existing = await self.query_repo.get_folder_by_parent_and_name(
                            payload.parent_folder_id, clean_name, owner_id
                        )
                        if existing:
                            if on_col == "merge":
                                return existing
                            else:  # replace
                                await self.trash_repo.trash_folder(existing["id"])
    
                    return await self.management_repo.create_folder(
                        owner_id,
                        payload.parent_folder_id,
                        final_name,
                    )
    
            try:
                row = await with_db_retry(_perform_operation)
            except DuplicateRecordError:
                raise DuplicateRecordError("Folder name already exists.")
    
            return self._as_folder_response(row)

    async def move_folder(
            self,
            current_user: dict[str, Any],
            folder_id: uuid.UUID,
            payload: schemas.FolderMoveRequest,
        ) -> schemas.FolderResponse:
            folder = await self.query_repo.get_folder_by_id(folder_id)
            if not folder:
                raise ItemNotFoundError("Folder not found.")
            self._require_owner(folder, current_user["id"])
            self._require_target_live(folder)
            await self._require_parent_access(payload.parent_folder_id, current_user["id"])
    
            if payload.parent_folder_id == folder_id:
                raise InfrastructureError("Folder cannot be moved into itself.")
    
            folder_name = folder["folder_name"]
    
            async def _perform_operation():
                async with self.management_repo.conn.transaction():
                    await self.management_repo.move_folder(
                        folder_id,
                        payload.parent_folder_id,
                        on_collision=payload.on_collision,
                        file_mode=payload.file_mode,
                        file_decisions=payload.file_decisions,
                    )
                    row = await self.query_repo.get_folder_by_id(folder_id)
                    if row is None:
                        row = await self.query_repo.get_folder_by_parent_and_name(
                            payload.parent_folder_id, folder_name, current_user["id"]
                        )
                    return row
    
            try:
                row = await with_db_retry(_perform_operation)
            except ItemNotFoundError:
                raise ItemNotFoundError("Destination folder not found.")
            except QuotaExceededError:
                raise InfrastructureError("Not enough storage.")
            except InvalidOperationError, InfrastructureError:
                raise DuplicateRecordError("A folder with that name already exists at the destination. "
                    "Resubmit with on_collision set to 'merge' or 'keep_duplicate'.",)
    
            if not row:
                raise ItemNotFoundError("Folder not found after move.")
            return self._as_folder_response(row)

    async def move_file(
            self,
            current_user: dict[str, Any],
            file_id: uuid.UUID,
            payload: schemas.FileMoveRequest,
        ) -> schemas.FileResponse:
            file_row = await self.query_repo.get_file_by_id(file_id)
            if not file_row:
                raise ItemNotFoundError("File not found.")
            self._require_owner(file_row, current_user["id"])
            self._require_target_live(file_row)
            await self._require_parent_access(payload.parent_folder_id, current_user["id"])
    
            async def _perform_operation():
                async with self.management_repo.conn.transaction():
                    await self.management_repo.move_file(
                        file_id, payload.parent_folder_id, on_collision=payload.on_collision
                    )
                    return await self.query_repo.get_file_by_id(file_id)
    
            try:
                row = await with_db_retry(_perform_operation)
            except ItemNotFoundError:
                raise ItemNotFoundError("Destination folder not found.")
            except InvalidOperationError, InfrastructureError:
                raise DuplicateRecordError("A file with that name already exists at the destination. "
                    "Resubmit with on_collision set to 'replace' or 'keep_duplicate'.",)
    
            if not row:
                raise ItemNotFoundError("File not found.")
            return self._as_file_response(row)

    async def delete_folder(
            self,
            current_user: dict[str, Any],
            folder_id: uuid.UUID,
        ) -> schemas.MessageResponse:
            folder = await self.query_repo.get_folder_by_id(folder_id)
            if not folder:
                raise ItemNotFoundError("Folder not found.")
            self._require_owner(folder, current_user["id"])
            if folder["is_trashed"]:
                return schemas.MessageResponse(message="Folder already in trash.")
    
            row = await self.trash_repo.trash_folder(folder_id)
            if not row:
                raise ItemNotFoundError("Folder not found.")
            await self._recalculate_user_storage(current_user["id"])
            return schemas.MessageResponse(message="Folder moved to trash.")

    async def delete_file(
            self,
            current_user: dict[str, Any],
            file_id: uuid.UUID,
        ) -> schemas.MessageResponse:
            file_row = await self.query_repo.get_file_by_id(file_id)
            if not file_row:
                raise ItemNotFoundError("File not found.")
            self._require_owner(file_row, current_user["id"])
            if file_row["is_trashed"]:
                return schemas.MessageResponse(message="File already in trash.")
    
            row = await self.trash_repo.trash_file(file_id)
            if not row:
                raise ItemNotFoundError("File not found.")
            await self._recalculate_user_storage(current_user["id"])
            return schemas.MessageResponse(message="File moved to trash.")
