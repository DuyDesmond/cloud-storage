import uuid
from fastapi import APIRouter, Depends, Request, HTTPException, status
from app.core.rate_limit import limiter
import asyncpg

from app.core.database import get_db_connection
from app.core.dependencies import get_current_user, get_optional_current_user
from app.core.exceptions import AccessDeniedError, ItemNotFoundError, InvalidOperationError, UserNotFoundError
from app.modules.share import schemas
from app.modules.share.service import ShareService

router = APIRouter(prefix="/share", tags=["Share"])

@router.post("/user", response_model=schemas.GenericMessageResponse)
@limiter.limit("100/minute")
async def share_with_user(
    request: Request, 
    payload: schemas.ShareWithUserRequest,
    current_user: dict = Depends(get_current_user),
    share_service: ShareService = Depends(ShareService),
    ):
    try:
        return await share_service.share_with_user(payload, current_user['id'])
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (ItemNotFoundError, UserNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidOperationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/user", response_model=schemas.GenericMessageResponse)
@limiter.limit("30/minute")
async def revoke_user_share(
    request: Request, 
    payload: schemas.RevokeUserShareRequest,
    current_user: dict = Depends(get_current_user),
    share_service: ShareService = Depends(ShareService),
    ):
    try:
        return await share_service.revoke_user_share(payload, current_user['id'])
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (ItemNotFoundError, UserNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/public", response_model=schemas.GenericMessageResponse)
@limiter.limit("100/minute")
async def set_public_link(
    request: Request, 
    payload: schemas.SetPublicLinkRequest,
    current_user: dict = Depends(get_current_user),
    share_service: ShareService = Depends(ShareService),
    ):
    try:
        return await share_service.set_public_link(payload, current_user['id'])
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.get("/state", response_model=schemas.ShareStateResponse)
@limiter.limit("100/minute")
async def get_share_state(
    request: Request, 
    target_id: uuid.UUID,
    is_file: bool,
    current_user: dict = Depends(get_current_user),
    share_service: ShareService = Depends(ShareService),
    ):
    try:
        return await share_service.get_share_state(target_id, is_file, current_user['id'])
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.post("/visit/{share_token}", response_model=schemas.VisitPublicLinkResponse)
@limiter.limit("100/minute")
async def visit_public_link(
    request: Request, 
    share_token: str,
    current_user: dict | None = Depends(get_optional_current_user),
    share_service: ShareService = Depends(ShareService),
    ):
    try:
        return await share_service.visit_public_link(share_token, current_user['id'] if current_user else None)
    except ItemNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
