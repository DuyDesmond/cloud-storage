from __future__ import annotations

import asyncio
import random
import hashlib
import io
import secrets
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import aioboto3
from contextlib import asynccontextmanager
from botocore.exceptions import ClientError
from fastapi import Depends, UploadFile, Request, Header, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.object_bucket import R2StorageGateway
from app.core.hash_reader import HashReader
from app.core.security import hash_password
from app.modules.files import schemas
from app.modules.files.repository import FileOperationsRepository
from app.core.exceptions import DomainError, ItemNotFoundError, QuotaExceededError, DuplicateRecordError, AccessDeniedError, InvalidOperationError, InfrastructureError
import logging

logger = logging.getLogger(__name__)




def sanitize_filename(filename: str) -> str:
    cleaned = filename.replace("\\", "/").split("/")[-1]
    cleaned = "".join(c for c in cleaned if c.isprintable() and c not in '<>:"|?*')
    return cleaned.strip() or "unnamed_file"






class FileOperationsService:
    async def _handle_restored_name_collision(self, parent_id, owner_id, original_name, is_file: bool):
        await self.repo.call_lock_naming_scope(parent_id, owner_id)
        if is_file:
            new_name = await self.repo.resolve_restored_file_name(parent_id, owner_id, original_name)
        else:
            new_name = await self.repo.resolve_restored_folder_name(parent_id, owner_id, original_name)
            
        if new_name is None:
            raise InfrastructureError(f"Could not resolve a valid name for the restored {'file' if is_file else 'folder'}.")
        return new_name

    async def _handle_filename_collision(self, parent_folder_id, current_user_id, clean_name, on_collision):
        if on_collision == "keep_duplicate":
            return await self.repo.resolve_file_name_collision(
                parent_folder_id, current_user_id, clean_name
            )
        elif on_collision == "replace":
            existing = await self.repo.get_file_by_parent_and_name(
                parent_folder_id, clean_name, current_user_id
            )
            if existing:
                await self.repo.trash_file(existing["id"])
            return clean_name
        return clean_name

    async def _resolve_owner_id(self, parent_folder_id: uuid.UUID | None, current_user_id: uuid.UUID) -> uuid.UUID:
        if parent_folder_id:
            parent = await self.repo.get_folder_by_id(parent_folder_id)
            if parent:
                return parent["owner_id"]
        return current_user_id

    async def _check_storage_available(self, owner_id, size: int) -> bool:
        return await self.repo.check_storage_available(owner_id, size)

    async def _recalculate_user_storage(self, owner_id) -> None:
        await self.repo.update_user_storage_usage(owner_id)

    async def _get_user_storage_quota(self, owner_id) -> dict:
        return await self.repo.get_user_storage_quota(owner_id)

    def __init__(
        self,
        repo: FileOperationsRepository = Depends(),
        storage: R2StorageGateway = Depends(),
        x_share_password: str | None = Header(default=None, alias="X-Share-Password"),
    ) -> None:
        self.repo = repo
        self.storage = storage
        self.provided_password = x_share_password

    async def request_presigned_upload(
        self,
        current_user: dict[str, Any],
        payload: schemas.PresignedUploadRequest,
    ) -> schemas.PresignedUploadResponse:
        await self._require_parent_access(payload.parent_folder_id, current_user["id"])
        if payload.size_bytes > 0:
            has_space = await self._check_storage_available(current_user["id"], payload.size_bytes)
            if not has_space:
                raise QuotaExceededError("Storage quota exceeded.",)

        clean_name = sanitize_filename(payload.file_name)
        storage_key = f"storage/{current_user['id']}/{uuid.uuid4()}/{clean_name}"

        expires_in = 600
        presign_metadata: dict[str, str] | None = None
        headers: dict[str, str] = {}
        if payload.mime_type:
            headers["Content-Type"] = payload.mime_type
        if payload.content_hash:
            # include a metadata key for the client's checksum so the object store
            # will have it available for later verification
            presign_metadata = {"sha256": payload.content_hash}
            # browsers send metadata as `x-amz-meta-<key>`; instruct client to include it
            headers["x-amz-meta-sha256"] = payload.content_hash

        url = await self.storage.generate_presigned_put_url(
            object_name=storage_key,
            expires_in=expires_in,
            content_type=payload.mime_type,
            metadata=presign_metadata,
        )

        return schemas.PresignedUploadResponse(
            presigned_url=url,
            storage_key=storage_key,
            expires_in=expires_in,
            headers=headers,
        )

    async def complete_direct_upload(
        self,
        current_user: dict[str, Any],
        payload: schemas.CompleteUploadRequest,
    ) -> schemas.FileResponse:
        await self._require_parent_access(payload.parent_folder_id, current_user["id"])
        owner_id = await self._resolve_owner_id(payload.parent_folder_id, current_user["id"])

        user_prefix = f"storage/{current_user['id']}/"
        if not payload.storage_key.startswith(user_prefix):
            raise AccessDeniedError("Invalid storage key for current user.",)

        head = await self.storage.head_object(payload.storage_key)
        if head is None:
            raise InfrastructureError("Uploaded storage object not found.",)

        # Enforce quota check before committing to DB
        actual_size = payload.size_bytes
        if head and "ContentLength" in head and head["ContentLength"] > 0:
            actual_size = head["ContentLength"]

        has_space = await self._check_storage_available(current_user["id"], actual_size)
        if not has_space:
            await self.storage.delete_object(payload.storage_key)
            raise QuotaExceededError("Storage quota exceeded.",)

        # If client supplied a checksum, validate against object metadata or ETag
        if payload.content_hash:
            metadata = (head.get("Metadata") or {})
            head_etag = head.get("ETag") or head.get("ETag")
            normalized_etag = head_etag.strip('"') if head_etag else None
            if metadata.get("sha256"):
                if metadata.get("sha256") != payload.content_hash:
                    await self.storage.delete_object(payload.storage_key)
                    raise InfrastructureError("Checksum mismatch for uploaded object.")
            elif normalized_etag:
                if normalized_etag != payload.content_hash:
                    await self.storage.delete_object(payload.storage_key)
                    raise InfrastructureError("Checksum mismatch for uploaded object.")
            else:
                # No checksum available from storage to validate against
                await self.storage.delete_object(payload.storage_key)
                raise InfrastructureError("Unable to validate checksum for uploaded object.")

        clean_name = sanitize_filename(payload.file_name)

        async def _do_create():
            await self.repo.call_lock_naming_scope(payload.parent_folder_id, current_user["id"])

            final_name = clean_name
            if await self.repo.file_exists_by_name(
                payload.parent_folder_id,
                current_user["id"],
                clean_name,
            ):
                final_name = await self.repo.resolve_file_name_collision(
                    payload.parent_folder_id,
                    current_user["id"],
                    clean_name,
                )

            file_id = uuid.uuid4()
            row = await self.repo.create_file(
                file_id=file_id,
                owner_id=current_user["id"],
                parent_folder_id=payload.parent_folder_id,
                storage_key=payload.storage_key,
                file_name=final_name,
                size_bytes=payload.size_bytes,
                mime_type=payload.mime_type,
                content_hash=payload.content_hash,
            )
            return row

        row = await self._with_db_retry(_do_create)
        await self._recalculate_user_storage(current_user["id"])
        return self._as_file_response(row)

    async def initiate_multipart_upload(
        self,
        current_user: dict[str, Any],
        payload: schemas.InitiateMultipartUploadRequest,
    ) -> schemas.InitiateMultipartUploadResponse:
        await self._require_parent_access(payload.parent_folder_id, current_user["id"])
        if payload.size_bytes > 0:
            has_space = await self._check_storage_available(current_user["id"], payload.size_bytes)
            if not has_space:
                raise QuotaExceededError("Storage quota exceeded.",)

        clean_name = sanitize_filename(payload.file_name)
        storage_key = f"storage/{current_user['id']}/{uuid.uuid4()}/{clean_name}"

        upload_id = await self.storage.create_multipart_upload(
            object_name=storage_key,
            content_type=payload.mime_type,
        )

        return schemas.InitiateMultipartUploadResponse(
            upload_id=upload_id,
            storage_key=storage_key,
            part_size=8 * 1024 * 1024,
        )

    async def presign_multipart_part(
        self,
        current_user: dict[str, Any],
        payload: schemas.PresignPartRequest,
    ) -> schemas.PresignPartResponse:
        user_prefix = f"storage/{current_user['id']}/"
        if not payload.storage_key.startswith(user_prefix):
            raise AccessDeniedError("Invalid storage key for current user.",)

        url = await self.storage.generate_presigned_part_url(
            object_name=payload.storage_key,
            upload_id=payload.upload_id,
            part_number=payload.part_number,
            expires_in=600,
        )

        return schemas.PresignPartResponse(
            presigned_url=url,
            part_number=payload.part_number,
        )

    async def complete_multipart_upload(
        self,
        current_user: dict[str, Any],
        payload: schemas.CompleteMultipartUploadRequest,
    ) -> schemas.FileResponse:
        await self._require_parent_access(payload.parent_folder_id, current_user["id"])
        user_prefix = f"storage/{current_user['id']}/"
        if not payload.storage_key.startswith(user_prefix):
            raise AccessDeniedError("Invalid storage key for current user.",)

        if payload.size_bytes > 0:
            has_space = await self._check_storage_available(current_user["id"], payload.size_bytes)
            if not has_space:
                await self.storage.abort_multipart_upload(
                    object_name=payload.storage_key,
                    upload_id=payload.upload_id,
                )
                await self.storage.delete_object(payload.storage_key)
                raise QuotaExceededError("Storage quota exceeded.",)

        parts_formatted = []
        for p in payload.parts:
            etag = p.etag
            if etag:
                etag = etag.strip('"').strip("'")
            parts_formatted.append({"PartNumber": p.part_number, "ETag": etag})

        await self.storage.complete_multipart_upload(
            object_name=payload.storage_key,
            upload_id=payload.upload_id,
            parts=parts_formatted,
        )

        clean_name = sanitize_filename(payload.file_name)

        async def _do_create():
            await self.repo.call_lock_naming_scope(payload.parent_folder_id, current_user["id"])

            final_name = clean_name
            if await self.repo.file_exists_by_name(
                payload.parent_folder_id,
                current_user["id"],
                clean_name,
            ):
                final_name = await self.repo.resolve_file_name_collision(
                    payload.parent_folder_id,
                    current_user["id"],
                    clean_name,
                )

            file_id = uuid.uuid4()
            row = await self.repo.create_file(
                file_id=file_id,
                owner_id=current_user["id"],
                parent_folder_id=payload.parent_folder_id,
                storage_key=payload.storage_key,
                file_name=final_name,
                size_bytes=payload.size_bytes,
                mime_type=payload.mime_type,
                content_hash=payload.content_hash,
            )
            return row

        row = await self._with_db_retry(_do_create)
        await self._recalculate_user_storage(current_user["id"])
        return self._as_file_response(row)

    async def abort_multipart_upload(
        self,
        current_user: dict[str, Any],
        payload: schemas.AbortMultipartUploadRequest,
    ) -> schemas.MessageResponse:
        user_prefix = f"storage/{current_user['id']}/"
        if not payload.storage_key.startswith(user_prefix):
            raise AccessDeniedError("Invalid storage key for current user.",)

        await self.storage.abort_multipart_upload(
            object_name=payload.storage_key,
            upload_id=payload.upload_id,
        )

        return schemas.MessageResponse(message="Multipart upload aborted successfully.")

    async def _with_db_retry(self, fn, max_attempts: int = 3, base_delay: float = 0.1):
        attempt = 1
        while True:
            try:
                return await fn()
            except (DuplicateRecordError, InvalidOperationError, InfrastructureError):
                if attempt >= max_attempts:
                    raise
                delay = base_delay * (2 ** (attempt - 1)) * (1 + random.random())
                await asyncio.sleep(delay)
                attempt += 1

    @staticmethod
    def _as_file_response(row: dict[str, Any]) -> schemas.FileResponse:
        return schemas.FileResponse(**row)

    @staticmethod
    def _as_folder_response(row: dict[str, Any]) -> schemas.FolderResponse:
        return schemas.FolderResponse(**row)

    @staticmethod
    def _as_share_response(row: dict[str, Any]) -> schemas.ShareResponse:
        return schemas.ShareResponse(**row)

    @staticmethod
    def _require_owner(item: dict[str, Any], current_user_id: uuid.UUID) -> None:
        if item["owner_id"] != current_user_id:
            raise AccessDeniedError("Owner access required.")

    @staticmethod
    def _require_target_live(item: dict[str, Any]) -> None:
        if item["is_trashed"]:
            raise InfrastructureError("Target is trashed.")

    async def _require_edit_access(
        self,
        *,
        target_type: Literal["file", "folder"],
        target_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> None:
        is_file = target_type == "file"
        path = await (self.repo.get_path_for_file(target_id) if is_file else self.repo.get_path_for_folder(target_id))
        if not path:
            raise ItemNotFoundError("Target not found.")
        owner_row = await (self.repo.get_owner_and_trashed_for_file(target_id) if is_file else self.repo.get_owner_and_trashed_for_folder(target_id))
        if not owner_row:
            raise ItemNotFoundError("Target not found.")

        if owner_row["owner_id"] == current_user_id:
            if owner_row["is_trashed"]:
                raise InfrastructureError("Target is trashed.")
            return

        acl = await self.repo.get_effective_acl(path, is_file, target_id, current_user_id)
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
            collision = await self.repo.folder_exists_by_name(payload.parent_folder_id, owner_id, clean_name)
            if collision:
                raise DuplicateRecordError("A folder with that name already exists. Resubmit with on_collision set to 'replace', 'keep_duplicate', or 'merge'.")

        async def _perform_operation():
            async with self.repo.conn.transaction():
                await self.repo.call_lock_naming_scope(payload.parent_folder_id, current_user["id"])
                
                final_name = clean_name
                if on_col == "keep_duplicate":
                    counter = 1
                    while await self.repo.folder_exists_by_name(payload.parent_folder_id, owner_id, final_name):
                        final_name = f"{clean_name} ({counter})"
                        counter += 1
                elif on_col in ("replace", "merge"):
                    existing = await self.repo.get_folder_by_parent_and_name(
                        payload.parent_folder_id, clean_name, owner_id
                    )
                    if existing:
                        if on_col == "merge":
                            return existing
                        else:  # replace
                            await self.repo.trash_folder(existing["id"])

                return await self.repo.create_folder(
                    owner_id,
                    payload.parent_folder_id,
                    final_name,
                )

        try:
            row = await self._with_db_retry(_perform_operation)
        except DuplicateRecordError:
            raise DuplicateRecordError("Folder name already exists.")

        return self._as_folder_response(row)

    async def upload_file(
        self,
        current_user: dict[str, Any],
        parent_folder_id: uuid.UUID | None,
        upload_file: UploadFile,
        on_collision: Literal["replace", "keep_duplicate"] | None = "keep_duplicate",
    ) -> schemas.FileResponse:
        await self._require_parent_access(parent_folder_id, current_user["id"])
        owner_id = await self._resolve_owner_id(parent_folder_id, current_user["id"])

        clean_name = sanitize_filename(upload_file.filename or "untitled")

        if on_collision is None:
            collision = await self.repo.file_exists_by_name(parent_folder_id, owner_id, clean_name)
            if collision:
                raise DuplicateRecordError("A file with that name already exists. Resubmit with on_collision set to "
                    "'replace' (overwrite) or 'keep_duplicate' (add a suffix).",
                )

        # Stream upload without loading the entire file into memory.
        file_obj = upload_file.file
        try:
            file_obj.seek(0)
        except Exception as e:
            logger.warning(f"Failed to seek file object: {e}")


        file_id = uuid.uuid4()
        storage_key = f"storage/{current_user['id']}/{file_id}/{clean_name}"
        reader = HashReader(file_obj)

        extra_args: dict[str, str] = {}
        if upload_file.content_type:
            extra_args["ContentType"] = upload_file.content_type

        try:
            await asyncio.to_thread(
                self.storage._get_client().upload_fileobj,
                Fileobj=reader,
                Bucket=self.storage.bucket_name,
                Key=storage_key,
                ExtraArgs=extra_args if extra_args else None,
            )
        except ClientError as exc:  # pragma: no cover - external storage failure
            raise InfrastructureError("File storage upload failed.")
        except DomainError:
            raise
        except Exception as exc:  # pragma: no cover
            raise InfrastructureError("File storage upload failed.")

        content_hash = reader.hexdigest() if reader.size > 0 else None

        has_space = await self._check_storage_available(current_user["id"], reader.size)
        if not has_space:
            await self.storage.delete_object(storage_key)
            raise QuotaExceededError("Storage quota exceeded.",)

        async def _perform_operation():
            async with self.repo.conn.transaction():
                await self.repo.call_lock_naming_scope(parent_folder_id, current_user["id"])

                final_name = await self._handle_filename_collision(parent_folder_id, owner_id, clean_name, on_collision)

                return await self.repo.create_file(
                    file_id,
                    owner_id,
                    parent_folder_id,
                    storage_key,
                    final_name,
                    reader.size,
                    upload_file.content_type,
                    content_hash,
                )

        try:
            row = await self._with_db_retry(_perform_operation)
        except DuplicateRecordError:
            await self.storage.delete_object(storage_key)
            raise DuplicateRecordError("A file with that name already exists. Resubmit with on_collision set to "
                "'replace' or 'keep_duplicate'.",)
        except QuotaExceededError:
            await self.storage.delete_object(storage_key)
            raise QuotaExceededError("Storage quota exceeded.",)
        except Exception:
            await self.storage.delete_object(storage_key)
            raise

        await self._recalculate_user_storage(current_user["id"])
        return self._as_file_response(row)

    async def move_folder(
        self,
        current_user: dict[str, Any],
        folder_id: uuid.UUID,
        payload: schemas.FolderMoveRequest,
    ) -> schemas.FolderResponse:
        folder = await self.repo.get_folder_by_id(folder_id)
        if not folder:
            raise ItemNotFoundError("Folder not found.")
        self._require_owner(folder, current_user["id"])
        self._require_target_live(folder)
        await self._require_parent_access(payload.parent_folder_id, current_user["id"])

        if payload.parent_folder_id == folder_id:
            raise InfrastructureError("Folder cannot be moved into itself.")

        folder_name = folder["folder_name"]

        async def _perform_operation():
            async with self.repo.conn.transaction():
                await self.repo.move_folder(
                    folder_id,
                    payload.parent_folder_id,
                    on_collision=payload.on_collision,
                    file_mode=payload.file_mode,
                    file_decisions=payload.file_decisions,
                )
                row = await self.repo.get_folder_by_id(folder_id)
                if row is None:
                    row = await self.repo.get_folder_by_parent_and_name(
                        payload.parent_folder_id, folder_name, current_user["id"]
                    )
                return row

        try:
            row = await self._with_db_retry(_perform_operation)
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
        file_row = await self.repo.get_file_by_id(file_id)
        if not file_row:
            raise ItemNotFoundError("File not found.")
        self._require_owner(file_row, current_user["id"])
        self._require_target_live(file_row)
        await self._require_parent_access(payload.parent_folder_id, current_user["id"])

        async def _perform_operation():
            async with self.repo.conn.transaction():
                await self.repo.move_file(
                    file_id, payload.parent_folder_id, on_collision=payload.on_collision
                )
                return await self.repo.get_file_by_id(file_id)

        try:
            row = await self._with_db_retry(_perform_operation)
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
        folder = await self.repo.get_folder_by_id(folder_id)
        if not folder:
            raise ItemNotFoundError("Folder not found.")
        self._require_owner(folder, current_user["id"])
        if folder["is_trashed"]:
            return schemas.MessageResponse(message="Folder already in trash.")

        row = await self.repo.trash_folder(folder_id)
        if not row:
            raise ItemNotFoundError("Folder not found.")
        await self._recalculate_user_storage(current_user["id"])
        return schemas.MessageResponse(message="Folder moved to trash.")

    async def restore_folder(
        self,
        current_user: dict[str, Any],
        folder_id: uuid.UUID,
    ) -> schemas.FolderResponse:
        folder = await self.repo.get_folder_by_id(folder_id)
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
            trashed_size = await self.repo.get_folder_trashed_size(folder_path)
            if trashed_size > 0:
                has_space = await self._check_storage_available(current_user["id"], trashed_size)
                if not has_space:
                    raise QuotaExceededError("Storage quota exceeded.",)

        async def _perform_operation():
            async with self.repo.conn.transaction():
                new_name = await self._handle_restored_name_collision(parent_id, owner_id, folder_name, is_file=False)
                return await self.repo.restore_folder(folder_id, new_name)

        try:
            restored = await self._with_db_retry(_perform_operation)
        except DuplicateRecordError:
            raise DuplicateRecordError("Name collision during restore; please retry.")
        except InvalidOperationError, InfrastructureError:
            raise DuplicateRecordError("Deadlock during restore; please retry.")

        if not restored:
            raise InfrastructureError("Failed to restore folder.")

        await self._recalculate_user_storage(current_user["id"])
        return self._as_folder_response(restored)

    async def delete_file(
        self,
        current_user: dict[str, Any],
        file_id: uuid.UUID,
    ) -> schemas.MessageResponse:
        file_row = await self.repo.get_file_by_id(file_id)
        if not file_row:
            raise ItemNotFoundError("File not found.")
        self._require_owner(file_row, current_user["id"])
        if file_row["is_trashed"]:
            return schemas.MessageResponse(message="File already in trash.")

        row = await self.repo.trash_file(file_id)
        if not row:
            raise ItemNotFoundError("File not found.")
        await self._recalculate_user_storage(current_user["id"])
        return schemas.MessageResponse(message="File moved to trash.")

    async def restore_file(
        self,
        current_user: dict[str, Any],
        file_id: uuid.UUID,
    ) -> schemas.FileResponse:
        file_row = await self.repo.get_file_by_id(file_id)
        if not file_row:
            raise ItemNotFoundError("File not found.")
        self._require_owner(file_row, current_user["id"])
        if not file_row["is_trashed"]:
            return self._as_file_response(file_row)

        file_size = file_row.get("size_bytes", 0)
        if file_size > 0:
            has_space = await self._check_storage_available(current_user["id"], file_size)
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
            async with self.repo.conn.transaction():
                new_name = await self._handle_restored_name_collision(parent_id, owner_id, file_name, is_file=True)
                return await self.repo.restore_file(file_id, new_name)

        try:
            restored = await self._with_db_retry(_perform_operation)
        except DuplicateRecordError:
            raise DuplicateRecordError("Name collision during restore; please retry.")
        except InvalidOperationError, InfrastructureError:
            raise DuplicateRecordError("Deadlock during restore; please retry.")

        if not restored:
            raise InfrastructureError("Failed to restore file.")

        await self._recalculate_user_storage(current_user["id"])
        return self._as_file_response(restored)


    async def hard_delete_file(
        self,
        current_user: dict[str, Any],
        file_id: uuid.UUID,
    ) -> schemas.MessageResponse:
        file_row = await self.repo.get_file_by_id(file_id)
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
            async with self.repo.conn.transaction():
                deleted = await self.repo.delete_file_by_id(file_id)
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
        folder = await self.repo.get_folder_by_id(folder_id)
        if not folder:
            raise ItemNotFoundError("Folder not found.")
        self._require_owner(folder, current_user["id"])
        if not folder["is_trashed"]:
            raise InfrastructureError("Folder is not in trash.")

        folder_path = folder.get("path")
        # gather files under this path
        files = await self.repo.list_files_under_path(folder_path)

        # Attempt to delete each object's blob synchronously with retries. If any fail, abort and return error.
        for f in files:
            storage_key = f.get("storage_key")
            if not storage_key:
                continue
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
                raise InfrastructureError(f"Failed to delete object {storage_key}; please try again later.")

        # All object deletions succeeded (or no storage_key). Delete folder rows and files under path atomically.
        try:
            async with self.repo.conn.transaction():
                await self.repo.delete_files_under_path(folder_path)
                await self.repo.delete_folders_under_path(folder_path)
        except Exception as exc:
            raise InfrastructureError("Failed to delete folder rows.")

        await self._recalculate_user_storage(current_user["id"])
        return schemas.MessageResponse(message="Folder and contents permanently deleted.")

    async def hard_delete_all_trash(
        self,
        current_user: dict[str, Any],
    ) -> schemas.MessageResponse:
        owner_id = current_user["id"]
        files = await self.repo.list_trashed_files_by_owner(owner_id)

        for f in files:
            storage_key = f.get("storage_key")
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
                    # stop and return error; do not remove DB rows for failed objects
                    raise InfrastructureError(f"Failed to delete object {storage_key}; please try again later.")

            # delete DB row for this file
            try:
                async with self.repo.conn.transaction():
                    await self.repo.delete_file_by_id(f["id"])
            except Exception:
                pass

        # Remove trashed folder rows
        async with self.repo.conn.transaction():
            await self.repo.delete_trashed_folders_by_owner(owner_id)

        await self._recalculate_user_storage(owner_id)
        return schemas.MessageResponse(message="Trash emptied (permanently deleted).")

    async def _require_view_access(
        self,
        *,
        target_type: Literal["file", "folder"],
        target_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> None:
        is_file = target_type == "file"
        path = await (self.repo.get_path_for_file(target_id) if is_file else self.repo.get_path_for_folder(target_id))
        if not path:
            raise ItemNotFoundError("Target not found.")
        owner_row = await (self.repo.get_owner_and_trashed_for_file(target_id) if is_file else self.repo.get_owner_and_trashed_for_folder(target_id))
        if not owner_row:
            raise ItemNotFoundError("Target not found.")

        if owner_row["owner_id"] == current_user_id:
            if owner_row["is_trashed"]:
                raise InfrastructureError("Target is trashed.")
            return

        acl = await self.repo.get_effective_acl(path, is_file, target_id, current_user_id)
        if not acl or not acl.get("permission"):
            raise AccessDeniedError("View permission required.")

        permission = acl["permission"]
        password_hash = acl.get("password_hash")
        
        if password_hash:
            if not self.provided_password:
                raise AccessDeniedError("PASSWORD_REQUIRED")
            if hash_password(self.provided_password) != password_hash:
                raise AccessDeniedError("INVALID_PASSWORD")

    async def download_file_stream(
        self,
        current_user: dict[str, Any],
        file_id: uuid.UUID,
        range_header: str | None = None,
    ) -> StreamingResponse:
        file_row = await self.repo.get_file_by_id(file_id)
        if not file_row:
            raise ItemNotFoundError("File not found.")
        await self._require_view_access(target_type="file", target_id=file_id, current_user_id=current_user["id"])

        # Fetch headers via head_object first to build StreamingResponse headers
        head_res = await self.storage.head_object(file_row["storage_key"])
        if not head_res:
            raise ItemNotFoundError("Object not found in storage.")

        headers: dict[str, str] = {}
        if "ContentLength" in head_res:
            headers["Content-Length"] = str(head_res["ContentLength"])
        
        status_code = status.HTTP_200_OK
        if range_header:
            headers["Content-Range"] = head_res.get("ContentRange") or head_res.get("Content-Range") or ""
            status_code = status.HTTP_206_PARTIAL_CONTENT
            
        media_type = head_res.get("ContentType") or file_row.get("mime_type") or "application/octet-stream"
        headers["Accept-Ranges"] = "bytes"
        headers["Content-Disposition"] = f'attachment; filename="{file_row.get("file_name")}"'

        async def stream_generator():
            async with self.storage._get_client() as client:
                params = {"Bucket": self.storage.bucket_name, "Key": file_row["storage_key"]}
                if range_header:
                    params["Range"] = range_header
                try:
                    response = await client.get_object(**params)
                    async for chunk in response["Body"]:
                        yield chunk
                except Exception:
                    pass

        return StreamingResponse(stream_generator(), status_code=status_code, media_type=media_type, headers=headers)

    async def get_storage_usage(
        self,
        current_user: dict[str, Any],
    ) -> schemas.StorageUsageResponse:
        used = await self.repo.get_storage_usage(current_user["id"])
        quota_row = await self._get_user_storage_quota(current_user["id"])
        total = quota_row["storage_quota"] if quota_row else getattr(settings, "STORAGE_QUOTA_BYTES", 20 * 1024 ** 3)
        return schemas.StorageUsageResponse(used_bytes=used, total_bytes=total)


    async def get_storage_contents(
        self,
        current_user: dict[str, Any],
        parent_folder_id: uuid.UUID | None = None,
    ) -> schemas.StorageContentResponse:
        if parent_folder_id:
            await self._require_view_access(
                target_type="folder", target_id=parent_folder_id, current_user_id=current_user["id"]
            )

        folders_raw = await self.repo.list_user_folders(current_user["id"], parent_folder_id)
        files_raw = await self.repo.list_user_files(current_user["id"], parent_folder_id)

        return schemas.StorageContentResponse(
            folders=[self._as_folder_response(f) for f in folders_raw],
            files=[self._as_file_response(f) for f in files_raw],
        )

    async def get_trashed_contents(
        self,
        current_user: dict[str, Any],
    ) -> schemas.StorageContentResponse:
        """Return trashed folders and files owned by the current user."""
        owner_id = current_user["id"]
        folders_raw = await self.repo.list_trashed_folders_by_owner(owner_id)
        files_raw = await self.repo.list_trashed_files_by_owner(owner_id)

        return schemas.StorageContentResponse(
            folders=[self._as_folder_response(f) for f in folders_raw],
            files=[self._as_file_response(f) for f in files_raw],
        )

    async def get_shared_with_me_contents(
        self,
        current_user: dict[str, Any],
    ) -> schemas.StorageContentResponse:
        owner_id = current_user["id"]
        folders_raw = await self.repo.list_shared_with_me_folders(owner_id)
        files_raw = await self.repo.list_shared_with_me_files(owner_id)
        
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
    ) -> list[dict[str, str]]:
        path_str = await (self.repo.get_path_for_file(target_id) if is_file else self.repo.get_path_for_folder(target_id))
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
            
        folders = await self.repo.get_folders_by_ids(uuids)
        folder_dict = {f["id"]: f["folder_name"] for f in folders}
        
        result = []
        for u in uuids:
            if u in folder_dict:
                result.append({"id": str(u), "name": folder_dict[u]})
        return result