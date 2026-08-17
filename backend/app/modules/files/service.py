from __future__ import annotations

import asyncio
import random
import hashlib
import io
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import asyncpg
import boto3
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig
from fastapi import Depends, HTTPException, UploadFile, status, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.security import hash_password
from app.modules.files import schemas
from app.modules.files.repository import FileOperationsRepository


class R2StorageGateway:
    
    def __init__(self) -> None:
        self.endpoint_url = getattr(settings, "R2_ENDPOINT_URL", None)
        self.access_key = getattr(settings, "R2_ACCESS_KEY_ID", None)
        self.secret_key = getattr(settings, "R2_SECRET_ACCESS_KEY", None)
        self.bucket_name = getattr(settings, "R2_BUCKET_NAME", None)
        self._client: Any | None = None
        self.config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,  # 8 MB: threshold to trigger multipart
            multipart_chunksize=16 * 1024 * 1024, # 16 MB: size of each uploaded chunk
            max_concurrency=10,                    # Number of simultaneous threads
            use_threads=False
        )

    def _get_client(self) -> Any:
        if not self.endpoint_url or not self.access_key or not self.secret_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cloudflare R2 storage is not configured.",
            )

        if self._client is None:
            self._client = boto3.client(
                service_name="s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name="auto",
            )

        return self._client

    async def upload_bytes(
        self,
        *,
        object_name: str,
        data: bytes,
        content_type: str | None,
    ) -> None:
        client = self._get_client()
        stream = io.BytesIO(data)
        
        extra_args: dict[str, str] = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            await asyncio.to_thread(
                client.upload_fileobj,
                Fileobj=stream,
                Bucket=self.bucket_name,
                Key=object_name,
                ExtraArgs=extra_args if extra_args else None,
            )
        except ClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to upload file to Cloudflare R2.",
            ) from exc

    async def delete_object(self, object_name: str) -> None:
        if not self.endpoint_url or not self.access_key or not self.secret_key:
            return
        
        client = self._get_client()
        try:
            await asyncio.to_thread(
                client.delete_object,
                Bucket=self.bucket_name,
                Key=object_name,
            )
        except ClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to delete object from Cloudflare R2.",
            ) from exc

    async def generate_presigned_put_url(
        self,
        *,
        object_name: str,
        expires_in: int = 3600,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Generate a presigned URL for PUT uploads (client performs HTTP PUT).

        Returns a URL string that the client can use to PUT the object directly
        to R2/MinIO.
        """
        client = self._get_client()
        params: dict[str, object] = {"Bucket": self.bucket_name, "Key": object_name}
        if content_type:
            params["ContentType"] = content_type
        if metadata:
            params["Metadata"] = metadata

        try:
            url = await asyncio.to_thread(
                client.generate_presigned_url,
                ClientMethod="put_object",
                Params=params,
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to generate presigned upload URL.",
            ) from exc

    async def generate_presigned_get_url(self, *, object_name: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for downloading an object (GET).

        Returns a URL string that the client can use to GET the object directly
        from R2/MinIO.
        """
        client = self._get_client()
        params = {"Bucket": self.bucket_name, "Key": object_name}
        try:
            url = await asyncio.to_thread(
                client.generate_presigned_url,
                ClientMethod="get_object",
                Params=params,
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to generate presigned download URL.",
            ) from exc

    async def generate_presigned_post(
        self,
        *,
        object_name: str,
        expires_in: int = 3600,
        content_type: str | None = None,
        max_file_size: int | None = None,
    ) -> dict[str, object]:
        """Generate a presigned POST for browser-style multipart/form uploads.

        Returns the dict returned by boto3's `generate_presigned_post` (url + fields).
        """
        client = self._get_client()
        fields: dict[str, str] = {"key": object_name}
        conditions: list[object] = []
        if content_type:
            # enforce content type in a condition
            conditions.append(["eq", "$Content-Type", content_type])
            fields["Content-Type"] = content_type
        if max_file_size is not None:
            conditions.append(["content-length-range", 0, max_file_size])

        try:
            result = await asyncio.to_thread(
                client.generate_presigned_post,
                Bucket=self.bucket_name,
                Key=object_name,
                Fields=fields if fields else None,
                Conditions=conditions if conditions else None,
                ExpiresIn=expires_in,
            )
            return result
        except ClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to generate presigned POST.",
            ) from exc

    async def head_object(self, object_name: str) -> dict[str, Any] | None:
        client = self._get_client()
        try:
            res = await asyncio.to_thread(
                client.head_object,
                Bucket=self.bucket_name,
                Key=object_name,
            )
            return res
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return None
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to verify storage object.",
            ) from exc

    async def create_multipart_upload(
        self,
        *,
        object_name: str,
        content_type: str | None = None,
    ) -> str:
        client = self._get_client()
        kwargs: dict[str, Any] = {"Bucket": self.bucket_name, "Key": object_name}
        if content_type:
            kwargs["ContentType"] = content_type
        try:
            res = await asyncio.to_thread(
                client.create_multipart_upload,
                **kwargs,
            )
            return res["UploadId"]
        except ClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to initiate multipart upload in storage.",
            ) from exc

    async def generate_presigned_part_url(
        self,
        *,
        object_name: str,
        upload_id: str,
        part_number: int,
        expires_in: int = 600,
    ) -> str:
        client = self._get_client()
        params = {
            "Bucket": self.bucket_name,
            "Key": object_name,
            "UploadId": upload_id,
            "PartNumber": part_number,
        }
        try:
            url = await asyncio.to_thread(
                client.generate_presigned_url,
                ClientMethod="upload_part",
                Params=params,
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to generate presigned URL for upload part.",
            ) from exc

    async def complete_multipart_upload(
        self,
        *,
        object_name: str,
        upload_id: str,
        parts: list[dict[str, Any]],
    ) -> None:
        client = self._get_client()
        try:
            await asyncio.to_thread(
                client.complete_multipart_upload,
                Bucket=self.bucket_name,
                Key=object_name,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
        except ClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to complete multipart upload in storage.",
            ) from exc

    async def abort_multipart_upload(
        self,
        *,
        object_name: str,
        upload_id: str,
    ) -> None:
        client = self._get_client()
        try:
            await asyncio.to_thread(
                client.abort_multipart_upload,
                Bucket=self.bucket_name,
                Key=object_name,
                UploadId=upload_id,
            )
        except ClientError:
            pass



