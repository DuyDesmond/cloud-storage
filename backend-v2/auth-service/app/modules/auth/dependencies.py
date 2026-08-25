import uuid
import asyncpg
from fastapi import Depends, HTTPException, Request, status
from app.core.database import get_db_connection
from app.core.security import decode_token
from app.modules.auth.repository import AuthRepository

auth_repository = AuthRepository()

async def get_current_user(
    request: Request,
    conn: asyncpg.Connection = Depends(get_db_connection),
) -> dict:
    """FastAPI Dependency: Ensures request is authenticated via access_token cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing.",
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    try:
        user_id = uuid.UUID(str(sub))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject identifier.",
        )

    # Check Redis for token revocation based on payload['iat']
    from app.core.redis import redis_client
    if redis_client:
        revoked_ts = await redis_client.get(f"revoked:user:{user_id}")
        if revoked_ts:
            iat = payload.get("iat", 0)
            if int(revoked_ts) > iat:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked.",
                )

    import json

    # Attempt to fetch user profile from cache
    if redis_client:
        cached_profile = await redis_client.get(f"user_profile:{user_id}")
        if cached_profile:
            user = json.loads(cached_profile)
            # Reconstruct UUID fields natively
            if "id" in user:
                user["id"] = uuid.UUID(user["id"])
            return user

    user = await auth_repository.get_by_id(conn, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    # Save user to cache for subsequent requests
    if redis_client:
        cache_data = dict(user)
        # STRIP OUT SENSITIVE DATA
        cache_data.pop("hashed_password", None)
        
        # Serialize UUIDs and Datetimes for JSON storage
        for k, v in cache_data.items():
            if isinstance(v, uuid.UUID):
                cache_data[k] = str(v)
            elif hasattr(v, "isoformat"):
                cache_data[k] = v.isoformat()
                
        await redis_client.set(f"user_profile:{user_id}", json.dumps(cache_data), ex=3600)

    return user