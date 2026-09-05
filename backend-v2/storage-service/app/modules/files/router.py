from __future__ import annotations

import uuid
from typing import Literal

import asyncpg
from fastapi import APIRouter, Depends, File, UploadFile, status, Request
from app.core.rate_limit import limiter

from app.core.database import get_db_connection
from app.core.dependencies import get_current_user, get_optional_current_user
from app.modules.files import schemas
from app.modules.files.services import (
    FileQueryService,
    FileUploadService,
    StorageQuotaService,
    FileManagementService,
    TrashService
)

import functools
from fastapi import HTTPException, status
from app.core.exceptions import DomainError, DuplicateRecordError, InvalidOperationError, ItemNotFoundError, QuotaExceededError, AccessDeniedError, InfrastructureError

def map_domain_exceptions(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ItemNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except DuplicateRecordError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        except QuotaExceededError as e:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e))
        except AccessDeniedError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except InvalidOperationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except InfrastructureError as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        except DomainError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return wrapper



router = APIRouter(prefix="/storage", tags=["File Operations"])

@router.get("/retrieve", response_model=schemas.StorageContentResponse)
@limiter.limit("100/minute")
@map_domain_exceptions
async def get_storage_contents(request: Request, 
    parent_folder_id: uuid.UUID | None = None,
    current_user: dict | None = Depends(get_optional_current_user),
    service: FileQueryService = Depends(FileQueryService),
):
    return await service.get_storage_contents(current_user, parent_folder_id)

@router.get("/shared-with-me", response_model=schemas.StorageContentResponse)
@limiter.limit("100/minute")
@map_domain_exceptions
async def get_shared_with_me_contents(request: Request, 
    current_user: dict = Depends(get_current_user),
    service: FileQueryService = Depends(FileQueryService),
):
    return await service.get_shared_with_me_contents(current_user)

@router.get("/breadcrumbs", response_model=schemas.BreadcrumbsResponse)
@limiter.limit("100/minute")
@map_domain_exceptions
async def get_breadcrumbs(request: Request, 
    target_id: uuid.UUID,
    is_file: bool = False,
    current_user: dict | None = Depends(get_optional_current_user),
    service: FileQueryService = Depends(FileQueryService),
):
    breadcrumbs = await service.get_breadcrumbs(target_id, is_file, current_user)
    return schemas.BreadcrumbsResponse(breadcrumbs=breadcrumbs)

@router.get("/usage", response_model=schemas.StorageUsageResponse)
@limiter.limit("100/minute")
@map_domain_exceptions
async def get_storage_usage(request: Request, 
    current_user: dict = Depends(get_current_user),
    service: StorageQuotaService = Depends(StorageQuotaService),
):
    return await service.get_storage_usage(current_user)

