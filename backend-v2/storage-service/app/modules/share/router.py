import uuid
from fastapi import APIRouter, Depends, Request
from app.core.rate_limit import limiter
import asyncpg

from app.core.database import get_db_connection
from app.core.dependencies import get_current_user
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
    return await share_service.share_with_user(payload, current_user['id'])

@router.delete("/user", response_model=schemas.GenericMessageResponse)
@limiter.limit("30/minute")
async def revoke_user_share(
    request: Request, 
    payload: schemas.RevokeUserShareRequest,
    current_user: dict = Depends(get_current_user),
    share_service: ShareService = Depends(ShareService),
    ):
    return await share_service.revoke_user_share(payload, current_user['id'])

@router.post("/public", response_model=schemas.GenericMessageResponse)
@limiter.limit("100/minute")
async def set_public_link(
    request: Request, 
    payload: schemas.SetPublicLinkRequest,
    current_user: dict = Depends(get_current_user),
    share_service: ShareService = Depends(ShareService),
    ):
    return await share_service.set_public_link(payload, current_user['id'])

@router.get("/state", response_model=schemas.ShareStateResponse)
@limiter.limit("100/minute")
async def get_share_state(
    request: Request, 
    target_id: uuid.UUID,
    is_file: bool,
    current_user: dict = Depends(get_current_user),
    share_service: ShareService = Depends(ShareService),
    ):
    return await share_service.get_share_state(target_id, is_file, current_user['id'])

@router.post("/visit/{share_token}", response_model=schemas.VisitPublicLinkResponse)
@limiter.limit("100/minute")
async def visit_public_link(
    request: Request, 
    share_token: str,
    current_user: dict = Depends(get_current_user),
    share_service: ShareService = Depends(ShareService),
    ):
    return await share_service.visit_public_link(share_token, current_user['id'])
