from __future__ import annotations

import uuid

import asyncpg
from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi import APIRouter, Depends, File, UploadFile, status, Request

from app.core.database import get_db_connection
from app.modules.auth.dependencies import get_current_user
from app.modules.files import schemas
from app.modules.files.service import FileOperationsService


router = APIRouter(prefix="/storage", tags=["File Operations"])

@router.get("/retrieve", response_model=schemas.StorageContentResponse)
async def get_storage_contents(
    parent_folder_id: uuid.UUID | None = None,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.get_storage_contents(conn, current_user, parent_folder_id)

@router.post("/folders", response_model=schemas.FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    payload: schemas.FolderCreateRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.create_folder(conn, current_user, payload)


@router.post("/files", response_model=schemas.FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    parent_folder_id: uuid.UUID | None = None,
    upload_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.upload_file(conn, current_user, parent_folder_id, upload_file)

@router.post("/upload/presign", response_model=schemas.PresignedUploadResponse)
async def request_presigned_upload(
    payload: schemas.PresignedUploadRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.request_presigned_upload(conn, current_user, payload)


@router.post("/upload/complete", response_model=schemas.FileResponse, status_code=status.HTTP_201_CREATED)
async def complete_direct_upload(
    payload: schemas.CompleteUploadRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.complete_direct_upload(conn, current_user, payload)


@router.post("/upload/multipart/initiate", response_model=schemas.InitiateMultipartUploadResponse)
async def initiate_multipart_upload(
    payload: schemas.InitiateMultipartUploadRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.initiate_multipart_upload(conn, current_user, payload)


@router.post("/upload/multipart/presign-part", response_model=schemas.PresignPartResponse)
async def presign_multipart_part(
    payload: schemas.PresignPartRequest,
    current_user: dict = Depends(get_current_user),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.presign_multipart_part(current_user, payload)


@router.post("/upload/multipart/complete", response_model=schemas.FileResponse, status_code=status.HTTP_201_CREATED)
async def complete_multipart_upload(
    payload: schemas.CompleteMultipartUploadRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.complete_multipart_upload(conn, current_user, payload)


@router.post("/upload/multipart/abort", response_model=schemas.MessageResponse)
async def abort_multipart_upload(
    payload: schemas.AbortMultipartUploadRequest,
    current_user: dict = Depends(get_current_user),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.abort_multipart_upload(current_user, payload)

@router.get("/files/{file_id}/download")
async def download_file(
    file_id: uuid.UUID,
    request: Request,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    range_header = request.headers.get("range") or request.headers.get("Range")
    return await service.download_file_stream(conn, current_user, file_id, range_header)


@router.patch("/folders/{folder_id}/move", response_model=schemas.FolderResponse)
async def move_folder(
    folder_id: uuid.UUID,
    payload: schemas.FolderMoveRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.move_folder(conn, current_user, folder_id, payload)


@router.patch("/files/{file_id}/move", response_model=schemas.FileResponse)
async def move_file(
    file_id: uuid.UUID,
    payload: schemas.FileMoveRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.move_file(conn, current_user, file_id, payload)


@router.delete("/folders/{folder_id}", response_model=schemas.MessageResponse)
async def delete_folder(
    folder_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.delete_folder(conn, current_user, folder_id)


@router.delete("/files/{file_id}", response_model=schemas.MessageResponse)
async def delete_file(
    file_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.delete_file(conn, current_user, file_id)


@router.post("/shares", response_model=schemas.ShareResponse, status_code=status.HTTP_201_CREATED)
async def share_item(
    payload: schemas.ShareCreateRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.share_item(conn, current_user, payload)


@router.delete("/shares/{share_id}", response_model=schemas.MessageResponse)
async def revoke_share(
    share_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.revoke_share(conn, current_user, share_id)


@router.delete("/trash/files/{file_id}", response_model=schemas.MessageResponse)
async def hard_delete_file(
    file_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.hard_delete_file(conn, current_user, file_id)


@router.delete("/trash/folders/{folder_id}", response_model=schemas.MessageResponse)
async def hard_delete_folder(
    folder_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.hard_delete_folder(conn, current_user, folder_id)


@router.delete("/trash/empty", response_model=schemas.MessageResponse)
async def empty_trash(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.hard_delete_all_trash(conn, current_user)


@router.post("/trash/files/{file_id}/restore", response_model=schemas.FileResponse)
async def restore_file(
    file_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.restore_file(conn, current_user, file_id)


@router.post("/trash/folders/{folder_id}/restore", response_model=schemas.FolderResponse)
async def restore_folder(
    folder_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.restore_folder(conn, current_user, folder_id)


@router.get("/trash", response_model=schemas.StorageContentResponse)
async def get_trashed_contents(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.get_trashed_contents(conn, current_user)