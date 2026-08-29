from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg
from app.core.database import get_db_connection
from app.modules.auth.repository import AuthRepository
from app.modules.auth.cache import CacheRepository
from app.modules.auth import schemas

router = APIRouter(prefix="/internal/users", tags=["Internal"])

@router.get("/by-email")
async def get_user_by_email(
    email: str,
    repo: AuthRepository = Depends()
):
    """Internal endpoint for Storage Service to lookup user by email (e.g. for sharing)."""
    user = await repo.get_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"id": user["id"], "email": user["email"], "full_name": user["full_name"]}


@router.get("/{user_id}/storage")
async def get_user_storage(
    user_id: UUID,
    repo: AuthRepository = Depends()
):
    """Internal endpoint for Storage Service to get user's storage quota/usage."""
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"storage_used": user["storage_used"], "storage_quota": user["storage_quota"]}

from pydantic import BaseModel
class UpdateStorageRequest(BaseModel):
    storage_used: int

@router.put("/{user_id}/storage")
async def update_user_storage(
    user_id: UUID,
    payload: UpdateStorageRequest,
    repo: AuthRepository = Depends(),
    cache: CacheRepository = Depends()
):
    """Internal endpoint for Storage Service to update user's storage usage."""
    await repo.update_user_storage(user_id, payload.storage_used)
    
    await cache.delete_user_profile(str(user_id))
        
    return {"status": "ok"}