def sanitize_filename(filename: str) -> str:
    cleaned = filename.replace("\\", "/").split("/")[-1]
    cleaned = "".join(c for c in cleaned if c.isprintable() and c not in '<>:"|?*')
    return cleaned.strip() or "unnamed_file"


class FileOperationsService:
    def __init__(
        self,
        repo: FileOperationsRepository = Depends(),
        storage: R2StorageGateway = Depends(),
    ) -> None:
        self.repo = repo
        self.storage = storage

    async def request_presigned_upload(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        payload: schemas.PresignedUploadRequest,
    ) -> schemas.PresignedUploadResponse:
        await self._require_parent_access(conn, payload.parent_folder_id, current_user["id"])
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
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        payload: schemas.CompleteUploadRequest,
    ) -> schemas.FileResponse:
        await self._require_parent_access(conn, payload.parent_folder_id, current_user["id"])

        user_prefix = f"storage/{current_user['id']}/"
        if not payload.storage_key.startswith(user_prefix):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid storage key for current user.",
            )

        head = await self.storage.head_object(payload.storage_key)
        if head is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded storage object not found.",
            )

        # If client supplied a checksum, validate against object metadata or ETag
        if payload.content_hash:
            metadata = (head.get("Metadata") or {})
            head_etag = head.get("ETag") or head.get("ETag")
            normalized_etag = head_etag.strip('"') if head_etag else None
            if metadata.get("sha256"):
                if metadata.get("sha256") != payload.content_hash:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Checksum mismatch for uploaded object.")
            elif normalized_etag:
                if normalized_etag != payload.content_hash:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Checksum mismatch for uploaded object.")
            else:
                # No checksum available from storage to validate against
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to validate checksum for uploaded object.")

        clean_name = sanitize_filename(payload.file_name)

        async def _do_create():
            await self.repo.call_lock_naming_scope(conn, payload.parent_folder_id, current_user["id"])

            final_name = clean_name
            if await self.repo.file_exists_by_name(
                conn,
                payload.parent_folder_id,
                current_user["id"],
                clean_name,
            ):
                final_name = await self.repo.resolve_file_name_collision(
                    conn,
                    payload.parent_folder_id,
                    current_user["id"],
                    clean_name,
                )

            # file_exists = await self.repo.file_exists_by_name(
            #     conn, payload.parent_folder_id, current_user["id"], clean_name
            # )

            # if file_exists:
            #     final_name = await self.repo.resolve_file_name_collision(
            #         conn, payload.parent_folder_id, current_user["id"], clean_name
            #     )
            # else:
            #     final_name = clean_name

            file_id = uuid.uuid4()
            row = await self.repo.create_file(
                conn,
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
        return self._as_file_response(row)

    async def initiate_multipart_upload(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        payload: schemas.InitiateMultipartUploadRequest,
    ) -> schemas.InitiateMultipartUploadResponse:
        await self._require_parent_access(conn, payload.parent_folder_id, current_user["id"])
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid storage key for current user.",
            )

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
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        payload: schemas.CompleteMultipartUploadRequest,
    ) -> schemas.FileResponse:
        await self._require_parent_access(conn, payload.parent_folder_id, current_user["id"])
        user_prefix = f"storage/{current_user['id']}/"
        if not payload.storage_key.startswith(user_prefix):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid storage key for current user.",
            )

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
            await self.repo.call_lock_naming_scope(conn, payload.parent_folder_id, current_user["id"])

            final_name = clean_name
            if await self.repo.file_exists_by_name(
                conn,
                payload.parent_folder_id,
                current_user["id"],
                clean_name,
            ):
                final_name = await self.repo.resolve_file_name_collision(
                    conn,
                    payload.parent_folder_id,
                    current_user["id"],
                    clean_name,
                )

            # file_exists = await self.repo.file_exists_by_name(
            #     conn, payload.parent_folder_id, current_user["id"], clean_name
            # )

            # if file_exists:
            #     final_name = await self.repo.resolve_file_name_collision(
            #         conn, payload.parent_folder_id, current_user["id"], clean_name
            #     )
            # else:
            #     final_name = clean_name

            file_id = uuid.uuid4()
            row = await self.repo.create_file(
                conn,
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
        return self._as_file_response(row)

    async def abort_multipart_upload(
        self,
        current_user: dict[str, Any],
        payload: schemas.AbortMultipartUploadRequest,
    ) -> schemas.MessageResponse:
        user_prefix = f"storage/{current_user['id']}/"
        if not payload.storage_key.startswith(user_prefix):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid storage key for current user.",
            )

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
            except (asyncpg.exceptions.DeadlockDetectedError, asyncpg.exceptions.UniqueViolationError) as exc:
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
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required.")

    @staticmethod
    def _require_target_live(item: dict[str, Any]) -> None:
        if item["is_trashed"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target is trashed.")

    async def _require_edit_access(
        self,
        conn: asyncpg.Connection,
        *,
        target_type: Literal["file", "folder"],
        target_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> None:
        is_file = target_type == "file"
        path = await (self.repo.get_path_for_file(conn, target_id) if is_file else self.repo.get_path_for_folder(conn, target_id))
        if not path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found.")
        owner_row = await (self.repo.get_owner_and_trashed_for_file(conn, target_id) if is_file else self.repo.get_owner_and_trashed_for_folder(conn, target_id))
        if not owner_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found.")

        if owner_row["owner_id"] == current_user_id:
            if owner_row["is_trashed"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target is trashed.")
            return

        permission = await self.repo.get_effective_permission(conn, path, is_file, target_id, current_user_id)

        if permission != "edit":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Edit permission required.")

    async def _require_parent_access(
        self,
        conn: asyncpg.Connection,
        parent_folder_id: uuid.UUID | None,
        current_user_id: uuid.UUID,
    ) -> None:
        if parent_folder_id is None:
            return
        await self._require_edit_access(
            conn,
            target_type="folder",
            target_id=parent_folder_id,
            current_user_id=current_user_id,
        )

    async def create_folder(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        payload: schemas.FolderCreateRequest,
    ) -> schemas.FolderResponse:
        await self._require_parent_access(conn, payload.parent_folder_id, current_user["id"])

        try:
            row = await self.repo.create_folder(
                conn,
                current_user["id"],
                payload.parent_folder_id,
                payload.folder_name,
            )
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Folder name already exists.")

        return self._as_folder_response(row)

    async def upload_file(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        parent_folder_id: uuid.UUID | None,
        upload_file: UploadFile,
        on_collision: Literal["replace", "keep_duplicate"] | None = "keep_duplicate",
    ) -> schemas.FileResponse:
        await self._require_parent_access(conn, parent_folder_id, current_user["id"])

        clean_name = sanitize_filename(upload_file.filename or "untitled")

        if on_collision is None:
            collision = await self.repo.file_exists_by_name(conn, parent_folder_id, current_user["id"], clean_name)
            if collision:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A file with that name already exists. Resubmit with on_collision set to "
                    "'replace' (overwrite) or 'keep_duplicate' (add a suffix).",
                )

        # Stream upload without loading the entire file into memory.
        file_obj = upload_file.file
        try:
            file_obj.seek(0)
        except Exception:
            pass

        class _HashingReader:
            def __init__(self, fobj):
                self._f = fobj
                self._hasher = hashlib.sha256()
                self.size = 0

            def read(self, n=-1):
                chunk = self._f.read(n)
                if chunk:
                    # chunk may be str in some contexts; ensure bytes
                    if isinstance(chunk, str):
                        chunk = chunk.encode()
                    self._hasher.update(chunk)
                    self.size += len(chunk)
                return chunk

            def hexdigest(self):
                return self._hasher.hexdigest()

            def seek(self, *args, **kwargs):
                return getattr(self._f, "seek")( *args, **kwargs)

            def tell(self):
                return getattr(self._f, "tell")()

        file_id = uuid.uuid4()
        storage_key = f"storage/{current_user['id']}/{file_id}/{clean_name}"
        reader = _HashingReader(file_obj)

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
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File storage upload failed.") from exc
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File storage upload failed.") from exc

        content_hash = reader.hexdigest() if reader.size > 0 else None

        async def _perform_operation():
            async with conn.transaction():
                await self.repo.call_lock_naming_scope(conn, parent_folder_id, current_user["id"])

                final_name = clean_name
                if on_collision == "keep_duplicate":
                    final_name = await self.repo.resolve_file_name_collision(
                        conn, parent_folder_id, current_user["id"], clean_name
                    )
                elif on_collision == "replace":
                    existing = await self.repo.get_file_by_parent_and_name(
                        conn, parent_folder_id, clean_name, current_user["id"]
                    )
                    if existing:
                        await self.repo.trash_file(conn, existing["id"])

                return await self.repo.create_file(
                    conn,
                    file_id,
                    current_user["id"],
                    parent_folder_id,
                    storage_key,
                    final_name,
                    reader.size,
                    upload_file.content_type,
                    content_hash,
                )

        try:
            row = await self._with_db_retry(_perform_operation)
        except asyncpg.UniqueViolationError:
            await self.storage.delete_object(storage_key)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A file with that name already exists. Resubmit with on_collision set to "
                "'replace' or 'keep_duplicate'.",
            )
        except asyncpg.CheckViolationError:
            await self.storage.delete_object(storage_key)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Storage quota exceeded.",
            )
        except Exception:
            await self.storage.delete_object(storage_key)
            raise

        return self._as_file_response(row)

    async def move_folder(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        folder_id: uuid.UUID,
        payload: schemas.FolderMoveRequest,
    ) -> schemas.FolderResponse:
        folder = await self.repo.get_folder_by_id(conn, folder_id)
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found.")
        self._require_owner(folder, current_user["id"])
        self._require_target_live(folder)
        await self._require_parent_access(conn, payload.parent_folder_id, current_user["id"])

        if payload.parent_folder_id == folder_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Folder cannot be moved into itself.")

        folder_name = folder["folder_name"]

        async def _perform_operation():
            async with conn.transaction():
                await self.repo.move_folder(
                    conn,
                    folder_id,
                    payload.parent_folder_id,
                    on_collision=payload.on_collision,
                    file_mode=payload.file_mode,
                    file_decisions=payload.file_decisions,
                )
                row = await self.repo.get_folder_by_id(conn, folder_id)
                if row is None:
                    row = await self.repo.get_folder_by_parent_and_name(
                        conn, payload.parent_folder_id, folder_name, current_user["id"]
                    )
                return row

        try:
            row = await self._with_db_retry(_perform_operation)
        except asyncpg.ForeignKeyViolationError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination folder not found.")
        except asyncpg.CheckViolationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except asyncpg.RaiseError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A folder with that name already exists at the destination. "
                "Resubmit with on_collision set to 'merge' or 'keep_duplicate'.",
            )

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found after move.")
        return self._as_folder_response(row)

    async def move_file(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        file_id: uuid.UUID,
        payload: schemas.FileMoveRequest,
    ) -> schemas.FileResponse:
        file_row = await self.repo.get_file_by_id(conn, file_id)
        if not file_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
        self._require_owner(file_row, current_user["id"])
        self._require_target_live(file_row)
        await self._require_parent_access(conn, payload.parent_folder_id, current_user["id"])

        async def _perform_operation():
            async with conn.transaction():
                await self.repo.move_file(
                    conn, file_id, payload.parent_folder_id, on_collision=payload.on_collision
                )
                return await self.repo.get_file_by_id(conn, file_id)

        try:
            row = await self._with_db_retry(_perform_operation)
        except asyncpg.ForeignKeyViolationError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination folder not found.")
        except asyncpg.RaiseError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A file with that name already exists at the destination. "
                "Resubmit with on_collision set to 'replace' or 'keep_duplicate'.",
            )

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
        return self._as_file_response(row)

    async def delete_folder(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        folder_id: uuid.UUID,
    ) -> schemas.MessageResponse:
        folder = await self.repo.get_folder_by_id(conn, folder_id)
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found.")
        self._require_owner(folder, current_user["id"])
        if folder["is_trashed"]:
            return schemas.MessageResponse(message="Folder already in trash.")

        row = await self.repo.trash_folder(conn, folder_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found.")
        return schemas.MessageResponse(message="Folder moved to trash.")

    async def restore_folder(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        folder_id: uuid.UUID,
    ) -> schemas.FolderResponse:
        folder = await self.repo.get_folder_by_id(conn, folder_id)
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found.")
        self._require_owner(folder, current_user["id"])
        if not folder["is_trashed"]:
            return self._as_folder_response(folder)

        parent_id = folder.get("parent_folder_id")
        owner_id = folder.get("owner_id")
        folder_name = folder.get("folder_name")

        if not owner_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Folder record is missing a valid owner ID."
            )

        if not folder_name:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Folder name mút not be empty."
            )

        async def _perform_operation():
            async with conn.transaction():
                await self.repo.call_lock_naming_scope(conn, parent_id, owner_id)
                new_name = await self.repo.resolve_restored_folder_name(conn, parent_id, owner_id, folder_name)
                if new_name is None:
                            raise HTTPException(
                                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Could not resolve a valid name for the restored folder."
                            )
                return await self.repo.restore_folder(conn, folder_id, new_name)

        try:
            restored = await self._with_db_retry(_perform_operation)
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Name collision during restore; please retry.")
        except asyncpg.DeadlockDetectedError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Deadlock during restore; please retry.")

        if not restored:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to restore folder.")

        return self._as_folder_response(restored)

    async def delete_file(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        file_id: uuid.UUID,
    ) -> schemas.MessageResponse:
        file_row = await self.repo.get_file_by_id(conn, file_id)
        if not file_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
        self._require_owner(file_row, current_user["id"])
        if file_row["is_trashed"]:
            return schemas.MessageResponse(message="File already in trash.")

        row = await self.repo.trash_file(conn, file_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
        return schemas.MessageResponse(message="File moved to trash.")

    async def restore_file(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        file_id: uuid.UUID,
    ) -> schemas.FileResponse:
        file_row = await self.repo.get_file_by_id(conn, file_id)
        if not file_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
        self._require_owner(file_row, current_user["id"])
        if not file_row["is_trashed"]:
            return self._as_file_response(file_row)

        parent_id = file_row.get("parent_folder_id")
        owner_id = file_row.get("owner_id")
        file_name = file_row.get("file_name")

        if not owner_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File record is missing a valid owner ID."
            )

        if not file_name:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File name is missing."
            )

        async def _perform_operation():
            async with conn.transaction():
                await self.repo.call_lock_naming_scope(conn, parent_id, owner_id)
                new_name = await self.repo.resolve_restored_file_name(conn, parent_id, owner_id, file_name)
                if new_name is None:
                            raise HTTPException(
                                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Could not resolve a valid name for the restored file."
                            )
                return await self.repo.restore_file(conn, file_id, new_name)

        try:
            restored = await self._with_db_retry(_perform_operation)
        except asyncpg.UniqueViolationError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Name collision during restore; please retry.")
        except asyncpg.DeadlockDetectedError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Deadlock during restore; please retry.")

        if not restored:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to restore file.")

        return self._as_file_response(restored)

    async def share_item(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        payload: schemas.ShareCreateRequest,
    ) -> schemas.ShareResponse:
        if payload.target_type == "file":
            target = await self.repo.get_file_by_id(conn, payload.target_id)
            file_id = payload.target_id
            folder_id = None
        else:
            target = await self.repo.get_folder_by_id(conn, payload.target_id)
            file_id = None
            folder_id = payload.target_id

        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found.")

        self._require_owner(target, current_user["id"])
        self._require_target_live(target)

        if payload.principal_type == "user":
            if not payload.grantee_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="grantee_id is required for user shares.")
            if payload.grantee_id == current_user["id"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot share with yourself.")
            existing = await self.repo.get_live_user_share(
                conn,
                file_id=file_id,
                folder_id=folder_id,
                grantee_id=payload.grantee_id,
            )
            if existing:
                updated = await self.repo.update_acl_entry_permission(conn, existing["id"], payload.permission)
                if not updated:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Failed to update share permissions; entry no longer exists."
                        )
                return self._as_share_response(updated)

            row = await self.repo.create_acl_entry(
                conn,
                file_id=file_id,
                folder_id=folder_id,
                principal_type="user",
                grantee_id=payload.grantee_id,
                share_token=None,
                password_hash=None,
                permission=payload.permission,
                created_by=current_user["id"],
            )
            return self._as_share_response(row)

        share_token = payload.share_token or secrets.token_urlsafe(32)
        password_hash = hash_password(payload.password) if payload.password else None
        existing_link = await self.repo.get_live_public_link(conn, file_id=file_id, folder_id=folder_id)
        if existing_link:
            updated = await self.repo.update_live_public_link(
                conn,
                existing_link["id"],
                share_token=share_token if payload.share_token else existing_link["share_token"],
                password_hash=password_hash,
                permission=payload.permission,
            )
            if not updated:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, 
                        detail="Failed to update public link; link no longer exists."
                    )
            return self._as_share_response(updated)

        row = await self.repo.create_acl_entry(
            conn,
            file_id=file_id,
            folder_id=folder_id,
            principal_type="public_link",
            grantee_id=None,
            share_token=share_token,
            password_hash=password_hash,
            permission=payload.permission,
            created_by=current_user["id"],
        )
        return self._as_share_response(row)

    async def revoke_share(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        share_id: uuid.UUID,
    ) -> schemas.MessageResponse:
        share = await self.repo.get_acl_entry(conn, share_id)
        if not share:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found.")

        if share["created_by"] != current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner access required.")

        await self.repo.revoke_acl_entry(conn, share_id)
        return schemas.MessageResponse(message="Share revoked.")

    async def hard_delete_file(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        file_id: uuid.UUID,
    ) -> schemas.MessageResponse:
        file_row = await self.repo.get_file_by_id(conn, file_id)
        if not file_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
        self._require_owner(file_row, current_user["id"])
        if not file_row["is_trashed"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is not in trash.")
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
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to delete object from storage; please try again later.")

        # Object deleted (or no storage_key). Now remove DB row.
        try:
            async with conn.transaction():
                deleted = await self.repo.delete_file_by_id(conn, file_id)
                if not deleted:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete file row.")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete file row.") from exc

        return schemas.MessageResponse(message="File permanently deleted.")

    async def hard_delete_folder(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        folder_id: uuid.UUID,
    ) -> schemas.MessageResponse:
        folder = await self.repo.get_folder_by_id(conn, folder_id)
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found.")
        self._require_owner(folder, current_user["id"])
        if not folder["is_trashed"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Folder is not in trash.")

        folder_path = folder.get("path")
        # gather files under this path
        files = await self.repo.list_files_under_path(conn, folder_path)

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
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Failed to delete object {storage_key}; please try again later.")

        # All object deletions succeeded (or no storage_key). Delete folder rows and files under path atomically.
        try:
            async with conn.transaction():
                await self.repo.delete_files_under_path(conn, folder_path)
                await self.repo.delete_folders_under_path(conn, folder_path)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete folder rows.") from exc

        return schemas.MessageResponse(message="Folder and contents permanently deleted.")

    async def hard_delete_all_trash(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
    ) -> schemas.MessageResponse:
        owner_id = current_user["id"]
        files = await self.repo.list_trashed_files_by_owner(conn, owner_id)

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
                    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Failed to delete object {storage_key}; please try again later.")

            # delete DB row for this file
            try:
                async with conn.transaction():
                    await self.repo.delete_file_by_id(conn, f["id"])
            except Exception:
                pass

        # Remove trashed folder rows
        async with conn.transaction():
            await self.repo.delete_trashed_folders_by_owner(conn, owner_id)

        return schemas.MessageResponse(message="Trash emptied (permanently deleted).")

    async def _require_view_access(
        self,
        conn: asyncpg.Connection,
        *,
        target_type: Literal["file", "folder"],
        target_id: uuid.UUID,
        current_user_id: uuid.UUID,
    ) -> None:
        is_file = target_type == "file"
        path = await (self.repo.get_path_for_file(conn, target_id) if is_file else self.repo.get_path_for_folder(conn, target_id))
        if not path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found.")
        owner_row = await (self.repo.get_owner_and_trashed_for_file(conn, target_id) if is_file else self.repo.get_owner_and_trashed_for_folder(conn, target_id))
        if not owner_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found.")

        if owner_row["owner_id"] == current_user_id:
            if owner_row["is_trashed"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target is trashed.")
            return

        permission = await self.repo.get_effective_permission(conn, path, is_file, target_id, current_user_id)

        if permission is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="View permission required.")

    async def download_file_stream(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        file_id: uuid.UUID,
        range_header: str | None = None,
    ) -> StreamingResponse:
        file_row = await self.repo.get_file_by_id(conn, file_id)
        if not file_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
        await self._require_view_access(conn, target_type="file", target_id=file_id, current_user_id=current_user["id"])

        client = self.storage._get_client()
        params = {"Bucket": self.storage.bucket_name, "Key": file_row["storage_key"]}
        if range_header:
            params["Range"] = range_header

        try:
            response = await asyncio.to_thread(client.get_object, **params)
        except ClientError as exc:
            # Map 404 from object store to 404
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found in storage.") from exc

        body = response["Body"]

        async def stream_generator():
            try:
                while True:
                    chunk = await asyncio.to_thread(body.read, 64 * 1024)
                    if not chunk:
                        break
                    yield chunk
            finally:
                try:
                    body.close()
                except Exception:
                    pass

        headers: dict[str, str] = {}
        # Content-Length
        if "ContentLength" in response:
            headers["Content-Length"] = str(response.get("ContentLength"))
        # Content-Range (when partial)
        content_range = response.get("ContentRange") or response.get("Content-Range")
        if content_range:
            headers["Content-Range"] = content_range
            status_code = status.HTTP_206_PARTIAL_CONTENT
        else:
            status_code = status.HTTP_200_OK

        # Content-Type
        media_type = response.get("ContentType") or file_row.get("mime_type") or "application/octet-stream"

        headers["Accept-Ranges"] = "bytes"
        headers["Content-Disposition"] = f'attachment; filename="{file_row.get("file_name")}"'

        return StreamingResponse(stream_generator(), status_code=status_code, media_type=media_type, headers=headers)

    async def get_storage_usage(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
    ) -> schemas.StorageUsageResponse:
        used = await self.repo.get_storage_usage(conn, current_user["id"])
        quota_row = await self.repo.get_user_storage_quota(conn, current_user["id"])
        total = quota_row["storage_quota"] if quota_row else getattr(settings, "STORAGE_QUOTA_BYTES", 20 * 1024 ** 3)
        return schemas.StorageUsageResponse(used_bytes=used, total_bytes=total)


    async def get_storage_contents(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
        parent_folder_id: uuid.UUID | None = None,
    ) -> schemas.StorageContentResponse:
        if parent_folder_id:
            await self._require_view_access(
                conn, target_type="folder", target_id=parent_folder_id, current_user_id=current_user["id"]
            )

        folders_raw = await self.repo.list_user_folders(conn, current_user["id"], parent_folder_id)
        files_raw = await self.repo.list_user_files(conn, current_user["id"], parent_folder_id)

        return schemas.StorageContentResponse(
            folders=[self._as_folder_response(f) for f in folders_raw],
            files=[self._as_file_response(f) for f in files_raw],
        )

    async def get_trashed_contents(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
    ) -> schemas.StorageContentResponse:
        """Return trashed folders and files owned by the current user."""
        owner_id = current_user["id"]
        folders_raw = await self.repo.list_trashed_folders_by_owner(conn, owner_id)
        files_raw = await self.repo.list_trashed_files_by_owner(conn, owner_id)

        return schemas.StorageContentResponse(
            folders=[self._as_folder_response(f) for f in folders_raw],
            files=[self._as_file_response(f) for f in files_raw],
        )

    async def get_shared_with_me_contents(
        self,
        conn: asyncpg.Connection,
        current_user: dict[str, Any],
    ) -> schemas.StorageContentResponse:
        owner_id = current_user["id"]
        folders_raw = await self.repo.list_shared_with_me_folders(conn, owner_id)
        files_raw = await self.repo.list_shared_with_me_files(conn, owner_id)
        
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
        conn: asyncpg.Connection,
        target_id: uuid.UUID,
        is_file: bool,
    ) -> list[dict[str, str]]:
        path_str = await (self.repo.get_path_for_file(conn, target_id) if is_file else self.repo.get_path_for_folder(conn, target_id))
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
            
        folders = await self.repo.get_folders_by_ids(conn, uuids)
        folder_dict = {f["id"]: f["folder_name"] for f in folders}
        
        result = []
        for u in uuids:
            if u in folder_dict:
                result.append({"id": str(u), "name": folder_dict[u]})
        return result