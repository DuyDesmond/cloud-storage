from app.core.exceptions import ItemNotFoundError
from app.core.security import hash_password
from typing import Any, Literal
import uuid
from app.core.exceptions import AccessDeniedError, InfrastructureError
from app.modules.files.repositories import FileQueryRepository, StorageQuotaRepository, TrashRepository, FileManagementRepository
from app.core.object_bucket import StorageGateway

class BaseFileService:
    def __init__(
        self,
        query_repo: FileQueryRepository,
        quota_repo: StorageQuotaRepository,
        trash_repo: TrashRepository,
        management_repo: FileManagementRepository,
        storage: StorageGateway,
    ):
        self.query_repo = query_repo
        self.quota_repo = quota_repo
        self.trash_repo = trash_repo
        self.management_repo = management_repo
        self.storage = storage

    @staticmethod
    def _as_file_response(row: dict[str, Any]):
        from app.modules.files import schemas
        return schemas.FileResponse(**row)

    @staticmethod
    def _as_folder_response(row: dict[str, Any]):
        from app.modules.files import schemas
        return schemas.FolderResponse(**row)

    @staticmethod
    def _require_owner(item: dict[str, Any], current_user_id: uuid.UUID) -> None:
        if item["owner_id"] != current_user_id:
            raise AccessDeniedError("Owner access required.")

    @staticmethod
    def _require_target_live(item: dict[str, Any]) -> None:
        if item["is_trashed"]:
            raise InfrastructureError("Target is trashed.")

    async def _resolve_owner_id(self, parent_folder_id: uuid.UUID | None, current_user_id: uuid.UUID) -> uuid.UUID:
            if parent_folder_id:
                parent = await self.query_repo.get_folder_by_id(parent_folder_id)
                if parent:
                    return parent["owner_id"]
            return current_user_id

    async def _require_edit_access(
            self,
            *,
            target_type: Literal["file", "folder"],
            target_id: uuid.UUID,
            current_user_id: uuid.UUID,
        ) -> None:
            is_file = target_type == "file"
            path = await (self.query_repo.get_path_for_file(target_id) if is_file else self.query_repo.get_path_for_folder(target_id))
            if not path:
                raise ItemNotFoundError("Target not found.")
            owner_row = await (self.query_repo.get_owner_and_trashed_for_file(target_id) if is_file else self.query_repo.get_owner_and_trashed_for_folder(target_id))
            if not owner_row:
                raise ItemNotFoundError("Target not found.")
    
            if owner_row["owner_id"] == current_user_id:
                if owner_row["is_trashed"]:
                    raise InfrastructureError("Target is trashed.")
                return
    
            acl = await self.query_repo.get_effective_acl(path, is_file, target_id, current_user_id)
            if not acl or not acl.get("permission"):
                raise AccessDeniedError("Access denied.")
                
            permission = acl["permission"]
            password_hash = acl.get("password_hash")
            
            # Validate password if required
            if password_hash:
                if not self.provided_password:
                    raise AccessDeniedError("PASSWORD_REQUIRED")
                if hash_password(self.provided_password) != password_hash:
                    raise AccessDeniedError("INVALID_PASSWORD")
    
            if permission != "edit":
                raise AccessDeniedError("Edit access required.")

    async def _require_parent_access(
            self,
            parent_folder_id: uuid.UUID | None,
            current_user_id: uuid.UUID,
        ) -> None:
            if parent_folder_id is None:
                return
            await self._require_edit_access(
                target_type="folder",
                target_id=parent_folder_id,
                current_user_id=current_user_id,
            )

    async def _require_view_access(
            self,
            *,
            target_type: Literal["file", "folder"],
            target_id: uuid.UUID,
            current_user_id: uuid.UUID | None,
        ) -> None:
            is_file = target_type == "file"
            path = await (self.query_repo.get_path_for_file(target_id) if is_file else self.query_repo.get_path_for_folder(target_id))
            if not path:
                raise ItemNotFoundError("Target not found.")
            owner_row = await (self.query_repo.get_owner_and_trashed_for_file(target_id) if is_file else self.query_repo.get_owner_and_trashed_for_folder(target_id))
            if not owner_row:
                raise ItemNotFoundError("Target not found.")
    
            if current_user_id and owner_row["owner_id"] == current_user_id:
                if owner_row["is_trashed"]:
                    raise InfrastructureError("Target is trashed.")
                return
    
            acl = await self.query_repo.get_effective_acl(path, is_file, target_id, current_user_id)
            if not acl or not acl.get("permission"):
                raise AccessDeniedError("View permission required.")
    
            permission = acl["permission"]
            password_hash = acl.get("password_hash")
            
            if password_hash:
                if not self.provided_password:
                    raise AccessDeniedError("PASSWORD_REQUIRED")
                if hash_password(self.provided_password) != password_hash:
                    raise AccessDeniedError("INVALID_PASSWORD")

    async def _handle_filename_collision(self, parent_folder_id, current_user_id, clean_name, on_collision):
            if on_collision == "keep_duplicate":
                return await self.management_repo.resolve_file_name_collision(
                    parent_folder_id, current_user_id, clean_name
                )
            elif on_collision == "replace":
                existing = await self.query_repo.get_file_by_parent_and_name(
                    parent_folder_id, clean_name, current_user_id
                )
                if existing:
                    await self.trash_repo.trash_file(existing["id"])
                return clean_name
            return clean_name
        
    async def _recalculate_user_storage(self, owner_id) -> None:
            await self.quota_repo.update_user_storage_usage(owner_id)