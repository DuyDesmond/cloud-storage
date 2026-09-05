import json
import uuid
from typing import Optional
from fastapi import Depends
import redis.asyncio as redis
from app.core.redis import get_redis_client
from app.core.config import settings

class CacheRepository:
    def __init__(self, client: redis.Redis | None = Depends(get_redis_client)):
        self.client = client

    async def revoke_user_tokens(self, user_id: str, now_ts: int) -> None:
        if self.client:
            await self.client.set(
                f"revoked:user:{user_id}", 
                now_ts, 
                ex=settings.REFRESH_TOKEN_EXPIRE * 86400
            )

    async def is_user_revoked(self, user_id: uuid.UUID) -> Optional[int]:
        if self.client:
            revoked_ts = await self.client.get(f"revoked:user:{user_id}")
            if revoked_ts:
                return int(revoked_ts)
        return None

    async def publish_user_deleted(self, user_id: str) -> None:
        if self.client:
            await self.client.publish(
                "events:user_deleted", 
                json.dumps({"user_id": user_id})
            )

    async def delete_user_profile(self, user_id: str) -> None:
        if self.client:
            await self.client.delete(f"user_profile:{user_id}")

    async def get_user_profile(self, user_id: uuid.UUID) -> Optional[dict]:
        if self.client:
            cached_profile = await self.client.get(f"user_profile:{user_id}")
            if cached_profile:
                user = json.loads(cached_profile)
                if "id" in user:
                    user["id"] = uuid.UUID(user["id"])
                return user
        return None

    async def set_user_profile(self, user_id: uuid.UUID, user_data: dict) -> None:
        if self.client:
            cache_data = dict(user_data)
            cache_data.pop("hashed_password", None)
            
            for k, v in cache_data.items():
                if isinstance(v, uuid.UUID):
                    cache_data[k] = str(v)
                elif hasattr(v, "isoformat"):
                    cache_data[k] = v.isoformat()
                    
            await self.client.set(f"user_profile:{user_id}", json.dumps(cache_data), ex=3600)
