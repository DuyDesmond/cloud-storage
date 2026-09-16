import uuid
from fastapi import Depends, HTTPException, Request, status
from app.core.security import decode_token
from app.modules.auth.repository import AuthRepository
from app.modules.auth.cache import CacheRepository

async def get_current_user(
    request: Request,
    repo: AuthRepository = Depends(AuthRepository),
    cache: CacheRepository = Depends(CacheRepository),
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

    # Check Redis for token revocation based on payload
    revoked_ts = await cache.is_user_revoked(user_id)
    if revoked_ts:
        iat = payload.get("iat", 0)
        if revoked_ts >= iat:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked.",
            )

    # Attempt to fetch user profile from cache
    user = await cache.get_user_profile(user_id)
    if user:
        return user

    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    # Save user to cache for subsequent requests
    await cache.set_user_profile(user_id, user)

    return user