@router.post("/folders", response_model=schemas.FolderResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("100/minute")
@map_domain_exceptions
async def create_folder(request: Request, 
    payload: schemas.FolderCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: FileManagementService = Depends(FileManagementService),
):
    return await service.create_folder(current_user, payload)


@router.post("/files", response_model=schemas.FileResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("100/minute")
@map_domain_exceptions
async def upload_file(request: Request, 
    parent_folder_id: uuid.UUID | None = None,
    on_collision: Literal["replace", "keep_duplicate"] | None = "keep_duplicate",
    upload_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    service: FileUploadService = Depends(FileUploadService),
):
    return await service.upload_file(current_user, parent_folder_id, upload_file, on_collision)

@router.post("/upload/presign", response_model=schemas.PresignedUploadResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def request_presigned_upload(request: Request, 
    payload: schemas.PresignedUploadRequest,
    current_user: dict = Depends(get_current_user),
    service: FileUploadService = Depends(FileUploadService),
):
    return await service.request_presigned_upload(current_user, payload)


@router.post("/upload/complete", response_model=schemas.FileResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
@map_domain_exceptions
async def complete_direct_upload(request: Request, 
    payload: schemas.CompleteUploadRequest,
    current_user: dict = Depends(get_current_user),
    service: FileUploadService = Depends(FileUploadService),
):
    return await service.complete_direct_upload(current_user, payload)


@router.post("/upload/multipart/initiate", response_model=schemas.InitiateMultipartUploadResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def initiate_multipart_upload(request: Request, 
    payload: schemas.InitiateMultipartUploadRequest,
    current_user: dict = Depends(get_current_user),
    service: FileUploadService = Depends(FileUploadService),
):
    return await service.initiate_multipart_upload(current_user, payload)


@router.post("/upload/multipart/presign-part", response_model=schemas.PresignPartResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def presign_multipart_part(request: Request, 
    payload: schemas.PresignPartRequest,
    current_user: dict = Depends(get_current_user),
    service: FileUploadService = Depends(FileUploadService),
):
    return await service.presign_multipart_part(current_user, payload)


@router.post("/upload/multipart/complete", response_model=schemas.FileResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
@map_domain_exceptions
async def complete_multipart_upload(request: Request, 
    payload: schemas.CompleteMultipartUploadRequest,
    current_user: dict = Depends(get_current_user),
    service: FileUploadService = Depends(FileUploadService),
):
    return await service.complete_multipart_upload(current_user, payload)


@router.post("/upload/multipart/abort", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def abort_multipart_upload(request: Request, 
    payload: schemas.AbortMultipartUploadRequest,
    current_user: dict = Depends(get_current_user),
    service: FileUploadService = Depends(FileUploadService),
):
    return await service.abort_multipart_upload(current_user, payload)

@router.get("/files/{file_id}/download")
@limiter.limit("100/minute")
@map_domain_exceptions
async def download_file(request: Request, 
    file_id: uuid.UUID,
    current_user: dict | None = Depends(get_optional_current_user),
    service: FileUploadService = Depends(FileUploadService),
):
    range_header = request.headers.get("range") or request.headers.get("Range")
    return await service.download_file_stream(current_user, file_id, range_header)


@router.patch("/folders/{folder_id}/move", response_model=schemas.FolderResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def move_folder(request: Request, 
    folder_id: uuid.UUID,
    payload: schemas.FolderMoveRequest,
    current_user: dict = Depends(get_current_user),
    service: FileManagementService = Depends(FileManagementService),
):
    return await service.move_folder(current_user, folder_id, payload)


@router.patch("/files/{file_id}/move", response_model=schemas.FileResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def move_file(request: Request, 
    file_id: uuid.UUID,
    payload: schemas.FileMoveRequest,
    current_user: dict = Depends(get_current_user),
    service: FileManagementService = Depends(FileManagementService),
):
    return await service.move_file(current_user, file_id, payload)


@router.delete("/folders/{folder_id}", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def delete_folder(request: Request, 
    folder_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: FileManagementService = Depends(FileManagementService),
):
    return await service.delete_folder(current_user, folder_id)


@router.delete("/files/{file_id}", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def delete_file(request: Request, 
    file_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: FileManagementService = Depends(FileManagementService),
):
    return await service.delete_file(current_user, file_id)


@router.delete("/trash/files/{file_id}", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def hard_delete_file(request: Request, 
    file_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: TrashService = Depends(TrashService),
):
    return await service.hard_delete_file(current_user, file_id)


@router.delete("/trash/folders/{folder_id}", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def hard_delete_folder(request: Request, 
    folder_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: TrashService = Depends(TrashService),
):
    return await service.hard_delete_folder(current_user, folder_id)


@router.delete("/trash/empty", response_model=schemas.MessageResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def empty_trash(request: Request, 
    current_user: dict = Depends(get_current_user),
    service: TrashService = Depends(TrashService),
):
    return await service.hard_delete_all_trash(current_user)


@router.post("/trash/files/{file_id}/restore", response_model=schemas.FileResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def restore_file(request: Request, 
    file_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: TrashService = Depends(TrashService),
):
    return await service.restore_file(current_user, file_id)


@router.post("/trash/folders/{folder_id}/restore", response_model=schemas.FolderResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def restore_folder(request: Request, 
    folder_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    service: TrashService = Depends(TrashService),
):
    return await service.restore_folder(current_user, folder_id)


@router.get("/trash", response_model=schemas.StorageContentResponse)
@limiter.limit("30/minute")
@map_domain_exceptions
async def get_trashed_contents(request: Request, 
    current_user: dict = Depends(get_current_user),
    service: TrashService = Depends(TrashService),
):
    return await service.get_trashed_contents(current_user)