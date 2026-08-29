import uuid
from typing import Optional, Dict, Any
import httpx
from fastapi import HTTPException, status
from app.core.config import settings

from urllib.parse import urlparse

class AuthServiceClient:
    def __init__(self):
        parsed = urlparse(settings.AUTH_SERVICE_URL)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

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

