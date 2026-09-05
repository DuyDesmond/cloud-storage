from app.core.exceptions import DomainError
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

class TrashService(BaseFileService):
    def __init__(
        self,
        query_repo: FileQueryRepository = Depends(FileQueryRepository),
        quota_repo: StorageQuotaRepository = Depends(StorageQuotaRepository),
        trash_repo: TrashRepository = Depends(TrashRepository),
        management_repo: FileManagementRepository = Depends(FileManagementRepository),
        storage: StorageGateway = Depends(R2StorageGateway),
    ):
        super().__init__(query_repo, quota_repo, trash_repo, management_repo, storage)

    async def _handle_restored_name_collision(self, parent_id, owner_id, original_name, is_file: bool):
            await self.management_repo.call_lock_naming_scope(parent_id, owner_id)
            if is_file:
                new_name = await self.trash_repo.resolve_restored_file_name(parent_id, owner_id, original_name)
            else:
                new_name = await self.trash_repo.resolve_restored_folder_name(parent_id, owner_id, original_name)
                
            if new_name is None:
                raise InfrastructureError(f"Could not resolve a valid name for the restored {'file' if is_file else 'folder'}.")
            return new_name

    async def hard_delete_file(
            self,
            current_user: dict[str, Any],
            file_id: uuid.UUID,
        ) -> schemas.MessageResponse:
            file_row = await self.query_repo.get_file_by_id(file_id)
            if not file_row:
                raise ItemNotFoundError("File not found.")
            self._require_owner(file_row, current_user["id"])
            if not file_row["is_trashed"]:
                raise InfrastructureError("File is not in trash.")
            storage_key = file_row.get("storage_key")
    
            # If there is an object to delete, attempt it synchronously with retries.
            if storage_key:
                last_exc: Exception | None = None
                for attempt in range(1, 4):
                    try:
                        await self.storage.delete_object(storage_key)
                        last_exc = None
                        break
                    except Exception as exc:
                        last_exc = exc
                        await asyncio.sleep(0.5 * attempt)
    
                if last_exc is not None:
                    raise InfrastructureError("Failed to delete object from storage; please try again later.")
    
            # Object deleted (or no storage_key). Now remove DB row.
            try:
                async with self.trash_repo.conn.transaction():
                    deleted = await self.trash_repo.delete_file_by_id(file_id)
                    if not deleted:
                        raise InfrastructureError("Failed to delete file row.")
            except DomainError:
                raise
            except Exception as exc:
                raise InfrastructureError("Failed to delete file row.")
    
            await self._recalculate_user_storage(current_user["id"])
            return schemas.MessageResponse(message="File permanently deleted.")

    async def hard_delete_folder(
            self,
            current_user: dict[str, Any],
            folder_id: uuid.UUID,
        ) -> schemas.MessageResponse:
            folder = await self.query_repo.get_folder_by_id(folder_id)
            if not folder:
                raise ItemNotFoundError("Folder not found.")
            self._require_owner(folder, current_user["id"])
            if not folder["is_trashed"]:
                raise InfrastructureError("Folder is not in trash.")
    
            folder_path = folder.get("path")
            # gather files under this path
            files = await self.query_repo.list_files_under_path(folder_path)
    
            # Batch delete from S3
            storage_keys = [f.get("storage_key") for f in files if f.get("storage_key")]
            if storage_keys:
                await self.storage.batch_delete_objects(storage_keys)
    
            # All object deletions succeeded (or no storage_key). Delete folder rows and files under path atomically.
            try:
                async with self.trash_repo.conn.transaction():
                    await self.trash_repo.delete_files_under_path(folder_path)
                    await self.trash_repo.delete_folders_under_path(folder_path)
            except Exception as exc:
                raise InfrastructureError("Failed to delete folder rows.")
    
            await self._recalculate_user_storage(current_user["id"])
            return schemas.MessageResponse(message="Folder and contents permanently deleted.")

    async def hard_delete_all_trash(
            self,
            current_user: dict[str, Any],
        ) -> schemas.MessageResponse:
            owner_id = current_user["id"]
            files = await self.trash_repo.list_trashed_files_by_owner(owner_id)
    
            storage_keys = [f.get("storage_key") for f in files if f.get("storage_key")]
            if storage_keys:
                await self.storage.batch_delete_objects(storage_keys)
                
            for f in files:
    
                # delete DB row for this file
                try:
                    async with self.trash_repo.conn.transaction():
                        await self.trash_repo.delete_file_by_id(f["id"])
                except Exception:
                    pass
    
            # Remove trashed folder rows
            async with self.trash_repo.conn.transaction():
                await self.trash_repo.delete_trashed_folders_by_owner(owner_id)
    
            await self._recalculate_user_storage(owner_id)
            return schemas.MessageResponse(message="Trash emptied (permanently deleted).")

    async def restore_file(
            self,
            current_user: dict[str, Any],
            file_id: uuid.UUID,
        ) -> schemas.FileResponse:
            file_row = await self.query_repo.get_file_by_id(file_id)
            if not file_row:
                raise ItemNotFoundError("File not found.")
            self._require_owner(file_row, current_user["id"])
            if not file_row["is_trashed"]:
                return self._as_file_response(file_row)
    
            file_size = file_row.get("size_bytes", 0)
            if file_size > 0:
                has_space = await self.quota_repo.check_storage_available(current_user["id"], file_size)
                if not has_space:
                    raise QuotaExceededError("Storage quota exceeded.",)
    
            parent_id = file_row.get("parent_folder_id")
            owner_id = file_row.get("owner_id")
            file_name = file_row.get("file_name")
    
            if not owner_id:
                raise InfrastructureError("File record is missing a valid owner ID.")
    
            if not file_name:
                raise InfrastructureError("File name is missing.")
    
            async def _perform_operation():
                async with self.trash_repo.conn.transaction():
                    new_name = await self._handle_restored_name_collision(parent_id, owner_id, file_name, is_file=True)
                    return await self.trash_repo.restore_file(file_id, new_name)
    
            try:
                restored = await with_db_retry(_perform_operation)
            except DuplicateRecordError:
                raise DuplicateRecordError("Name collision during restore; please retry.")
            except (InvalidOperationError, InfrastructureError):
                raise DuplicateRecordError("Deadlock during restore; please retry.")
    
            if not restored:
                raise InfrastructureError("Failed to restore file.")
    
            await self._recalculate_user_storage(current_user["id"])
            return self._as_file_response(restored)

    async def restore_folder(
            self,
            current_user: dict[str, Any],
            folder_id: uuid.UUID,
        ) -> schemas.FolderResponse:
            folder = await self.query_repo.get_folder_by_id(folder_id)
            if not folder:
                raise ItemNotFoundError("Folder not found.")
            self._require_owner(folder, current_user["id"])
            if not folder["is_trashed"]:
                return self._as_folder_response(folder)
    
            parent_id = folder.get("parent_folder_id")
            owner_id = folder.get("owner_id")
            folder_name = folder.get("folder_name")
            folder_path = folder.get("path")
    
            if not owner_id:
                raise InfrastructureError("Folder record is missing a valid owner ID.")
    
            if not folder_name:
                raise InfrastructureError("Folder name must not be empty.")
    
            if folder_path:
                trashed_size = await self.query_repo.get_folder_trashed_size(folder_path)
                if trashed_size > 0:
                    has_space = await self.quota_repo.check_storage_available(current_user["id"], trashed_size)
                    if not has_space:
                        raise QuotaExceededError("Storage quota exceeded.",)
    
            async def _perform_operation():
                async with self.trash_repo.conn.transaction():
                    new_name = await self._handle_restored_name_collision(parent_id, owner_id, folder_name, is_file=False)
                    return await self.trash_repo.restore_folder(folder_id, new_name)
    
            try:
                restored = await with_db_retry(_perform_operation)
            except DuplicateRecordError:
                raise DuplicateRecordError("Name collision during restore; please retry.")
            except (InvalidOperationError, InfrastructureError):
                raise DuplicateRecordError("Deadlock during restore; please retry.")
    
            if not restored:
                raise InfrastructureError("Failed to restore folder.")
    
            await self._recalculate_user_storage(current_user["id"])
            return self._as_folder_response(restored)

    async def get_trashed_contents(
            self,
            current_user: dict[str, Any],
        ) -> schemas.StorageContentResponse:
            """Return trashed folders and files owned by the current user."""
            owner_id = current_user["id"]
            folders_raw = await self.trash_repo.list_trashed_folders_by_owner(owner_id)
            files_raw = await self.trash_repo.list_trashed_files_by_owner(owner_id)
    
            return schemas.StorageContentResponse(
                folders=[self._as_folder_response(f) for f in folders_raw],
                files=[self._as_file_response(f) for f in files_raw],
            )
