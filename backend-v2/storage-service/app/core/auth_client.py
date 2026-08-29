import uuid
from typing import Optional, Dict, Any
import httpx
from fastapi import HTTPException, status
from app.core.config import settings

class AuthServiceClient:
    def __init__(self):
        self.base_url = settings.AUTH_SERVICE_URL

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch user details by email via internal auth service API."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/internal/users/by-email", 
                params={"email": email}
            )
            if resp.status_code == status.HTTP_404_NOT_FOUND:
                return None
            resp.raise_for_status()
            return resp.json()

    async def get_user_storage(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Fetch user storage quota and usage."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/internal/users/{user_id}/storage")
            resp.raise_for_status()
            return resp.json()

    async def update_user_storage(self, user_id: uuid.UUID, storage_used: int) -> None:
        """Update user storage usage."""
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{self.base_url}/internal/users/{user_id}/storage", 
                json={"storage_used": storage_used}
            )
            resp.raise_for_status()
