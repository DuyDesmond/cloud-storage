from typing import Any
from fastapi import Depends
import uuid
import asyncio
from app.core.exceptions import ItemNotFoundError, InvalidOperationError, DuplicateRecordError, InfrastructureError, QuotaExceededError
from app.modules.files import schemas
from app.modules.files.utils.sanitization import sanitize_filename
from app.modules.files.utils.db_retry import with_db_retry
from app.core.object_bucket import StorageGateway, R2StorageGateway
from app.core.hash_reader import HashReader
from app.modules.files.repositories import FileQueryRepository, StorageQuotaRepository, TrashRepository, FileManagementRepository
from .base import BaseFileService

class FileUploadService(BaseFileService):
    def __init__(
        self,
        query_repo: FileQueryRepository = Depends(FileQueryRepository),
        quota_repo: StorageQuotaRepository = Depends(StorageQuotaRepository),
        trash_repo: TrashRepository = Depends(TrashRepository),
        management_repo: FileManagementRepository = Depends(FileManagementRepository),
        storage: StorageGateway = Depends(R2StorageGateway),
    ):
        super().__init__(query_repo, quota_repo, trash_repo, management_repo, storage)

    async def request_presigned_upload(
            self,
            current_user: dict[str, Any],
            payload: schemas.PresignedUploadRequest,
        ) -> schemas.PresignedUploadResponse:
            await self._require_parent_access(payload.parent_folder_id, current_user["id"])
            if payload.size_bytes > 0:
                has_space = await self.quota_repo.check_storage_available(current_user["id"], payload.size_bytes)
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
    
            has_space = await self.quota_repo.check_storage_available(current_user["id"], actual_size)
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
                await self.management_repo.call_lock_naming_scope(payload.parent_folder_id, current_user["id"])
    
                final_name = clean_name
                if await self.query_repo.file_exists_by_name(
                    payload.parent_folder_id,
                    current_user["id"],
                    clean_name,
                ):
                    final_name = await self.management_repo.resolve_file_name_collision(
                        payload.parent_folder_id,
                        current_user["id"],
                        clean_name,
                    )
    
                file_id = uuid.uuid4()
                row = await self.management_repo.create_file(
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
    
            row = await with_db_retry(_do_create)
            await self._recalculate_user_storage(current_user["id"])
            return self._as_file_response(row)

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
                collision = await self.query_repo.file_exists_by_name(parent_folder_id, owner_id, clean_name)
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
    
            has_space = await self.quota_repo.check_storage_available(current_user["id"], reader.size)
            if not has_space:
                await self.storage.delete_object(storage_key)
                raise QuotaExceededError("Storage quota exceeded.",)
    
            async def _perform_operation():
                async with self.management_repo.conn.transaction():
                    await self.management_repo.call_lock_naming_scope(parent_folder_id, current_user["id"])
    
                    final_name = await self._handle_filename_collision(parent_folder_id, owner_id, clean_name, on_collision)
    
                    return await self.management_repo.create_file(
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
                row = await with_db_retry(_perform_operation)
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

    async def initiate_multipart_upload(
            self,
            current_user: dict[str, Any],
            payload: schemas.InitiateMultipartUploadRequest,
        ) -> schemas.InitiateMultipartUploadResponse:
            await self._require_parent_access(payload.parent_folder_id, current_user["id"])
            if payload.size_bytes > 0:
                has_space = await self.quota_repo.check_storage_available(current_user["id"], payload.size_bytes)
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
                has_space = await self.quota_repo.check_storage_available(current_user["id"], payload.size_bytes)
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
                await self.management_repo.call_lock_naming_scope(payload.parent_folder_id, current_user["id"])
    
                final_name = clean_name
                if await self.query_repo.file_exists_by_name(
                    payload.parent_folder_id,
                    current_user["id"],
                    clean_name,
                ):
                    final_name = await self.management_repo.resolve_file_name_collision(
                        payload.parent_folder_id,
                        current_user["id"],
                        clean_name,
                    )
    
                file_id = uuid.uuid4()
                row = await self.management_repo.create_file(
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
    
            row = await with_db_retry(_do_create)
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

    async def download_file_stream(
            self,
            current_user: dict[str, Any],
            file_id: uuid.UUID,
            range_header: str | None = None,
        ) -> StreamingResponse:
            file_row = await self.query_repo.get_file_by_id(file_id)
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
