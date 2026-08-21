from __future__ import annotations

import uuid
from typing import Literal

import asyncpg
from fastapi import APIRouter, Depends, File, UploadFile, status, Request
from app.core.rate_limit import limiter

from app.core.database import get_db_connection
from app.core.dependencies import get_current_user
from app.modules.files import schemas
from app.modules.files.service import FileOperationsService


router = APIRouter(prefix="/storage", tags=["File Operations"])

@router.get("/retrieve", response_model=schemas.StorageContentResponse)
@limiter.limit("100/minute")
async def get_storage_contents(request: Request, 
    parent_folder_id: uuid.UUID | None = None,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.get_storage_contents(conn, current_user, parent_folder_id)

@router.get("/shared-with-me", response_model=schemas.StorageContentResponse)
@limiter.limit("100/minute")
async def get_shared_with_me_contents(request: Request, 
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.get_shared_with_me_contents(conn, current_user)

@router.get("/breadcrumbs", response_model=schemas.BreadcrumbsResponse)
@limiter.limit("100/minute")
async def get_breadcrumbs(request: Request, 
    target_id: uuid.UUID,
    is_file: bool = False,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    breadcrumbs = await service.get_breadcrumbs(conn, target_id, is_file)
    return schemas.BreadcrumbsResponse(breadcrumbs=breadcrumbs)

@router.get("/usage", response_model=schemas.StorageUsageResponse)
@limiter.limit("100/minute")
async def get_storage_usage(request: Request, 
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.get_storage_usage(conn, current_user)

@router.post("/folders", response_model=schemas.FolderResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("100/minute")
async def create_folder(request: Request, 
    payload: schemas.FolderCreateRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.create_folder(conn, current_user, payload)


@router.post("/files", response_model=schemas.FileResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("100/minute")
async def upload_file(request: Request, 
    parent_folder_id: uuid.UUID | None = None,
    on_collision: Literal["replace", "keep_duplicate"] | None = "keep_duplicate",
    upload_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.upload_file(conn, current_user, parent_folder_id, upload_file, on_collision)

@router.post("/upload/presign", response_model=schemas.PresignedUploadResponse)
@limiter.limit("30/minute")
async def request_presigned_upload(request: Request, 
    payload: schemas.PresignedUploadRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.request_presigned_upload(conn, current_user, payload)


@router.post("/upload/complete", response_model=schemas.FileResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def complete_direct_upload(request: Request, 
    payload: schemas.CompleteUploadRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.complete_direct_upload(conn, current_user, payload)


@router.post("/upload/multipart/initiate", response_model=schemas.InitiateMultipartUploadResponse)
@limiter.limit("30/minute")
async def initiate_multipart_upload(request: Request, 
    payload: schemas.InitiateMultipartUploadRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.initiate_multipart_upload(conn, current_user, payload)


@router.post("/upload/multipart/presign-part", response_model=schemas.PresignPartResponse)
@limiter.limit("30/minute")
async def presign_multipart_part(request: Request, 
    payload: schemas.PresignPartRequest,
    current_user: dict = Depends(get_current_user),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.presign_multipart_part(current_user, payload)


@router.post("/upload/multipart/complete", response_model=schemas.FileResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def complete_multipart_upload(request: Request, 
    payload: schemas.CompleteMultipartUploadRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.complete_multipart_upload(conn, current_user, payload)


@router.post("/upload/multipart/abort", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
async def abort_multipart_upload(request: Request, 
    payload: schemas.AbortMultipartUploadRequest,
    current_user: dict = Depends(get_current_user),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.abort_multipart_upload(current_user, payload)

@router.get("/files/{file_id}/download")
@limiter.limit("100/minute")
async def download_file(request: Request, 
    file_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    range_header = request.headers.get("range") or request.headers.get("Range")
    return await service.download_file_stream(conn, current_user, file_id, range_header)


@router.patch("/folders/{folder_id}/move", response_model=schemas.FolderResponse)
@limiter.limit("30/minute")
async def move_folder(request: Request, 
    folder_id: uuid.UUID,
    payload: schemas.FolderMoveRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.move_folder(conn, current_user, folder_id, payload)


@router.patch("/files/{file_id}/move", response_model=schemas.FileResponse)
@limiter.limit("30/minute")
async def move_file(request: Request, 
    file_id: uuid.UUID,
    payload: schemas.FileMoveRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.move_file(conn, current_user, file_id, payload)


@router.delete("/folders/{folder_id}", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
async def delete_folder(request: Request, 
    folder_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.delete_folder(conn, current_user, folder_id)


@router.delete("/files/{file_id}", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
async def delete_file(request: Request, 
    file_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.delete_file(conn, current_user, file_id)


@router.post("/shares", response_model=schemas.ShareResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("100/minute")
async def share_item(request: Request, 
    payload: schemas.ShareCreateRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.share_item(conn, current_user, payload)


@router.delete("/shares/{share_id}", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
async def revoke_share(request: Request, 
    share_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.revoke_share(conn, current_user, share_id)


@router.delete("/trash/files/{file_id}", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
async def hard_delete_file(request: Request, 
    file_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.hard_delete_file(conn, current_user, file_id)


@router.delete("/trash/folders/{folder_id}", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
async def hard_delete_folder(request: Request, 
    folder_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.hard_delete_folder(conn, current_user, folder_id)


@router.delete("/trash/empty", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
async def empty_trash(request: Request, 
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.hard_delete_all_trash(conn, current_user)


@router.post("/trash/files/{file_id}/restore", response_model=schemas.FileResponse)
@limiter.limit("30/minute")
async def restore_file(request: Request, 
    file_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.restore_file(conn, current_user, file_id)


@router.post("/trash/folders/{folder_id}/restore", response_model=schemas.FolderResponse)
@limiter.limit("30/minute")
async def restore_folder(request: Request, 
    folder_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.restore_folder(conn, current_user, folder_id)


@router.get("/trash", response_model=schemas.StorageContentResponse)
@limiter.limit("30/minute")
async def get_trashed_contents(request: Request, 
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
    service: FileOperationsService = Depends(FileOperationsService),
):
    return await service.get_trashed_contents(conn, current_user)