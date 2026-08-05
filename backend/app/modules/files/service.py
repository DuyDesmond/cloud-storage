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
        except ClientError:
            # Silence deletion exceptions to avoid masking primary application errors
            pass

    async def generate_presigned_put_url(
        self,
        *,
        object_name: str,
        expires_in: int = 3600,
        content_type: str | None = None,
    ) -> str:
        """Generate a presigned URL for PUT uploads (client performs HTTP PUT).

        Returns a URL string that the client can use to PUT the object directly
        to R2/MinIO.
        """
        client = self._get_client()
        params: dict[str, object] = {"Bucket": self.bucket_name, "Key": object_name}
        if content_type:
            params["ContentType"] = content_type

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


class FileOperationsService:
    def __init__(
        self,
        repo: FileOperationsRepository = Depends(),
        storage: R2StorageGateway = Depends(),
    ) -> None:
        self.repo = repo
        self.storage = storage

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
    ) -> schemas.FileResponse:
        await self._require_parent_access(conn, parent_folder_id, current_user["id"])
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
        storage_key = f"{current_user['id']}/{file_id}"
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

        try:
            row = await self.repo.create_file(
                conn,
                file_id,
                current_user["id"],
                parent_folder_id,
                storage_key,
                upload_file.filename or "untitled",
                reader.size,
                upload_file.content_type,
                content_hash,
            )
        except asyncpg.UniqueViolationError:
            await self.storage.delete_object(storage_key)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="File name already exists.")
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

        async def _op():
            return await self.repo.move_folder(conn, folder_id, payload.parent_folder_id)

        try:
            row = await self._with_db_retry(_op)
        except asyncpg.ForeignKeyViolationError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination folder not found.")
        except asyncpg.CheckViolationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found.")
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

        async def _op():
            return await self.repo.move_file(conn, file_id, payload.parent_folder_id)

        try:
            row = await self._with_db_retry(_op)
        except asyncpg.ForeignKeyViolationError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination folder not found.")

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

        async def _op():
            async with conn.transaction():
                await self.repo.call_lock_naming_scope(conn, parent_id, owner_id)
                new_name = await self.repo.resolve_restored_folder_name(conn, parent_id, owner_id, folder.get("folder_name"))
                return await self.repo.restore_folder(conn, folder_id, new_name)

        try:
            restored = await self._with_db_retry(_op)
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

        async def _op():
            async with conn.transaction():
                await self.repo.call_lock_naming_scope(conn, parent_id, owner_id)
                new_name = await self.repo.resolve_restored_file_name(conn, parent_id, owner_id, file_row.get("file_name"))
                return await self.repo.restore_file(conn, file_id, new_name)

        try:
            restored = await self._with_db_retry(_op)
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