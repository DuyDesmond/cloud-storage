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

