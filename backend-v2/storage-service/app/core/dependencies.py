import uuid
from fastapi import HTTPException, Request, status, Depends
from app.core.security import decode_token
from app.core.cache import CacheRepository
from app.core.auth_client import AuthServiceClient

async def get_current_user(
    request: Request,
    auth_client: AuthServiceClient = Depends(AuthServiceClient),
    cache: CacheRepository = Depends(CacheRepository),
) -> dict:
    """FastAPI Dependency: Stateless JWT verification."""
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

    # 4. Check Redis for Token Revocation via Cache abstraction
    revoked_ts = await cache.get_revoked_token_ts(user_id)
    if revoked_ts:
        iat = payload.get("iat", 0)
        if revoked_ts >= iat:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked.",
            )

    return {"id": user_id}
