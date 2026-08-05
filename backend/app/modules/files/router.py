from __future__ import annotations

import uuid

import asyncpg
from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.database import get_db_connection
from app.modules.auth.dependencies import get_current_user
from app.modules.files import schemas
from app.modules.files.service import FileOperationsService


router = APIRouter(prefix="/storage", tags=["File Operations"])


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