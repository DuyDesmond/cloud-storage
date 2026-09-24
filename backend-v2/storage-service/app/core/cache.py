import json
import uuid
from typing import Optional
from fastapi import Depends
import redis.asyncio as redis
from app.core.redis import get_redis_client

class CacheRepository:
    def __init__(self, client: redis.Redis | None = Depends(get_redis_client)):
        self.client = client

    async def get_revoked_token_ts(self, user_id: uuid.UUID) -> Optional[int]:
        if self.client:
            revoked_ts = await self.client.get(f"revoked:user:{user_id}")
            if revoked_ts:
                return int(revoked_ts)
        return None

    async def get_share_acl(self, share_token: str) -> Optional[dict]:
        if self.client:
            cached_acl = await self.client.get(f"share:acl:{share_token}")
            if cached_acl:
                return json.loads(cached_acl)
        return None

    async def set_share_acl(self, share_token: str, acl_data: dict, ttl_seconds: int = 300) -> None:
        if self.client:
            # Serialize UUIDs if any
            cache_data = {}
            for k, v in acl_data.items():
                if isinstance(v, uuid.UUID):
                    cache_data[k] = str(v)
                elif hasattr(v, "isoformat"):
                    cache_data[k] = v.isoformat()
                else:
                    cache_data[k] = v
                    
            await self.client.set(
                f"share:acl:{share_token}", 
                json.dumps(cache_data),
                ex=ttl_seconds
            )
