from __future__ import annotations

import asyncio
import hashlib
import io
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import asyncpg
from fastapi import Depends, HTTPException, UploadFile, status

try:
    from minio import Minio
except ImportError:  # pragma: no cover - optional runtime dependency
    Minio = None

from app.core.config import settings
from app.core.security import hash_password
from app.modules.file_operations import schemas
from app.modules.file_operations.repository import FileOperationsRepository


class MinioStorageGateway:
    def __init__(self) -> None:
        self.endpoint = getattr(settings, "MINIO_ENDPOINT", None)
        self.access_key = getattr(settings, "MINIO_ACCESS_KEY", None)
        self.secret_key = getattr(settings, "MINIO_SECRET_KEY", None)
        self.secure = bool(getattr(settings, "MINIO_SECURE", False))
        self.bucket_name = getattr(settings, "MINIO_BUCKET_NAME", "nephos")
        self._client: Minio | None = None

    def _get_client(self) -> Minio:
        if Minio is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MinIO client is not installed.",
            )

        if not self.endpoint or not self.access_key or not self.secret_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MinIO is not configured.",
            )

        if self._client is None:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )

        return self._client

    async def ensure_bucket(self) -> None:
        client = self._get_client()
        exists = await asyncio.to_thread(client.bucket_exists, self.bucket_name)
        if not exists:
            await asyncio.to_thread(client.make_bucket, self.bucket_name)

    async def upload_bytes(
        self,
        *,
        object_name: str,
        data: bytes,
        content_type: str | None,
    ) -> None:
        await self.ensure_bucket()
        client = self._get_client()
        stream = io.BytesIO(data)
        await asyncio.to_thread(
            client.put_object,
            self.bucket_name,
            object_name,
            stream,
            len(data),
            content_type,
        )

    async def delete_object(self, object_name: str) -> None:
        if Minio is None or not self.endpoint or not self.access_key or not self.secret_key:
            return
        client = self._get_client()
        await asyncio.to_thread(client.remove_object, self.bucket_name, object_name)


class FileOperationsService:
    def __init__(
        self,
        repo: FileOperationsRepository = Depends(),
        storage: MinioStorageGateway = Depends(),
    ) -> None:
        self.repo = repo
        self.storage = storage

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
        path_query = "SELECT path FROM nephos.files WHERE id = $1" if is_file else "SELECT path FROM nephos.folders WHERE id = $1"
        path = await conn.fetchval(path_query, target_id)
        if not path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found.")

        owner_query = "SELECT owner_id, is_trashed FROM nephos.files WHERE id = $1" if is_file else "SELECT owner_id, is_trashed FROM nephos.folders WHERE id = $1"
        owner_row = await conn.fetchrow(owner_query, target_id)
        if not owner_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found.")

        if owner_row["owner_id"] == current_user_id:
            if owner_row["is_trashed"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target is trashed.")
            return

        permission = await conn.fetchval(
            "SELECT nephos.effective_permission($1, $2, $3, $4)",
            path,
            is_file,
            target_id,
            current_user_id,
        )

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

        file_bytes = await upload_file.read()
        file_id = uuid.uuid4()
        storage_key = f"{current_user['id']}/{file_id}"
        content_hash = hashlib.sha256(file_bytes).hexdigest() if file_bytes else None

        try:
            await self.storage.upload_bytes(
                object_name=storage_key,
                data=file_bytes,
                content_type=upload_file.content_type,
            )
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - external storage failure
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File storage upload failed.") from exc

        try:
            row = await self.repo.create_file(
                conn,
                file_id,
                current_user["id"],
                parent_folder_id,
                storage_key,
                upload_file.filename or "untitled",
                len(file_bytes),
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

        try:
            row = await self.repo.move_folder(conn, folder_id, payload.parent_folder_id)
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

        try:
            row = await self.repo.move_file(conn, file_id, payload.parent_folder_id)
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
                expires_at=None,
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
                expires_at=payload.expires_at,
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
            expires_at=payload.expires_at,
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
