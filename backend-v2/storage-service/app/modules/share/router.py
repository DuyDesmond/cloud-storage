import uuid
from fastapi import APIRouter, Depends
import asyncpg

from app.core.database import get_db_connection
from app.core.dependencies import get_current_user
from app.modules.share import schemas
from app.modules.share.service import ShareService

router = APIRouter(prefix="/share", tags=["Share"])
share_service = ShareService()

@router.post("/user", response_model=schemas.GenericMessageResponse)
async def share_with_user(
    request: schemas.ShareWithUserRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    return await share_service.share_with_user(conn, request, current_user['id'])

@router.delete("/user", response_model=schemas.GenericMessageResponse)
async def revoke_user_share(
    request: schemas.RevokeUserShareRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    return await share_service.revoke_user_share(conn, request, current_user['id'])

@router.post("/public", response_model=schemas.GenericMessageResponse)
async def set_public_link(
    request: schemas.SetPublicLinkRequest,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    return await share_service.set_public_link(conn, request, current_user['id'])

@router.get("/state", response_model=schemas.ShareStateResponse)
async def get_share_state(
    target_id: uuid.UUID,
    is_file: bool,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    return await share_service.get_share_state(conn, target_id, is_file, current_user['id'])

@router.post("/visit/{share_token}", response_model=schemas.VisitPublicLinkResponse)
async def visit_public_link(
    share_token: str,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    return await share_service.visit_public_link(conn, share_token, current_user['id'])
